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
$python = if ($PythonPath) { $PythonPath } else { Join-Path $projectDir ".venv\Scripts\python.exe" }
$outputDir = if ($OutputDirectory) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    Join-Path $projectDir "dist\runtime-installer"
}
$workDir = Join-Path $projectDir "build\runtime-installer-work"
$specDir = Join-Path $projectDir "build\runtime-installer-spec"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "빌드용 Python을 찾을 수 없습니다: $python"
}

New-Item -ItemType Directory -Path $outputDir, $workDir, $specDir -Force | Out-Null

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "video-music-separator-setup" `
    --distpath $outputDir `
    --workpath $workDir `
    --specpath $specDir `
    --paths $appDir `
    (Join-Path $appDir "runtime_asset_installer.py")
if ($LASTEXITCODE -ne 0) {
    throw "필수 구성요소 설치 파일 빌드에 실패했습니다."
}

$setupPath = Join-Path $outputDir "video-music-separator-setup.exe"
if ($CodeSigningCertificateThumbprint) {
    $certificatePath = "Cert:\CurrentUser\My\$CodeSigningCertificateThumbprint"
    $certificate = Get-Item -LiteralPath $certificatePath -ErrorAction Stop
    $signature = Set-AuthenticodeSignature `
        -FilePath $setupPath `
        -Certificate $certificate `
        -HashAlgorithm SHA256 `
        -TimestampServer $TimestampServer
    if ($signature.Status -ne "Valid") {
        throw "설치 파일 코드 서명에 실패했습니다: $($signature.StatusMessage)"
    }
    Write-Host "설치 파일 코드 서명 완료: $($certificate.Thumbprint)"
} else {
    Write-Warning "코드 서명 인증서가 지정되지 않아 설치 파일은 미서명 상태입니다."
}

$setupHash = (Get-FileHash -LiteralPath $setupPath -Algorithm SHA256).Hash.ToLowerInvariant()
$setupHashPath = "$setupPath.sha256"
"$setupHash  $([System.IO.Path]::GetFileName($setupPath))" |
    Set-Content -LiteralPath $setupHashPath -Encoding ascii

Write-Host "설치 파일 생성 완료: $setupPath"
Write-Host "설치 파일 SHA-256: $setupHashPath"
