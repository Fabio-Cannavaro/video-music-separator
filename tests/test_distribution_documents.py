from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCRIPTS = ROOT / "scripts"


class DistributionDocumentTests(unittest.TestCase):
    def test_license_protects_original_and_requires_share_alike_source(self) -> None:
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("No-Resale Share-Alike License 1.0", license_text)
        self.assertIn("insubstantial changes", license_text)
        self.assertIn("claim copyright only", license_text)
        self.assertIn("same license", license_text)
        self.assertIn("corresponding source code", license_text)
        self.assertIn("not impose additional terms", license_text)

    def test_privacy_notice_names_network_destinations_and_local_processing(self) -> None:
        privacy = (DOCS / "PRIVACY.md").read_text(encoding="utf-8")
        self.assertIn("로컬 PC", privacy)
        self.assertIn("drive.usercontent.google.com", privacy)
        self.assertIn("huggingface.co", privacy)
        self.assertIn("github.com", privacy)
        self.assertIn("IP 주소", privacy)

    def test_builds_generate_checksums_and_support_optional_code_signing(self) -> None:
        installer_build = (SCRIPTS / "build_runtime_installer.ps1").read_text(encoding="utf-8")
        portable_build = (SCRIPTS / "build_portable.ps1").read_text(encoding="utf-8")
        executable_build = (SCRIPTS / "build_executables.ps1").read_text(encoding="utf-8")
        self.assertIn("CodeSigningCertificateThumbprint", installer_build)
        self.assertIn("Set-AuthenticodeSignature", installer_build)
        self.assertIn(".sha256", installer_build)
        self.assertIn("tar.exe -a -c -f", portable_build)
        self.assertIn("SHA256SUMS.txt", portable_build)
        self.assertIn("$archivePath.sha256", portable_build)
        self.assertIn("SIGNING_STATUS.txt", portable_build)
        self.assertIn("audit_python_licenses.py", portable_build)
        self.assertIn('Join-Path $outputDir "audiosep"', portable_build)
        self.assertIn('--onefile', executable_build)
        self.assertIn('Join-Path $appDir "sound_separator_app.py"', executable_build)

        runtime_build = (SCRIPTS / "build_ai_runtime_archive.ps1").read_text(encoding="utf-8")
        self.assertIn("PartSizeMiB = 1900", runtime_build)
        self.assertIn("runtime-parts.json", runtime_build)

    def test_public_build_excludes_legacy_workers(self) -> None:
        portable_build = (SCRIPTS / "build_portable.ps1").read_text(encoding="utf-8")
        self.assertNotIn(
            'Copy-Item -LiteralPath (Join-Path $projectDir "audiosep_worker.py")',
            portable_build,
        )
        self.assertNotIn(
            'Copy-Item -LiteralPath (Join-Path $projectDir "bandit_worker.py")',
            portable_build,
        )

    def test_repository_uses_organized_top_level_directories(self) -> None:
        self.assertEqual(list(ROOT.glob("*.py")), [])
        for name in ("app", "tests", "scripts", "docs", "licenses"):
            self.assertTrue((ROOT / name).is_dir(), name)


if __name__ == "__main__":
    unittest.main()
