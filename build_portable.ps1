param(
    [string]$PythonPath = "",
    [string]$OutputDirectory = ""
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
$ffmpegDir = "C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "빌드용 Python을 찾을 수 없습니다: $python"
}
if (-not (Test-Path -LiteralPath $ffmpegDir -PathType Container)) {
    throw "FFmpeg 폴더를 찾을 수 없습니다: $ffmpegDir"
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

$portableFfmpeg = Join-Path $outputDir "ffmpeg"
$portableAudioSep = Join-Path $outputDir "audiosep"
New-Item -ItemType Directory -Path $portableFfmpeg -Force | Out-Null
New-Item -ItemType Directory -Path $portableAudioSep -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $ffmpegDir "ffmpeg.exe") -Destination $portableFfmpeg -Force
Copy-Item -LiteralPath (Join-Path $ffmpegDir "ffprobe.exe") -Destination $portableFfmpeg -Force
Copy-Item -LiteralPath (Join-Path $ffmpegDir "ffplay.exe") -Destination $portableFfmpeg -Force
Copy-Item -LiteralPath (Join-Path $projectDir "bandit_worker.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "audiosep_worker.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "avcass_worker.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "separation_quality.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "LICENSE") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "MODEL_LICENSES.md") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "THIRD_PARTY_NOTICES.md") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "licenses") -Destination $outputDir -Recurse -Force

$avCassReady =
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "env\python.exe") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "avcass\repo\models_avdnr_zero_conv_2vid.py") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "avcass\deps\diffusers\__init__.py") -PathType Leaf) -and
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

영상을 연 뒤 'AV-CASS로 분리'를 누르세요.
AV-CASS는 속도보다 분리 품질과 원본 스테레오 보존을 우선합니다.
AV-CASS는 영상 장면까지 분석하며 NVIDIA GPU가 필요합니다.
앱 맨 위의 작은 영상 화면에서 전체 믹스와 각 분리본을 영상과 함께 확인할 수 있습니다.
음악 행을 뮤트한 뒤 전체 영상을 재생하고, 원본 옆에 _음악제거 사본으로 저장할 수 있습니다.
두 행의 듣기/정지, 행별 뮤트/해제, 공통 볼륨 조절 기능이 포함되어 있습니다.
인터넷 연결이나 별도 Python 설치는 필요하지 않습니다.

처리할 영상·음원의 저작권과 이용 권리를 확인하고, 결과물을 사용하는 책임은 사용자에게 있습니다.
앱의 '라이선스·출처'에서 제3자 고지, 출처, 논문과 라이선스 전문을 확인할 수 있습니다.
"@
if (-not $avCassReady) {
    $usage += "`r`nAV-CASS 실행 파일이나 모델을 찾을 수 없습니다.`r`n"
}
$usage | Set-Content -LiteralPath (Join-Path $outputDir "사용법.txt") -Encoding UTF8

Write-Host "이동용 폴더 생성 완료: $outputDir"
