from __future__ import annotations

import hashlib
import io
import argparse
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import runtime_asset_installer as installer


class FakeResponse(io.BytesIO):
    def __init__(self, payload: bytes, status: int = 200) -> None:
        super().__init__(payload)
        self.status = status

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


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

    def test_disclosure_lists_downloads_network_data_and_user_responsibility(self) -> None:
        disclosure = installer.installation_disclosure_text()
        self.assertIn("총 다운로드 약 5.9GB", disclosure)
        self.assertIn("AI Python 실행환경", disclosure)
        self.assertIn("github.com/Fabio-Cannavaro", disclosure)
        self.assertIn("drive.usercontent.google.com", disclosure)
        self.assertIn("huggingface.co", disclosure)
        self.assertIn("github.com/BtbN", disclosure)
        self.assertIn("IP 주소", disclosure)
        self.assertIn("업로드하지 않습니다", disclosure)
        self.assertIn("저작권", disclosure)
        self.assertIn("공식 앱이 아니며", disclosure)

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
        self.assertIn("lgpl-shared", installer.FFMPEG_ARCHIVE.url)

    def test_base_runtime_parts_are_below_github_asset_limit(self) -> None:
        self.assertEqual(len(installer.BASE_RUNTIME_ASSETS), 2)
        self.assertTrue(all(asset.size < 2 * 1024**3 for asset in installer.BASE_RUNTIME_ASSETS))
        self.assertEqual(
            sum(asset.size for asset in installer.BASE_RUNTIME_ASSETS),
            installer.BASE_RUNTIME_ARCHIVE_SIZE,
        )

    def test_installs_combined_base_runtime_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            archive = root / "source.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("audiosep/env/python.exe", b"python")
                package.writestr(
                    "audiosep/avcass/repo/models_avdnr_zero_conv_2vid.py", b"model"
                )
                package.writestr(
                    "audiosep/avcass/deps/diffusers/__init__.py", b"diffusers"
                )
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
                patch.object(installer, "BASE_RUNTIME_ASSETS", assets),
                patch.object(installer, "BASE_RUNTIME_ARCHIVE", "runtime.zip"),
                patch.object(installer, "BASE_RUNTIME_ARCHIVE_SIZE", len(payload)),
                patch.object(
                    installer,
                    "BASE_RUNTIME_ARCHIVE_SHA256",
                    hashlib.sha256(payload).hexdigest(),
                ),
            ):
                installer.install_base_runtime(root, lambda *_: None)
                self.assertTrue(installer.base_runtime_is_current(root))
            self.assertEqual(installer.validate_base_runtime(root), [])
            self.assertFalse((root / ".downloads" / "runtime.zip").exists())

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
