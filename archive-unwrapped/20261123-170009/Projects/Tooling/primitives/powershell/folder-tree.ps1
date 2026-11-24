function Test-PathFolderMatch {
    param(
        [string]$Path,
        [string[]]$FolderNames
    )

    if (-not $FolderNames -or $FolderNames.Count -eq 0) { return $false }
    $segments = $Path -split '[\\/]'
    foreach ($folderName in $FolderNames) {
        if (-not [string]::IsNullOrWhiteSpace($folderName) -and ($segments -contains $folderName)) {
            return $true
        }
    }

    return $false
}

function New-FolderTreeText {
    param(
        [string]$RootPath,
        [string[]]$IncludeTypes,
        [string[]]$IgnoreTypes,
        [string[]]$SummarizeTypes,
        [string[]]$IncludeFolders,
        [string[]]$IgnoreFolders,
        [string[]]$SummarizeFolders,
        [bool]$AddFilesAsLeaves = $true,
        [scriptblock]$SummarizationCallback
    )

    $lines = [System.Collections.Generic.List[string]]::new()
    $rootName = Split-Path -Path $RootPath -Leaf
    [void]$lines.Add($rootName)

    function Add-Node {
        param(
            [string]$CurrentPath,
            [string]$Prefix
        )

        $dirs = @(Get-ChildItem -Path $CurrentPath -Directory -ErrorAction SilentlyContinue | Sort-Object Name)
        $files = @(Get-ChildItem -Path $CurrentPath -File -ErrorAction SilentlyContinue | Sort-Object Name)

        $visibleDirs = @()
        foreach ($dir in $dirs) {
            if (Test-PathFolderMatch -Path $dir.FullName -FolderNames $IgnoreFolders) { continue }
            $visibleDirs += $dir
        }

        $visibleFiles = @()
        if ($AddFilesAsLeaves) {
            foreach ($file in $files) {
                if (Test-PathFolderMatch -Path $file.FullName -FolderNames $IgnoreFolders) { continue }
                if ($IncludeFolders -and $IncludeFolders.Count -gt 0 -and -not (Test-PathFolderMatch -Path $file.FullName -FolderNames $IncludeFolders)) {
                    continue
                }

                $ext = [System.IO.Path]::GetExtension($file.FullName)
                if ($IgnoreTypes -contains $ext) { continue }
                if ($IncludeTypes -and $IncludeTypes.Count -gt 0 -and ($IncludeTypes -notcontains '*') -and -not ($IncludeTypes -contains $ext)) {
                    continue
                }

                $visibleFiles += $file
            }
        }

        $allItems = @($visibleDirs + $visibleFiles)
        for ($i = 0; $i -lt $allItems.Count; $i++) {
            $item = $allItems[$i]
            $isLast = ($i -eq ($allItems.Count - 1))
            $branch = if ($isLast) { '\-- ' } else { '|-- ' }
            $nextPrefix = if ($isLast) { "$Prefix    " } else { "$Prefix|   " }

            if ($item.PSIsContainer) {
                if ($SummarizeFolders -contains $item.Name) {
                    $summaryLine = if ($SummarizationCallback) {
                        & $SummarizationCallback $item.FullName $IgnoreTypes $SummarizeTypes
                    } else {
                        "[summary] $($item.Name)"
                    }
                    [void]$lines.Add("$Prefix$branch$summaryLine")
                } else {
                    [void]$lines.Add("$Prefix$branch$($item.Name)/")
                    Add-Node -CurrentPath $item.FullName -Prefix $nextPrefix
                }
            } else {
                [void]$lines.Add("$Prefix$branch$($item.Name)")
            }
        }
    }

    Add-Node -CurrentPath $RootPath -Prefix ''
    return ($lines -join "`n")
}