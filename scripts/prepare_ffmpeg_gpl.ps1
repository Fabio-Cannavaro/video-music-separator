param(
    [string]$DestinationDirectory = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$destinationDir = if ($DestinationDirectory) {
    [System.IO.Path]::GetFullPath($DestinationDirectory)
} else {
    Join-Path $projectDir "third_party\ffmpeg-gpl"
}

$archiveName = "ffmpeg-release-essentials.zip"
$downloadUrl = "https://www.gyan.dev/ffmpeg/builds/$archiveName"
$checksumUrl = "${downloadUrl}.sha256"
$versionUrl = "${downloadUrl}.ver"

function Test-GplFfmpeg([string]$Root, [string]$ExpectedVersion) {
    $binDir = Join-Path $Root "bin"
    foreach ($name in @("ffmpeg.exe", "ffprobe.exe", "ffplay.exe")) {
        $program = Join-Path $binDir $name
        if (-not (Test-Path -LiteralPath $program -PathType Leaf)) {
            return $false
        }
        $versionText = (& $program -version 2>&1 | Out-String)
        if (
            $LASTEXITCODE -ne 0 -or
            -not $versionText.Contains("$($name.Replace('.exe', '')) version $ExpectedVersion-") -or
            -not $versionText.Contains("-essentials_build-www.gyan.dev") -or
            -not $versionText.Contains("--enable-gpl") -or
            -not $versionText.Contains("--enable-version3") -or
            -not $versionText.Contains("--enable-static") -or
            $versionText.Contains("--enable-nonfree")
        ) {
            return $false
        }
    }
    return $true
}

$expectedVersion = ([string](Invoke-RestMethod -Uri $versionUrl)).Trim()
$expectedSha256 = ([string](Invoke-RestMethod -Uri $checksumUrl)).Trim().ToUpperInvariant()
if ($expectedVersion -notmatch '^\d+\.\d+(\.\d+)?$') {
    throw "Gyan FFmpeg 버전 정보가 올바르지 않습니다: $expectedVersion"
}
if ($expectedSha256 -notmatch '^[0-9A-F]{64}$') {
    throw "Gyan FFmpeg SHA-256 정보가 올바르지 않습니다."
}

if (Test-GplFfmpeg $destinationDir $expectedVersion) {
    Write-Host "GPL FFmpeg 준비 완료: $destinationDir"
    exit 0
}

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
    if (-not $sourceRoot -or -not (Test-GplFfmpeg $sourceRoot.FullName $expectedVersion)) {
        throw "다운로드한 파일이 지정된 GPL Essentials FFmpeg 빌드가 아닙니다."
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

if (-not (Test-GplFfmpeg $destinationDir $expectedVersion)) {
    throw "GPL FFmpeg 준비 결과를 검증하지 못했습니다."
}

Write-Host "GPL FFmpeg 준비 완료: $destinationDir"
