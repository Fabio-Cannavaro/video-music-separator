Set-StrictMode -Version Latest


function ConvertTo-ReleaseRelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $normalized = $Path.Trim().Replace("\", "/")
    $parts = @($normalized.Split("/"))
    if (
        -not $normalized -or
        [System.IO.Path]::IsPathRooted($normalized) -or
        $normalized.Contains(":") -or
        $parts.Count -eq 0 -or
        @($parts | Where-Object { -not $_ -or $_ -eq "." -or $_ -eq ".." }).Count -gt 0
    ) {
        throw "허용 목록에 안전하지 않은 상대 경로가 있습니다: $Path"
    }
    return $normalized
}


function Get-ReleaseAllowlist {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AllowlistPath
    )

    $resolvedAllowlist = (Resolve-Path -LiteralPath $AllowlistPath -ErrorAction Stop).Path
    $seen = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    $entries = [System.Collections.Generic.List[string]]::new()
    foreach ($line in Get-Content -LiteralPath $resolvedAllowlist -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }
        $relativePath = ConvertTo-ReleaseRelativePath $trimmed
        if (-not $seen.Add($relativePath)) {
            throw "허용 목록에 중복 경로가 있습니다: $relativePath"
        }
        $entries.Add($relativePath)
    }
    if ($entries.Count -eq 0) {
        throw "허용 목록에 복사할 파일이 없습니다: $resolvedAllowlist"
    }
    return $entries.ToArray()
}


function Assert-NoReparsePoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $current = [System.IO.Path]::GetFullPath($Root)
    $rootItem = Get-Item -LiteralPath $current -Force -ErrorAction Stop
    if (
        -not $rootItem.PSIsContainer -or
        ($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0
    ) {
        throw "배포 입력 루트는 실제 폴더여야 하며 링크 또는 재분석 지점일 수 없습니다: $Root"
    }
    foreach ($part in $RelativePath.Split("/")) {
        $current = Join-Path $current $part
        $item = Get-Item -LiteralPath $current -Force -ErrorAction Stop
        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "배포 입력에는 링크 또는 재분석 지점을 사용할 수 없습니다: $RelativePath"
        }
    }
}


function Test-ReleasePathWithin {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $candidate = [System.IO.Path]::GetFullPath($Path).TrimEnd("\")
    $boundary = [System.IO.Path]::GetFullPath($Root).TrimEnd("\")
    return (
        $candidate -eq $boundary -or
        $candidate.StartsWith(
            $boundary + [System.IO.Path]::DirectorySeparatorChar,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    )
}


function Assert-ReleasePathsDisjoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FirstPath,
        [Parameter(Mandatory = $true)]
        [string]$SecondPath,
        [string]$FirstLabel = "첫 번째 경로",
        [string]$SecondLabel = "두 번째 경로"
    )

    if (
        (Test-ReleasePathWithin -Path $FirstPath -Root $SecondPath) -or
        (Test-ReleasePathWithin -Path $SecondPath -Root $FirstPath)
    ) {
        throw "$FirstLabel 및 $SecondLabel 경로는 서로 같거나 포함 관계일 수 없습니다: $FirstPath / $SecondPath"
    }
}


function Copy-AllowlistedTree {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceRoot,
        [Parameter(Mandatory = $true)]
        [string]$DestinationRoot,
        [string]$AllowlistPath = "",
        [string[]]$RelativePaths = @(),
        [string[]]$RequiredPaths = @()
    )

    $sourceItem = Get-Item -LiteralPath $SourceRoot -Force -ErrorAction Stop
    if (
        -not $sourceItem.PSIsContainer -or
        ($sourceItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0
    ) {
        throw "허용 목록 원본은 실제 폴더여야 하며 링크 또는 재분석 지점일 수 없습니다: $SourceRoot"
    }
    $source = (Resolve-Path -LiteralPath $SourceRoot -ErrorAction Stop).Path
    $destination = [System.IO.Path]::GetFullPath($DestinationRoot)
    if (Test-Path -LiteralPath $destination) {
        $destinationItem = Get-Item -LiteralPath $destination -Force -ErrorAction Stop
        if (
            -not $destinationItem.PSIsContainer -or
            ($destinationItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0
        ) {
            throw "허용 목록 복사 대상은 실제 폴더여야 하며 링크 또는 재분석 지점일 수 없습니다: $destination"
        }
        $existing = Get-ChildItem -LiteralPath $destination -Force | Select-Object -First 1
        if ($existing) {
            throw "허용 목록 복사 대상은 비어 있어야 합니다: $destination"
        }
    } else {
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
    }

    if ($AllowlistPath -and $RelativePaths.Count -gt 0) {
        throw "AllowlistPath와 RelativePaths는 동시에 지정할 수 없습니다."
    }
    $entries = if ($AllowlistPath) {
        @(Get-ReleaseAllowlist $AllowlistPath)
    } else {
        @($RelativePaths | ForEach-Object { ConvertTo-ReleaseRelativePath $_ })
    }
    if ($entries.Count -eq 0) {
        throw "복사할 허용 파일 목록이 비어 있습니다."
    }

    $entrySet = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($entry in $entries) {
        if (-not $entrySet.Add($entry)) {
            throw "허용 목록에 중복 경로가 있습니다: $entry"
        }
    }
    foreach ($required in $RequiredPaths) {
        $normalizedRequired = ConvertTo-ReleaseRelativePath $required
        if (-not $entrySet.Contains($normalizedRequired)) {
            throw "허용 목록에 필수 파일이 없습니다: $normalizedRequired"
        }
    }

    $sourcePrefix = $source.TrimEnd("\") + "\"
    $destinationPrefix = $destination.TrimEnd("\") + "\"
    $copied = [System.Collections.Generic.List[string]]::new()
    foreach ($relativePath in $entries) {
        $platformPath = $relativePath.Replace("/", "\")
        $sourcePath = [System.IO.Path]::GetFullPath((Join-Path $source $platformPath))
        if (-not $sourcePath.StartsWith($sourcePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "허용 파일이 원본 루트 밖을 가리킵니다: $relativePath"
        }
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            throw "허용 목록 파일을 찾을 수 없습니다: $relativePath"
        }
        Assert-NoReparsePoint -Root $source -RelativePath $relativePath
        $resolvedSource = (Resolve-Path -LiteralPath $sourcePath -ErrorAction Stop).Path
        if (-not $resolvedSource.StartsWith($sourcePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "허용 파일이 링크를 통해 원본 루트 밖을 가리킵니다: $relativePath"
        }

        $destinationPath = [System.IO.Path]::GetFullPath((Join-Path $destination $platformPath))
        if (-not $destinationPath.StartsWith($destinationPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "허용 파일의 복사 대상이 스테이징 루트 밖입니다: $relativePath"
        }
        $destinationParent = Split-Path -Parent $destinationPath
        New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
        Copy-Item -LiteralPath $resolvedSource -Destination $destinationPath -Force
        $copied.Add($relativePath)
    }
    return $copied.ToArray()
}


function Get-ReleaseTreeFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $resolvedRoot = (Resolve-Path -LiteralPath $Root -ErrorAction Stop).Path
    $rootPrefix = $resolvedRoot.TrimEnd("\") + "\"
    $files = [System.Collections.Generic.List[string]]::new()
    foreach ($item in Get-ChildItem -LiteralPath $resolvedRoot -Recurse -Force) {
        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "배포 스테이징에는 링크 또는 재분석 지점을 둘 수 없습니다: $($item.FullName)"
        }
        if (-not $item.PSIsContainer) {
            $files.Add($item.FullName.Substring($rootPrefix.Length).Replace("\", "/"))
        }
    }
    return $files.ToArray()
}


function Get-ReleaseFileSha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $stream = [System.IO.File]::OpenRead([System.IO.Path]::GetFullPath($Path))
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $digest = $sha256.ComputeHash($stream)
        return ([System.BitConverter]::ToString($digest).Replace("-", "").ToLowerInvariant())
    } finally {
        $sha256.Dispose()
        $stream.Dispose()
    }
}


function Assert-ReleaseTreeMatchesExpected {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [string[]]$ExpectedFiles
    )

    $expected = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($path in $ExpectedFiles) {
        $normalized = ConvertTo-ReleaseRelativePath $path
        if (-not $expected.Add($normalized)) {
            throw "예상 배포 파일 목록에 중복 경로가 있습니다: $normalized"
        }
    }
    $actual = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($path in Get-ReleaseTreeFiles $Root) {
        $actual.Add($path) | Out-Null
    }

    $unexpected = @($actual | Where-Object { -not $expected.Contains($_) } | Sort-Object)
    $missing = @($expected | Where-Object { -not $actual.Contains($_) } | Sort-Object)
    if ($unexpected.Count -gt 0 -or $missing.Count -gt 0) {
        $details = @()
        if ($unexpected.Count -gt 0) { $details += "예상 밖 파일: $($unexpected -join ', ')" }
        if ($missing.Count -gt 0) { $details += "누락 파일: $($missing -join ', ')" }
        throw "배포 스테이징 파일 목록이 허용 목록과 다릅니다. $($details -join '; ')"
    }
}


function Assert-ZipEntriesMatchExpected {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ArchivePath,
        [Parameter(Mandatory = $true)]
        [string[]]$ExpectedFiles
    )

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $expected = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    $expectedDirectories = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($path in $ExpectedFiles) {
        $normalizedExpected = ConvertTo-ReleaseRelativePath $path
        if (-not $expected.Add($normalizedExpected)) {
            throw "예상 배포 ZIP 파일 목록에 중복 경로가 있습니다: $normalizedExpected"
        }
        $parts = @($normalizedExpected.Split("/"))
        for ($index = 1; $index -lt $parts.Count; $index += 1) {
            $expectedDirectories.Add(($parts[0..($index - 1)] -join "/")) | Out-Null
        }
    }
    $actual = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    $archive = [System.IO.Compression.ZipFile]::OpenRead(
        [System.IO.Path]::GetFullPath($ArchivePath)
    )
    try {
        foreach ($entry in $archive.Entries) {
            if ($entry.FullName.StartsWith("./") -or $entry.FullName.Contains("\")) {
                throw "Windows 기본 압축 풀기와 호환되지 않는 ZIP 경로입니다: $($entry.FullName)"
            }
            if (-not $entry.Name) {
                $directoryPath = ConvertTo-ReleaseRelativePath $entry.FullName.TrimEnd("/")
                if (-not $expectedDirectories.Contains($directoryPath)) {
                    throw "배포 ZIP에 예상 밖 폴더 항목이 있습니다: $directoryPath"
                }
                continue
            }
            $normalized = ConvertTo-ReleaseRelativePath $entry.FullName
            if (-not $actual.Add($normalized)) {
                throw "배포 ZIP에 중복 파일 경로가 있습니다: $normalized"
            }
        }
    } finally {
        $archive.Dispose()
    }
    $unexpected = @($actual | Where-Object { -not $expected.Contains($_) } | Sort-Object)
    $missing = @($expected | Where-Object { -not $actual.Contains($_) } | Sort-Object)
    if ($unexpected.Count -gt 0 -or $missing.Count -gt 0) {
        throw "배포 ZIP 파일 목록이 검증된 스테이징과 다릅니다."
    }
}


function New-ReleaseZipFromDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceRoot,
        [Parameter(Mandatory = $true)]
        [string]$ArchivePath,
        [Parameter(Mandatory = $true)]
        [string[]]$ExpectedFiles
    )

    $source = (Resolve-Path -LiteralPath $SourceRoot -ErrorAction Stop).Path
    $sourcePrefix = $source.TrimEnd("\") + "\"
    $archiveFile = [System.IO.Path]::GetFullPath($ArchivePath)
    if (
        $archiveFile.StartsWith($sourcePrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
        (Test-Path -LiteralPath $archiveFile)
    ) {
        throw "새 배포 ZIP은 스테이징 밖의 존재하지 않는 파일 경로에 만들어야 합니다: $archiveFile"
    }
    Assert-ReleaseTreeMatchesExpected -Root $source -ExpectedFiles $ExpectedFiles

    Add-Type -AssemblyName System.IO.Compression
    $archiveStream = [System.IO.File]::Open(
        $archiveFile,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
    $archive = [System.IO.Compression.ZipArchive]::new(
        $archiveStream,
        [System.IO.Compression.ZipArchiveMode]::Create,
        $false
    )
    try {
        foreach ($path in $ExpectedFiles) {
            $normalized = ConvertTo-ReleaseRelativePath $path
            $sourcePath = [System.IO.Path]::GetFullPath(
                (Join-Path $source $normalized.Replace("/", "\"))
            )
            if (
                -not $sourcePath.StartsWith($sourcePrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
                -not (Test-Path -LiteralPath $sourcePath -PathType Leaf)
            ) {
                throw "배포 ZIP 원본 파일을 찾을 수 없습니다: $normalized"
            }
            $entry = $archive.CreateEntry(
                $normalized,
                [System.IO.Compression.CompressionLevel]::Optimal
            )
            $input = [System.IO.File]::OpenRead($sourcePath)
            $output = $entry.Open()
            try {
                $input.CopyTo($output)
            } finally {
                $output.Dispose()
                $input.Dispose()
            }
        }
    } finally {
        $archive.Dispose()
        $archiveStream.Dispose()
    }
    Assert-ZipEntriesMatchExpected -ArchivePath $archiveFile -ExpectedFiles $ExpectedFiles
}


function New-ReleaseStagingDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DestinationPath
    )

    $destination = [System.IO.Path]::GetFullPath($DestinationPath).TrimEnd("\")
    $parent = Split-Path -Parent $destination
    $leaf = Split-Path -Leaf $destination
    if (-not $parent -or -not $leaf) {
        throw "배포 출력 경로로 파일 시스템 루트를 사용할 수 없습니다: $destination"
    }
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $staging = Join-Path $parent ".$leaf.stage.$([System.Guid]::NewGuid().ToString('N'))"
    New-Item -ItemType Directory -Path $staging -ErrorAction Stop | Out-Null
    return [System.IO.Path]::GetFullPath($staging)
}


function Publish-ReleaseStagingDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StagingPath,
        [Parameter(Mandatory = $true)]
        [string]$DestinationPath
    )

    $staging = (Resolve-Path -LiteralPath $StagingPath -ErrorAction Stop).Path.TrimEnd("\")
    $destination = [System.IO.Path]::GetFullPath($DestinationPath).TrimEnd("\")
    $destinationParent = Split-Path -Parent $destination
    $destinationLeaf = Split-Path -Leaf $destination
    $stagingParent = Split-Path -Parent $staging
    if (
        -not $destinationParent -or
        -not $destinationLeaf -or
        $stagingParent -ne $destinationParent -or
        -not (Split-Path -Leaf $staging).StartsWith(".$destinationLeaf.stage.")
    ) {
        throw "스테이징 폴더가 대상 폴더의 검증된 임시 경로가 아닙니다: $staging"
    }
    $stagingItem = Get-Item -LiteralPath $staging -Force
    if (($stagingItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "스테이징 폴더는 링크 또는 재분석 지점일 수 없습니다: $staging"
    }

    $backup = Join-Path $destinationParent ".$destinationLeaf.previous.$([System.Guid]::NewGuid().ToString('N'))"
    $movedPrevious = $false
    try {
        if (Test-Path -LiteralPath $destination) {
            Move-Item -LiteralPath $destination -Destination $backup -ErrorAction Stop
            $movedPrevious = $true
        }
        Move-Item -LiteralPath $staging -Destination $destination -ErrorAction Stop
    } catch {
        if ($movedPrevious -and -not (Test-Path -LiteralPath $destination) -and (Test-Path -LiteralPath $backup)) {
            Move-Item -LiteralPath $backup -Destination $destination -ErrorAction SilentlyContinue
        }
        throw
    }
    if ($movedPrevious -and (Test-Path -LiteralPath $backup)) {
        Remove-Item -LiteralPath $backup -Recurse -Force
    }
}


Export-ModuleMember -Function @(
    "Assert-NoReparsePoint",
    "Assert-ReleasePathsDisjoint",
    "Assert-ReleaseTreeMatchesExpected",
    "Assert-ZipEntriesMatchExpected",
    "Copy-AllowlistedTree",
    "Get-ReleaseAllowlist",
    "Get-ReleaseFileSha256",
    "Get-ReleaseTreeFiles",
    "New-ReleaseZipFromDirectory",
    "New-ReleaseStagingDirectory",
    "Publish-ReleaseStagingDirectory",
    "Test-ReleasePathWithin"
)
