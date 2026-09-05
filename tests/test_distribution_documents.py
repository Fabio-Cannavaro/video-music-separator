from __future__ import annotations

import unittest
from pathlib import Path
from app.release_info import APP_VERSION


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
        privacy_en = (DOCS / "PRIVACY.en.md").read_text(encoding="utf-8")
        self.assertIn("로컬 PC", privacy)
        self.assertIn("drive.usercontent.google.com", privacy)
        self.assertIn("huggingface.co", privacy)
        self.assertIn("github.com", privacy)
        self.assertIn("www.gyan.dev", privacy)
        self.assertIn("IP 주소", privacy)
        self.assertNotIn("일회용 인증 코드", privacy)
        self.assertNotIn("one-time authentication code", privacy_en)
        self.assertNotIn("GitHub CLI가 처리", privacy)
        self.assertNotIn("handled by GitHub CLI", privacy_en)

    def test_public_build_documents_unsigned_state_and_uses_locked_isolated_dependencies(self) -> None:
        installer_build = (SCRIPTS / "build_runtime_installer.ps1").read_text(encoding="utf-8")
        portable_build = (SCRIPTS / "build_portable.ps1").read_text(encoding="utf-8")
        executable_build = (SCRIPTS / "build_executables.ps1").read_text(encoding="utf-8")
        packaging_module = (SCRIPTS / "release_packaging.psm1").read_text(encoding="utf-8")
        self.assertIn("CodeSigningCertificateThumbprint", installer_build)
        self.assertIn("Set-AuthenticodeSignature", installer_build)
        self.assertIn(".sha256", installer_build)
        self.assertIn("New-ReleaseZipFromDirectory", portable_build)
        self.assertIn("ConvertTo-ReleaseRelativePath", packaging_module)
        self.assertNotIn("tar.exe -a -c -f", portable_build)
        self.assertIn("SHA256SUMS.txt", portable_build)
        self.assertIn("$archivePath.sha256", portable_build)
        self.assertIn("SIGNING_STATUS.txt", portable_build)
        self.assertIn("if (-not $CodeSigningCertificateThumbprint)", portable_build)
        self.assertIn("TimeStamperCertificate", portable_build)
        self.assertIn("3.13.7", portable_build)
        self.assertIn("python.3.13.7.nupkg", portable_build)
        self.assertIn("E74272A824E23702DFB5F3E11C3660CEABAC7487E3366D4551391DB5CD762853", portable_build)
        self.assertIn("Python Software Foundation", portable_build)
        self.assertIn("PythonNuGetPackagePath", portable_build)
        self.assertIn("PythonTclTkMsiPath", portable_build)
        self.assertIn("python-3.13.7-tcltk.msi", portable_build)
        self.assertIn("86F7C339A885A19306877281C058C8D49DF713624B7ED686F66993E0D16CE5B1", portable_build)
        self.assertIn('"/a", $pythonTclTkMsi', portable_build)
        self.assertNotIn("InstallAllUsers=0", portable_build)
        self.assertIn("tkinter.Tcl()", portable_build)
        self.assertIn("pip 25\\.2", portable_build)
        self.assertIn("if ($PythonPath)", portable_build)
        self.assertIn("--require-hashes", portable_build)
        self.assertIn("release-venv", portable_build)
        self.assertIn("WARNING: UNSIGNED PUBLIC BUILD", portable_build)
        self.assertIn('if ($signature.Status -ne "NotSigned")', portable_build)
        self.assertNotIn("공개 배포 ZIP에는 Authenticode 코드 서명 인증서 thumbprint가 필요합니다", portable_build)
        self.assertIn("git -c $gitSafeDirectory -C $projectDir rev-parse HEAD", portable_build)
        self.assertIn("git -c $gitSafeDirectory -C $projectDir status --porcelain --untracked-files=normal", portable_build)
        self.assertIn('Join-Path $outputDocsDir "SOURCE_COMMIT.txt"', portable_build)
        self.assertIn("audit_python_licenses.py", portable_build)
        self.assertIn("prepare_ffmpeg_gpl.ps1", portable_build)
        self.assertNotIn("prepare_ffmpeg_lgpl.ps1", portable_build)
        self.assertIn('Join-Path $outputDir "audiosep"', portable_build)
        self.assertIn("New-ReleaseStagingDirectory", portable_build)
        self.assertIn("Assert-ReleaseTreeMatchesExpected", packaging_module)
        self.assertIn("Assert-ZipEntriesMatchExpected", packaging_module)
        self.assertIn("Publish-ReleaseStagingDirectory", portable_build)
        self.assertIn("RuntimeAllowlistPath", portable_build)
        self.assertIn("Assert-ReleasePathsDisjoint", portable_build)
        self.assertIn("Assert-NoReparsePoint", portable_build)
        self.assertIn("--trusted-root", portable_build)
        self.assertNotIn('Copy-Item -Path (Join-Path $docsDir "*")', portable_build)
        self.assertNotIn('Copy-Item -Path (Join-Path $ffmpegDir "*")', portable_build)
        self.assertIn('--onefile', executable_build)
        self.assertIn("avcass_worker.py');app", executable_build)
        self.assertIn("separation_quality.py');app", executable_build)
        self.assertIn('Join-Path $appDir "sound_separator_app.py"', executable_build)

        runtime_build = (SCRIPTS / "build_ai_runtime_archive.ps1").read_text(encoding="utf-8")
        self.assertIn("PartSizeMiB = 1900", runtime_build)
        self.assertIn("runtime-parts.json", runtime_build)
        self.assertIn("AllowlistPath", runtime_build)
        self.assertIn("Copy-AllowlistedTree", runtime_build)
        self.assertIn("New-ReleaseZipFromDirectory", runtime_build)
        self.assertNotIn("tar.exe -a -c -f", runtime_build)
        self.assertIn("sha256 = Get-ReleaseFileSha256", runtime_build)

    def test_ci_dependencies_and_actions_are_immutable(self) -> None:
        windows = (ROOT / ".github" / "workflows" / "windows-tests.yml").read_text(encoding="utf-8")
        safety = (ROOT / ".github" / "workflows" / "repository-safety.yml").read_text(encoding="utf-8")
        for workflow in (windows, safety):
            for line in workflow.splitlines():
                if "uses:" in line:
                    reference = line.split("@", 1)[1].split()[0]
                    self.assertRegex(reference, r"^[0-9a-f]{40}$")
        self.assertIn("--require-hashes", windows)
        self.assertNotIn("pip install --upgrade pip", windows)
        self.assertNotIn("choco install ffmpeg", windows)
        self.assertIn("ffmpeg-9.0.1-essentials_build.zip", windows)
        self.assertIn("FEC81AE03971D9DD4BE3EBE02E263BD2", windows)

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
        self.assertNotIn(
            'Copy-Item -LiteralPath (Join-Path $appDir "avcass_worker.py")',
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
        self.assertIn("GitHub Draft로 전환", readme)
        self.assertIn(f"installer-v{APP_VERSION}", readme)
        self.assertIn("미서명 공개 테스트 프리릴리스", readme)
        for section in (readme.split("## English")[0], readme.split("## English")[1]):
            self.assertIn("SmartScreen", section)
            self.assertIn("SHA-256", section)
            self.assertIn("https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation", section)
        self.assertIn("https://www.youtube.com/@ms-0606", readme)

        korean = lines.index("## 한국어")
        english = lines.index("## English")
        install = lines.index("### 설치 안내")
        usage = lines.index("### 사용 방법")
        processing = lines.index("### 앱 처리 흐름")
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
        self.assertNotIn("releases/tag/installer-v0.2.3", readme)
        self.assertNotIn("releases/tag/installer-v0.2.5", readme)
        self.assertNotIn("releases/tag/installer-v0.2.6", readme)
        self.assertIn(f"releases/tag/installer-v{APP_VERSION}", readme)
        self.assertIn("Source code (zip)", readme)
        for section in readme.split("## English"):
            self.assertIn("`.sha256`", section)
        self.assertIn("빌드·배포 스크립트, 문서와 라이선스 전문", readme)
        self.assertIn("build and distribution scripts, documentation, and full license texts", readme)
        self.assertNotIn("## 이동용 폴더", readme)
        explanation = readme.split("### 음악·비음악 분리 원리", 1)[1].split("###", 1)[0]
        for term in ("CAVP", "AV-CASS", "16kHz", "마스크"):
            self.assertIn(term, explanation)
        self.assertIn("Gyan", readme)
        self.assertIn("GPL Essentials", readme)
        self.assertNotIn("BtbN", readme)
        self.assertNotIn("prepare_ffmpeg_lgpl.ps1", readme)
        self.assertIn("runtime-release-allowlist.txt", readme)
        self.assertIn("RuntimeAllowlistPath", readme)
        self.assertIn("새 스테이징 폴더", readme)
        self.assertIn("fresh staging directory", readme)

        portable_build = (SCRIPTS / "build_portable.ps1").read_text(encoding="utf-8")
        self.assertIn("'앱 정보·라이선스'", portable_build)
        self.assertNotIn("'라이선스·출처'", portable_build)

        privacy = (DOCS / "PRIVACY.md").read_text(encoding="utf-8")
        privacy_en = (DOCS / "PRIVACY.en.md").read_text(encoding="utf-8")
        self.assertIn("`docs/runtime-assets.json`", privacy)
        self.assertIn("`docs/runtime-assets.json`", privacy_en)


if __name__ == "__main__":
    unittest.main()
