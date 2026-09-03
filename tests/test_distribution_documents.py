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

    def test_readme_documents_supported_environment_and_first_install(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Windows 64비트", readme)
        self.assertIn("NVIDIA GPU", readme)
        self.assertIn("약 5.9GB", readme)
        self.assertIn("약 15GB", readme)
        self.assertIn("video-music-separator-setup.exe", readme)
        self.assertIn("미서명 빌드", readme)
        self.assertIn("https://www.youtube.com/@ms-0606", readme)

        install = readme.index("## 설치 안내")
        usage = readme.index("## 사용 방법")
        processing = readme.index("## 처리 구조")
        exclusions = readme.index("## 저장소에 포함되지 않는 파일")
        self.assertLess(install, usage)
        self.assertLess(usage, processing)
        self.assertLess(processing, exclusions)
        self.assertIn("### 2. 설치에 필요한 두 파일", readme)
        self.assertIn("### 6. 설치 후 폴더 사용과 이동", readme)
        self.assertNotIn("## 이동용 폴더", readme)
        self.assertIn(
            "CAVP가 영상 장면의 시각 특징을 추출하고, AV-CASS가 이 특징과 오디오를 함께 분석",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
