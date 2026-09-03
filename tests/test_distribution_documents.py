from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCRIPTS = ROOT / "scripts"


class DistributionDocumentTests(unittest.TestCase):
    def test_repository_uses_unmodified_gpl_v3_only_license(self) -> None:
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        packaged_gpl = (ROOT / "licenses" / "GPL-3.0.txt").read_text(encoding="utf-8")
        self.assertEqual(license_text, packaged_gpl)
        self.assertIn("GNU GENERAL PUBLIC LICENSE", license_text)
        self.assertIn("Version 3, 29 June 2007", license_text)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        checklist = (DOCS / "DISTRIBUTION_CHECKLIST.md").read_text(encoding="utf-8")
        copyright_notice = (DOCS / "COPYRIGHT.md").read_text(encoding="utf-8")
        self.assertIn("GPL-3.0-only", readme)
        self.assertIn(
            "Copyright © 2026 @ms-0606 (GitHub: Fabio-Cannavaro)", readme
        )
        self.assertIn("GPL-3.0-only", checklist)
        self.assertIn(
            "Copyright © 2026 @ms-0606 (GitHub: Fabio-Cannavaro)",
            copyright_notice,
        )
        self.assertNotIn("SONG HO PARK", readme)
        self.assertNotIn("SONG HO PARK", copyright_notice)
        self.assertIn("GPL-3.0-only", copyright_notice)

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
        self.assertIn("[System.IO.Compression.ZipFile]::CreateFromDirectory", portable_build)
        self.assertIn('StartsWith("./")', portable_build)
        self.assertNotIn("tar.exe -a -c -f", portable_build)
        self.assertIn("SHA256SUMS.txt", portable_build)
        self.assertIn("$archivePath.sha256", portable_build)
        self.assertIn("SIGNING_STATUS.txt", portable_build)
        self.assertIn("git -C $projectDir rev-parse HEAD", portable_build)
        self.assertIn("git -C $projectDir status --porcelain --untracked-files=no", portable_build)
        self.assertIn('Join-Path $outputDocsDir "SOURCE_COMMIT.txt"', portable_build)
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
        lines = readme.splitlines()
        self.assertIn("Windows 64비트", readme)
        self.assertIn("NVIDIA GPU", readme)
        self.assertIn("약 5.9GB", readme)
        self.assertIn("약 15GB", readme)
        self.assertIn("video-music-separator-setup.exe", readme)
        self.assertIn("미서명 빌드", readme)
        self.assertIn("https://www.youtube.com/@ms-0606", readme)

        korean = lines.index("## 한국어")
        english = lines.index("## English")
        install = lines.index("### 설치 안내")
        usage = lines.index("### 사용 방법")
        processing = lines.index("### 처리 구조")
        exclusions = lines.index("### 저장소에 포함되지 않는 파일")
        english_install = lines.index("### Installation Guide")
        english_license = lines.index("### License")
        self.assertLess(korean, install)
        self.assertLess(install, usage)
        self.assertLess(usage, processing)
        self.assertLess(processing, exclusions)
        self.assertLess(exclusions, english)
        self.assertLess(english, english_install)
        self.assertLess(english_install, english_license)
        self.assertIn("#### 2. Windows 설치 파일 다운로드", lines)
        self.assertIn("#### 6. 설치 후 폴더 사용과 이동", lines)
        self.assertIn("#### 2. Download the Windows Installer", lines)
        self.assertIn("#### 6. Using and Moving the Installed Folder", lines)
        self.assertIn(
            "https://github.com/Fabio-Cannavaro/video-music-separator/releases/tag/installer-v0.2.0-r2",
            readme,
        )
        self.assertIn("Source code (zip)", readme)
        self.assertIn("video-music-separator-0.2.0-windows-x64.zip.sha256", readme)
        self.assertIn("설치 ZIP 하나만 내려받으면 된다", readme)
        self.assertIn("only the installer ZIP is required", readme)
        self.assertIn("선택 사항(무결성 확인용)", readme)
        self.assertIn("Optional integrity check", readme)
        self.assertIn("빌드·배포 스크립트, 문서와 라이선스 전문", readme)
        self.assertIn("build and distribution scripts, documentation, and full license texts", readme)
        self.assertNotIn("## 이동용 폴더", readme)
        self.assertIn(
            "CAVP가 영상 장면의 시각 특징을 추출하고, AV-CASS가 이 특징과 오디오를 함께 분석",
            readme,
        )

        privacy = (DOCS / "PRIVACY.md").read_text(encoding="utf-8")
        privacy_en = (DOCS / "PRIVACY.en.md").read_text(encoding="utf-8")
        self.assertIn("`docs/runtime-assets.json`", privacy)
        self.assertIn("`docs/runtime-assets.json`", privacy_en)


if __name__ == "__main__":
    unittest.main()
