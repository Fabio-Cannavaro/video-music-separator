param(
    [string]$DestinationDirectory = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$destinationDir = if ($DestinationDirectory) {
    [System.IO.Path]::GetFullPath($DestinationDirectory)
} else {
    Join-Path $projectDir "third_party\ffmpeg-lgpl"
}

$archiveName = "ffmpeg-n8.1-latest-win64-lgpl-shared-8.1.zip"
$releaseApiUrl = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/latest"
$expectedVersionFamily = "ffmpeg version n8.1"

function Test-LgplFfmpeg([string]$Root) {
    $binDir = Join-Path $Root "bin"
    $ffmpeg = Join-Path $binDir "ffmpeg.exe"
    $requiredFiles = @(
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
    foreach ($name in $requiredFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $binDir $name) -PathType Leaf)) {
            return $false
        }
    }

    $versionText = (& $ffmpeg -version 2>&1 | Out-String)
    return (
        $LASTEXITCODE -eq 0 -and
        $versionText.Contains($expectedVersionFamily) -and
        $versionText.Contains("--enable-shared") -and
        -not $versionText.Contains("--enable-gpl") -and
        -not $versionText.Contains("--enable-nonfree")
    )
}

if (Test-LgplFfmpeg $destinationDir) {
    Write-Host "LGPL FFmpeg 준비 완료: $destinationDir"
    exit 0
}

$release = Invoke-RestMethod -Uri $releaseApiUrl -Headers @{ Accept = "application/vnd.github+json" }
$asset = $release.assets | Where-Object { $_.name -eq $archiveName } | Select-Object -First 1
if (-not $asset) {
    throw "BtbN 공식 latest Release에서 FFmpeg 8.1 LGPL 공유 빌드를 찾지 못했습니다."
}
$downloadUrl = [string]$asset.browser_download_url
$digestParts = ([string]$asset.digest).Split(':', 2)
if ($digestParts.Count -ne 2 -or $digestParts[0] -ne "sha256" -or $digestParts[1].Length -ne 64) {
    throw "BtbN FFmpeg Release의 SHA-256 정보가 올바르지 않습니다."
}
$expectedSha256 = $digestParts[1].ToUpperInvariant()

$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("video-music-separator-ffmpeg-" + [guid]::NewGuid().ToString("N"))
$archivePath = Join-Path $temporaryRoot $archiveName
$extractDir = Join-Path $temporaryRoot "extracted"

try {
    New-Item -ItemType Directory -Path $temporaryRoot -Force | Out-Null
    Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath

    $actualSha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
    if ($actualSha256 -ne $expectedSha256) {
        throw "FFmpeg 다운로드 체크섬이 일치하지 않습니다. 예상: $expectedSha256 / 실제: $actualSha256"
    }

    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractDir -Force
    $sourceRoot = Get-ChildItem -LiteralPath $extractDir -Directory | Select-Object -First 1
    if (-not $sourceRoot -or -not (Test-LgplFfmpeg $sourceRoot.FullName)) {
        throw "다운로드한 파일이 지정된 LGPL 공유 FFmpeg 빌드가 아닙니다."
    }

    if (Test-Path -LiteralPath $destinationDir) {
        $resolvedProject = [System.IO.Path]::GetFullPath($projectDir).TrimEnd('\') + '\'
        $resolvedDestination = [System.IO.Path]::GetFullPath($destinationDir)
        if (-not $resolvedDestination.StartsWith($resolvedProject, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "프로젝트 밖의 기존 폴더는 자동 교체하지 않습니다: $resolvedDestination"
        }
        Remove-Item -LiteralPath $destinationDir -Recurse -Force
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $destinationDir) -Force | Out-Null
    Move-Item -LiteralPath $sourceRoot.FullName -Destination $destinationDir
} finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}

if (-not (Test-LgplFfmpeg $destinationDir)) {
    throw "LGPL FFmpeg 준비 결과를 검증하지 못했습니다."
}

Write-Host "LGPL FFmpeg 준비 완료: $destinationDir"
