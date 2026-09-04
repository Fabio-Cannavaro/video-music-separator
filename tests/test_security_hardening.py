from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import runtime_integrity
from audio_core import MAX_COMMAND_OUTPUT_BYTES, require_program, run_command
from security_policy import (
    MAX_MEDIA_DURATION_SECONDS,
    ffmpeg_file_input,
    require_local_media_file,
    require_work_disk_space,
    validate_media_duration,
    validate_media_streams,
)


class LocalMediaBoundaryTests(unittest.TestCase):
    def test_accepts_existing_local_file_and_builds_file_only_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            media = Path(temporary) / "clip with space.mp4"
            media.write_bytes(b"video")
            self.assertEqual(require_local_media_file(media), media.resolve())
            self.assertEqual(
                ffmpeg_file_input(media),
                [
                    "-protocol_whitelist",
                    "file",
                    "-format_whitelist",
                    "mov,mp4,m4a,3gp,3g2,mj2",
                    "-i",
                    str(media.resolve()),
                ],
            )

    def test_rejects_protocol_like_and_missing_inputs_before_subprocess(self) -> None:
        for value in ("https://example.invalid/video.mp4", "concat:a.mp4|b.mp4", "data:text/plain,x"):
            with self.subTest(value=value), self.assertRaises(FileNotFoundError):
                require_local_media_file(value)

    def test_rejects_unc_path_before_file_access(self) -> None:
        with self.assertRaisesRegex(ValueError, "로컬 고정 디스크"):
            require_local_media_file(r"\\server\share\clip.mp4")

    def test_rejects_playlist_format_before_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            playlist = Path(temporary) / "local.m3u8"
            playlist.write_text("#EXTM3U\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "지원하지 않는"):
                ffmpeg_file_input(playlist)


class ResourcePolicyTests(unittest.TestCase):
    def test_rejects_invalid_and_over_limit_duration(self) -> None:
        for value in (0.0, -1.0, float("nan"), float("inf"), MAX_MEDIA_DURATION_SECONDS + 0.1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_media_duration(value)

    def test_rejects_insufficient_work_disk_before_processing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            media = Path(temporary) / "clip.mp4"
            media.write_bytes(b"video")
            usage = type("Usage", (), {"free": 1})()
            with patch("security_policy.shutil.disk_usage", return_value=usage):
                with self.assertRaisesRegex(RuntimeError, "작업 공간"):
                    require_work_disk_space(media, Path(temporary), 10.0)

    def test_rejects_oversized_video_and_audio_streams(self) -> None:
        with self.assertRaisesRegex(ValueError, "해상도"):
            validate_media_streams(
                [{"codec_type": "video", "width": 8192, "height": 4320}]
            )
        with self.assertRaisesRegex(ValueError, "채널"):
            validate_media_streams(
                [{"codec_type": "audio", "channels": 16, "sample_rate": "48000"}]
            )


class RuntimeIntegrityTests(unittest.TestCase):
    def test_same_size_runtime_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "audiosep" / "env"
            runtime.mkdir(parents=True)
            executable = runtime / "python.exe"
            executable.write_bytes(b"trusted")
            fingerprint = runtime_integrity.runtime_tree_fingerprint(root / "audiosep")
            expected = {
                "BASE_RUNTIME_TREE_SHA256": fingerprint["sha256"],
                "BASE_RUNTIME_TREE_FILES": fingerprint["files"],
                "BASE_RUNTIME_TREE_BYTES": fingerprint["bytes"],
            }
            state_root = root / "state"
            with patch.dict(os.environ, {"LOCALAPPDATA": str(state_root)}), patch.multiple(
                runtime_integrity, **expected
            ):
                runtime_integrity.record_runtime_integrity(root)
                runtime_integrity.verify_runtime_integrity(root)
                executable.write_bytes(b"altered")
                with self.assertRaisesRegex(RuntimeError, "무결성"):
                    runtime_integrity.verify_runtime_integrity(root)

    def test_bundled_ffmpeg_tampering_is_rejected_by_application(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ffmpeg = root / "ffmpeg"
            ffmpeg.mkdir()
            (ffmpeg / "ffmpeg.exe").write_bytes(b"tampered")
            with patch("audio_core.application_root", return_value=root):
                with self.assertRaisesRegex(RuntimeError, "무결성"):
                    require_program("ffmpeg")

    def test_bundled_ffmpeg_is_rehashed_on_every_use(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ffmpeg_root = root / "ffmpeg"
            ffmpeg_root.mkdir()
            executable = ffmpeg_root / "ffmpeg.exe"
            executable.write_bytes(b"trusted")
            expected = {
                "size": len(b"trusted"),
                "sha256": __import__("hashlib").sha256(b"trusted").hexdigest(),
            }
            with patch("audio_core.application_root", return_value=root), patch.dict(
                "audio_core.FFMPEG_EXECUTABLES", {"ffmpeg.exe": expected}, clear=True
            ):
                require_program("ffmpeg")
                executable.write_bytes(b"altered")
                with self.assertRaisesRegex(RuntimeError, "무결성"):
                    require_program("ffmpeg")

    def test_subprocess_output_is_bounded(self) -> None:
        command = [
            sys.executable,
            "-c",
            f"import sys; sys.stdout.write('x' * {MAX_COMMAND_OUTPUT_BYTES + 4096})",
        ]
        with self.assertRaisesRegex(RuntimeError, "출력"):
            run_command(command, timeout=30)


if __name__ == "__main__":
    unittest.main()
