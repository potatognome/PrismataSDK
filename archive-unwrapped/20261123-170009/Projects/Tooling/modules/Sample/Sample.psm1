Set-StrictMode -Version Latest

function Initialize-SampleModule {
    [CmdletBinding()]
    param()

    Import-Module powershell-yaml -ErrorAction Stop

    $Global:SampleDefaults = @{
        sampleString = @('Sample String (Default)')
        sampleInt    = @(24)
        samplePath   = @('C:\Sample\Path\Default')
        sampleArray  = @('Sample', 'Array', 'Default')
        sampleSwitch = @($true)
        mode         = @('default')
    }

    return $Global:SampleDefaults
}

function Get-SampleConfigPaths {
    [CmdletBinding()]
    param()

    $moduleRoot = $PSScriptRoot

    return [pscustomobject]@{
        ConfigPath       = Join-Path $moduleRoot 'config.yaml'
        ModeRegistryPath = Join-Path $moduleRoot 'sample-modes.registry.yaml'
    }
}

function Get-SampleYaml {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "YAML file not found: $Path"
    }

    if (-not (Get-Command -Name ConvertFrom-Yaml -ErrorAction SilentlyContinue)) {
        Import-Module powershell-yaml -ErrorAction Stop
    }

    $raw = Get-Content -LiteralPath $Path -Raw
    return (ConvertFrom-Yaml $raw)
}

function ConvertTo-SampleHashtable {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [object] $InputObject
    )

    $out = @{}
    if ($null -eq $InputObject) {
        return $out
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        foreach ($key in $InputObject.Keys) {
            $out[[string]$key] = $InputObject[$key]
        }
        return $out
    }

    foreach ($prop in $InputObject.PSObject.Properties) {
        $out[$prop.Name] = $prop.Value
    }

    return $out
}

function Get-SampleModeRegistry {
    [CmdletBinding()]
    param(
        [string] $Path
    )

    $paths = Get-SampleConfigPaths
    $registryPath = if ($Path) { $Path } else { $paths.ModeRegistryPath }

    $yaml = Get-SampleYaml -Path $registryPath

    if ($null -eq $yaml -or $null -eq $yaml.modes) {
        return @{}
    }

    if ($yaml.modes -is [hashtable]) {
        return $yaml.modes
    }

    $registry = @{}
    foreach ($mode in $yaml.modes) {
        if ($mode.name) {
            $registry[$mode.name] = $mode
        }
    }

    return $registry
}

function Resolve-SampleMode {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string] $Mode,

        [Parameter(Mandatory = $true)]
        [hashtable] $Registry
    )

    if (-not $Registry.ContainsKey($Mode)) {
        return @{}
    }

    $current = ConvertTo-SampleHashtable -InputObject $Registry[$Mode]

    if (-not $current.ContainsKey('name')) {
        $current['name'] = $Mode
    }

    if ($current.ContainsKey('extends') -and $current['extends']) {
        $parentData = Resolve-SampleMode -Mode ([string]$current['extends']) -Registry $Registry
        foreach ($key in $parentData.Keys) {
            if (-not $current.ContainsKey($key)) {
                $current[$key] = $parentData[$key]
            }
        }
    }

    return $current
}

function Merge-SampleSettings {
    [CmdletBinding()]
    param(
        [hashtable] $Defaults = @{},
        [hashtable] $ConfigData = @{},
        [hashtable] $ModeData = @{},
        [hashtable] $StyleData = @{},
        [hashtable] $CliData = @{},
        [string] $ConflictMode
    )

    $cli = @{}
    if ($CliData) {
        foreach ($k in $CliData.Keys) {
            $cli[$k] = $CliData[$k]
        }
    }

    if ($ConflictMode) {
        $cli['conflictMode'] = $ConflictMode
    }

    if (Get-Command -Name Merge-Config -ErrorAction SilentlyContinue) {
        return (Merge-Config -Defaults $Defaults -Mode $ModeData -Config $ConfigData -Style $StyleData -Cli $cli)
    }

    $merged = @{}
    foreach ($key in $Defaults.Keys) { $merged[$key] = $Defaults[$key] }
    foreach ($key in $ConfigData.Keys) { $merged[$key] = $ConfigData[$key] }
    foreach ($key in $ModeData.Keys) { $merged[$key] = $ModeData[$key] }
    foreach ($key in $StyleData.Keys) { $merged[$key] = $StyleData[$key] }
    foreach ($key in $cli.Keys) { $merged[$key] = $cli[$key] }

    return $merged
}

function Invoke-Sample {
    [CmdletBinding()]
    param(
        [string] $InputPath,
        [string] $OutputPath,
        [string] $ConfigPath,
        [string] $Mode = 'default',
        [switch] $Relative,
        [string] $ConflictMode
    )

    if (-not $Global:SampleDefaults) {
        Initialize-SampleModule | Out-Null
    }

    $paths = Get-SampleConfigPaths
    $effectiveConfigPath = if ($ConfigPath) { $ConfigPath } else { $paths.ConfigPath }

    $registry = Get-SampleModeRegistry
    $modeData = Resolve-SampleMode -Mode $Mode -Registry $registry

    $configData = @{}
    if ($effectiveConfigPath -and (Test-Path -LiteralPath $effectiveConfigPath)) {
        $rawConfig = Get-SampleYaml -Path $effectiveConfigPath
        $configData = ConvertTo-SampleHashtable -InputObject $rawConfig
    }

    $cliData = @{}
    if ($Mode) {
        $cliData['mode'] = $Mode
    }

    $settings = Merge-SampleSettings -Defaults $Global:SampleDefaults `
        -ConfigData $configData `
        -ModeData $modeData `
        -StyleData @{} `
        -CliData $cliData `
        -ConflictMode $ConflictMode

    return [pscustomobject]@{
        InputPath    = $InputPath
        OutputPath   = $OutputPath
        Relative     = [bool]$Relative
        Mode         = $Mode
        Settings     = $settings
        ConfigPath   = $effectiveConfigPath
        RegistryPath = $paths.ModeRegistryPath
    }
}

function Get-SampleHelp {
    [CmdletBinding()]
    param(
        [switch] $VerboseOutput
    )

    $help = @()
    $help += 'Sample module functions:'
    $help += ' - Initialize-SampleModule'
    $help += ' - Get-SampleConfigPaths'
    $help += ' - Get-SampleModeRegistry'
    $help += ' - Resolve-SampleMode'
    $help += ' - Merge-SampleSettings'
    $help += ' - Invoke-Sample'
    $help += ' - Get-SampleHelp'

    if ($VerboseOutput) {
        $help += ''
        $help += 'Example:'
        $help += "    Invoke-Sample -InputPath 'C:\Projects\MyApp' -OutputPath 'C:\scrapes' -Mode 'sample-composite'"
    }

    return ($help -join "`n")
}

Export-ModuleMember -Function Initialize-SampleModule,Get-SampleConfigPaths,Get-SampleModeRegistry,Resolve-SampleMode,Merge-SampleSettings,Invoke-Sample,Get-SampleHelp
