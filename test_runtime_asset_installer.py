from __future__ import annotations

import hashlib
import io
import tempfile
import unittest
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
    def test_manifest_pins_official_model_sources_and_hashes(self) -> None:
        avcass, cavp = installer.MODEL_ASSETS
        self.assertIn("drive.usercontent.google.com", avcass.url)
        self.assertEqual(avcass.size, 738_312_597)
        self.assertEqual(len(avcass.sha256), 64)
        self.assertIn("b17ddbe76e6d42f4b4135eeb443b1c1644267e3e", cavp.url)
        self.assertEqual(cavp.size, 1_361_483_035)
        self.assertEqual(len(cavp.sha256), 64)
        self.assertIn("lgpl-shared", installer.FFMPEG_ARCHIVE.url)

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
