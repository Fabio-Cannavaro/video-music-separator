$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoDir = Split-Path -Parent $projectDir
$outputDir = Join-Path $repoDir "video-music-separator-portable"
$buildDir = Join-Path $projectDir "build"
$distDir = Join-Path $projectDir "dist"
$python = Join-Path $projectDir ".venv\Scripts\python.exe"
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
Copy-Item -LiteralPath (Join-Path $projectDir "tiger_worker.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "bandit_worker.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "audiosep_worker.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "avcass_worker.py") -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $projectDir "separation_quality.py") -Destination $outputDir -Force

$tigerReady =
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "env\python.exe") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "tiger\repo\look2hear\models\tiger_dnr.py") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "tiger\model\config.json") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "tiger\model\model.safetensors") -PathType Leaf)
$banditReady =
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "env\python.exe") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "bandit\repo\core\__init__.py") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "bandit\hparams.yaml") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "bandit\model\dnr-3s-mus64-l1snr-plus.ckpt") -PathType Leaf)
$audioSepReady =
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "env\python.exe") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "audiosep\repo\models\resunet.py") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "audiosep\model\pytorch_model.bin") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "audiosep\roberta-base\model.safetensors") -PathType Leaf)
$avCassReady =
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "env\python.exe") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "avcass\repo\models_avdnr_zero_conv_2vid.py") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "avcass\deps\diffusers\__init__.py") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "avcass\model\av_cass_checkpoint.pt") -PathType Leaf) -and
    (Test-Path -LiteralPath (Join-Path $portableAudioSep "avcass\model\cavp\cavp_epoch66.ckpt") -PathType Leaf)

if ($tigerReady) {
    $usage = @"
같은 PC에서는 이 폴더를 복사하지 말고 현재 위치에서 실행하세요.
어느 폴더의 영상이든 영상 열기로 선택할 수 있고, 결과는 원본 영상 옆에 저장됩니다.
자주 쓸 때는 video-music-separator.exe의 바로가기를 만들어 두면 됩니다.
다른 PC로 옮길 때만 이 폴더 전체를 함께 이동하세요.

실행: video-music-separator.exe

영상을 연 뒤 AV-CASS 또는 TIGER-DnR 라디오 버튼을 선택하고 '선택 모델로 분리'를 누르세요.
각 모델은 같은 원본에서 독립적으로 분리되며, 모델을 바꾸면 기존 결과를 즉시 다시 불러옵니다.
두 모델 모두 속도보다 분리 품질과 원본 스테레오 보존을 우선합니다.
AV-CASS는 영상 장면까지 분석하며 NVIDIA GPU가 필요합니다.
앱 맨 위의 작은 영상 화면에서 전체 믹스와 각 분리본을 영상과 함께 확인할 수 있습니다.
음악 행을 뮤트한 뒤 전체 영상을 재생하고, 원본 옆에 _음악제거 사본으로 저장할 수 있습니다.
두 행의 듣기/정지, 행별 뮤트/해제, 공통 볼륨 조절 기능이 포함되어 있습니다.
인터넷 연결이나 별도 Python 설치는 필요하지 않습니다.
NVIDIA GPU가 없으면 TIGER-DnR 분리가 CPU로 실행되어 느릴 수 있습니다.
"@
    if (-not $banditReady) {
        $usage += "`r`nBandIt 실행 파일이 없어 BandIt 선택은 비활성화됩니다.`r`n"
    }
    if (-not $audioSepReady) {
        $usage += "`r`nAudioSep 실행 파일이 없어 AudioSep 선택은 비활성화됩니다.`r`n"
    }
    if (-not $avCassReady) {
        $usage += "`r`nAV-CASS 실행 파일이 없어 AV-CASS 선택은 비활성화됩니다.`r`n"
    }
} else {
    $usage = @"
같은 PC에서는 이 폴더를 복사하지 말고 현재 위치에서 실행하세요.
다른 PC로 옮길 때만 이 폴더 전체를 함께 이동하세요.

실행: video-music-separator.exe

TIGER-DnR 음악 분리 런타임이 아직 포함되지 않았습니다.
"@
}
$usage | Set-Content -LiteralPath (Join-Path $outputDir "사용법.txt") -Encoding UTF8

Write-Host "이동용 폴더 생성 완료: $outputDir"
