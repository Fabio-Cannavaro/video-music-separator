from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from audio_core import (
    SoundEvent,
    build_mute_filter,
    build_partition_filter,
    create_muted_preview_video,
    create_preview_proxy,
    create_preview_video,
    extract_audio,
    load_manifest,
    merge_window_detections,
    preview_proxy_is_current,
    probe_duration,
    save_manifest,
    export_video,
    run_command,
    is_music_partition,
)


class RunCommandTests(unittest.TestCase):
    @patch("audio_core.run_bounded_command")
    def test_uses_bounded_capture(self, mocked_run) -> None:
        mocked_run.return_value = subprocess.CompletedProcess(
            ["worker.exe", "--test"], 0, "", ""
        )
        run_command(["worker.exe", "--test"])
        mocked_run.assert_called_once_with(
            ["worker.exe", "--test"], timeout=4 * 60 * 60
        )

    @patch("audio_core.run_command")
    @patch("audio_core.require_work_disk_space")
    @patch("audio_core.probe_duration", return_value=1.0)
    @patch("audio_core.require_program", return_value="ffmpeg.exe")
    def test_extracts_model_input_as_44100hz_pcm16(
        self, _mocked_require, _mocked_duration, _mocked_disk, mocked_command
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "clip.mp4"
            source.write_bytes(b"video")
            extract_audio(source, Path(temp_dir) / "work" / "source.wav")
        command = mocked_command.call_args.args[0]
        self.assertIn("44100", command)
        self.assertIn("pcm_s16le", command)
        self.assertNotIn("pcm_s24le", command)

    @patch("audio_core.run_command")
    @patch("audio_core.probe_duration", return_value=1.0)
    @patch("audio_core.require_program", return_value="ffmpeg.exe")
    def test_preview_proxy_is_small_fixed_rate_h264(
        self, _mocked_require, _mocked_duration, mocked_command
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.mp4"
            source.write_bytes(b"video")
            create_preview_proxy(source, Path(temporary) / "preview.mkv")
        command = mocked_command.call_args.args[0]
        video_filter = command[command.index("-vf") + 1]
        self.assertIn(
            "scale=420:236:force_original_aspect_ratio=decrease", video_filter
        )
        self.assertIn("fps=24", video_filter)
        self.assertEqual(command[command.index("-c:v") + 1], "libx264")

    @patch("audio_core.run_command")
    @patch("audio_core.probe_duration", return_value=1.0)
    @patch("audio_core.require_program", return_value="ffmpeg.exe")
    def test_final_export_copies_video_but_muted_preview_transcodes_it(
        self, _mocked_require, _mocked_duration, mocked_command
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.mp4"
            stem = Path(temporary) / "music.wav"
            source.write_bytes(b"video")
            stem.write_bytes(b"audio")
            event = SoundEvent(
                "music", "Music", 0.0, 1.0, 1.0,
                muted=True, extracted_path=str(stem)
            )
            saved = Path(temporary) / "saved.mp4"

            def create_output(command, **_kwargs) -> None:
                Path(command[-1]).write_bytes(b"saved")

            mocked_command.side_effect = create_output
            export_video(source, saved, [event])
            final_command = mocked_command.call_args.args[0]
            self.assertIn("-y", final_command)
            self.assertEqual(final_command.count("-protocol_whitelist"), 2)
            for index, value in enumerate(final_command):
                if value == "-i":
                    self.assertEqual(final_command[index - 4], "-protocol_whitelist")
                    self.assertEqual(final_command[index - 3], "file")
                    self.assertEqual(final_command[index - 2], "-format_whitelist")
            self.assertEqual(
                final_command[final_command.index("-c:v") + 1], "copy"
            )
            self.assertEqual(saved.read_bytes(), b"saved")
            self.assertEqual(list(saved.parent.glob(".*.tmp.mp4")), [])

            mocked_command.side_effect = None
            create_muted_preview_video(source, Path(temporary) / "preview.mkv", [event])
            preview_command = mocked_command.call_args.args[0]
            self.assertIn("-y", preview_command)
            self.assertEqual(
                preview_command[preview_command.index("-c:v") + 1], "libx264"
            )

    def test_preview_cache_requires_nonempty_proxy_newer_than_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.mp4"
            proxy = root / "preview.mkv"
            source.write_bytes(b"source")
            proxy.write_bytes(b"proxy")
            os.utime(source, ns=(2_000_000_000, 2_000_000_000))
            os.utime(proxy, ns=(3_000_000_000, 3_000_000_000))
            self.assertTrue(preview_proxy_is_current(source, proxy))
            os.utime(source, ns=(4_000_000_000, 4_000_000_000))
            self.assertFalse(preview_proxy_is_current(source, proxy))


class MergeDetectionTests(unittest.TestCase):
    def test_merges_adjacent_same_label_and_keeps_best_score(self) -> None:
        events = merge_window_detections(
            [
                ("발자국", 0.0, 1.0, 0.61),
                ("발자국", 0.8, 1.8, 0.82),
                ("새 울음", 0.2, 0.6, 0.72),
                ("발자국", 3.0, 3.5, 0.70),
            ],
            max_gap=0.2,
        )
        self.assertEqual([(event.label, event.start, event.end) for event in events], [
            ("발자국", 0.0, 1.8),
            ("새 울음", 0.2, 0.6),
            ("발자국", 3.0, 3.5),
        ])
        self.assertEqual(events[0].score, 0.82)

    def test_discards_invalid_spans(self) -> None:
        events = merge_window_detections(
            [("", 0, 1, 0.9), ("충격음", 2, 1, 0.9), ("충격음", 1, 1.1, 0.9)],
            minimum_duration=0.15,
        )
        self.assertEqual(events, [])


class ManifestTests(unittest.TestCase):
    def test_round_trip_preserves_query_and_mute(self) -> None:
        event = SoundEvent("sound-0001", "발자국 (Footsteps)", 1.2, 2.4, 0.8, query="Footsteps", muted=True)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sounds.json"
            clip = Path(temporary) / "clip.mp4"
            clip.write_bytes(b"video")
            save_manifest(path, clip, [event])
            video, loaded = load_manifest(path)
        self.assertEqual(video, clip.resolve())
        self.assertEqual(loaded, [event])

    def test_loads_older_manifest_without_query(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sounds.json"
            clip = Path(temporary) / "clip.mp4"
            clip.write_bytes(b"video")
            path.write_text(json.dumps({
                "version": 1,
                "video_path": str(clip),
                "events": [{
                    "event_id": "sound-0001",
                    "label": "Wind",
                    "start": 0.0,
                    "end": 1.0,
                    "score": 0.5,
                    "muted": False,
                    "extracted_path": "",
                    "extraction_start": 0.0,
                }],
            }), encoding="utf-8")
            _, loaded = load_manifest(path)
        self.assertEqual(loaded[0].query, "Wind")


class MuteFilterTests(unittest.TestCase):
    def test_no_muted_stems_keeps_original_audio(self) -> None:
        graph, label = build_mute_filter([])
        self.assertEqual(graph, "[0:a]apad[aout]")
        self.assertEqual(label, "[aout]")

    def test_muted_stem_is_inverted_and_delayed(self) -> None:
        event = SoundEvent(
            "sound-0001",
            "Footsteps",
            1.0,
            2.0,
            0.9,
            query="Footsteps",
            muted=True,
            extracted_path="footsteps.wav",
            extraction_start=0.75,
        )
        graph, _ = build_mute_filter([event])
        self.assertIn("volume=-1", graph)
        self.assertIn("adelay=750|750", graph)
        self.assertIn("amix=inputs=2", graph)
        self.assertIn("apad[aout]", graph)

    def test_music_partition_uses_kept_stem_directly(self) -> None:
        events = [
            SoundEvent("music", "음악", 0.0, 5.0, 1.0, muted=True, extracted_path="music.wav"),
            SoundEvent("non-music", "음악 아님", 0.0, 5.0, 1.0, extracted_path="non-music.wav"),
        ]
        self.assertTrue(is_music_partition(events))
        graph, label = build_partition_filter(events)
        self.assertEqual(label, "[aout]")
        self.assertIn("[2:a]aresample=48000", graph)
        self.assertNotIn("[1:a]", graph)
        self.assertIn("apad[aout]", graph)

    def test_muting_both_partition_stems_creates_silence(self) -> None:
        events = [
            SoundEvent("music", "음악", 0.0, 5.0, 1.0, muted=True, extracted_path="music.wav"),
            SoundEvent("non-music", "음악 아님", 0.0, 5.0, 1.0, muted=True, extracted_path="non-music.wav"),
        ]
        graph, _ = build_partition_filter(events)
        self.assertEqual(graph, "[0:a]volume=0,apad[aout]")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg 필요")
class FfmpegIntegrationTests(unittest.TestCase):
    def test_local_playlist_cannot_open_remote_segment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            playlist = Path(temporary) / "remote.m3u8"
            playlist.write_text(
                "#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXTINF:1,\n"
                "https://example.invalid/segment.ts\n#EXT-X-ENDLIST\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                probe_duration(playlist)

    def test_exports_video_with_one_muted_event(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.mp4"
            stem = root / "stem.wav"
            output = root / "output.mp4"
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=160x90:d=2",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1.5",
                "-c:v", "mpeg4", "-q:v", "5", "-pix_fmt", "yuv420p", "-c:a", "aac",
                str(source),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([
                "ffmpeg", "-y", "-ss", "0.25", "-t", "1.5", "-i", str(source),
                "-vn", "-ar", "48000", "-c:a", "pcm_s24le", str(stem),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            preview = root / "preview.mkv"
            create_preview_video(source, stem, preview)
            preview_probe = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "stream=codec_type,width,height,avg_frame_rate",
                "-of", "csv=p=0", str(preview),
            ], check=True, capture_output=True, text=True)
            self.assertIn("video", preview_probe.stdout)
            self.assertIn("420", preview_probe.stdout)
            self.assertIn("236", preview_probe.stdout)
            self.assertIn("24/1", preview_probe.stdout)
            self.assertIn("audio", preview_probe.stdout)
            event = SoundEvent(
                "sound-0001", "Tone", 0.5, 1.5, 1.0,
                query="tone", muted=True, extracted_path=str(stem),
                extraction_start=0.25, extracted_duration=1.5,
            )
            export_video(source, output, [event])
            self.assertTrue(output.exists())
            original_bytes = output.read_bytes()
            with self.assertRaises(FileExistsError):
                export_video(source, output, [event])
            self.assertEqual(output.read_bytes(), original_bytes)
            probe = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                "-of", "csv=p=0", str(output),
            ], check=True, capture_output=True, text=True)
            self.assertIn("video", probe.stdout)
            self.assertIn("audio", probe.stdout)
            codec_probe = subprocess.run([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_name", "-of", "csv=p=0",
                str(output),
            ], check=True, capture_output=True, text=True)
            self.assertEqual(codec_probe.stdout.strip(), "mpeg4")
            source_frames = subprocess.run([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=nb_frames", "-of", "csv=p=0",
                str(source),
            ], check=True, capture_output=True, text=True)
            output_frames = subprocess.run([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=nb_frames", "-of", "csv=p=0",
                str(output),
            ], check=True, capture_output=True, text=True)
            self.assertEqual(output_frames.stdout.strip(), source_frames.stdout.strip())


if __name__ == "__main__":
    unittest.main()
