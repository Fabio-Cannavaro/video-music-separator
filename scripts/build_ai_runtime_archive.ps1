param(
    [Parameter(Mandatory = $true)]
    [string]$AIRuntimeDirectory,
    [Parameter(Mandatory = $true)]
    [string]$AllowlistPath,
    [string]$OutputDirectory = "",
    [int]$PartSizeMiB = 1900
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Import-Module (Join-Path $scriptDir "release_packaging.psm1") -Force
$runtimeDir = [System.IO.Path]::GetFullPath($AIRuntimeDirectory)
$outputDir = if ($OutputDirectory) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    Join-Path $projectDir "dist\runtime-release"
}
$allowlist = (Resolve-Path -LiteralPath $AllowlistPath -ErrorAction Stop).Path

if ((Split-Path -Leaf $runtimeDir.TrimEnd("\")) -ne "audiosep") {
    throw "AI 런타임 원본 폴더 이름은 audiosep이어야 합니다: $runtimeDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $runtimeDir "env\python.exe") -PathType Leaf)) {
    throw "AI Python 실행환경을 찾을 수 없습니다: $runtimeDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $runtimeDir "avcass\repo\models_avdnr_zero_conv_2vid.py") -PathType Leaf)) {
    throw "AV-CASS 실행 코드를 찾을 수 없습니다: $runtimeDir"
}
if ($PartSizeMiB -le 0 -or $PartSizeMiB -ge 2048) {
    throw "GitHub Release 제한을 위해 PartSizeMiB는 1 이상 2048 미만이어야 합니다."
}
$runtimePrefix = $runtimeDir.TrimEnd("\") + "\"
$resolvedOutput = [System.IO.Path]::GetFullPath($outputDir)
if ($resolvedOutput -eq $runtimeDir -or $resolvedOutput.StartsWith($runtimePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "AI 런타임 배포 출력은 원본 런타임 폴더 밖에 있어야 합니다: $resolvedOutput"
}

$forbidden = @(
    (Join-Path $runtimeDir "audiosep"),
    (Join-Path $runtimeDir "bandit"),
    (Join-Path $runtimeDir "avcass\model\av_cass_checkpoint.pt"),
    (Join-Path $runtimeDir "avcass\model\cavp\cavp_epoch66.ckpt"),
    (Join-Path $runtimeDir "env\Lib\site-packages\pedalboard")
)
$found = @($forbidden | Where-Object { Test-Path -LiteralPath $_ })
$found += @(Get-ChildItem (Join-Path $runtimeDir "env\Lib\site-packages") -Force -ErrorAction Stop |
    Where-Object { $_.Name -like "pedalboard-*.dist-info" })
if ($found.Count -gt 0) {
    throw "런타임 패키지에 배포 제외 항목이 남아 있습니다: $($found -join ', ')"
}

New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$archiveName = "video-music-separator-ai-runtime-0.2.0.zip"
$archivePath = Join-Path $outputDir $archiveName
$stagingDir = Join-Path $outputDir ".runtime-stage.$([System.Guid]::NewGuid().ToString('N'))"
$pendingArchive = Join-Path $outputDir ".$archiveName.pending.$([System.Guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $stagingDir -ErrorAction Stop | Out-Null
try {
    $stagingRuntime = Join-Path $stagingDir "audiosep"
    $requiredRuntimeFiles = @(
        "env/python.exe",
        "avcass/repo/models_avdnr_zero_conv_2vid.py",
        "avcass/deps/diffusers/__init__.py"
    )
    $copiedRuntimeFiles = @(Copy-AllowlistedTree `
        -SourceRoot $runtimeDir `
        -DestinationRoot $stagingRuntime `
        -AllowlistPath $allowlist `
        -RequiredPaths $requiredRuntimeFiles)
    $inventoryPath = Join-Path $stagingRuntime "runtime-file-inventory.json"
    $inventory = @(
        foreach ($relativePath in $copiedRuntimeFiles) {
            $copiedFile = Join-Path $stagingRuntime $relativePath.Replace("/", "\")
            [ordered]@{
                path = $relativePath
                size = (Get-Item -LiteralPath $copiedFile).Length
                sha256 = Get-ReleaseFileSha256 $copiedFile
            }
        }
    )
    [ordered]@{
        schema = 2
        files = $inventory
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $inventoryPath -Encoding UTF8

    $expectedArchiveFiles = @(
        $copiedRuntimeFiles | ForEach-Object { "audiosep/$_" }
        "audiosep/runtime-file-inventory.json"
    )
    Assert-ReleaseTreeMatchesExpected -Root $stagingDir -ExpectedFiles $expectedArchiveFiles
    New-ReleaseZipFromDirectory `
        -SourceRoot $stagingDir `
        -ArchivePath $pendingArchive `
        -ExpectedFiles $expectedArchiveFiles
    if (Test-Path -LiteralPath $archivePath -PathType Leaf) {
        Remove-Item -LiteralPath $archivePath -Force
    }
    Move-Item -LiteralPath $pendingArchive -Destination $archivePath -ErrorAction Stop
} finally {
    if (Test-Path -LiteralPath $pendingArchive -PathType Leaf) {
        Remove-Item -LiteralPath $pendingArchive -Force
    }
    if (Test-Path -LiteralPath $stagingDir -PathType Container) {
        Remove-Item -LiteralPath $stagingDir -Recurse -Force
    }
}

Get-ChildItem $outputDir -Filter "$archiveName.*" -File |
    Where-Object { $_.Name -match '\.\d{3}$' -or $_.Name -like '*.sha256' -or $_.Name -eq 'runtime-parts.json' } |
    Remove-Item -Force

$partBytes = [int64]$PartSizeMiB * 1MB
$buffer = New-Object byte[] (4MB)
$input = [System.IO.File]::OpenRead($archivePath)
$parts = @()
try {
    $partNumber = 1
    while ($input.Position -lt $input.Length) {
        $partName = "$archiveName.$($partNumber.ToString('000'))"
        $partPath = Join-Path $outputDir $partName
        $output = [System.IO.File]::Create($partPath)
        try {
            $written = [int64]0
            while ($written -lt $partBytes -and $input.Position -lt $input.Length) {
                $wanted = [int][Math]::Min($buffer.Length, $partBytes - $written)
                $read = $input.Read($buffer, 0, $wanted)
                if ($read -le 0) { break }
                $output.Write($buffer, 0, $read)
                $written += $read
            }
        } finally {
            $output.Dispose()
        }
        $partHash = Get-ReleaseFileSha256 $partPath
        "$partHash  $partName" | Set-Content -LiteralPath "$partPath.sha256" -Encoding ascii
        $parts += [ordered]@{ name = $partName; size = (Get-Item $partPath).Length; sha256 = $partHash }
        $partNumber += 1
    }
} finally {
    $input.Dispose()
}

$archiveHash = Get-ReleaseFileSha256 $archivePath
$manifest = [ordered]@{
    archive = $archiveName
    archive_size = (Get-Item $archivePath).Length
    archive_sha256 = $archiveHash
    parts = $parts
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputDir "runtime-parts.json") -Encoding UTF8
"$archiveHash  $archiveName" | Set-Content -LiteralPath "$archivePath.sha256" -Encoding ascii

Write-Host "AI 실행환경 압축 및 분할 완료: $outputDir"
Get-Content -LiteralPath (Join-Path $outputDir "runtime-parts.json")
