param(
    [string]$PythonPath = "",
    [string]$PythonNuGetPackagePath = "",
    [string]$PythonTclTkMsiPath = "",
    [string]$OutputDirectory = "",
    [string]$FFmpegDirectory = "",
    [string]$AIRuntimeDirectory = "",
    [string]$RuntimeAllowlistPath = "",
    [switch]$BundleRuntimeAssets,
    [string]$CodeSigningCertificateThumbprint = "",
    [string]$TimestampServer = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Import-Module (Join-Path $scriptDir "release_packaging.psm1") -Force
$appDir = Join-Path $projectDir "app"
$docsDir = Join-Path $projectDir "docs"
$finalOutputDir = if ($OutputDirectory) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    Join-Path $projectDir "dist\package"
}
$buildDir = Join-Path $projectDir "build"
$distDir = Join-Path $projectDir "dist"
$releaseDir = Join-Path $distDir "release"
$ffmpegRoot = if ($FFmpegDirectory) {
    [System.IO.Path]::GetFullPath($FFmpegDirectory)
} else {
    Join-Path $projectDir "third_party\ffmpeg-gpl"
}
$ffmpegDir = Join-Path $ffmpegRoot "bin"

if (-not $CodeSigningCertificateThumbprint) {
    Write-Warning "코드 서명 인증서가 지정되지 않았습니다. 공개 ZIP은 미서명 상태로 생성되며 Windows SmartScreen이 경고할 수 있습니다."
}
if ($PythonPath) {
    throw "공개 배포 빌드는 임의 PythonPath를 허용하지 않습니다. 고정 해시의 공식 CI 패키지는 -PythonNuGetPackagePath로만 지정하세요."
}

$gitSafeDirectory = "safe.directory=$projectDir"
$sourceCommit = (& git -c $gitSafeDirectory -C $projectDir rev-parse HEAD 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $sourceCommit) {
    throw "배포본에 기록할 Git 소스 커밋을 확인하지 못했습니다."
}
$trackedChanges = (& git -c $gitSafeDirectory -C $projectDir status --porcelain --untracked-files=normal 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "배포 전 Git 작업 트리 상태를 확인하지 못했습니다."
}
if ($trackedChanges) {
    throw "정확히 대응하는 소스를 기록하려면 추적 파일의 변경을 먼저 커밋해 주세요."
}

$pythonPackageUrl = "https://api.nuget.org/v3-flatcontainer/python/3.13.7/python.3.13.7.nupkg"
$pythonPackageSize = [int64]14176560
$pythonPackageSha256 = "E74272A824E23702DFB5F3E11C3660CEABAC7487E3366D4551391DB5CD762853"
$pythonTclTkUrl = "https://www.python.org/ftp/python/3.13.7/amd64/tcltk.msi"
$pythonTclTkSize = [int64]3276800
$pythonTclTkSha256 = "86F7C339A885A19306877281C058C8D49DF713624B7ED686F66993E0D16CE5B1"
$pythonDownloads = Join-Path $buildDir "downloads"
New-Item -ItemType Directory -Path $pythonDownloads -Force | Out-Null
$pythonPackage = if ($PythonNuGetPackagePath) {
    (Resolve-Path -LiteralPath $PythonNuGetPackagePath -ErrorAction Stop).Path
} else {
    Join-Path $pythonDownloads "python.3.13.7.nupkg"
}
if (-not (Test-Path -LiteralPath $pythonPackage -PathType Leaf)) {
    Invoke-WebRequest -UseBasicParsing -Uri $pythonPackageUrl -OutFile $pythonPackage
}
$pythonPackageItem = Get-Item -LiteralPath $pythonPackage
$pythonPackageHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $pythonPackage).Hash
if (
    $pythonPackageItem.Length -ne $pythonPackageSize -or
    $pythonPackageHash -ne $pythonPackageSha256
) {
    throw "공식 Python 3.13.7 NuGet CI 패키지 무결성 검증에 실패했습니다."
}
$pythonTclTkMsi = if ($PythonTclTkMsiPath) {
    (Resolve-Path -LiteralPath $PythonTclTkMsiPath -ErrorAction Stop).Path
} else {
    Join-Path $pythonDownloads "python-3.13.7-tcltk.msi"
}
if (-not (Test-Path -LiteralPath $pythonTclTkMsi -PathType Leaf)) {
    Invoke-WebRequest -UseBasicParsing -Uri $pythonTclTkUrl -OutFile $pythonTclTkMsi
}
$pythonTclTkItem = Get-Item -LiteralPath $pythonTclTkMsi
$pythonTclTkHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $pythonTclTkMsi).Hash
$pythonTclTkSignature = Get-AuthenticodeSignature -LiteralPath $pythonTclTkMsi
if (
    $pythonTclTkItem.Length -ne $pythonTclTkSize -or
    $pythonTclTkHash -ne $pythonTclTkSha256 -or
    $pythonTclTkSignature.Status -ne "Valid" -or
    -not $pythonTclTkSignature.SignerCertificate -or
    $pythonTclTkSignature.SignerCertificate.Subject -notlike "CN=Python Software Foundation,*"
) {
    throw "공식 Python 3.13.7 Tcl/Tk MSI의 무결성 또는 Authenticode 서명 검증에 실패했습니다."
}
$bootstrapRoot = Join-Path $buildDir "cpython-3.13.7"
if (Test-Path -LiteralPath $bootstrapRoot) {
    Remove-Item -LiteralPath $bootstrapRoot -Recurse -Force
}
try {
    [System.IO.Compression.ZipFile]::ExtractToDirectory($pythonPackage, $bootstrapRoot)
} catch {
    throw "검증된 Python 3.13.7 NuGet CI 패키지를 추출하지 못했습니다: $($_.Exception.Message)"
}
$tclTkExtractRoot = Join-Path $buildDir "cpython-3.13.7-tcltk"
if (Test-Path -LiteralPath $tclTkExtractRoot) {
    Remove-Item -LiteralPath $tclTkExtractRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $tclTkExtractRoot -Force | Out-Null
$tclTkExtract = Start-Process `
    -FilePath "msiexec.exe" `
    -ArgumentList @("/a", $pythonTclTkMsi, "/qn", "TARGETDIR=$tclTkExtractRoot") `
    -Wait `
    -PassThru `
    -WindowStyle Hidden
if ($tclTkExtract.ExitCode -ne 0) {
    throw "검증된 Python 3.13.7 Tcl/Tk MSI 관리 추출에 실패했습니다: $($tclTkExtract.ExitCode)"
}
$bootstrapTools = Join-Path $bootstrapRoot "tools"
Copy-Item -LiteralPath (Join-Path $tclTkExtractRoot "DLLs") -Destination $bootstrapTools -Recurse -Force
Copy-Item -LiteralPath (Join-Path $tclTkExtractRoot "Lib\tkinter") -Destination (Join-Path $bootstrapTools "Lib") -Recurse -Force
Copy-Item -LiteralPath (Join-Path $tclTkExtractRoot "tcl") -Destination $bootstrapTools -Recurse -Force
$bootstrapPython = Join-Path $bootstrapRoot "tools\python.exe"
if (-not (Test-Path -LiteralPath $bootstrapPython -PathType Leaf)) {
    throw "검증된 Python 3.13.7 실행 파일을 찾지 못했습니다."
}
$pythonSignedFiles = @(
    $bootstrapPython,
    (Join-Path $bootstrapRoot "tools\python3.dll"),
    (Join-Path $bootstrapRoot "tools\python313.dll"),
    (Join-Path $bootstrapRoot "tools\DLLs\_tkinter.pyd"),
    (Join-Path $bootstrapRoot "tools\DLLs\tcl86t.dll"),
    (Join-Path $bootstrapRoot "tools\DLLs\tk86t.dll")
)
foreach ($signedFile in $pythonSignedFiles) {
    $signature = Get-AuthenticodeSignature -LiteralPath $signedFile
    if (
        $signature.Status -ne "Valid" -or
        -not $signature.SignerCertificate -or
        $signature.SignerCertificate.Subject -notlike "CN=Python Software Foundation,*"
    ) {
        throw "공식 Python 3.13.7 실행 파일의 Authenticode 서명을 확인하지 못했습니다: $signedFile"
    }
}
$bootstrapVersion = (& $bootstrapPython -c "import platform; print(platform.python_version())" | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $bootstrapVersion -ne "3.13.7") {
    throw "공개 배포 빌드는 Python 3.13.7이 필요합니다. 현재: $bootstrapVersion"
}
$tclTkVersion = (& $bootstrapPython -c "import tkinter; print(tkinter.Tcl().eval('info patchlevel'))" | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $tclTkVersion -ne "8.6.15") {
    throw "공개 배포 GUI 빌드는 검증된 Tcl/Tk 8.6.15가 필요합니다. 현재: $tclTkVersion"
}
$releaseVenv = Join-Path $buildDir "release-venv"
& $bootstrapPython -m venv --clear $releaseVenv
if ($LASTEXITCODE -ne 0) {
    throw "격리된 공개 배포 빌드 환경을 만들지 못했습니다."
}
$python = Join-Path $releaseVenv "Scripts\python.exe"
$pipVersion = (& $python -m pip --version | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $pipVersion -notmatch '^pip 25\.2 ') {
    throw "공식 Python 3.13.7에 포함된 pip 25.2를 확인하지 못했습니다: $pipVersion"
}
& $python -m pip install --disable-pip-version-check --require-hashes -r (Join-Path $projectDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "해시 잠금된 공개 배포 의존성을 설치하지 못했습니다."
}
& $python -m pip check
if ($LASTEXITCODE -ne 0) {
    throw "공개 배포 빌드 환경의 의존성 검증에 실패했습니다."
}
if (-not $AIRuntimeDirectory) {
    throw "라이선스 목록 생성을 위한 정리된 AI 런타임 원본을 -AIRuntimeDirectory로 지정해 주세요."
}
if ($BundleRuntimeAssets -and -not $RuntimeAllowlistPath) {
    throw "오프라인 묶음에는 검토한 정확한 런타임 파일 목록인 -RuntimeAllowlistPath가 필요합니다."
}
$runtimeAllowlist = if ($RuntimeAllowlistPath) {
    (Resolve-Path -LiteralPath $RuntimeAllowlistPath -ErrorAction Stop).Path
} else {
    ""
}
$sourceRuntime = [System.IO.Path]::GetFullPath($AIRuntimeDirectory)
if (Test-ReleasePathWithin -Path $projectDir -Root $finalOutputDir) {
    throw "배포 출력 폴더는 프로젝트 루트 또는 그 상위 폴더일 수 없습니다: $finalOutputDir"
}
if (
    (Test-ReleasePathWithin -Path $finalOutputDir -Root $projectDir) -and
    -not (Test-ReleasePathWithin -Path $finalOutputDir -Root $distDir)
) {
    throw "프로젝트 안의 배포 출력 폴더는 dist 아래에 있어야 합니다: $finalOutputDir"
}
Assert-ReleasePathsDisjoint `
    -FirstPath $finalOutputDir -SecondPath $releaseDir `
    -FirstLabel "배포 출력" -SecondLabel "릴리스 ZIP 폴더"
Assert-ReleasePathsDisjoint `
    -FirstPath $finalOutputDir -SecondPath $buildDir `
    -FirstLabel "배포 출력" -SecondLabel "빌드 작업 폴더"
Assert-ReleasePathsDisjoint `
    -FirstPath $sourceRuntime -SecondPath $finalOutputDir `
    -FirstLabel "AI 런타임 원본" -SecondLabel "배포 출력"
Assert-ReleasePathsDisjoint `
    -FirstPath $sourceRuntime -SecondPath $releaseDir `
    -FirstLabel "AI 런타임 원본" -SecondLabel "릴리스 ZIP 폴더"
Assert-ReleasePathsDisjoint `
    -FirstPath $sourceRuntime -SecondPath $buildDir `
    -FirstLabel "AI 런타임 원본" -SecondLabel "빌드 작업 폴더"
Assert-NoReparsePoint -Root $sourceRuntime -RelativePath "env/Lib/site-packages"
if ($BundleRuntimeAssets -and -not $FFmpegDirectory -and -not (Test-Path -LiteralPath $ffmpegDir -PathType Container)) {
    & (Join-Path $scriptDir "prepare_ffmpeg_gpl.ps1") -DestinationDirectory $ffmpegRoot
    if ($LASTEXITCODE -ne 0) {
        throw "GPL FFmpeg 준비에 실패했습니다."
    }
}
if ($BundleRuntimeAssets -and -not (Test-Path -LiteralPath $ffmpegDir -PathType Container)) {
    throw "FFmpeg 폴더를 찾을 수 없습니다: $ffmpegDir"
}

$requiredFfmpegFiles = @(
    "ffmpeg.exe",
    "ffprobe.exe",
    "ffplay.exe"
)
if ($BundleRuntimeAssets) {
    $expectedFfmpegExecutables = @{
        "ffmpeg.exe" = @{ Size = [int64]102856192; Sha256 = "72A489ECCD008C2EC2C0A5856C5C75BC3D8BBFA90166C4566865C246445E6AA3" }
        "ffplay.exe" = @{ Size = [int64]104339968; Sha256 = "39A9BA4F207FE9EECFB094E632998C29E1DA88A5D5D23D0B8B71A357A7C47EB5" }
        "ffprobe.exe" = @{ Size = [int64]102652416; Sha256 = "19202B23C0043F15AD1B7BCE2344F406FD52BD6EFD8F995CE02E7392A1CEC52F" }
    }
    foreach ($name in $requiredFfmpegFiles) {
        $program = Join-Path $ffmpegDir $name
        $expected = $expectedFfmpegExecutables[$name]
        if (
            -not (Test-Path -LiteralPath $program -PathType Leaf) -or
            (Get-Item -LiteralPath $program).Length -ne $expected.Size -or
            (Get-FileHash -LiteralPath $program -Algorithm SHA256).Hash -ne $expected.Sha256
        ) {
            throw "GPL FFmpeg 구성 파일을 찾을 수 없습니다: $name"
        }
    }

    $ffmpegVersionText = (& (Join-Path $ffmpegDir "ffmpeg.exe") -version 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) {
        throw "FFmpeg 버전을 확인하지 못했습니다."
    }
    if (
        -not $ffmpegVersionText.Contains("-essentials_build-www.gyan.dev") -or
        -not $ffmpegVersionText.Contains("--enable-gpl") -or
        -not $ffmpegVersionText.Contains("--enable-version3") -or
        -not $ffmpegVersionText.Contains("--enable-static") -or
        $ffmpegVersionText.Contains("--enable-nonfree")
    ) {
        throw "배포에는 nonfree 옵션이 없는 Gyan GPL Essentials FFmpeg만 사용할 수 있습니다."
    }
}

$stagingDir = New-ReleaseStagingDirectory -DestinationPath $finalOutputDir
$outputDir = $stagingDir
$expectedPackageFiles = [System.Collections.Generic.List[string]]::new()
$packagePublished = $false
try {
$legacyExecutable = Join-Path $outputDir "video-sound-separator.exe"
if (Test-Path -LiteralPath $legacyExecutable -PathType Leaf) {
    Remove-Item -LiteralPath $legacyExecutable -Force
}
$executableBuildArguments = @{
    PythonPath = $python
    OutputDirectory = $outputDir
    TimestampServer = $TimestampServer
}
if ($CodeSigningCertificateThumbprint) {
    $executableBuildArguments.CodeSigningCertificateThumbprint = $CodeSigningCertificateThumbprint
}
& (Join-Path $scriptDir "build_executables.ps1") @executableBuildArguments
if ($LASTEXITCODE -ne 0) {
    throw "실행 파일 빌드에 실패했습니다."
}

$portableExecutable = Join-Path $outputDir "video-music-separator.exe"
$expectedPackageFiles.Add("video-music-separator.exe")
$expectedPackageFiles.Add("video-music-separator-setup.exe")

$portableFfmpeg = Join-Path $outputDir "ffmpeg"
$portableAudioSep = Join-Path $outputDir "audiosep"
if (Test-Path -LiteralPath $portableFfmpeg -PathType Container) {
    $resolvedOutput = [System.IO.Path]::GetFullPath($outputDir).TrimEnd('\') + '\'
    $resolvedFfmpeg = [System.IO.Path]::GetFullPath($portableFfmpeg)
    if (-not $resolvedFfmpeg.StartsWith($resolvedOutput, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "FFmpeg 교체 대상이 이동용 폴더 밖에 있습니다: $resolvedFfmpeg"
    }
    Remove-Item -LiteralPath $portableFfmpeg -Recurse -Force
}

$resolvedOutput = [System.IO.Path]::GetFullPath($outputDir).TrimEnd('\') + '\'
$resolvedFinalOutput = [System.IO.Path]::GetFullPath($finalOutputDir).TrimEnd('\') + '\'
if (
    $sourceRuntime.StartsWith($resolvedOutput, [System.StringComparison]::OrdinalIgnoreCase) -or
    $sourceRuntime.StartsWith($resolvedFinalOutput, [System.StringComparison]::OrdinalIgnoreCase)
) {
    throw "AI 런타임 원본은 출력 폴더 밖에 있어야 합니다: $sourceRuntime"
}
foreach ($requiredDirectory in @("env", "avcass")) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceRuntime $requiredDirectory) -PathType Container)) {
        throw "AI 런타임 원본에 필수 폴더가 없습니다: $requiredDirectory"
    }
}
$sourceSitePackages = Join-Path $sourceRuntime "env\Lib\site-packages"
$sourcePedalboard = @(Get-ChildItem $sourceSitePackages -Force -ErrorAction Stop |
    Where-Object { $_.Name -eq "pedalboard" -or $_.Name -like "pedalboard-*.dist-info" })
if ($sourcePedalboard.Count -gt 0) {
    throw "공개 빌드에는 pedalboard가 제거된 AI 런타임 원본이 필요합니다."
}

if ($BundleRuntimeAssets) {
    $requiredRuntimeFiles = @(
        "env/python.exe",
        "avcass/repo/models_avdnr_zero_conv_2vid.py",
        "avcass/deps/diffusers/__init__.py"
    )
    $copiedRuntimeFiles = @(Copy-AllowlistedTree `
        -SourceRoot $sourceRuntime `
        -DestinationRoot $portableAudioSep `
        -AllowlistPath $runtimeAllowlist `
        -RequiredPaths $requiredRuntimeFiles)
    foreach ($relativePath in $copiedRuntimeFiles) {
        $expectedPackageFiles.Add("audiosep/$relativePath")
    }
    $runtimeInventoryPath = Join-Path $portableAudioSep "runtime-file-inventory.json"
    [ordered]@{
        schema = 1
        files = @(
            foreach ($relativePath in $copiedRuntimeFiles) {
                $copiedFile = Join-Path $portableAudioSep $relativePath.Replace("/", "\")
                [ordered]@{ path = $relativePath; size = (Get-Item -LiteralPath $copiedFile).Length }
            }
        )
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $runtimeInventoryPath -Encoding UTF8
    $expectedPackageFiles.Add("audiosep/runtime-file-inventory.json")
} else {
    if (Test-Path -LiteralPath $portableAudioSep -PathType Container) {
        $resolvedAudioSep = [System.IO.Path]::GetFullPath($portableAudioSep)
        if (-not $resolvedAudioSep.StartsWith($resolvedOutput, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "AI 런타임 제거 대상이 출력 폴더 밖에 있습니다: $resolvedAudioSep"
        }
        Remove-Item -LiteralPath $portableAudioSep -Recurse -Force
    }
}

if ($BundleRuntimeAssets) {
    New-Item -ItemType Directory -Path $portableFfmpeg -Force | Out-Null
    foreach ($name in $requiredFfmpegFiles) {
        Copy-Item -LiteralPath (Join-Path $ffmpegDir $name) -Destination (Join-Path $portableFfmpeg $name) -Force
        $expectedPackageFiles.Add("ffmpeg/$name")
    }
} else {
    $downloadedModelFiles = @(
        (Join-Path $portableAudioSep "avcass\model\av_cass_checkpoint.pt"),
        (Join-Path $portableAudioSep "avcass\model\cavp\cavp_epoch66.ckpt")
    )
    foreach ($modelFile in $downloadedModelFiles) {
        if (Test-Path -LiteralPath $modelFile -PathType Leaf) {
            Remove-Item -LiteralPath $modelFile -Force
        }
    }
}
$outputAppDir = Join-Path $outputDir "app"
$outputDocsDir = Join-Path $outputDir "docs"
New-Item -ItemType Directory -Path $outputAppDir, $outputDocsDir -Force | Out-Null
$trackedDocs = @(& git -c $gitSafeDirectory -C $projectDir ls-files -- docs)
if ($LASTEXITCODE -ne 0 -or $trackedDocs.Count -eq 0) {
    throw "배포 문서의 Git 추적 파일 목록을 읽지 못했습니다."
}
$trackedDocFiles = @($trackedDocs | ForEach-Object { $_.Substring("docs/".Length) })
$copiedDocs = @(Copy-AllowlistedTree -SourceRoot $docsDir -DestinationRoot $outputDocsDir -RelativePaths $trackedDocFiles)
foreach ($relativePath in $copiedDocs) {
    $expectedPackageFiles.Add("docs/$relativePath")
}
Copy-Item -LiteralPath (Join-Path $projectDir "LICENSE") -Destination $outputDocsDir -Force
$expectedPackageFiles.Add("docs/LICENSE")
$trackedLicenses = @(& git -c $gitSafeDirectory -C $projectDir ls-files -- licenses)
if ($LASTEXITCODE -ne 0 -or $trackedLicenses.Count -eq 0) {
    throw "배포 라이선스의 Git 추적 파일 목록을 읽지 못했습니다."
}
$trackedLicenseFiles = @($trackedLicenses | ForEach-Object { $_.Substring("licenses/".Length) })
$outputLicenseDir = Join-Path $outputDocsDir "licenses"
$copiedLicenses = @(Copy-AllowlistedTree -SourceRoot (Join-Path $projectDir "licenses") -DestinationRoot $outputLicenseDir -RelativePaths $trackedLicenseFiles)
foreach ($relativePath in $copiedLicenses) {
    $expectedPackageFiles.Add("docs/licenses/$relativePath")
}
$sourceCommitText = @(
    "Repository: https://github.com/Fabio-Cannavaro/video-music-separator",
    "Source commit: $sourceCommit",
    "Project code license: GPL-3.0-only"
)
$sourceCommitText | Set-Content -LiteralPath (Join-Path $outputDocsDir "SOURCE_COMMIT.txt") -Encoding UTF8
$expectedPackageFiles.Add("docs/SOURCE_COMMIT.txt")

$pythonLicenseDir = Join-Path $outputDocsDir "licenses\python"
$auditSitePackages = if ($BundleRuntimeAssets) {
    Join-Path $portableAudioSep "env\Lib\site-packages"
} else {
    $sourceSitePackages
}
$auditTrustedRoot = if ($BundleRuntimeAssets) { $portableAudioSep } else { $sourceRuntime }
& $python (Join-Path $scriptDir "audit_python_licenses.py") `
    --site-packages $auditSitePackages `
    --trusted-root $auditTrustedRoot `
    --output (Join-Path $outputDocsDir "PYTHON_PACKAGES_NOTICES.md") `
    --license-output $pythonLicenseDir `
    --json-output (Join-Path $outputDocsDir "PYTHON_PACKAGES_INVENTORY.json")
if ($LASTEXITCODE -ne 0) {
    throw "Python 패키지 라이선스 목록 생성에 실패했습니다."
}
$expectedPackageFiles.Add("docs/PYTHON_PACKAGES_NOTICES.md")
$expectedPackageFiles.Add("docs/PYTHON_PACKAGES_INVENTORY.json")
foreach ($relativePath in Get-ReleaseTreeFiles $pythonLicenseDir) {
    $expectedPackageFiles.Add("docs/licenses/python/$relativePath")
}

$appSignature = Get-AuthenticodeSignature -FilePath $portableExecutable
$setupSignature = Get-AuthenticodeSignature -FilePath (Join-Path $outputDir "video-music-separator-setup.exe")
$signingStatus = if ($CodeSigningCertificateThumbprint) {
    $expectedSigner = $CodeSigningCertificateThumbprint.Replace(" ", "").ToUpperInvariant()
    foreach ($signature in @($appSignature, $setupSignature)) {
        $actualSigner = if ($signature.SignerCertificate) {
            $signature.SignerCertificate.Thumbprint.Replace(" ", "").ToUpperInvariant()
        } else { "" }
        if (
            $signature.Status -ne "Valid" -or
            $actualSigner -ne $expectedSigner -or
            -not $signature.TimeStamperCertificate
        ) {
            throw "공개 배포 파일의 Authenticode 서명·서명자·타임스탬프 검증에 실패했습니다."
        }
    }
    @(
        "Video Music Separator code-signing status",
        "video-music-separator.exe: $($appSignature.Status)",
        "video-music-separator-setup.exe: $($setupSignature.Status)",
        "Certificate thumbprint: $CodeSigningCertificateThumbprint",
        "RFC 3161 timestamp: present"
    )
} else {
    foreach ($signature in @($appSignature, $setupSignature)) {
        if ($signature.Status -ne "NotSigned") {
            throw "인증서 없는 공개 빌드에서 예상하지 않은 Authenticode 상태를 확인했습니다: $($signature.Status)"
        }
    }
    Write-Warning "UNSIGNED PUBLIC BUILD: 게시자 신원을 Windows가 확인할 수 없습니다. SHA-256을 Release 설명과 대조하세요."
    @(
        "Video Music Separator code-signing status",
        "WARNING: UNSIGNED PUBLIC BUILD",
        "video-music-separator.exe: $($appSignature.Status)",
        "video-music-separator-setup.exe: $($setupSignature.Status)",
        "Publisher identity: not verified by Authenticode",
        "Integrity: compare docs/SHA256SUMS.txt and the Release .sha256 file"
    )
}
$signingStatus | Set-Content -LiteralPath (Join-Path $outputDocsDir "SIGNING_STATUS.txt") -Encoding UTF8
$expectedPackageFiles.Add("docs/SIGNING_STATUS.txt")

$avCassBaseReady =
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "env\python.exe") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "avcass\repo\models_avdnr_zero_conv_2vid.py") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "avcass\deps\diffusers\__init__.py") -PathType Leaf)
$avCassAssetsReady =
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "avcass\model\av_cass_checkpoint.pt") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "avcass\model\cavp\cavp_epoch66.ckpt") -PathType Leaf)

$legacyTigerWorker = Join-Path $outputDir "tiger_worker.py"
if (Test-Path -LiteralPath $legacyTigerWorker -PathType Leaf) {
    Remove-Item -LiteralPath $legacyTigerWorker -Force
}
$legacyTigerRuntime = Join-Path $portableAudioSep "tiger"
if (Test-Path -LiteralPath $legacyTigerRuntime -PathType Container) {
    $resolvedRuntime = (Resolve-Path -LiteralPath $portableAudioSep).Path
    $resolvedTiger = (Resolve-Path -LiteralPath $legacyTigerRuntime).Path
    if (-not $resolvedTiger.StartsWith($resolvedRuntime + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "TIGER 정리 대상이 휴대용 런타임 밖에 있습니다: $resolvedTiger"
    }
    Remove-Item -LiteralPath $resolvedTiger -Recurse -Force
}

$usage = @"
같은 PC에서는 이 폴더를 복사하지 말고 현재 위치에서 실행하세요.
어느 폴더의 영상이든 영상 열기로 선택할 수 있고, 결과는 원본 영상 옆에 저장됩니다.
자주 쓸 때는 video-music-separator.exe의 바로가기를 만들어 두면 됩니다.
다른 PC로 옮길 때만 이 폴더 전체를 함께 이동하세요.

실행: video-music-separator.exe

영상을 연 뒤 '영상에서 음악 분리'를 누르세요.
영상 미리보기 오른쪽에서 한국어 또는 English 인터페이스를 선택할 수 있습니다.
AV-CASS는 속도보다 분리 품질과 원본 스테레오 보존을 우선합니다.
AV-CASS는 영상 장면까지 분석하며 NVIDIA GPU가 필요합니다.
앱 맨 위의 작은 영상 화면에서 전체 믹스와 각 분리본을 영상과 함께 확인할 수 있습니다.
음악 행을 뮤트한 뒤 전체 영상을 재생하고, 원본 옆에 _음악제거 사본으로 저장할 수 있습니다.
두 행의 듣기/정지, 행별 뮤트/해제, 공통 볼륨 조절 기능이 포함되어 있습니다.
처음 한 번 video-music-separator-setup.exe를 실행하면 AV-CASS, CAVP와 GPL FFmpeg를
각 공식 배포처에서 자동으로 내려받고 SHA-256을 확인합니다. 설치할 때는 인터넷 연결이 필요합니다.
설치가 끝난 뒤 앱 사용에는 인터넷 연결이나 별도 Python 설치가 필요하지 않습니다.

처리할 영상·음원의 저작권과 이용 권리를 확인하고, 결과물을 사용하는 책임은 사용자에게 있습니다.
영상 미리보기 왼쪽의 '앱 정보·라이선스'에서 제3자 고지, 출처, 논문과 라이선스 전문을 확인할 수 있습니다.
"@
if (-not $avCassBaseReady) {
    $usage += "`r`n처음 사용하기 전에 video-music-separator-setup.exe를 실행해 AI 실행환경과 필수 구성요소를 설치해 주세요.`r`n"
} elseif (-not $avCassAssetsReady -or -not (Test-Path -LiteralPath (Join-Path $portableFfmpeg "ffmpeg.exe") -PathType Leaf)) {
    $usage += "`r`n처음 사용하기 전에 video-music-separator-setup.exe를 실행해 주세요.`r`n"
}
$usage | Set-Content -LiteralPath (Join-Path $outputDocsDir "사용법.txt") -Encoding UTF8
$expectedPackageFiles.Add("docs/사용법.txt")

$setupExecutable = Join-Path $outputDir "video-music-separator-setup.exe"
$checksumLines = @(
    "$(Get-ReleaseFileSha256 $portableExecutable)  video-music-separator.exe",
    "$(Get-ReleaseFileSha256 $setupExecutable)  video-music-separator-setup.exe"
)
$checksumLines | Set-Content -LiteralPath (Join-Path $outputDocsDir "SHA256SUMS.txt") -Encoding ascii
$expectedPackageFiles.Add("docs/SHA256SUMS.txt")

$forbiddenPublicPaths = @(
    (Join-Path $outputDir "audiosep"),
    (Join-Path $outputDir "ffmpeg"),
    (Join-Path $portableAudioSep "audiosep"),
    (Join-Path $portableAudioSep "bandit"),
    (Join-Path $outputAppDir "audiosep_worker.py"),
    (Join-Path $outputAppDir "bandit_worker.py"),
    (Join-Path $portableAudioSep "avcass\model\av_cass_checkpoint.pt"),
    (Join-Path $portableAudioSep "avcass\model\cavp\cavp_epoch66.ckpt"),
    (Join-Path $portableAudioSep "env\Lib\site-packages\pedalboard"),
    (Join-Path $portableAudioSep "env\Lib\site-packages\pedalboard-0.9.24.dist-info")
)
if (-not $BundleRuntimeAssets) {
    $foundForbidden = @($forbiddenPublicPaths | Where-Object { Test-Path -LiteralPath $_ })
    if ($foundForbidden.Count -gt 0) {
        throw "공개 배포본에 금지된 런타임 파일이 남아 있습니다: $($foundForbidden -join ', ')"
    }
    $remainingModelFiles = @(Get-ChildItem $outputDir -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in ".pt", ".pth", ".ckpt", ".safetensors", ".onnx", ".bin" })
    if ($remainingModelFiles.Count -gt 0) {
        throw "공개 배포본에 모델 또는 가중치 파일이 남아 있습니다: $($remainingModelFiles.FullName -join ', ')"
    }
}

$versionLine = Select-String -LiteralPath (Join-Path $appDir "release_info.py") -Pattern '^APP_VERSION = "([^"]+)"$'
if (-not $versionLine) {
    throw "release_info.py에서 앱 버전을 읽지 못했습니다."
}
$appVersion = $versionLine.Matches[0].Groups[1].Value
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
$archiveSuffix = if ($BundleRuntimeAssets) { "windows-x64-internal-offline" } else { "windows-x64" }
$archivePath = Join-Path $releaseDir "video-music-separator-$appVersion-$archiveSuffix.zip"
if (Test-Path -LiteralPath $archivePath -PathType Leaf) {
    Remove-Item -LiteralPath $archivePath -Force
}
New-ReleaseZipFromDirectory `
    -SourceRoot $outputDir `
    -ArchivePath $archivePath `
    -ExpectedFiles $expectedPackageFiles.ToArray()
$archiveHash = Get-ReleaseFileSha256 $archivePath
"$archiveHash  $([System.IO.Path]::GetFileName($archivePath))" |
    Set-Content -LiteralPath "$archivePath.sha256" -Encoding ascii

Publish-ReleaseStagingDirectory -StagingPath $stagingDir -DestinationPath $finalOutputDir
$packagePublished = $true
Write-Host "이동용 폴더 생성 완료: $finalOutputDir"
Write-Host "배포 ZIP 생성 완료: $archivePath"
Write-Host "배포 ZIP SHA-256: $archivePath.sha256"
} finally {
    if (-not $packagePublished -and (Test-Path -LiteralPath $stagingDir -PathType Container)) {
        Remove-Item -LiteralPath $stagingDir -Recurse -Force
    }
}
