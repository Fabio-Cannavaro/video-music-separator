param(
    [Parameter(Mandatory = $true)]
    [string]$AIRuntimeDirectory,
    [string]$OutputDirectory = "",
    [int]$PartSizeMiB = 1900
)

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = [System.IO.Path]::GetFullPath($AIRuntimeDirectory)
$outputDir = if ($OutputDirectory) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    Join-Path $projectDir "dist\runtime-release"
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
if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}

& tar.exe -a -c -f $archivePath -C (Split-Path -Parent $runtimeDir) (Split-Path -Leaf $runtimeDir)
if ($LASTEXITCODE -ne 0) {
    throw "AI 실행환경 ZIP64 압축 생성에 실패했습니다."
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
        $partHash = (Get-FileHash -LiteralPath $partPath -Algorithm SHA256).Hash.ToLowerInvariant()
        "$partHash  $partName" | Set-Content -LiteralPath "$partPath.sha256" -Encoding ascii
        $parts += [ordered]@{ name = $partName; size = (Get-Item $partPath).Length; sha256 = $partHash }
        $partNumber += 1
    }
} finally {
    $input.Dispose()
}

$archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
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
