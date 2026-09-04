from __future__ import annotations

import hashlib
import io
import argparse
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import runtime_asset_installer as installer


class FakeResponse(io.BytesIO):
    def __init__(
        self,
        payload: bytes,
        status: int = 200,
        url: str = "https://example.invalid/response",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(payload)
        self.status = status
        self.url = url
        self.headers = headers or {}

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


class BrokenConsoleStream:
    def write(self, _value: str) -> None:
        raise OSError(22, "Invalid argument")

    def flush(self) -> None:
        raise OSError(22, "Invalid argument")


def fake_asset(payload: bytes) -> installer.DownloadAsset:
    return installer.DownloadAsset(
        asset_id="test",
        label="테스트 파일",
        url="https://example.invalid/test.bin",
        relative_path="models/test.bin",
        sha256=hashlib.sha256(payload).hexdigest(),
        size=len(payload),
        source="https://example.invalid",
    )


class RuntimeAssetInstallerTests(unittest.TestCase):
    def test_headless_install_requires_explicit_terms_acceptance(self) -> None:
        args = argparse.Namespace(
            install_dir=Path("."),
            verify_only=False,
            headless=True,
            accept_terms=False,
        )
        with patch.object(installer, "parse_args", return_value=args):
            with patch.object(installer, "install_all") as install_all:
                self.assertEqual(installer.main(), 2)
        install_all.assert_not_called()

    def test_headless_install_handles_missing_windowed_console(self) -> None:
        args = argparse.Namespace(
            install_dir=Path("."),
            verify_only=False,
            headless=True,
            accept_terms=True,
        )

        def install_with_progress(_root: Path, progress) -> None:
            progress("설치 진행", 1, 1)

        with (
            patch.object(installer, "parse_args", return_value=args),
            patch.object(installer, "install_all", side_effect=install_with_progress),
            patch.object(installer.sys, "stdout", BrokenConsoleStream()),
        ):
            self.assertEqual(installer.main(), 0)

    def test_headless_install_failure_returns_nonzero_without_console(self) -> None:
        args = argparse.Namespace(
            install_dir=Path("."),
            verify_only=False,
            headless=True,
            accept_terms=True,
        )
        with (
            patch.object(installer, "parse_args", return_value=args),
            patch.object(installer, "install_all", side_effect=RuntimeError("failed")),
            patch.object(installer.sys, "stderr", BrokenConsoleStream()),
        ):
            self.assertEqual(installer.main(), 1)

    def test_verify_only_handles_missing_windowed_console(self) -> None:
        args = argparse.Namespace(
            install_dir=Path("."),
            verify_only=True,
            headless=False,
            accept_terms=False,
        )
        with (
            patch.object(installer, "parse_args", return_value=args),
            patch.object(installer, "verify_installation", return_value=[]),
            patch.object(installer.sys, "stdout", BrokenConsoleStream()),
        ):
            self.assertEqual(installer.main(), 0)

    @unittest.skipUnless(os.name == "nt", "Windows extended paths are Windows-only")
    def test_extracts_zip_member_past_legacy_windows_path_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            archive = root / "long-path.zip"
            destination = root / ("d" * 120)
            destination.mkdir()
            member = ("f" * 120) + ".bin"
            target = destination / member
            self.assertGreater(len(str(target)), 260)
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr(member, b"long path payload")

            installer._extract_zip_with_progress(
                archive, destination, "extract", lambda *_: None
            )

            extended_target = Path(installer._filesystem_path(target))
            self.assertEqual(extended_target.read_bytes(), b"long path payload")
            extended_target.unlink()

    def test_disclosure_lists_downloads_network_data_and_user_responsibility(self) -> None:
        disclosure = installer.installation_disclosure_text()
        self.assertIn("총 다운로드 약 5.9GB", disclosure)
        self.assertIn("AI Python 실행환경", disclosure)
        self.assertIn("github.com/Fabio-Cannavaro", disclosure)
        self.assertIn("drive.usercontent.google.com", disclosure)
        self.assertIn("huggingface.co", disclosure)
        self.assertIn("www.gyan.dev", disclosure)
        self.assertIn("GPL Essentials", disclosure)
        self.assertIn("IP 주소", disclosure)
        self.assertIn("업로드하지 않습니다", disclosure)
        self.assertIn("저작권", disclosure)
        self.assertIn("공식 앱이 아니며", disclosure)

    def test_english_disclosure_lists_the_same_downloads_and_terms(self) -> None:
        disclosure = installer.installation_disclosure_text("en")
        self.assertIn("approximately 5.9 GB", disclosure)
        self.assertIn("AI Python runtime", disclosure)
        self.assertIn("github.com/Fabio-Cannavaro", disclosure)
        self.assertIn("drive.usercontent.google.com", disclosure)
        self.assertIn("huggingface.co", disclosure)
        self.assertIn("www.gyan.dev", disclosure)
        self.assertIn("GPL Essentials", disclosure)
        self.assertIn("not an official application", disclosure)
        self.assertIn("User responsibility", disclosure)

    def test_installer_languages_have_matching_interface_keys(self) -> None:
        self.assertEqual(
            set(installer.INSTALLER_UI["ko"]),
            set(installer.INSTALLER_UI["en"]),
        )
        self.assertEqual(
            installer.localized_document_names("en"),
            (
                "COPYRIGHT.en.md",
                "LICENSE",
                "MODEL_LICENSES.en.md",
                "THIRD_PARTY_NOTICES.en.md",
                "PRIVACY.en.md",
                "FFMPEG_BUILD.en.md",
            ),
        )

    def test_progress_labels_switch_to_english(self) -> None:
        self.assertEqual(
            installer.translate_progress_label(
                "AI Python 실행환경 1/2 · 무결성 확인 중", "en"
            ),
            "AI Python runtime 1/2 · Verifying integrity",
        )
        self.assertEqual(
            installer.translate_progress_label("필수 구성요소 설치 완료", "en"),
            "Required components installed",
        )

    def test_manifest_pins_official_model_sources_and_hashes(self) -> None:
        self.assertIn("runtime-v0.2.0", installer.BASE_RUNTIME_ASSETS[0].url)
        self.assertEqual(len(installer.BASE_RUNTIME_ARCHIVE_SHA256), 64)
        avcass, cavp = installer.MODEL_ASSETS
        self.assertIn("drive.usercontent.google.com", avcass.url)
        self.assertEqual(avcass.size, 738_312_597)
        self.assertEqual(len(avcass.sha256), 64)
        self.assertIn("b17ddbe76e6d42f4b4135eeb443b1c1644267e3e", cavp.url)
        self.assertEqual(cavp.size, 1_361_483_035)
        self.assertEqual(len(cavp.sha256), 64)
        self.assertEqual(
            installer.FFMPEG_ASSET_NAME,
            "ffmpeg-9.0.1-essentials_build.zip",
        )
        self.assertEqual(
            installer.FFMPEG_ARCHIVE.url,
            "https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.1-essentials_build.zip",
        )
        self.assertEqual(installer.FFMPEG_ARCHIVE.size, 111_253_802)
        self.assertEqual(
            installer.FFMPEG_ARCHIVE.sha256,
            "fec81ae03971d9dd4be3ebe02e263bd2ec1d789483f931bdba5f5715e65da2e9",
        )

    def test_resolves_first_party_locked_ffmpeg_without_network(self) -> None:
        with patch.object(installer.urllib.request, "urlopen") as urlopen:
            asset = installer.resolve_ffmpeg_archive()
        self.assertEqual(asset.size, 111_253_802)
        self.assertEqual(asset.sha256, installer.FFMPEG_SHA256)
        self.assertEqual(asset.url, installer.FFMPEG_DOWNLOAD_URL)
        self.assertEqual(asset.version, "9.0.1")
        self.assertEqual(
            asset.relative_path,
            ".downloads/ffmpeg-9.0.1-essentials_build.zip",
        )
        urlopen.assert_not_called()

    def test_validates_matching_gpl_essentials_static_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            directory = Path(temp_name)
            for name in installer.FFMPEG_REQUIRED_FILES:
                (directory / name).write_bytes(b"exe")
            locked = {
                name: {"size": 3, "sha256": hashlib.sha256(b"exe").hexdigest()}
                for name in installer.FFMPEG_REQUIRED_FILES
            }

            def version_result(command, **_kwargs):
                program = Path(command[0]).stem
                return CompletedProcess(
                    command,
                    0,
                    (
                        f"{program} version 9.0.1-essentials_build-www.gyan.dev\n"
                        "configuration: --enable-gpl --enable-version3 "
                        "--enable-static\n"
                    ),
                    "",
                )

            with (
                patch.object(installer, "FFMPEG_EXECUTABLES", locked),
                patch.object(installer.subprocess, "run", side_effect=version_result),
            ):
                self.assertTrue(installer.validate_ffmpeg(directory, "9.0.1"))
                self.assertFalse(installer.validate_ffmpeg(directory, "9.1"))

    def test_rejects_nonfree_ffmpeg_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            directory = Path(temp_name)
            for name in installer.FFMPEG_REQUIRED_FILES:
                (directory / name).write_bytes(b"exe")
            locked = {
                name: {"size": 3, "sha256": hashlib.sha256(b"exe").hexdigest()}
                for name in installer.FFMPEG_REQUIRED_FILES
            }
            version_text = (
                "ffmpeg version 9.0.1-essentials_build-www.gyan.dev\n"
                "configuration: --enable-gpl --enable-version3 --enable-static "
                "--enable-nonfree\n"
            )
            with patch.object(
                installer.subprocess,
                "run",
                return_value=CompletedProcess([], 0, version_text, ""),
            ), patch.object(installer, "FFMPEG_EXECUTABLES", locked):
                self.assertFalse(installer.validate_ffmpeg(directory, "9.0.1"))

    def test_rejects_tampered_ffmpeg_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            directory = Path(temp_name)
            for name in installer.FFMPEG_REQUIRED_FILES:
                (directory / name).write_bytes(b"tampered")
            with patch.object(installer.subprocess, "run") as run:
                self.assertFalse(installer.validate_ffmpeg(directory, "9.0.1"))
            run.assert_not_called()

    def test_base_runtime_parts_are_below_github_asset_limit(self) -> None:
        self.assertEqual(len(installer.BASE_RUNTIME_ASSETS), 2)
        self.assertTrue(all(asset.size < 2 * 1024**3 for asset in installer.BASE_RUNTIME_ASSETS))
        self.assertEqual(
            sum(asset.size for asset in installer.BASE_RUNTIME_ASSETS),
            installer.BASE_RUNTIME_ARCHIVE_SIZE,
        )

    def test_public_runtime_download_does_not_require_github_login(self) -> None:
        payload = b"public runtime"
        asset = fake_asset(payload)
        with tempfile.TemporaryDirectory() as temp_name:
            destination = Path(temp_name) / asset.relative_path
            with patch.object(installer, "download_asset") as public_download:
                installer.download_base_runtime_asset(
                    asset, destination, lambda *_: None
                )
            public_download.assert_called_once()

    def test_installer_contains_no_github_cli_login_path(self) -> None:
        source = Path(installer.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"--clipboard"', source)
        self.assertNotIn('"auth", "login"', source)
        self.assertNotIn("download_private_runtime_asset", source)
        self.assertNotIn("GitHub CLI 응답", source)

    def test_public_runtime_access_error_does_not_start_github_login(self) -> None:
        payload = b"public runtime"
        asset = fake_asset(payload)
        denied = installer.urllib.error.HTTPError(
            asset.url, 404, "Not Found", {}, None
        )
        with tempfile.TemporaryDirectory() as temp_name:
            destination = Path(temp_name) / asset.relative_path
            with (
                patch.object(installer, "download_asset", side_effect=denied),
                patch.object(installer.subprocess, "run") as run,
                patch.object(installer.subprocess, "Popen") as popen,
            ):
                with self.assertRaisesRegex(RuntimeError, "공개 AI 실행환경"):
                    installer.download_base_runtime_asset(
                        asset, destination, lambda *_: None
                    )
            run.assert_not_called()
            popen.assert_not_called()

    def test_runtime_network_failure_does_not_trigger_login(self) -> None:
        payload = b"runtime"
        asset = fake_asset(payload)
        with tempfile.TemporaryDirectory() as temp_name:
            destination = Path(temp_name) / asset.relative_path
            with (
                patch.object(installer, "download_asset", side_effect=OSError("offline")),
                patch.object(installer.subprocess, "run") as run,
                patch.object(installer.subprocess, "Popen") as popen,
            ):
                with self.assertRaisesRegex(OSError, "offline"):
                    installer.download_base_runtime_asset(
                        asset, destination, lambda *_: None
                    )
            run.assert_not_called()
            popen.assert_not_called()

    def test_installs_combined_base_runtime_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temporary_root = Path(temp_name)
            component_length = 95 - len(str(temporary_root)) - 1
            self.assertGreater(component_length, 8)
            root = temporary_root / ("install-" + "x" * (component_length - 8))
            root.mkdir()
            archive = root / "source.zip"
            long_member = (
                "audiosep/env/Lib/site-packages/transformers/models/"
                "audio_spectrogram_transformer/__pycache__/"
                "configuration_audio_spectrogram_transformer.cpython-310.pyc"
            )
            self.assertLess(len(str(root / long_member)), 260)
            legacy_staging_target = (
                root / ".downloads" / "runtime-extract-abcdefgh" / long_member
            )
            self.assertGreater(len(str(legacy_staging_target)), 260)
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("audiosep/env/python.exe", b"python")
                package.writestr(
                    "audiosep/avcass/repo/models_avdnr_zero_conv_2vid.py", b"model"
                )
                package.writestr(
                    "audiosep/avcass/deps/diffusers/__init__.py", b"diffusers"
                )
                package.writestr(long_member, b"generated cache")
            payload = archive.read_bytes()
            split_at = len(payload) // 2
            chunks = (payload[:split_at], payload[split_at:])
            assets = tuple(
                installer.DownloadAsset(
                    asset_id=f"runtime-{index}",
                    label="runtime",
                    url="https://example.invalid/runtime",
                    relative_path=f".downloads/runtime.{index:03d}",
                    sha256=hashlib.sha256(chunk).hexdigest(),
                    size=len(chunk),
                    source="https://example.invalid",
                )
                for index, chunk in enumerate(chunks, start=1)
            )
            for asset, chunk in zip(assets, chunks):
                destination = root / asset.relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(chunk)
            with (
                patch.dict(os.environ, {"LOCALAPPDATA": temp_name}),
                patch.object(installer, "BASE_RUNTIME_ASSETS", assets),
                patch.object(installer, "BASE_RUNTIME_ARCHIVE", "runtime.zip"),
                patch.object(installer, "BASE_RUNTIME_ARCHIVE_SIZE", len(payload)),
                patch.object(
                    installer,
                    "BASE_RUNTIME_ARCHIVE_SHA256",
                    hashlib.sha256(payload).hexdigest(),
                ),
                patch.object(installer, "record_runtime_integrity") as record_integrity,
                patch.object(installer, "runtime_integrity_is_valid", return_value=True),
            ):
                updates: list[tuple[str, int, int]] = []
                observed_staging: list[Path] = []

                def record_progress(label: str, current: int, total: int) -> None:
                    updates.append((label, current, total))
                    if "압축을 푸는 중" in label and current == 0:
                        observed_staging.extend(root.glob(".vms-r-*"))

                installer.install_base_runtime(
                    root,
                    record_progress,
                )
                self.assertTrue(installer.base_runtime_is_current(root))
                record_integrity.assert_called_once()
            self.assertEqual(installer.validate_base_runtime(root), [])
            self.assertEqual((root / long_member).read_bytes(), b"generated cache")
            self.assertEqual(len(observed_staging), 1)
            self.assertEqual(observed_staging[0].parent, root)
            self.assertFalse((root / ".downloads" / "runtime.zip").exists())
            labels = [label for label, _, _ in updates]
            self.assertTrue(any("분할 파일을 결합하는 중" in label for label in labels))
            self.assertTrue(any("결합 파일 무결성 확인 중" in label for label in labels))
            self.assertTrue(any("압축을 푸는 중" in label for label in labels))

    def test_downloads_and_verifies_asset_before_replacing_target(self) -> None:
        payload = b"verified model bytes"
        asset = fake_asset(payload)
        with tempfile.TemporaryDirectory() as temp_name:
            destination = Path(temp_name) / asset.relative_path
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"old invalid file")
            updates: list[tuple[str, int, int]] = []
            with patch.object(
                installer, "_open_download", return_value=FakeResponse(payload)
            ):
                installer.download_asset(
                    asset,
                    destination,
                    lambda label, current, total: updates.append(
                        (label, current, total)
                    ),
                )
            self.assertEqual(destination.read_bytes(), payload)
            self.assertTrue(installer.asset_is_valid(destination, asset))

    def test_oversized_download_is_stopped_and_partial_removed(self) -> None:
        payload = b"expected"
        asset = fake_asset(payload)
        with tempfile.TemporaryDirectory() as temp_name:
            destination = Path(temp_name) / asset.relative_path
            with patch.object(
                installer,
                "_open_download",
                return_value=FakeResponse(payload + b"unexpected"),
            ):
                with self.assertRaisesRegex(RuntimeError, "초과"):
                    installer.download_asset(asset, destination, lambda *_: None)
            self.assertFalse(destination.with_name(destination.name + ".part").exists())

    def test_keeps_partial_download_after_network_failure(self) -> None:
        payload = b"partial payload"
        asset = fake_asset(payload)

        class BrokenResponse(FakeResponse):
            def read(self, size: int = -1) -> bytes:
                if self.tell() > 0:
                    raise OSError("network stopped")
                return super().read(4)

        with tempfile.TemporaryDirectory() as temp_name:
            destination = Path(temp_name) / asset.relative_path
            with patch.object(
                installer, "_open_download", return_value=BrokenResponse(payload)
            ):
                with self.assertRaises(OSError):
                    installer.download_asset(asset, destination, lambda *_: None)
            self.assertFalse(destination.exists())
            self.assertTrue(destination.with_name(destination.name + ".part").exists())

    def test_reuses_already_verified_asset_without_network(self) -> None:
        payload = b"already installed"
        asset = fake_asset(payload)
        with tempfile.TemporaryDirectory() as temp_name:
            destination = Path(temp_name) / asset.relative_path
            destination.parent.mkdir(parents=True)
            destination.write_bytes(payload)
            with patch.object(installer, "_open_download") as download:
                installer.download_asset(asset, destination, lambda *_: None)
            download.assert_not_called()

    def test_resumes_a_partial_download(self) -> None:
        payload = b"resume this model download"
        asset = fake_asset(payload)
        with tempfile.TemporaryDirectory() as temp_name:
            destination = Path(temp_name) / asset.relative_path
            destination.parent.mkdir(parents=True)
            partial = destination.with_name(destination.name + ".part")
            partial.write_bytes(payload[:7])
            with patch.object(
                installer,
                "_open_download",
                return_value=FakeResponse(payload[7:], status=206),
            ) as open_download:
                installer.download_asset(asset, destination, lambda *_: None)
            open_download.assert_called_once_with(asset, 7)
            self.assertEqual(destination.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
