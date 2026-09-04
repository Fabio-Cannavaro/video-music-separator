from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")


def ps_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "Windows PowerShell is required")
class ReleasePackagingTests(unittest.TestCase):
    def run_powershell(self, command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(POWERSHELL),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

    def test_allowlisted_copy_excludes_unlisted_file_and_zip_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            destination = root / "stage"
            archive = root / "stage.zip"
            allowlist = root / "allowlist.txt"
            source.mkdir()
            (source / "approved.txt").write_text("approved", encoding="utf-8")
            (source / "credentials.json").write_text("private", encoding="utf-8")
            allowlist.write_text("approved.txt\n", encoding="utf-8")

            command = (
                f"Import-Module {ps_quote(SCRIPTS / 'release_packaging.psm1')} -Force; "
                f"$files=@(Copy-AllowlistedTree -SourceRoot {ps_quote(source)} "
                f"-DestinationRoot {ps_quote(destination)} -AllowlistPath {ps_quote(allowlist)}); "
                f"Assert-ReleaseTreeMatchesExpected -Root {ps_quote(destination)} -ExpectedFiles $files; "
                f"New-ReleaseZipFromDirectory -SourceRoot {ps_quote(destination)} "
                f"-ArchivePath {ps_quote(archive)} -ExpectedFiles $files"
            )
            result = self.run_powershell(command)

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertTrue((destination / "approved.txt").is_file())
            self.assertFalse((destination / "credentials.json").exists())
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(["approved.txt"], package.namelist())

    def test_allowlist_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            destination = root / "stage"
            allowlist = root / "allowlist.txt"
            source.mkdir()
            (root / "outside.txt").write_text("outside", encoding="utf-8")
            allowlist.write_text("../outside.txt\n", encoding="utf-8")

            command = (
                f"Import-Module {ps_quote(SCRIPTS / 'release_packaging.psm1')} -Force; "
                f"Copy-AllowlistedTree -SourceRoot {ps_quote(source)} "
                f"-DestinationRoot {ps_quote(destination)} -AllowlistPath {ps_quote(allowlist)}"
            )
            result = self.run_powershell(command)

            self.assertNotEqual(0, result.returncode)
            self.assertFalse((destination / "outside.txt").exists())

    def test_path_overlap_validation_is_symmetric(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = root / "dist" / "package"
            command = (
                f"Import-Module {ps_quote(SCRIPTS / 'release_packaging.psm1')} -Force; "
                f"Assert-ReleasePathsDisjoint -FirstPath {ps_quote(root)} "
                f"-SecondPath {ps_quote(nested)}"
            )
            result = self.run_powershell(command)
            self.assertNotEqual(0, result.returncode)

    def test_publishing_fresh_stage_removes_stale_destination_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "package"
            destination.mkdir()
            (destination / "stale.txt").write_text("stale", encoding="utf-8")

            command = (
                f"Import-Module {ps_quote(SCRIPTS / 'release_packaging.psm1')} -Force; "
                f"$stage=New-ReleaseStagingDirectory -DestinationPath {ps_quote(destination)}; "
                "Set-Content -LiteralPath (Join-Path $stage 'approved.txt') -Value 'approved'; "
                f"Publish-ReleaseStagingDirectory -StagingPath $stage -DestinationPath {ps_quote(destination)}"
            )
            result = self.run_powershell(command)

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertTrue((destination / "approved.txt").is_file())
            self.assertFalse((destination / "stale.txt").exists())

    def test_zip_validation_rejects_incompatible_and_unexpected_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incompatible_archive = root / "incompatible.zip"
            unexpected_directory_archive = root / "unexpected-directory.zip"
            with zipfile.ZipFile(incompatible_archive, "w") as package:
                package.writestr("folder\\approved.txt", "approved")
            with zipfile.ZipFile(unexpected_directory_archive, "w") as package:
                package.writestr("approved.txt", "approved")
                package.writestr("unexpected/", "")

            for archive in (incompatible_archive, unexpected_directory_archive):
                command = (
                    f"Import-Module {ps_quote(SCRIPTS / 'release_packaging.psm1')} -Force; "
                    f"Assert-ZipEntriesMatchExpected -ArchivePath {ps_quote(archive)} "
                    "-ExpectedFiles @('approved.txt')"
                )
                result = self.run_powershell(command)
                self.assertNotEqual(0, result.returncode, archive.name)

    def test_runtime_archive_uses_exact_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "audiosep"
            output = root / "output"
            allowlist = root / "runtime-allowlist.txt"
            required = [
                "env/python.exe",
                "avcass/repo/models_avdnr_zero_conv_2vid.py",
                "avcass/deps/diffusers/__init__.py",
            ]
            for relative_path in required:
                path = runtime / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(relative_path, encoding="utf-8")
            (runtime / "env" / "Lib" / "site-packages").mkdir(parents=True)
            (runtime / "credentials.json").write_text("private", encoding="utf-8")
            allowlist.write_text("\n".join(required) + "\n", encoding="utf-8")

            result = subprocess.run(
                [
                    str(POWERSHELL),
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(SCRIPTS / "build_ai_runtime_archive.ps1"),
                    "-AIRuntimeDirectory",
                    str(runtime),
                    "-AllowlistPath",
                    str(allowlist),
                    "-OutputDirectory",
                    str(output),
                    "-PartSizeMiB",
                    "1",
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            archive = output / "video-music-separator-ai-runtime-0.2.0.zip"
            with zipfile.ZipFile(archive) as package:
                names = set(package.namelist())
                self.assertNotIn("audiosep/credentials.json", names)
                self.assertEqual(
                    {*(f"audiosep/{path}" for path in required), "audiosep/runtime-file-inventory.json"},
                    names,
                )
                inventory = json.loads(package.read("audiosep/runtime-file-inventory.json"))
                self.assertEqual(required, [item["path"] for item in inventory["files"]])


if __name__ == "__main__":
    unittest.main()
