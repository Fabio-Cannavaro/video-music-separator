from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from audiosep_worker import load_jobs
from avcass_worker import (
    DEFAULT_BLEND_MODE,
    DEFAULT_OVERLAP_SAMPLES,
    DEFAULT_OVERLAP_SECONDS,
    INFERENCE_HOP,
    INFERENCE_LENGTH,
    configure_yapf_cache,
    inference_starts,
    init_cavp_with_restricted_checkpoint,
    load_avcass_ema_state,
)

from sound_separator_app import (
    CREATOR_LINE_INDENT,
    CREATOR_YOUTUBE_URL,
    DEFAULT_MODEL_ID,
    DEFAULT_VOLUME,
    TRANSLATIONS,
    VISIBLE_MODEL_IDS,
    SoundSeparatorApp,
    available_output_path,
    assess_partition_metrics,
    avcass_runtime_paths,
    audiosep_result_key,
    audiosep_runtime_paths,
    bandit_runtime_paths,
    build_ffplay_command,
    build_partition_events,
    clamp_volume,
    cleanup_work_directory,
    load_legal_information,
    load_legal_display,
    load_license_texts,
    model_result_directory,
    muted_copy_output_path,
    muted_mix_preview_path,
    next_preview_delay_ms,
    normalized_preview_fps,
    open_creator_youtube_channel,
    original_preview_path,
    format_playback_time,
    playback_position,
    preview_path_for_event,
    replace_latest,
    run_worker_command,
    terminate_preview_process,
    worker_progress_message,
)


class PlaybackCommandTests(unittest.TestCase):
    def test_waits_for_previous_player_to_exit_before_restarting(self) -> None:
        class Process:
            def __init__(self) -> None:
                self.terminated = False
                self.wait_timeouts: list[float] = []

            def poll(self):
                return None

            def terminate(self) -> None:
                self.terminated = True

            def wait(self, timeout: float):
                self.wait_timeouts.append(timeout)
                return 0

            def kill(self) -> None:
                raise AssertionError("정상 종료된 프로세스를 강제 종료하면 안 됩니다.")

        process = Process()
        terminate_preview_process(process)
        self.assertTrue(process.terminated)
        self.assertEqual(process.wait_timeouts, [0.5])

    def test_force_kills_a_preview_player_that_does_not_terminate(self) -> None:
        class Process:
            def __init__(self) -> None:
                self.killed = False
                self.wait_count = 0

            def poll(self):
                return None

            def terminate(self) -> None:
                pass

            def wait(self, timeout: float):
                self.wait_count += 1
                if self.wait_count == 1:
                    raise subprocess.TimeoutExpired("ffplay", timeout)
                return 0

            def kill(self) -> None:
                self.killed = True

        process = Process()
        terminate_preview_process(process)
        self.assertTrue(process.killed)
        self.assertEqual(process.wait_count, 2)

    def test_stale_video_callback_cannot_touch_a_restarted_player(self) -> None:
        app = SimpleNamespace(
            playback_generation=8,
            video_poll_after_id="old-callback",
            _player_is_running=lambda: (_ for _ in ()).throw(
                AssertionError("이전 재생 콜백이 새 플레이어를 건드렸습니다.")
            ),
        )
        SoundSeparatorApp._poll_video_frame(app, generation=7)
        self.assertIsNone(app.video_poll_after_id)

    def test_stale_player_callback_cannot_stop_a_restarted_player(self) -> None:
        app = SimpleNamespace(
            playback_generation=8,
            player_poll_after_id="old-callback",
            _player_is_running=lambda: (_ for _ in ()).throw(
                AssertionError("이전 재생 콜백이 새 플레이어를 건드렸습니다.")
            ),
        )
        SoundSeparatorApp._poll_player(app, generation=7)
        self.assertIsNone(app.player_poll_after_id)

    def test_streams_worker_output_for_live_progress(self) -> None:
        lines: list[str] = []
        run_worker_command(
            [sys.executable, "-c", "print('[run 1/2] 0.00-8.00초')"],
            lines.append,
        )
        self.assertEqual(lines, ["[run 1/2] 0.00-8.00초"])

    def test_starts_at_full_volume(self) -> None:
        self.assertEqual(DEFAULT_VOLUME, 100)

    def test_clamps_volume_to_ffplay_range(self) -> None:
        self.assertEqual(clamp_volume(-5), 0)
        self.assertEqual(clamp_volume(52.6), 53)
        self.assertEqual(clamp_volume(140), 100)

    @patch("sound_separator_app.require_program", return_value="ffplay.exe")
    def test_builds_shared_volume_command_and_keeps_offset(self, _require_program) -> None:
        command = build_ffplay_command(Path("stem.wav"), 63, 4.25)
        self.assertEqual(command[0], "ffplay.exe")
        self.assertIn("-nodisp", command)
        self.assertIn("-vn", command)
        self.assertIn("-sn", command)
        self.assertNotIn("-sync", command)
        self.assertEqual(command[command.index("-volume") + 1], "63")
        self.assertIn("-ss", command)
        self.assertIn("4.250", command)
        self.assertEqual(command[-1], "stem.wav")

    def test_formats_short_and_long_playback_times(self) -> None:
        self.assertEqual(format_playback_time(65.2), "01:05")
        self.assertEqual(format_playback_time(3661), "01:01:01")

    def test_playback_position_uses_one_clock_and_clamps_to_duration(self) -> None:
        self.assertAlmostEqual(playback_position(12.5, 100.0, 103.25, 30.0), 15.75)
        self.assertEqual(playback_position(12.5, 100.0, 200.0, 30.0), 30.0)

    def test_preview_timing_uses_source_fps_and_fixed_deadlines(self) -> None:
        self.assertEqual(normalized_preview_fps(24.0), 24.0)
        self.assertEqual(normalized_preview_fps(0.0), 30.0)
        self.assertEqual(next_preview_delay_ms(100.0, 100.0, 24.0), 42)
        self.assertEqual(next_preview_delay_ms(100.0, 100.050, 24.0), 33)

    def test_late_decoded_frames_are_replaced_by_the_newest_frame(self) -> None:
        frames = queue.Queue(maxsize=1)
        replace_latest(frames, (1.0, "old"))
        replace_latest(frames, (2.0, "new"))
        self.assertEqual(frames.get_nowait(), (2.0, "new"))

    @patch("sound_separator_app.time.monotonic", return_value=100.1)
    def test_video_poll_uses_background_decoder_latest_frame(self, _monotonic) -> None:
        displayed: list[object] = []

        class Decoder:
            def __init__(self) -> None:
                self.targets: list[float] = []

            def request(self, target: float) -> None:
                self.targets.append(target)

            def pop_latest(self):
                return 0.1, "newest-frame"

        decoder = Decoder()
        app = SimpleNamespace(
            playback_generation=3,
            video_poll_after_id="callback",
            _player_is_running=lambda: True,
            player_offset=0.0,
            player_started_at=100.0,
            player_duration=10.0,
            seek_dragging=False,
            video_decoder=decoder,
            video_position=0.0,
            _display_video_frame=displayed.append,
            _set_preview_position=lambda _position: None,
            after=lambda _delay, _callback: "next-callback",
            preview_fps=24.0,
        )
        SoundSeparatorApp._poll_video_frame(app, generation=3)
        self.assertAlmostEqual(decoder.targets[0], 0.1)
        self.assertEqual(displayed, ["newest-frame"])
        self.assertEqual(app.video_poll_after_id, "next-callback")


class MusicPartitionTests(unittest.TestCase):
    def test_loads_avcass_checkpoint_in_weights_only_mode(self) -> None:
        safe_globals_calls: list[list[object]] = []
        load_calls: list[tuple[Path, dict[str, object]]] = []

        class SafeGlobalsContext:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

        def safe_globals(values):
            safe_globals_calls.append(values)
            return SafeGlobalsContext()

        def load(path, **kwargs):
            load_calls.append((path, kwargs))
            return {"ema": {"weight": "tensor"}}

        torch_module = SimpleNamespace(
            load=load,
            serialization=SimpleNamespace(safe_globals=safe_globals),
        )
        checkpoint = Path("avcass.pt")

        state = load_avcass_ema_state(checkpoint, torch_module)

        self.assertEqual(state, {"weight": "tensor"})
        self.assertEqual(
            load_calls,
            [(checkpoint, {"map_location": "cpu", "weights_only": True})],
        )
        self.assertIn(argparse.Namespace, safe_globals_calls[0])

    def test_restricts_cavp_checkpoint_load_and_restores_torch(self) -> None:
        safe_globals_calls: list[list[object]] = []
        load_calls: list[dict[str, object]] = []

        class SafeGlobalsContext:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

        class FakeDtype:
            def __init__(self, value):
                self.value = value

        def safe_globals(values):
            safe_globals_calls.append(values)
            return SafeGlobalsContext()

        def original_load(*args, **kwargs):
            load_calls.append(kwargs)
            return {"state_dict": {}}

        torch_module = SimpleNamespace(
            load=original_load,
            serialization=SimpleNamespace(safe_globals=safe_globals),
        )
        numpy_module = SimpleNamespace(
            dtype=FakeDtype,
            float64=object(),
            core=SimpleNamespace(
                multiarray=SimpleNamespace(scalar=object()),
            ),
        )

        def init_visual_encoder(model_name):
            self.assertEqual(model_name, "cavp")
            torch_module.load("cavp.pth", weights_only=False)
            return "image-model", "metadata"

        result = init_cavp_with_restricted_checkpoint(
            init_visual_encoder,
            torch_module,
            numpy_module,
        )

        self.assertEqual(result, ("image-model", "metadata"))
        self.assertEqual(load_calls, [{"weights_only": True}])
        self.assertEqual(len(safe_globals_calls[0]), 3)
        self.assertIs(torch_module.load, original_load)

    def test_restores_torch_load_when_cavp_initialization_fails(self) -> None:
        class SafeGlobalsContext:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

        def original_load(*args, **kwargs):
            return None

        torch_module = SimpleNamespace(
            load=original_load,
            serialization=SimpleNamespace(
                safe_globals=lambda values: SafeGlobalsContext()
            ),
        )
        numpy_module = SimpleNamespace(
            dtype=lambda value: value,
            float64=object(),
            core=SimpleNamespace(
                multiarray=SimpleNamespace(scalar=object()),
            ),
        )

        def failing_init(model_name):
            raise RuntimeError("CAVP load failed")

        with self.assertRaisesRegex(RuntimeError, "CAVP load failed"):
            init_cavp_with_restricted_checkpoint(
                failing_init,
                torch_module,
                numpy_module,
            )
        self.assertIs(torch_module.load, original_load)

    def test_korean_and_english_translation_tables_have_matching_keys(self) -> None:
        self.assertEqual(set(TRANSLATIONS["ko"]), set(TRANSLATIONS["en"]))

    def test_app_information_labels_are_clear_in_both_languages(self) -> None:
        self.assertEqual(TRANSLATIONS["ko"]["licenses_sources"], "앱 정보·라이선스")
        self.assertEqual(TRANSLATIONS["ko"]["legal_title"], "앱 정보·라이선스·출처")
        self.assertEqual(TRANSLATIONS["en"]["licenses_sources"], "App Info & Licenses")
        self.assertEqual(
            TRANSLATIONS["en"]["legal_title"],
            "App Information, Licenses & Sources",
        )

    def test_non_music_labels_do_not_claim_unverified_voice_preservation(self) -> None:
        self.assertEqual(TRANSLATIONS["ko"]["event_non_music"], "음악 아님")
        self.assertEqual(TRANSLATIONS["en"]["event_non_music"], "Non-Music")

    def test_video_opened_status_uses_generic_music_separation_wording(self) -> None:
        self.assertEqual(
            TRANSLATIONS["ko"]["status_video_opened"],
            "영상을 열었습니다. 음악 분리를 실행해 주세요.",
        )
        self.assertEqual(
            TRANSLATIONS["en"]["status_video_opened"],
            "Video opened. Run music separation.",
        )

    @patch("sound_separator_app.webbrowser.open_new_tab")
    def test_creator_link_opens_ms_0606_youtube_channel(self, mocked_open) -> None:
        open_creator_youtube_channel()
        mocked_open.assert_called_once_with(CREATOR_YOUTUBE_URL)
        self.assertEqual(CREATOR_YOUTUBE_URL, "https://www.youtube.com/@ms-0606")

    def test_creator_line_aligns_with_license_button_outer_edge(self) -> None:
        self.assertEqual(CREATOR_LINE_INDENT, 0)

    def test_maps_worker_output_to_visible_progress_messages(self) -> None:
        self.assertEqual(
            worker_progress_message("avcass", "[run 2/4] 8.16-16.34초"),
            "구간 2/4 분리 중…",
        )
        self.assertIsNone(worker_progress_message("avcass", "일반 경고 메시지"))

    def test_maps_worker_output_to_english_progress_messages(self) -> None:
        self.assertEqual(
            worker_progress_message(
                "avcass", "[run 2/4] 8.16-16.34초", language="en"
            ),
            "Separating segment 2/4…",
        )

    def test_blue_status_messages_do_not_show_avcass_name(self) -> None:
        status_keys = (
            "status_loaded_existing",
            "status_model_selected",
            "status_model_selected_short",
            "status_prepare_audio",
            "status_prepare_separation",
            "status_separating",
            "status_separation_started",
            "status_separation_complete",
            "progress_video_frames",
            "progress_model_loading",
            "progress_visual_model_loading",
            "progress_segment",
            "progress_finalize",
            "progress_check_results",
            "progress_create_preview",
        )
        for language in ("ko", "en"):
            for key in status_keys:
                with self.subTest(language=language, key=key):
                    self.assertNotIn("AV-CASS", TRANSLATIONS[language][key])
                    self.assertNotIn("{model}", TRANSLATIONS[language][key])

    def test_uses_avcass_as_the_default_model(self) -> None:
        self.assertEqual(DEFAULT_MODEL_ID, "avcass")

    def test_keeps_only_avcass_as_the_visible_model(self) -> None:
        self.assertEqual(VISIBLE_MODEL_IDS, ("avcass",))

    def test_audiosep_batch_jobs_resolve_outputs_before_worker_changes_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            jobs_path = root / "jobs.json"
            jobs_path.write_text(
                json.dumps(
                    [
                        {
                            "query": "background music",
                            "music_output": str(root / "music.wav"),
                            "non_music_output": str(root / "non-music.wav"),
                        }
                    ]
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                jobs_json=str(jobs_path),
                query="music",
                music_output=None,
                non_music_output=None,
            )
            jobs = load_jobs(args)
            self.assertEqual(jobs[0]["query"], "background music")
            self.assertEqual(Path(jobs[0]["music_output"]), (root / "music.wav").resolve())

    def test_builds_exactly_music_and_non_music_rows(self) -> None:
        events = build_partition_events(
            5.25,
            Path("stems") / "music.wav",
            Path("stems") / "non-music.wav",
        )
        self.assertEqual([event.event_id for event in events], ["music", "non-music"])
        self.assertEqual([event.query for event in events], ["music", "non-music"])
        self.assertEqual([event.label for event in events], ["음악 (BGM)", "음악 아님"])
        self.assertTrue(all(event.extraction_quality == "ok" for event in events))
        self.assertTrue(all(event.extracted_duration == 5.25 for event in events))

    def test_preserves_selected_audiosep_query_in_music_event(self) -> None:
        events = build_partition_events(5.0, music_query="cinematic score")
        self.assertEqual(events[0].query, "cinematic score")
        self.assertEqual(events[1].query, "non-music")

    def test_flags_source_like_music_and_silent_non_music(self) -> None:
        quality, note = assess_partition_metrics(
            {
                "music_source_correlation": 1.0,
                "non_music_rms_ratio": 0.00001,
                "reconstruction_source_correlation": 1.0,
            }
        )
        self.assertEqual(quality, "review")
        self.assertIn("분리가 실패", note)

    def test_accepts_balanced_partition_metrics(self) -> None:
        quality, note = assess_partition_metrics(
            {
                "music_source_correlation": 0.51,
                "non_music_rms_ratio": 0.86,
                "reconstruction_source_correlation": 0.9999,
            }
        )
        self.assertEqual((quality, note), ("ok", ""))

    def test_derives_preview_and_word_based_copy_names(self) -> None:
        events = build_partition_events(
            5.0,
            Path("stems") / "music.wav",
            Path("stems") / "non-music.wav",
        )
        self.assertEqual(
            preview_path_for_event(Path("work"), events[0]),
            Path("work") / "previews" / "music_preview.mkv",
        )
        self.assertEqual(
            muted_mix_preview_path(Path("work")),
            Path("work") / "previews" / "muted_mix_preview.mkv",
        )
        self.assertEqual(
            original_preview_path(Path("work")),
            Path("work") / "previews" / "original_preview.mkv",
        )
        events[0].muted = True
        self.assertEqual(
            muted_copy_output_path(Path("folder") / "clip.mov", events),
            Path("folder") / "clip_음악제거.mp4",
        )
        events[0].muted = False
        events[1].muted = True
        self.assertEqual(
            muted_copy_output_path(Path("folder") / "clip.mov", events),
            Path("folder") / "clip_음악만.mp4",
        )

    def test_preserves_existing_saved_copies_with_numbered_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preferred = root / "clip_음악제거.mp4"
            preferred.write_bytes(b"first")
            (root / "clip_음악제거_2.mp4").write_bytes(b"second")
            self.assertEqual(
                available_output_path(preferred),
                root / "clip_음악제거_3.mp4",
            )

    def test_keeps_each_model_result_in_a_separate_cache(self) -> None:
        work_dir = Path("folder") / "clip_sound_work"
        self.assertEqual(
            model_result_directory(work_dir, "avcass"),
            work_dir / "models" / "avcass",
        )
        self.assertEqual(
            model_result_directory(work_dir, "bandit"),
            work_dir / "models" / "bandit",
        )
        self.assertEqual(
            model_result_directory(work_dir, "audiosep"),
            work_dir / "models" / "audiosep",
        )
        self.assertEqual(audiosep_result_key("music"), "audiosep")
        self.assertEqual(audiosep_result_key("cinematic"), "audiosep-cinematic")
        self.assertEqual(
            model_result_directory(work_dir, "audiosep-cinematic"),
            work_dir / "models" / "audiosep-cinematic",
        )
        with self.assertRaises(ValueError):
            audiosep_result_key("../outside")
        with self.assertRaises(ValueError):
            model_result_directory(work_dir, "unknown")

    def test_builds_portable_bandit_runtime_paths(self) -> None:
        runtime = Path("portable") / "audiosep"
        python_path, repo, hparams, checkpoint = bandit_runtime_paths(runtime)
        self.assertEqual(python_path, runtime / "env" / "python.exe")
        self.assertEqual(repo, runtime / "bandit" / "repo")
        self.assertEqual(hparams, runtime / "bandit" / "hparams.yaml")
        self.assertEqual(
            checkpoint,
            runtime / "bandit" / "model" / "dnr-3s-mus64-l1snr-plus.ckpt",
        )

    def test_builds_portable_audiosep_runtime_paths(self) -> None:
        runtime = Path("portable") / "audiosep"
        python_path, repo, checkpoint, runtime_root = audiosep_runtime_paths(runtime)
        self.assertEqual(python_path, runtime / "env" / "python.exe")
        self.assertEqual(repo, runtime / "audiosep" / "repo")
        self.assertEqual(
            checkpoint,
            runtime / "audiosep" / "model" / "pytorch_model.bin",
        )
        self.assertEqual(runtime_root, runtime / "audiosep")

    def test_builds_portable_avcass_runtime_paths(self) -> None:
        runtime = Path("portable") / "audiosep"
        python_path, repo, deps, checkpoint, cavp_checkpoint, runtime_root = (
            avcass_runtime_paths(runtime)
        )
        self.assertEqual(python_path, runtime / "env" / "python.exe")
        self.assertEqual(repo, runtime / "avcass" / "repo")
        self.assertEqual(deps, runtime / "avcass" / "deps")
        self.assertEqual(
            checkpoint,
            runtime / "avcass" / "model" / "av_cass_checkpoint.pt",
        )
        self.assertEqual(
            cavp_checkpoint,
            runtime / "avcass" / "model" / "cavp" / "cavp_epoch66.ckpt",
        )
        self.assertEqual(runtime_root, runtime / "avcass")

    def test_avcass_chunk_starts_cover_short_and_long_audio(self) -> None:
        self.assertEqual(inference_starts(INFERENCE_LENGTH), [0])
        long_length = INFERENCE_LENGTH + INFERENCE_HOP + 1234
        starts = inference_starts(long_length)
        self.assertEqual(starts[0], 0)
        self.assertEqual(starts[-1], long_length - INFERENCE_LENGTH)
        self.assertGreaterEqual(len(starts), 2)

    def test_avcass_defaults_to_one_second_cosine_ola(self) -> None:
        self.assertEqual(DEFAULT_OVERLAP_SECONDS, 1.0)
        self.assertEqual(DEFAULT_OVERLAP_SAMPLES, 16000)
        self.assertEqual(DEFAULT_BLEND_MODE, "cosine")

    def test_avcass_chunk_starts_accept_explicit_overlap(self) -> None:
        overlap = DEFAULT_OVERLAP_SAMPLES
        audio_length = INFERENCE_LENGTH * 3
        starts = inference_starts(audio_length, overlap)
        self.assertEqual(starts[1], INFERENCE_LENGTH - overlap)
        self.assertEqual(starts[-1], audio_length - INFERENCE_LENGTH)

    def test_avcass_chunk_starts_reject_invalid_overlap(self) -> None:
        with self.assertRaises(ValueError):
            inference_starts(INFERENCE_LENGTH * 2, INFERENCE_LENGTH)

    def test_avcass_yapf_cache_uses_writable_temp_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch("avcass_worker.tempfile.gettempdir", return_value=temporary):
                cache_dir = configure_yapf_cache()
            self.assertEqual(
                cache_dir, Path(temporary) / "video-music-separator-yapf"
            )
            self.assertTrue(cache_dir.is_dir())
            self.assertEqual(os.environ["YAPF_CACHE_DIR"], str(cache_dir))

    def test_loads_user_responsibility_and_third_party_notices(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "licenses").mkdir()
            (root / "THIRD_PARTY_NOTICES.md").write_text(
                "AV-CASS and CAVP sources", encoding="utf-8"
            )
            (root / "FFMPEG_BUILD.md").write_text(
                "FFmpeg GPL Essentials build", encoding="utf-8"
            )
            (root / "THIRD_PARTY_NOTICES.en.md").write_text(
                "English AV-CASS and CAVP sources", encoding="utf-8"
            )
            (root / "FFMPEG_BUILD.en.md").write_text(
                "English FFmpeg GPL Essentials build", encoding="utf-8"
            )
            (root / "PRIVACY.md").write_text(
                "영상과 음원은 로컬 PC에서 처리", encoding="utf-8"
            )
            (root / "PRIVACY.en.md").write_text(
                "Video and audio are processed locally", encoding="utf-8"
            )
            (root / "COPYRIGHT.md").write_text(
                "Copyright © 2026 @ms-0606 (GitHub: Fabio-Cannavaro)",
                encoding="utf-8",
            )
            (root / "COPYRIGHT.en.md").write_text(
                "English copyright notice for @ms-0606", encoding="utf-8"
            )
            (root / "LICENSE").write_text("app license", encoding="utf-8")
            (root / "licenses" / "MIT.txt").write_text("MIT", encoding="utf-8")
            (root / "licenses" / "Apache-2.0.txt").write_text(
                "Apache", encoding="utf-8"
            )
            (root / "licenses" / "LGPL-3.0.txt").write_text("LGPL", encoding="utf-8")
            (root / "licenses" / "GPL-3.0.txt").write_text("GPL", encoding="utf-8")
            (root / "runtime-assets.json").write_text(
                json.dumps(
                    {
                        "installed_at": "2026-09-04T00:00:00+00:00",
                        "ffmpeg_version": "ffmpeg version 9.0.1-test",
                        "ffmpeg": {"sha256": "f" * 64},
                    }
                ),
                encoding="utf-8",
            )

            information = load_legal_information(root)
            english_information = load_legal_information(root, language="en")
            license_texts = load_license_texts(root)
            english_license_texts = load_license_texts(root, language="en")
            combined_display = load_legal_display(root)
            (root / "runtime-assets.json").unlink()
            no_record_information = load_legal_information(root)

        self.assertIn("저작권과 이용 권리", information)
        self.assertIn("AV-CASS and CAVP sources", information)
        self.assertIn("FFmpeg GPL Essentials build", information)
        self.assertNotIn("app license", information)
        self.assertIn("공식 라이선스 원문(영문)", license_texts)
        self.assertIn("저작권과 이용 권리", combined_display)
        self.assertIn("공식 라이선스 원문(영문)", combined_display)
        self.assertIn("app license", combined_display)
        self.assertIn("app license", license_texts)
        self.assertIn("MIT", license_texts)
        self.assertIn("Apache", license_texts)
        self.assertIn("LGPL", license_texts)
        self.assertIn("GPL", license_texts)
        self.assertIn("Video Music Separator: 0.2.2", information)
        self.assertIn("66a8a3b9de317d2c508edae6bbd2d727", information)
        self.assertIn("ffmpeg version 9.0.1-test", information)
        self.assertIn("f" * 64, information)
        self.assertIn("2026-09-04T00:00:00+00:00", information)
        self.assertIn("영상과 음원은 로컬 PC에서 처리", information)
        self.assertIn("AI Python 실행환경", information)
        self.assertIn("출처:", information)
        self.assertIn("설치 중 Gyan 공식 체크섬에서 확인", no_record_information)
        self.assertNotIn(
            "Resolved from Gyan's official checksum during installation",
            no_record_information,
        )
        self.assertIn(
            "Copyright © 2026 @ms-0606 (GitHub: Fabio-Cannavaro)", information
        )
        self.assertIn("Video and audio are processed locally", english_information)
        self.assertIn("English copyright notice for @ms-0606", english_information)
        self.assertIn("User Content Notice", english_information)
        self.assertIn("You are responsible", english_information)
        self.assertIn("Third-Party Notices, Sources & Papers", english_information)
        self.assertIn("English AV-CASS and CAVP sources", english_information)
        self.assertIn("English FFmpeg GPL Essentials build", english_information)
        self.assertIn("official license terms", english_license_texts)
        self.assertIn("app license", english_license_texts)


class WorkDirectoryCleanupTests(unittest.TestCase):
    def test_removes_only_the_expected_clip_work_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video_path = root / "clip.mp4"
            work_dir = root / "clip_sound_work"
            work_dir.mkdir()
            (work_dir / "sounds.json").write_text("{}", encoding="utf-8")

            self.assertTrue(cleanup_work_directory(video_path, work_dir))
            self.assertFalse(work_dir.exists())

    def test_rejects_a_different_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video_path = root / "clip.mp4"
            other_dir = root / "other_sound_work"
            other_dir.mkdir()

            with self.assertRaises(RuntimeError):
                cleanup_work_directory(video_path, other_dir)
            self.assertTrue(other_dir.exists())


if __name__ == "__main__":
    unittest.main()
