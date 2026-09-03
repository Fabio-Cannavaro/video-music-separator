from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


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
        privacy = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
        self.assertIn("로컬 PC", privacy)
        self.assertIn("drive.usercontent.google.com", privacy)
        self.assertIn("huggingface.co", privacy)
        self.assertIn("github.com", privacy)
        self.assertIn("IP 주소", privacy)

    def test_builds_generate_checksums_and_support_optional_code_signing(self) -> None:
        installer_build = (ROOT / "build_runtime_installer.ps1").read_text(encoding="utf-8")
        portable_build = (ROOT / "build_portable.ps1").read_text(encoding="utf-8")
        self.assertIn("CodeSigningCertificateThumbprint", installer_build)
        self.assertIn("Set-AuthenticodeSignature", installer_build)
        self.assertIn(".sha256", installer_build)
        self.assertIn("tar.exe -a -c -f", portable_build)
        self.assertIn("SHA256SUMS.txt", portable_build)
        self.assertIn("$archivePath.sha256", portable_build)
        self.assertIn("SIGNING_STATUS.txt", portable_build)
        self.assertIn("audit_python_licenses.py", portable_build)
        self.assertIn("prune_python_distribution.py", portable_build)
        self.assertIn("--distribution pedalboard", portable_build)

    def test_public_build_excludes_legacy_workers(self) -> None:
        portable_build = (ROOT / "build_portable.ps1").read_text(encoding="utf-8")
        self.assertNotIn(
            'Copy-Item -LiteralPath (Join-Path $projectDir "audiosep_worker.py")',
            portable_build,
        )
        self.assertNotIn(
            'Copy-Item -LiteralPath (Join-Path $projectDir "bandit_worker.py")',
            portable_build,
        )


if __name__ == "__main__":
    unittest.main()
