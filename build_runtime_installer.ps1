param(
    [string]$PythonPath = "",
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = if ($PythonPath) { $PythonPath } else { Join-Path $projectDir ".venv\Scripts\python.exe" }
$outputDir = if ($OutputDirectory) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    Join-Path $projectDir "dist\runtime-installer"
}
$workDir = Join-Path $projectDir "build\runtime-installer"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "빌드용 Python을 찾을 수 없습니다: $python"
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "video-music-separator-setup" `
    --distpath $outputDir `
    --workpath $workDir `
    --specpath $projectDir `
    (Join-Path $projectDir "runtime_asset_installer.py")
if ($LASTEXITCODE -ne 0) {
    throw "필수 구성요소 설치 파일 빌드에 실패했습니다."
}

Write-Host "설치 파일 생성 완료: $(Join-Path $outputDir 'video-music-separator-setup.exe')"
