param(
    [string]$InputPath,
    [string]$OutputPath,
    [string]$ConfigPath,
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

# Initialization paths:
# OS-safe config path resolution
$toolingRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$defaultConfigPath = Join-Path $toolingRoot "modules/Scraper/config/scraper-config.yaml"
$resolvedConfigPath = if ($ConfigPath) { $ConfigPath } else { $defaultConfigPath }

# Ensure Scraper (and Get-Yaml) are available before loading YAML files.
Import-Module "$PSScriptRoot/../../modules/Scraper/Scraper.psd1" -Force
Initialize-ScraperModule

# Load config data from resolved config file.
$configData = Get-Yaml -Path $resolvedConfigPath
# Load mode registry from scraper-modes.registry.yaml when present.
$modeRegistryPath = Join-Path $toolingRoot "modules/Scraper/config/scraper-modes.registry.yaml"
$modeRegistry = if (Test-Path -LiteralPath $modeRegistryPath) { Get-Yaml -Path $modeRegistryPath } else { @{} }

$projectIncludeRoots = @()
if ($Projects -and $Projects.Count -gt 0) {
    $projectsIndex = Get-ProjectsIndex
    foreach ($projectName in $Projects) {
        if ($projectsIndex -and $projectsIndex.ContainsKey($projectName)) {
            $indexPath = [string]$projectsIndex[$projectName].path
            $trimmedPath = $indexPath.TrimEnd([char]'/', [char]92)
            $projectRoot = Split-Path -Path $trimmedPath -Leaf
            if ([string]::IsNullOrWhiteSpace($projectRoot)) {
                Write-ScraperMessage -ColourKey '!error' -Message "WARNING: Could not determine project root folder from projects index entry for '$projectName'."
                continue
            }

            if ($projectIncludeRoots -notcontains $projectRoot) {
                $projectIncludeRoots += $projectRoot
            }
        } else {
            Write-ScraperMessage -ColourKey '!error' -Message "WARNING: Project '$projectName' not found in projects index. includeFolders root could not be derived from index."
        }
    }
}

$projList = $Projects -join ','
$invocationLine = "& $PSCommandPath"
if ($InputPath) { $invocationLine += " -InputPath `"$InputPath`"" }
if ($OutputPath) { $invocationLine += " -OutputPath `"$OutputPath`"" }
if ($ConfigPath) { $invocationLine += " -ConfigPath `"$ConfigPath`"" }
if ($Mode) { $invocationLine += " -Mode `"$Mode`"" }
if ($Projects -and $Projects.Count -gt 0) { $invocationLine += " -Projects `"$projList`"" }
if ($IncludeType -and $IncludeType.Count -gt 0) { $invocationLine += " -IncludeType `"$($IncludeType -join ',')`"" }
if ($SummarizeType -and $SummarizeType.Count -gt 0) { $invocationLine += " -SummarizeType `"$($SummarizeType -join ',')`"" }
if ($IgnoreType -and $IgnoreType.Count -gt 0) { $invocationLine += " -IgnoreType `"$($IgnoreType -join ',')`"" }
if ($SummarizeFolder -and $SummarizeFolder.Count -gt 0) { $invocationLine += " -SummarizeFolder `"$($SummarizeFolder -join ',')`"" }
if ($IgnoreFolder -and $IgnoreFolder.Count -gt 0) { $invocationLine += " -IgnoreFolder `"$($IgnoreFolder -join ',')`"" }
if ($PSBoundParameters.ContainsKey('FolderTree')) { $invocationLine += " -FolderTree:$($FolderTree.IsPresent)" }
if ($PSBoundParameters.ContainsKey('AddFilesAsLeaves')) { $invocationLine += " -AddFilesAsLeaves:$($AddFilesAsLeaves.IsPresent)" }
if ($PSBoundParameters.ContainsKey('AddTreeToScrapeFile')) { $invocationLine += " -AddTreeToScrapeFile:$($AddTreeToScrapeFile.IsPresent)" }
if ($Relative) { $invocationLine += " -Relative" }

# Terminal/Logging output for auditability
Clear-Host
. "$PSScriptRoot/bordered-header.ps1"
Show-BorderedHeader -Message 'Prismata Scraper Primitive' -BorderChar '=' -BorderColor Cyan -MessageColor Magenta -Width 80
Write-Host ""
# Print exact invocation (command + args) for auditability using invocation table primitive
. "$PSScriptRoot/show-invocation-table.ps1"
# Build eligible params list so we can show all possible args (even if not provided)
$nullDefault = '<null>'
$outputDefault = if ($configData -and $configData.outputFolder) { [string]$configData.outputFolder } else { $nullDefault }
$modeDefault = if ($configData -and $configData.mode) { [string]$configData.mode } else { $nullDefault }
$includeTypeDefault = if ($configData -and $configData.includeType) { ($configData.includeType -join ', ') } elseif ($configData -and $configData.includeTypes) { ($configData.includeTypes -join ', ') } else { $nullDefault }
$summarizeTypeDefault = if ($configData -and $configData.summarizeType) { ($configData.summarizeType -join ', ') } else { $nullDefault }
$ignoreTypeDefault = if ($configData -and $configData.ignoreType) { ($configData.ignoreType -join ', ') } elseif ($configData -and $configData.excludeTypes) { ($configData.excludeTypes -join ', ') } else { $nullDefault }
$summarizeFolderDefault = if ($configData -and $configData.summarizeFolder) { ($configData.summarizeFolder -join ', ') } else { $nullDefault }
$ignoreFolderDefault = if ($configData -and $configData.ignoreFolder) { ($configData.ignoreFolder -join ', ') } elseif ($configData -and $configData.excludeFolders) { ($configData.excludeFolders -join ', ') } else { $nullDefault }
$folderTreeDefault = if ($configData -and $configData.PSObject.Properties.Name -contains 'FolderTree') { [bool]$configData.FolderTree } else { $true }
$addFilesAsLeavesDefault = if ($configData -and $configData.PSObject.Properties.Name -contains 'AddFilesAsLeaves') { [bool]$configData.AddFilesAsLeaves } else { $true }
$addTreeToScrapeFileDefault = if ($configData -and $configData.PSObject.Properties.Name -contains 'AddTreeToScrapeFile') { [bool]$configData.AddTreeToScrapeFile } else { $false }
$eligibleParams = @(
    [PSCustomObject]@{ Name = 'InputPath';  Type = 'string';   Default = $nullDefault },
    [PSCustomObject]@{ Name = 'OutputPath'; Type = 'string';   Default = $outputDefault },
    [PSCustomObject]@{ Name = 'ConfigPath'; Type = 'string';   Default = $resolvedConfigPath },
    [PSCustomObject]@{ Name = 'Mode';       Type = 'string';   Default = $modeDefault },
    [PSCustomObject]@{ Name = 'Projects';   Type = 'string[]'; Default = $nullDefault },
    [PSCustomObject]@{ Name = 'IncludeType';   Type = 'string[]'; Default = $includeTypeDefault },
    [PSCustomObject]@{ Name = 'SummarizeType'; Type = 'string[]'; Default = $summarizeTypeDefault },
    [PSCustomObject]@{ Name = 'IgnoreType';    Type = 'string[]'; Default = $ignoreTypeDefault },
    [PSCustomObject]@{ Name = 'SummarizeFolder';    Type = 'string[]'; Default = $summarizeFolderDefault },
    [PSCustomObject]@{ Name = 'IgnoreFolder';       Type = 'string[]'; Default = $ignoreFolderDefault },
    [PSCustomObject]@{ Name = 'FolderTree';         Type = 'switch';   Default = $folderTreeDefault },
    [PSCustomObject]@{ Name = 'AddFilesAsLeaves';   Type = 'switch';   Default = $addFilesAsLeavesDefault },
    [PSCustomObject]@{ Name = 'AddTreeToScrapeFile';Type = 'switch';   Default = $addTreeToScrapeFileDefault },
    [PSCustomObject]@{ Name = 'Relative';   Type = 'switch';   Default = $false }
)
Show-InvocationTable -InvocationArgs $PSBoundParameters -Title 'Command Invocation' -InvocationLine $invocationLine -Width 80 -ShowMode 'Both' -EligibleParams $eligibleParams -Format table -ShowTypes -ShowEmpty -ShowMeta
Write-Host ""
Write-Host ">>> Config imported from: $resolvedConfigPath" -ForegroundColor Cyan
Write-Host ($configData | ConvertTo-Yaml) -ForegroundColor Gray

# Show merged config breakdown using ConfigMerge (if available)
Write-Host "`n>>> Config Merge Table (layered view)" -ForegroundColor Cyan
$configMergePath = Join-Path $toolingRoot "modules/ConfigMerge/ConfigMerge.psm1"
if (Test-Path -LiteralPath $configMergePath) {
    try {
        Import-Module $configMergePath -Force -ErrorAction Stop

        $defaults = @{}
        if ($Global:ScraperDefaults) {
            foreach ($k in $Global:ScraperDefaults.Keys) { $defaults[$k] = $Global:ScraperDefaults[$k] }
        }

        $modeData = @{}
        $selectedMode = $null
        if ($Mode) {
            $selectedMode = $Mode
        } elseif ($configData -and $configData.mode) {
            if ($configData.mode -is [System.Array]) {
                if ($configData.mode.Count -gt 0) { $selectedMode = [string]$configData.mode[0] }
            } else {
                $selectedMode = [string]$configData.mode
            }
        }

        if ($selectedMode) {
            $registry = Get-ModeRegistry
            $modeData = Resolve-Mode -Mode $selectedMode -Registry $registry
        }

        $style = @{}
        $cli = @{}
        foreach ($p in $PSBoundParameters.Keys) {
            switch ($p) {
                'OutputPath' { $cli['outputFolder'] = $PSBoundParameters[$p] }
                default {
                    $mapped = ($p.Substring(0,1).ToLower() + $p.Substring(1))
                    $cli[$mapped] = $PSBoundParameters[$p]
                }
            }
        }

        if ($projectIncludeRoots -and $projectIncludeRoots.Count -gt 0) {
            $cli['includeFolders'] = @($projectIncludeRoots)
        }

        if ($IncludeType -and $IncludeType.Count -gt 0) { $cli['includeType'] = @($IncludeType) }
        if ($SummarizeType -and $SummarizeType.Count -gt 0) { $cli['summarizeType'] = @($SummarizeType) }
        if ($IgnoreType -and $IgnoreType.Count -gt 0) { $cli['ignoreType'] = @($IgnoreType) }
        if ($SummarizeFolder -and $SummarizeFolder.Count -gt 0) { $cli['summarizeFolder'] = @($SummarizeFolder) }
        if ($IgnoreFolder -and $IgnoreFolder.Count -gt 0) { $cli['ignoreFolder'] = @($IgnoreFolder) }
        if ($FolderTree -ne $null) { $cli['FolderTree'] = [bool]$FolderTree }
        if ($AddFilesAsLeaves -ne $null) { $cli['AddFilesAsLeaves'] = [bool]$AddFilesAsLeaves }
        if ($AddTreeToScrapeFile -ne $null) { $cli['AddTreeToScrapeFile'] = [bool]$AddTreeToScrapeFile }

        Show-ConfigMergeTable -Defaults $defaults -Mode $modeData -Config $configData -Style $style -Cli $cli
    } catch {
        Write-Warning "Failed to load ConfigMerge module: $_"
    }
} else {
    Write-Host ">>> ConfigMerge module not found at: $configMergePath" -ForegroundColor Yellow
}

Write-Host ">>> Running MAIN Script: Invoke-Scraper <<<" -ForegroundColor Green
Write-Host ""
$invokeArgs = @{
    InputPath = $InputPath
    Output = $OutputPath
    Config = $resolvedConfigPath
    Mode = $Mode
    Projects = $Projects
    IncludeType = $IncludeType
    SummarizeType = $SummarizeType
    IgnoreType = $IgnoreType
    SummarizeFolder = $SummarizeFolder
    IgnoreFolder = $IgnoreFolder
    Relative = $Relative
}
if ($PSBoundParameters.ContainsKey('FolderTree')) { $invokeArgs['FolderTree'] = $FolderTree.IsPresent }
if ($PSBoundParameters.ContainsKey('AddFilesAsLeaves')) { $invokeArgs['AddFilesAsLeaves'] = $AddFilesAsLeaves.IsPresent }
if ($PSBoundParameters.ContainsKey('AddTreeToScrapeFile')) { $invokeArgs['AddTreeToScrapeFile'] = $AddTreeToScrapeFile.IsPresent }
Invoke-Scraper @invokeArgs
Write-Host ">>> End <<<" -ForegroundColor Cyan