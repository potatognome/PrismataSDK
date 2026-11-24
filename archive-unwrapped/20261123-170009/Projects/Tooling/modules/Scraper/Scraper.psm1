# ---------------------------------------------------------
# Workspace Root Discovery
# ---------------------------------------------------------
function Get-WorkspaceRoot {
    param(
        [string]$StartPath = (Resolve-Path ".").Path
    )

    $current = $StartPath
    while ($true) {
        $marker = Join-Path $current ".workspace"
        if (Test-Path $marker) { return $current }

        $parent = Split-Path $current -Parent
        if ($parent -eq $current -or [string]::IsNullOrEmpty($parent)) {
            return $StartPath
        }
        $current = $parent
    }
}

function Get-ScraperProjectColoursPath {
    $workspaceRoot = Get-WorkspaceRoot
    $projectColours = Join-Path $workspaceRoot 'Prismata\.workspace\.projects_config\GLOBAL_SHARED.d\COLOURS.json'
    if (Test-Path -LiteralPath $projectColours) {
        return (Resolve-Path -LiteralPath $projectColours).Path
    }

    return $null
}

function Get-ScraperDictColoursPath {
    $workspaceRoot = Get-WorkspaceRoot
    $dictPath = Join-Path $workspaceRoot 'tUilKit\src\tUilKit\dict\DICT_COLOURS.py'
    if (Test-Path -LiteralPath $dictPath) {
        return (Resolve-Path -LiteralPath $dictPath).Path
    }

    return $null
}

function Get-ScraperColourKeyMap {
    $coloursPath = Get-ScraperProjectColoursPath
    if (-not $coloursPath) {
        return @{}
    }

    try {
        $json = Get-Content -LiteralPath $coloursPath -Raw | ConvertFrom-Json
        if ($json -and $json.COLOUR_KEY) {
            return @{} + $json.COLOUR_KEY
        }
    } catch {
    }

    return @{}
}

function Get-ScraperRgbDictionary {
    $dictPath = Get-ScraperDictColoursPath
    if (-not $dictPath) {
        return @{}
    }

    $rgb = @{}
    foreach ($line in (Get-Content -LiteralPath $dictPath)) {
        if ($line -match "^\s*'([^']+)'\s*:\s*'(\d+;\d+;\d+)m'\s*,?\s*$") {
            $rgb[$Matches[1]] = $Matches[2]
        }
    }

    return $rgb
}

function Convert-ScraperColourNameToRgb {
    param(
        [string]$ColourName,
        [hashtable]$RgbDictionary
    )

    if (-not $ColourName -or -not $RgbDictionary) {
        return $null
    }

    if ($RgbDictionary.ContainsKey($ColourName)) {
        return $RgbDictionary[$ColourName]
    }

    return $null
}

function Write-ScraperMessage {
    param(
        [string]$ColourKey,
        [string]$Message,
        [switch]$NoNewLine
    )

    $keyMap = Get-ScraperColourKeyMap
    $rgbMap = Get-ScraperRgbDictionary

    if ($keyMap.ContainsKey($ColourKey)) {
        $spec = [string]$keyMap[$ColourKey]
        $parts = $spec -split '\|'
        $fgName = if ($parts.Count -gt 0) { [string]$parts[0] } else { $null }
        $bgName = if ($parts.Count -gt 1) { [string]$parts[1] } else { $null }

        $fgRgb = Convert-ScraperColourNameToRgb -ColourName $fgName -RgbDictionary $rgbMap
        $bgRgb = Convert-ScraperColourNameToRgb -ColourName $bgName -RgbDictionary $rgbMap

        $fgAnsi = $null
        $bgAnsi = $null

        if ($fgRgb) {
            $fgParts = $fgRgb -split ';'
            if ($fgParts.Count -eq 3) {
                $fgAnsi = "$([char]27)[38;2;$($fgParts[0]);$($fgParts[1]);$($fgParts[2])m"
            }
        }

        if ($bgRgb) {
            $bgParts = $bgRgb -split ';'
            if ($bgParts.Count -eq 3) {
                $bgAnsi = "$([char]27)[48;2;$($bgParts[0]);$($bgParts[1]);$($bgParts[2])m"
            }
        }

        if ($fgAnsi -or $bgAnsi) {
            $reset = "$([char]27)[0m"
            $formatted = "${fgAnsi}${bgAnsi}$Message$reset"
            if ($NoNewLine) {
                Write-Host -NoNewline $formatted
            } else {
                Write-Host $formatted
            }
            return
        }
    }

    if ($NoNewLine) {
        Write-Host -NoNewline $Message
    } else {
        Write-Host $Message
    }
}

function Initialize-ScraperModule {
    Import-Module powershell-yaml -ErrorAction Stop

    # Empty arrays for includeType/includeFolders mean "include all" (no restriction)
    # Excludes are removed from includes (typically).  Ignores are skipped entirely.  Summarize lists are used for folder summaries.
    $Global:ScraperDefaults = @{
        includeFolders = @()
        excludeFolders = @()
        includeType       = @()
        summarizeType     = @()
        ignoreType        = @()
        summarizeFolder    = @()
        ignoreFolder       = @('.workspace', '.git', 'node_modules', 'bin', 'obj')
        FolderTree         = $true
        AddFilesAsLeaves   = $true
        AddTreeToScrapeFile = $false
        outputFolder   = 'Prismata/Projects/Tooling/primitives/scrapes'
        mode = @("default")
    }
}

function Get-Yaml {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "YAML file not found: $Path"
    }

    $raw = Get-Content $Path -Raw
    Write-Host ">>> Loading YAML from: $Path" -ForegroundColor DarkGreen
    return ConvertFrom-Yaml $raw
}

# ---------------------------------------------------------
# Load Project Index
# ---------------------------------------------------------
function Get-ProjectsIndex {
    $workspaceRoot = Get-WorkspaceRoot
    $indexPath = Join-Path $workspaceRoot ".workspace/.projects_index/projects.yaml"

    if (-not (Test-Path $indexPath)) { return @{} }

    return (Get-Yaml -Path $indexPath).projects
}

# ---------------------------------------------------------
# Resolve Project Names → Paths
# ---------------------------------------------------------
function Resolve-ProjectPaths {
    param(
        [string[]]$Projects,
        [hashtable]$Registry
    )

    $paths = @()

    foreach ($name in $Projects) {
        if ($Registry.ContainsKey($name)) {
            $paths += $Registry[$name].path
        } else {
            $paths += $name
        }
    }

    return $paths
}

# ---------------------------------------------------------
# Load Mode Registry
# ---------------------------------------------------------
function Get-ModeRegistry {
    # $PSScriptRoot points to the module folder; use it directly to locate the registry
    $moduleRoot = $PSScriptRoot
    $registryPath = Join-Path $moduleRoot "config/scraper-modes.registry.yaml"
    Write-Host ">>> Loading mode registry from: $registryPath"
    Write-Host ">>> (If this file is missing, the scraper will use default settings.)"
    Write-Host ""
    if (-not (Test-Path $registryPath)) {
        Write-Host ">>> Mode registry missing, returning empty hashtable"
        return @{}
    }

    $yaml = Get-Yaml -Path $registryPath

    # Support two YAML shapes:
    # 1) modes: - name: ... (array of mode objects)
    # 2) modes: { ts: { includeTypes: [...] }, ... } (mapping)
    if ($null -eq $yaml.modes) { return @{} }

    if ($yaml.modes -is [hashtable]) {
        return $yaml.modes
    }

    $ht = @{}
    foreach ($mode in $yaml.modes) {
        $name = $mode.name
        if ($name) { $ht[$name] = $mode }
    }

    Write-Host ">>> Mode registry loaded with $($ht.Keys.Count) modes."
    return $ht
}

# ---------------------------------------------------------
# Mode Inheritance Resolver
# ---------------------------------------------------------
function Resolve-Mode {
    param(
        [string]$Mode,
        [hashtable]$Registry
    )

    if (-not $Registry.ContainsKey($Mode)) { return @{} }

    $modeData = $Registry[$Mode].Clone()

    # Ensure `name` field exists for mapping-style registries
    if (-not $modeData.ContainsKey('name')) {
        $modeData['name'] = $Mode
    }

    if ($modeData.ContainsKey("extends")) {
        $parent = $modeData["extends"]
        $parentData = Resolve-Mode -Mode $parent -Registry $Registry

        foreach ($key in $parentData.Keys) {
            if (-not $modeData.ContainsKey($key)) {
                $modeData[$key] = $parentData[$key]
            }
        }
    }

    return $modeData
}

# ---------------------------------------------------------
# Merge Settings
# ---------------------------------------------------------
function Merge-ScraperSettings {
    param(
        [hashtable]$Defaults = @{},
        [hashtable]$ModeData = @{},
        [hashtable]$ConfigData = @{},
        [string]$CliMode
    )

    # Prefer using the canonical Merge-Config from ConfigMerge if available
    if (Get-Command -Name Merge-Config -ErrorAction SilentlyContinue) {
        $cli = @{}
        if ($CliMode) { $cli['mode'] = $CliMode }
        return Merge-Config -Defaults $Defaults -Mode $ModeData -Config $ConfigData -Cli $cli
    }

    # Fallback: simple last-wins merge (preserve previous behaviour)
    $merged = @{}
    foreach ($key in $Defaults.Keys) { $merged[$key] = $Defaults[$key] }
    foreach ($key in $ModeData.Keys) { $merged[$key] = $ModeData[$key] }
    foreach ($key in $ConfigData.Keys) { $merged[$key] = $ConfigData[$key] }
    if ($CliMode) { $merged["mode"] = $CliMode }
    return $merged
}

function Normalize-ScraperSettings {
    param([hashtable]$Settings)

    $normalized = @{}
    if ($Settings) {
        foreach ($k in $Settings.Keys) { $normalized[$k] = $Settings[$k] }
    }

    if (-not $normalized.ContainsKey('includeType') -or $null -eq $normalized['includeType']) {
        if ($normalized.ContainsKey('includeExtension')) {
            $normalized['includeType'] = @($normalized['includeExtension'])
        } elseif ($normalized.ContainsKey('includeTypes')) {
            $normalized['includeType'] = @($normalized['includeTypes'])
        } else {
            $normalized['includeType'] = @()
        }
    }
    if (-not $normalized.ContainsKey('ignoreType') -or $null -eq $normalized['ignoreType']) {
        if ($normalized.ContainsKey('ignoreExtension')) {
            $normalized['ignoreType'] = @($normalized['ignoreExtension'])
        } elseif ($normalized.ContainsKey('excludeTypes')) {
            $normalized['ignoreType'] = @($normalized['excludeTypes'])
        } else {
            $normalized['ignoreType'] = @()
        }
    }
    if (-not $normalized.ContainsKey('ignoreFolder') -or $null -eq $normalized['ignoreFolder']) {
        if ($normalized.ContainsKey('excludeFolders')) {
            $normalized['ignoreFolder'] = @($normalized['excludeFolders'])
        } else {
            $normalized['ignoreFolder'] = @()
        }
    }
    if (-not $normalized.ContainsKey('summarizeFolder') -or $null -eq $normalized['summarizeFolder']) {
        $normalized['summarizeFolder'] = @()
    }
    if (-not $normalized.ContainsKey('summarizeType') -or $null -eq $normalized['summarizeType']) {
        if ($normalized.ContainsKey('summarizeExtension')) {
            $normalized['summarizeType'] = @($normalized['summarizeExtension'])
        } else {
            $normalized['summarizeType'] = @()
        }
    }
    if (-not $normalized.ContainsKey('includeFolders') -or $null -eq $normalized['includeFolders']) {
        $normalized['includeFolders'] = @()
    }

    # Keep folder aliases in sync.
    $normalized['excludeFolders'] = @($normalized['ignoreFolder'])

    if (-not $normalized.ContainsKey('FolderTree') -or $null -eq $normalized['FolderTree']) { $normalized['FolderTree'] = $true }
    if (-not $normalized.ContainsKey('AddFilesAsLeaves') -or $null -eq $normalized['AddFilesAsLeaves']) { $normalized['AddFilesAsLeaves'] = $true }
    if (-not $normalized.ContainsKey('AddTreeToScrapeFile') -or $null -eq $normalized['AddTreeToScrapeFile']) { $normalized['AddTreeToScrapeFile'] = $false }

    return $normalized
}

# ---------------------------------------------------------
# Output Naming Engine
# ---------------------------------------------------------
function New-ScraperOutputName {
    param(
        [string]$ProjectName,
        [string]$Mode,
        [hashtable]$Settings
    )

    $timestamp = (Get-Date).ToString("yyyy-MM-ddTHH-mm-ss")

    $excludeTag = ""
    $excludeFolders = @($Settings.excludeFolders)
    $excludeTypes = @($Settings.excludeTypes)

    if ($excludeFolders.Count -gt 0) {
        $excludeTag = "_xf-" + ($excludeFolders -join "-")
    }
    if ($excludeTypes.Count -gt 0) {
        $excludeTag += "_xt-" + ($excludeTypes -join "-")
    }

    return "${timestamp}_${ProjectName}_${Mode}${excludeTag}.txt"
}

function New-ScraperTreeOutputName {
    param(
        [string]$ScrapeOutputPath
    )

    $dir = Split-Path -Path $ScrapeOutputPath -Parent
    $name = [System.IO.Path]::GetFileNameWithoutExtension($ScrapeOutputPath)
    return (Join-Path $dir ("${name}_tree.txt"))
}

function Test-ScraperPathContainsFolder {
    param(
        [string]$Path,
        [string[]]$FolderNames
    )

    if (-not (Get-Command Test-PathFolderMatch -ErrorAction SilentlyContinue)) {
        $toolingRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
        $folderTreePath = Join-Path $toolingRoot 'primitives\powershell\folder-tree.ps1'
        if (Test-Path -LiteralPath $folderTreePath) {
            . $folderTreePath
        }
    }

    return (Test-PathFolderMatch -Path $Path -FolderNames $FolderNames)
}

function New-ScraperFolderSummaryLine {
    param(
        [string]$FolderPath,
        [string[]]$IgnoreTypes,
        [string[]]$SummarizeTypes
    )

    $files = @(Get-ChildItem -Path $FolderPath -Recurse -File -ErrorAction SilentlyContinue)
    $counts = @{}
    foreach ($f in $files) {
        $ext = [System.IO.Path]::GetExtension($f.FullName)
        if ($IgnoreTypes -contains $ext) { continue }
        if ($SummarizeTypes -and $SummarizeTypes.Count -gt 0 -and -not ($SummarizeTypes -contains $ext)) { continue }
        if (-not $counts.ContainsKey($ext)) { $counts[$ext] = 0 }
        $counts[$ext]++
    }

    $parts = @()
    foreach ($k in ($counts.Keys | Sort-Object)) {
        $parts += ("{0}:{1}" -f $k, $counts[$k])
    }

    $countsText = if ($parts.Count -gt 0) { $parts -join ', ' } else { 'no matching files' }
    return "[summary] $(Split-Path -Path $FolderPath -Leaf) ({0})" -f $countsText
}

function New-ScraperFolderTreeText {
    param(
        [string]$RootPath,
        [string[]]$IncludeTypes,
        [string[]]$IgnoreTypes,
        [string[]]$SummarizeTypes,
        [string[]]$IncludeFolders,
        [string[]]$IgnoreFolders,
        [string[]]$SummarizeFolders,
        [bool]$AddFilesAsLeaves = $true
    )

    if (-not (Get-Command New-FolderTreeText -ErrorAction SilentlyContinue)) {
        $toolingRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
        $folderTreePath = Join-Path $toolingRoot 'primitives\powershell\folder-tree.ps1'
        if (Test-Path -LiteralPath $folderTreePath) {
            . $folderTreePath
        }
    }

    $summarizationCallback = {
        param($FolderPath, $LocalIgnoreTypes, $LocalSummarizeTypes)
        New-ScraperFolderSummaryLine -FolderPath $FolderPath -IgnoreTypes $LocalIgnoreTypes -SummarizeTypes $LocalSummarizeTypes
    }

    return (New-FolderTreeText -RootPath $RootPath `
                               -IncludeTypes $IncludeTypes `
                               -IgnoreTypes $IgnoreTypes `
                               -SummarizeTypes $SummarizeTypes `
                               -IncludeFolders $IncludeFolders `
                               -IgnoreFolders $IgnoreFolders `
                               -SummarizeFolders $SummarizeFolders `
                               -AddFilesAsLeaves:$AddFilesAsLeaves `
                               -SummarizationCallback $summarizationCallback)
}

# ---------------------------------------------------------
# Scrape Engine (Folder Walker)
# ---------------------------------------------------------
function Start-Scrape {
    param(
        [string]$InputPath,
        [hashtable]$Settings,
        [string]$OutputPath
    )

    $Settings = Normalize-ScraperSettings -Settings $Settings
    $includeTypes   = @($Settings.includeType)
    $excludeTypes   = @($Settings.ignoreType)
    $includeFolders = @($Settings.includeFolders)
    $excludeFolders = @($Settings.ignoreFolder)
    $summarizeExtensions = @($Settings.summarizeType)
    $summarizeFolders = @($Settings.summarizeFolder)
    $folderTreeEnabled = [bool]$Settings.FolderTree
    $addFilesAsLeaves = [bool]$Settings.AddFilesAsLeaves
    $addTreeToScrapeFile = [bool]$Settings.AddTreeToScrapeFile

    $files = Get-ChildItem -Path $InputPath -Recurse -File -ErrorAction SilentlyContinue
        $files = @($files)
    
    Write-ScraperMessage -ColourKey '!proc' -Message ">>> Perform-Scrape scanning: $InputPath"
    Write-ScraperMessage -ColourKey '!info' -Message ">>> Settings passed to scraper:"
    # Use existing config-helpers if available to produce a flattened, machine-friendly summary
    $toolingRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
    $configHelpersPath = Join-Path $toolingRoot 'primitives\powershell\config-helpers.ps1'
    $summary = @{}
    if (Test-Path $configHelpersPath) {
        try {
            . $configHelpersPath
            $settingsJson = $Settings | ConvertTo-Json -Depth 10
            $flatJson = Convert-ConfigToText -InputString $settingsJson -Format json -AsJson
            $flat = $flatJson | ConvertFrom-Json
            # Group by top-level key (before first dot or bracket)
            $groups = $flat | Group-Object { ($_.Key -split '\.|\[')[0] }
            foreach ($g in $groups) {
                $key = $g.Name
                $vals = $g.Group | ForEach-Object { $_.Value }
                # If values represent indexed array entries, collapse to array
                $vals = @($vals)
                if ($vals.Count -gt 1) { $summary[$key] = $vals } else { $summary[$key] = $vals[0] }
            }
            # For any missing top-level keys, fall back to defaults/none handling
            foreach ($k in $Settings.Keys) {
                if (-not $summary.ContainsKey($k)) {
                    $v = $Settings[$k]
                    if ($null -eq $v) { $summary[$k] = '<null>'; continue }
                    if ($v -is [System.Array] -and $v.Count -eq 0) {
                        if ($k -match '^include') { $summary[$k] = 'all' }
                        elseif ($k -match '^exclude') { $summary[$k] = 'none' }
                        else { $summary[$k] = @() }
                        continue
                    }
                    $summary[$k] = $v
                }
            }
        } catch {
            # Fallback to simple summarizer if helpers fail
            foreach ($k in $Settings.Keys) {
                $v = $Settings[$k]
                if ($null -eq $v) { $summary[$k] = '<null>'; continue }
                if ($v -is [System.Array]) {
                    if ($v.Count -eq 0) {
                        if ($k -match '^include') { $summary[$k] = 'all' }
                        elseif ($k -match '^exclude') { $summary[$k] = 'none' }
                        else { $summary[$k] = @() }
                    } else { $summary[$k] = $v }
                    continue
                }
                $summary[$k] = $v
            }
        }
    } else {
        foreach ($k in $Settings.Keys) {
            $v = $Settings[$k]
            if ($null -eq $v) { $summary[$k] = '<null>'; continue }
            if ($v -is [System.Array]) {
                if ($v.Count -eq 0) {
                    if ($k -match '^include') { $summary[$k] = 'all' }
                    elseif ($k -match '^exclude') { $summary[$k] = 'none' }
                    else { $summary[$k] = @() }
                } else { $summary[$k] = $v }
                continue
            }
            $summary[$k] = $v
        }
    }

    Write-ScraperMessage -ColourKey '!data' -Message ($summary | ConvertTo-Yaml)
    Write-ScraperMessage -ColourKey '!info' -Message ">>> Files found before filtering: $(@($files).Count)"

    $filtered = foreach ($file in $files) {

        $folderName = Split-Path $file.FullName -Parent

        if (Test-ScraperPathContainsFolder -Path $folderName -FolderNames $excludeFolders) { continue }

        if ($includeFolders.Count -gt 0) {
            if (-not (Test-ScraperPathContainsFolder -Path $folderName -FolderNames $includeFolders)) { continue }
        }

        if ($excludeTypes -contains $file.Extension) { continue }

        if ($includeTypes.Count -gt 0 -and $includeTypes -notcontains "*") {
            if (-not ($includeTypes -contains $file.Extension)) { continue }
        }

        $file
    }
    
    # Write file list to output
    foreach ($file in $filtered) {
        Add-Content -Path $OutputPath -Value "=========================================="
        Add-Content -Path $OutputPath -Value "FILE: $($file.FullName)"
        Add-Content -Path $OutputPath -Value "=========================================="
        Add-Content -Path $OutputPath -Value (Get-Content $file.FullName -Raw)
        Add-Content -Path $OutputPath -Value ""
    }

    if ($folderTreeEnabled) {
        $treeText = New-ScraperFolderTreeText -RootPath $InputPath `
                             -IncludeTypes $includeTypes `
                             -IgnoreTypes $excludeTypes `
                             -SummarizeTypes $summarizeExtensions `
                                             -IncludeFolders $includeFolders `
                                             -IgnoreFolders $excludeFolders `
                                             -SummarizeFolders $summarizeFolders `
                                             -AddFilesAsLeaves:$addFilesAsLeaves

        if ($addTreeToScrapeFile) {
            Add-Content -Path $OutputPath -Value ""
            Add-Content -Path $OutputPath -Value "=========================================="
            Add-Content -Path $OutputPath -Value "FOLDER TREE"
            Add-Content -Path $OutputPath -Value "=========================================="
            Add-Content -Path $OutputPath -Value $treeText
            Add-Content -Path $OutputPath -Value ""
            Write-ScraperMessage -ColourKey '!done' -Message ">>> Folder tree merged into scrape output file."
        } else {
            $treeOutputPath = New-ScraperTreeOutputName -ScrapeOutputPath $OutputPath
            Set-Content -Path $treeOutputPath -Value $treeText -Encoding UTF8
            Write-ScraperMessage -ColourKey '!save' -Message ">>> Folder tree written to: $treeOutputPath"
        }
    }

    Write-ScraperMessage -ColourKey '!done' -Message ">>> Files after filtering: $(@($filtered).Count)"

}

# ---------------------------------------------------------
# Single-Folder Scraper
# ---------------------------------------------------------
function Invoke-ScraperFolder {
    param(
        [string]$InputPath,
        [string]$OutputPath,
        [string]$ConfigPath,
        [string]$Mode,
        [string[]]$IncludeFolders,
        [string[]]$IncludeType,
        [string[]]$SummarizeType,
        [string[]]$IgnoreType,
        [string[]]$SummarizeFolder,
        [string[]]$IgnoreFolder,
        [switch]$FolderTree,
        [switch]$AddFilesAsLeaves,
        [switch]$AddTreeToScrapeFile,
        [switch]$Relative
    )
    
    # Load mode registry and resolve mode
    Write-ScraperMessage -ColourKey '!proc' -Message ">>> Loading mode registry..."

    $modeRegistry = Get-ModeRegistry
    $modeData     = Resolve-Mode -Mode $Mode -Registry $modeRegistry

    Write-ScraperMessage -ColourKey '!path' -Message "Loading config from: $ConfigPath"
    # Load config YAML
    $configData = @{}
    if ($ConfigPath -and (Test-Path $ConfigPath)) {
        $configData = Get-Yaml -Path $ConfigPath
    }

    Write-ScraperMessage -ColourKey '!proc' -Message ">>> Merge settings (defaults + config + mode + CLI)..."
    # Merge settings (defaults + config + mode + CLI)
    $settings = Merge-ScraperSettings -Defaults $Global:ScraperDefaults `
                                      -ConfigData $configData `
                                      -ModeData $modeData `
                                      -CliMode $Mode

    if ($IncludeFolders -and $IncludeFolders.Count -gt 0) {
        $settings['includeFolders'] = @($IncludeFolders)
    }
    if ($IncludeType -and $IncludeType.Count -gt 0) {
        $settings['includeType'] = @($IncludeType)
    }
    if ($SummarizeType -and $SummarizeType.Count -gt 0) {
        $settings['summarizeType'] = @($SummarizeType)
    }
    if ($IgnoreType -and $IgnoreType.Count -gt 0) {
        $settings['ignoreType'] = @($IgnoreType)
    }
    if ($SummarizeFolder -and $SummarizeFolder.Count -gt 0) {
        $settings['summarizeFolder'] = @($SummarizeFolder)
    }
    if ($IgnoreFolder -and $IgnoreFolder.Count -gt 0) {
        $settings['ignoreFolder'] = @($IgnoreFolder)
    }
    if ($PSBoundParameters.ContainsKey('FolderTree')) { $settings['FolderTree'] = [bool]$FolderTree.IsPresent }
    if ($PSBoundParameters.ContainsKey('AddFilesAsLeaves')) { $settings['AddFilesAsLeaves'] = [bool]$AddFilesAsLeaves.IsPresent }
    if ($PSBoundParameters.ContainsKey('AddTreeToScrapeFile')) { $settings['AddTreeToScrapeFile'] = [bool]$AddTreeToScrapeFile.IsPresent }

    $settings = Normalize-ScraperSettings -Settings $settings

    # Determine project name and output filename
    $projectName = Split-Path $InputPath -Leaf
    $outputName  = New-ScraperOutputName -ProjectName $projectName -Mode $Mode -Settings $settings

    # Build full output path: CLI OutputPath > merged settings outputFolder > current directory
    $resolvedOutputFolder = $null
    if ($OutputPath) {
        $resolvedOutputFolder = $OutputPath
    } elseif ($settings.ContainsKey('outputFolder') -and $settings.outputFolder) {
        $configuredOutputFolder = [string]$settings.outputFolder
        if ([System.IO.Path]::IsPathRooted($configuredOutputFolder)) {
            $resolvedOutputFolder = $configuredOutputFolder
        } else {
            $resolvedOutputFolder = Join-Path (Get-WorkspaceRoot) $configuredOutputFolder
        }
    } else {
        $resolvedOutputFolder = (Resolve-Path ".").Path
    }

    $outputPath = Join-Path $resolvedOutputFolder $outputName

    # Ensure output directory exists (IMPORTANT FIX)
    $directory = Split-Path $outputPath -Parent
    if (-not (Test-Path $directory)) {
        Write-ScraperMessage -ColourKey '!create' -Message ">>> Creating output directory: $directory"
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    # Start the actual scrape
    Start-Scrape -InputPath $InputPath -Settings $settings -OutputPath $outputPath

    # -------------------------------
    # User-facing confirmation output
    # -------------------------------
    Write-ScraperMessage -ColourKey '!info' -Message ""
    Write-ScraperMessage -ColourKey '!info' -Message "=========================================="
    Write-ScraperMessage -ColourKey '!done' -Message "Scraped files from: $InputPath"
    Write-ScraperMessage -ColourKey '!save' -Message "Output written to:"
    Write-ScraperMessage -ColourKey '!path' -Message "    $outputPath"
    Write-ScraperMessage -ColourKey '!info' -Message "=========================================="
}


# ---------------------------------------------------------
# Multi-Folder Scraper Entry
# ---------------------------------------------------------
function Invoke-Scraper {
    param(
        [string]$InputPath,
        [string]$Output,
        [string]$Config,
        [string]$Mode,
        [string[]]$Projects,
        [string[]]$IncludeType,
        [string[]]$SummarizeType,
        [string[]]$IgnoreType,
        [string[]]$SummarizeFolder,
        [string[]]$IgnoreFolder,
        [switch]$FolderTree,
        [switch]$AddFilesAsLeaves,
        [switch]$AddTreeToScrapeFile,
        [switch]$Relative
    )

    $registry = Get-ProjectsIndex

    if ($Projects -and $Projects.Count -gt 0) {
        foreach ($projectName in $Projects) {
            $projectPath = $null
            $projectRoot = $null

            if ($registry.ContainsKey($projectName)) {
                $projectPath = [string]$registry[$projectName].path
                if ($projectPath -and ($projectPath.StartsWith('/') -or $projectPath.StartsWith('\'))) {
                    $workspaceRoot = Get-WorkspaceRoot
                    $trimmedRelative = $projectPath.TrimStart([char]'/', [char]92)
                    $workspaceName = Split-Path -Path $workspaceRoot -Leaf
                    if ($workspaceName -and ($trimmedRelative.StartsWith($workspaceName + '/') -or $trimmedRelative.StartsWith($workspaceName + '\\'))) {
                        $trimmedRelative = $trimmedRelative.Substring($workspaceName.Length).TrimStart([char]'/', [char]92)
                    }

                    $candidatePath = Join-Path $workspaceRoot $trimmedRelative
                    if (Test-Path -LiteralPath $candidatePath) {
                        $projectPath = $candidatePath
                    }
                }
                $trimmedPath = $projectPath.TrimEnd([char]'/', [char]92)
                $projectRoot = Split-Path -Path $trimmedPath -Leaf

                if ([string]::IsNullOrWhiteSpace($projectRoot)) {
                    Write-ScraperMessage -ColourKey '!error' -Message "WARNING: Could not determine project root folder from projects index entry for '$projectName'."
                }
            } else {
                $projectPath = [string]$projectName
                Write-ScraperMessage -ColourKey '!error' -Message "WARNING: Project '$projectName' not found in projects index. includeFolders root could not be derived from index."
            }

            Write-ScraperMessage -ColourKey '!proc' -Message ">>> Resolving project path from registry for project $projectName -> $projectPath"
            $rootIncludeFolders = if ($projectRoot) { @($projectRoot) } else { @() }
            $scraperFolderArgs = @{
                InputPath = $projectPath
                OutputPath = $Output
                ConfigPath = $Config
                Mode = $Mode
                IncludeFolders = $rootIncludeFolders
                IncludeType = $IncludeType
                SummarizeType = $SummarizeType
                IgnoreType = $IgnoreType
                SummarizeFolder = $SummarizeFolder
                IgnoreFolder = $IgnoreFolder
                Relative = $Relative
            }
            if ($PSBoundParameters.ContainsKey('FolderTree')) { $scraperFolderArgs['FolderTree'] = $FolderTree.IsPresent }
            if ($PSBoundParameters.ContainsKey('AddFilesAsLeaves')) { $scraperFolderArgs['AddFilesAsLeaves'] = $AddFilesAsLeaves.IsPresent }
            if ($PSBoundParameters.ContainsKey('AddTreeToScrapeFile')) { $scraperFolderArgs['AddTreeToScrapeFile'] = $AddTreeToScrapeFile.IsPresent }
            Invoke-ScraperFolder @scraperFolderArgs
        }
        return
    }

    if ($InputPath) {
        $scraperFolderArgs = @{
            InputPath = $InputPath
            OutputPath = $Output
            ConfigPath = $Config
            Mode = $Mode
            IncludeFolders = @()
            IncludeType = $IncludeType
            SummarizeType = $SummarizeType
            IgnoreType = $IgnoreType
            SummarizeFolder = $SummarizeFolder
            IgnoreFolder = $IgnoreFolder
            Relative = $Relative
        }
        if ($PSBoundParameters.ContainsKey('FolderTree')) { $scraperFolderArgs['FolderTree'] = $FolderTree.IsPresent }
        if ($PSBoundParameters.ContainsKey('AddFilesAsLeaves')) { $scraperFolderArgs['AddFilesAsLeaves'] = $AddFilesAsLeaves.IsPresent }
        if ($PSBoundParameters.ContainsKey('AddTreeToScrapeFile')) { $scraperFolderArgs['AddTreeToScrapeFile'] = $AddTreeToScrapeFile.IsPresent }
        Invoke-ScraperFolder @scraperFolderArgs
        return
    }
}

Export-ModuleMember -Function * 

function Get-ScraperHelp {
    [CmdletBinding()]
    param(
        [switch]$VerboseOutput
    )

    $help = @()
    $help += "Scraper - available functions and configuration options:"
    $help += "Functions exported by this module (examples):"
    $help += " - Invoke-Scraper        : multi-folder entry (Params: -InputPath, -Output, -Config, -Mode, -Projects, -Relative)"
    $help += " - Invoke-ScraperFolder  : single folder scrape (Params: -InputPath, -OutputPath, -ConfigPath, -Mode, -Relative)"
    $help += " - Start-Scrape          : core folder walk and output (Params: -InputPath, -Settings, -OutputPath)"
    $help += " - Get-ModeRegistry      : loads mode registry from registry/scraper-modes.registry.yaml"
    $help += " - Resolve-Mode          : resolves mode inheritance (Params: -Mode, -Registry)"
    $help += " - Merge-ScraperSettings : merges defaults/mode/config/cli (delegates to Merge-Config when available)"
    $help += " - Get-Yaml              : loads a YAML file into a hashtable (Requires powershell-yaml)"
    $help += " - New-ScraperOutputName : generates a timestamped output filename"
    $help += "Common configuration keys (in default.yaml and modes):"
    $help += " - includeType: array of types to include, e.g. ['.ts','.py']"
    $help += " - ignoreType: array of types to exclude"
    $help += " - includeFolders: array of folder name patterns to include"
    $help += " - excludeFolders: array of folder name patterns to exclude"
    $help += " - includeType / ignoreType: annotator-style type include/ignore arrays"
    $help += " - summarizeType: type list used when summarizing folders in tree mode"
    $help += " - summarizeFolder / ignoreFolder: annotator-style folder summary/ignore arrays"
    $help += " - FolderTree: when true, produce a folder tree representation"
    $help += " - AddFilesAsLeaves: when true, include file names as leaves in folder tree"
    $help += " - AddTreeToScrapeFile: when true, merge tree into scrape output; otherwise write a *_tree.txt sibling file"
    $help += " - outputFolder: default output folder when -OutputPath is not supplied"
    $help += " - conflictMode: (if using ConfigMerge) removeWins|includeWins|unionWins"

    if ($VerboseOutput) {
        $help += ""
        $help += "Examples:" 
        $help += "    Invoke-ScraperFolder -InputPath 'C:\Projects\MyApp' -OutputPath 'C:\scrapes' -Mode 'code-only'"
        $help += "    Start-Scrape -InputPath 'C:\Projects\MyApp' -Settings @{ includeType = @('.ts') } -OutputPath 'C:\scrapes\out.txt'"
    }

    return ($help -join "`n")
}

Export-ModuleMember -Function Get-ScraperHelp

Initialize-ScraperModule