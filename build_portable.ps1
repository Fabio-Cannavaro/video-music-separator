param(
    [string]$PythonPath = "",
    [string]$OutputDirectory = "",
    [string]$FFmpegDirectory = "",
    [switch]$BundleRuntimeAssets
)

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoDir = Split-Path -Parent $projectDir
$outputDir = if ($OutputDirectory) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    Join-Path $repoDir "video-music-separator-portable"
}
$buildDir = Join-Path $projectDir "build"
$distDir = Join-Path $projectDir "dist"
$python = if ($PythonPath) { $PythonPath } else { Join-Path $projectDir ".venv\Scripts\python.exe" }
$ffmpegRoot = if ($FFmpegDirectory) {
    [System.IO.Path]::GetFullPath($FFmpegDirectory)
} else {
    Join-Path $projectDir "third_party\ffmpeg-lgpl"
}
$ffmpegDir = Join-Path $ffmpegRoot "bin"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "빌드용 Python을 찾을 수 없습니다: $python"
}
if ($BundleRuntimeAssets -and -not $FFmpegDirectory -and -not (Test-Path -LiteralPath $ffmpegDir -PathType Container)) {
    & (Join-Path $projectDir "prepare_ffmpeg_lgpl.ps1") -DestinationDirectory $ffmpegRoot
    if ($LASTEXITCODE -ne 0) {
        throw "LGPL FFmpeg 준비에 실패했습니다."
    }
}
if ($BundleRuntimeAssets -and -not (Test-Path -LiteralPath $ffmpegDir -PathType Container)) {
    throw "FFmpeg 폴더를 찾을 수 없습니다: $ffmpegDir"
}

$requiredFfmpegFiles = @(
    "ffmpeg.exe",
    "ffprobe.exe",
    "ffplay.exe",
    "avcodec-62.dll",
    "avformat-62.dll",
    "avfilter-11.dll",
    "avutil-60.dll",
    "swresample-6.dll",
    "swscale-9.dll"
)
if ($BundleRuntimeAssets) {
    foreach ($name in $requiredFfmpegFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $ffmpegDir $name) -PathType Leaf)) {
            throw "LGPL 공유 FFmpeg 구성 파일을 찾을 수 없습니다: $name"
        }
    }

    $ffmpegVersionText = (& (Join-Path $ffmpegDir "ffmpeg.exe") -version 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) {
        throw "FFmpeg 버전을 확인하지 못했습니다."
    }
    if (
        -not $ffmpegVersionText.Contains("--enable-shared") -or
        $ffmpegVersionText.Contains("--enable-gpl") -or
        $ffmpegVersionText.Contains("--enable-nonfree")
    ) {
        throw "배포에는 GPL/nonfree 옵션이 없는 LGPL 공유 FFmpeg만 사용할 수 있습니다."
    }
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name "video-music-separator" `
    --distpath $distDir `
    --workpath $buildDir `
    --specpath $projectDir `
    (Join-Path $projectDir "sound_separator_app.py")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller 빌드에 실패했습니다."
}

$builtDir = Join-Path $distDir "video-music-separator"
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$builtInternal = Join-Path $builtDir "_internal"
$portableInternal = Join-Path $outputDir "_internal"
if (Test-Path -LiteralPath $portableInternal -PathType Container) {
    $resolvedOutput = (Resolve-Path -LiteralPath $outputDir).Path
    $resolvedInternal = (Resolve-Path -LiteralPath $portableInternal).Path
    if (-not $resolvedInternal.StartsWith($resolvedOutput, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "교체 대상이 이동용 폴더 밖에 있습니다: $resolvedInternal"
    }
    Remove-Item -LiteralPath $resolvedInternal -Recurse -Force
}
Move-Item -LiteralPath $builtInternal -Destination $portableInternal
$legacyExecutable = Join-Path $outputDir "video-sound-separator.exe"
if (Test-Path -LiteralPath $legacyExecutable -PathType Leaf) {
    Remove-Item -LiteralPath $legacyExecutable -Force
}
Copy-Item -LiteralPath (Join-Path $builtDir "video-music-separator.exe") -Destination $outputDir -Force

& (Join-Path $projectDir "build_runtime_installer.ps1") `
    -PythonPath $python `
    -OutputDirectory (Join-Path $distDir "runtime-installer")
if ($LASTEXITCODE -ne 0) {
    throw "필수 구성요소 설치 파일 빌드에 실패했습니다."
}
Copy-Item -LiteralPath `
    (Join-Path $distDir "runtime-installer\video-music-separator-setup.exe") `
    -Destination $outputDir `
    -Force

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
New-Item -ItemType Directory -Path $portableAudioSep -Force | Out-Null

if ($BundleRuntimeAssets) {
    New-Item -ItemType Directory -Path $portableFfmpeg -Force | Out-Null
    Copy-Item -Path (Join-Path $ffmpegDir "*") -Destination $portableFfmpeg -Recurse -Force
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
Copy-Item -LiteralPath (Join-Path $projectDir "bandit_worker.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "audiosep_worker.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "avcass_worker.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "separation_quality.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "LICENSE") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "MODEL_LICENSES.md") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "THIRD_PARTY_NOTICES.md") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "THIRD_PARTY_NOTICES.en.md") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "FFMPEG_BUILD.md") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "FFMPEG_BUILD.en.md") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "licenses") -Destination $outputDir -Recurse -Force

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
처음 한 번 video-music-separator-setup.exe를 실행하면 AV-CASS, CAVP와 LGPL FFmpeg를
각 공식 배포처에서 자동으로 내려받고 SHA-256을 확인합니다. 설치할 때는 인터넷 연결이 필요합니다.
설치가 끝난 뒤 앱 사용에는 인터넷 연결이나 별도 Python 설치가 필요하지 않습니다.

처리할 영상·음원의 저작권과 이용 권리를 확인하고, 결과물을 사용하는 책임은 사용자에게 있습니다.
영상 미리보기 왼쪽의 '라이선스·출처'에서 제3자 고지, 출처, 논문과 라이선스 전문을 확인할 수 있습니다.
"@
if (-not $avCassBaseReady) {
    $usage += "`r`nAV-CASS 기본 실행환경을 찾을 수 없습니다. 기본 AI 런타임을 먼저 포함해 주세요.`r`n"
} elseif (-not $avCassAssetsReady -or -not (Test-Path -LiteralPath (Join-Path $portableFfmpeg "ffmpeg.exe") -PathType Leaf)) {
    $usage += "`r`n처음 사용하기 전에 video-music-separator-setup.exe를 실행해 주세요.`r`n"
}
$usage | Set-Content -LiteralPath (Join-Path $outputDir "사용법.txt") -Encoding UTF8

Write-Host "이동용 폴더 생성 완료: $outputDir"
