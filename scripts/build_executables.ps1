param(
    [string]$PythonPath = "",
    [string]$OutputDirectory = "",
    [string]$CodeSigningCertificateThumbprint = "",
    [string]$TimestampServer = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$appDir = Join-Path $projectDir "app"
$outputDir = if ($OutputDirectory) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    $projectDir
}
$python = if ($PythonPath) { $PythonPath } else { Join-Path $projectDir ".venv\Scripts\python.exe" }
$appDistDir = Join-Path $projectDir "dist\app"
$appWorkDir = Join-Path $projectDir "build\app"
$specDir = Join-Path $projectDir "build\spec"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "빌드용 Python을 찾을 수 없습니다: $python"
}

New-Item -ItemType Directory -Path $outputDir, $appDistDir, $appWorkDir, $specDir -Force | Out-Null

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name "video-music-separator" `
    --paths $appDir `
    --distpath $appDistDir `
    --workpath $appWorkDir `
    --specpath $specDir `
    (Join-Path $appDir "sound_separator_app.py")
if ($LASTEXITCODE -ne 0) {
    throw "앱 실행 파일 빌드에 실패했습니다."
}

$appExecutable = Join-Path $appDistDir "video-music-separator.exe"
if ($CodeSigningCertificateThumbprint) {
    $certificatePath = "Cert:\CurrentUser\My\$CodeSigningCertificateThumbprint"
    $certificate = Get-Item -LiteralPath $certificatePath -ErrorAction Stop
    $signature = Set-AuthenticodeSignature `
        -FilePath $appExecutable `
        -Certificate $certificate `
        -HashAlgorithm SHA256 `
        -TimestampServer $TimestampServer
    if ($signature.Status -ne "Valid") {
        throw "앱 실행 파일 코드 서명에 실패했습니다: $($signature.StatusMessage)"
    }
} else {
    Write-Warning "코드 서명 인증서가 지정되지 않아 앱 실행 파일은 미서명 상태입니다."
}

$installerArguments = @{
    PythonPath = $python
    OutputDirectory = (Join-Path $projectDir "dist\runtime-installer")
    TimestampServer = $TimestampServer
}
if ($CodeSigningCertificateThumbprint) {
    $installerArguments.CodeSigningCertificateThumbprint = $CodeSigningCertificateThumbprint
}
& (Join-Path $scriptDir "build_runtime_installer.ps1") @installerArguments
if ($LASTEXITCODE -ne 0) {
    throw "필수 구성요소 설치 파일 빌드에 실패했습니다."
}

$setupExecutable = Join-Path $projectDir "dist\runtime-installer\video-music-separator-setup.exe"
Copy-Item -LiteralPath $appExecutable -Destination (Join-Path $outputDir "video-music-separator.exe") -Force
Copy-Item -LiteralPath $setupExecutable -Destination (Join-Path $outputDir "video-music-separator-setup.exe") -Force

Write-Host "실행 파일 생성 완료: $(Join-Path $outputDir 'video-music-separator.exe')"
Write-Host "설치 파일 생성 완료: $(Join-Path $outputDir 'video-music-separator-setup.exe')"
