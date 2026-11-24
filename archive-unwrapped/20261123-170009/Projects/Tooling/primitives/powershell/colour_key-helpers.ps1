param(
    [string]$ErrorForeground = 'RED',
    [string]$ErrorBackground = 'BLACK'
)

function Get-WorkspaceRoot {
    param([string]$StartPath = $PSScriptRoot)

    $current = (Resolve-Path -LiteralPath $StartPath).Path
    $fallback = $current
    while ($true) {
        $hasPrismata = Test-Path -LiteralPath (Join-Path $current 'Prismata')
        $hasTuilKit = Test-Path -LiteralPath (Join-Path $current 'tUilKit')
        if ($hasPrismata -and $hasTuilKit) {
            return $current
        }

        $marker = Join-Path $current '.workspace'
        if (Test-Path -LiteralPath $marker) {
            $fallback = $current
        }

        $parent = Split-Path -Path $current -Parent
        if ($parent -eq $current -or [string]::IsNullOrWhiteSpace($parent)) {
            break
        }

        $current = $parent
    }

    return $fallback
}

function Set-Or-InsertLine {
    param(
        [string]$Text,
        [string]$Pattern,
        [string]$Replacement,
        [string]$AnchorPattern
    )

    if ($Text -match $Pattern) {
        return [System.Text.RegularExpressions.Regex]::Replace($Text, $Pattern, $Replacement)
    }

    $anchor = [System.Text.RegularExpressions.Regex]::Match($Text, $AnchorPattern)
    if ($anchor.Success) {
        return $Text.Insert($anchor.Index + $anchor.Length, "`r`n$Replacement")
    }

    return $Text
}

function Update-GlobalSharedColourKey {
    param(
        [string]$ColoursPath,
        [string]$ErrorSpec
    )

    if (-not (Test-Path -LiteralPath $ColoursPath)) {
        Write-Warning "GLOBAL_SHARED colours file not found: $ColoursPath"
        return
    }

    $raw = Get-Content -LiteralPath $ColoursPath -Raw
    $updated = $raw

    $errorKeyPattern = '"!error"\s*:\s*"[^"]*"'
    $errorKeyReplacement = ('"!error"        : "{0}"' -f $ErrorSpec)
    $updated = Set-Or-InsertLine -Text $updated -Pattern $errorKeyPattern -Replacement $errorKeyReplacement -AnchorPattern '"!fail"\s*:\s*"[^"]*"\s*,?'

    $helpPattern = '"!error"\s*:\s*"[^"]*"'
    $helpReplacement = '"!error"         : "For error handling, runtime warnings"'

    # Limit helper update scope to COLOUR_KEY_HELP block to avoid replacing COLOUR_KEY.
    $helpBlockPattern = '(?s)"COLOUR_KEY_HELP"\s*:\s*\{(?<body>.*?)\}\s*,\s*"COLOUR_KEY"'
    $helpBlockMatch = [System.Text.RegularExpressions.Regex]::Match($updated, $helpBlockPattern)
    if ($helpBlockMatch.Success) {
        $body = $helpBlockMatch.Groups['body'].Value
        if ($body -match $helpPattern) {
            $newBody = [System.Text.RegularExpressions.Regex]::Replace($body, $helpPattern, $helpReplacement)
        } else {
            $insertAnchor = [System.Text.RegularExpressions.Regex]::Match($body, '"!fail"\s*:\s*"[^"]*"\s*,?')
            if ($insertAnchor.Success) {
                $newBody = $body.Insert($insertAnchor.Index + $insertAnchor.Length, "`r`n        $helpReplacement")
            } else {
                $newBody = $body
            }
        }

        $updated = $updated.Substring(0, $helpBlockMatch.Groups['body'].Index) + $newBody + $updated.Substring($helpBlockMatch.Groups['body'].Index + $helpBlockMatch.Groups['body'].Length)
    }

    if ($updated -ne $raw) {
        Set-Content -LiteralPath $ColoursPath -Value $updated -Encoding UTF8
        Write-Host ">>> Updated GLOBAL_SHARED COLOURS.json !error mapping to $ErrorSpec" -ForegroundColor Green
    } else {
        Write-Host ">>> GLOBAL_SHARED COLOURS.json already contains expected !error mapping" -ForegroundColor Yellow
    }
}

function Update-TuilkitRgbDictionary {
    param(
        [string]$DictPath,
        [string]$ForegroundName,
        [string]$BackgroundName
    )

    if (-not (Test-Path -LiteralPath $DictPath)) {
        Write-Warning "tUilKit DICT_COLOURS.py not found: $DictPath"
        return
    }

    $raw = Get-Content -LiteralPath $DictPath -Raw
    $updated = $raw

    $defaultRgbByName = @{
        'RED'   = '255;0;0m'
        'BLACK' = '0;0;0m'
    }

    $missing = @()
    foreach ($colour in @($ForegroundName, $BackgroundName)) {
        $pattern = "'" + [System.Text.RegularExpressions.Regex]::Escape($colour) + "'"
        if (-not ([System.Text.RegularExpressions.Regex]::IsMatch($updated, $pattern))) {
            $missing += $colour
        }
    }

    if ($missing.Count -gt 0) {
        $inserted = @()
        foreach ($colour in $missing) {
            if ($defaultRgbByName.ContainsKey($colour)) {
                $entryLine = "    '{0}'          :'{1}'," -f $colour, $defaultRgbByName[$colour]
                $closeIndex = $updated.LastIndexOf('}')
                if ($closeIndex -gt 0) {
                    $updated = $updated.Insert($closeIndex, "$entryLine`r`n")
                    $inserted += $colour
                }
            }
        }

        if ($inserted.Count -gt 0 -and $updated -ne $raw) {
            Set-Content -LiteralPath $DictPath -Value $updated -Encoding UTF8
            Write-Host (">>> Added missing tUilKit RGB entries: {0}" -f ($inserted -join ', ')) -ForegroundColor Green
        }

        $stillMissing = @()
        foreach ($colour in @($ForegroundName, $BackgroundName)) {
            $pattern = "'" + [System.Text.RegularExpressions.Regex]::Escape($colour) + "'"
            if (-not ([System.Text.RegularExpressions.Regex]::IsMatch($updated, $pattern))) {
                $stillMissing += $colour
            }
        }

        if ($stillMissing.Count -gt 0) {
            Write-Warning ("Missing colour definitions in DICT_COLOURS.py: {0}" -f ($stillMissing -join ', '))
            Write-Warning "Add RGB entries for missing colours in tUilKit before using those colour-key values."
        }
    } else {
        Write-Host ">>> tUilKit DICT_COLOURS.py already contains required colours for !error" -ForegroundColor Green
    }
}

$workspaceRoot = Get-WorkspaceRoot
$errorSpec = "${ErrorForeground}|${ErrorBackground}"

$globalSharedColoursPath = Join-Path $workspaceRoot 'Prismata\.workspace\.projects_config\GLOBAL_SHARED.d\COLOURS.json'
if (-not (Test-Path -LiteralPath $globalSharedColoursPath)) {
    $globalSharedColoursPath = Join-Path $workspaceRoot '.workspace\.projects_config\GLOBAL_SHARED.d\COLOURS.json'
}

$tuilkitDictPath = Join-Path $workspaceRoot 'tUilKit\src\tUilKit\dict\DICT_COLOURS.py'
if (-not (Test-Path -LiteralPath $tuilkitDictPath)) {
    $tuilkitDictPath = Join-Path (Split-Path -Path $workspaceRoot -Parent) 'tUilKit\src\tUilKit\dict\DICT_COLOURS.py'
}

Write-Host ">>> Workspace root: $workspaceRoot" -ForegroundColor Cyan
Write-Host ">>> Patching !error colour key to: $errorSpec" -ForegroundColor Cyan

Update-GlobalSharedColourKey -ColoursPath $globalSharedColoursPath -ErrorSpec $errorSpec
Update-TuilkitRgbDictionary -DictPath $tuilkitDictPath -ForegroundName $ErrorForeground -BackgroundName $ErrorBackground

Write-Host '>>> colour_key-helpers completed.' -ForegroundColor Cyan
