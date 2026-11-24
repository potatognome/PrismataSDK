param(
    [string]$SampleString,
    [int]$SampleInt,
    [string]$SamplePath,
    [string[]]$SampleArray,
    [switch]$SampleSwitch,
    [string]$Mode
)

# Ensure console outputs UTF-8 to avoid mojibake on Windows
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}

# Also set PowerShell's default output encoding for redirections and child processes
if ($PSVersionTable.PSVersion.Major -ge 3) {
    $OutputEncoding = [System.Text.Encoding]::UTF8
}

# Also try setting console input encoding and the active code page to UTF-8
try {
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
} catch {
}
try {
    # Use chcp to set the console active code page to 65001 (UTF-8)
    chcp 65001 > $null 2>&1
} catch {
}

# Initialization paths:
# OS-safe config path resolution
$toolingRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$configPath = Join-Path $toolingRoot "modules/Sample/config/config.yaml"
$modeRegistryPath = Join-Path $toolingRoot "modules/Sample/config/sample-modes.registry.yaml"

# Ensure YAML helpers are loaded before reading config/registry files.
$configHelpersPath = Join-Path $PSScriptRoot 'config-helpers.ps1'
if (Test-Path -LiteralPath $configHelpersPath) {
    . $configHelpersPath
}

# Load config data from default.yaml
$configData = Get-Yaml -Path $configPath
# Load mode registry from sample-modes.registry.yaml
$modeRegistry = Get-Yaml -Path $modeRegistryPath

## Import and initialize Sample module early so defaults are available
Write-Host ">>> Importing Sample module..." -ForegroundColor Cyan
Import-Module "$PSScriptRoot/../../modules/Sample/Sample.psm1" -Force
Write-Host ">>> Initializing Sample module..." -ForegroundColor Cyan
Initialize-SampleModule

# Helper: normalize default values (flatten arrays to printable value)
function Get-DefaultForParam {
    param([string]$ParamName)
    if (-not $Global:SampleDefaults) { return $null }
    $key = ($ParamName.Substring(0,1).ToLower() + $ParamName.Substring(1))
    if (-not $Global:SampleDefaults.ContainsKey($key)) { return $null }
    $v = $Global:SampleDefaults[$key]
    if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) {
        if ($v.Count -eq 0) { return $null }
        if ($v.Count -eq 1) { return $v[0] }
        return ($v -join ', ')
    }
    return $v
}

# Build an array of PSCustomObject descriptors for EligibleParams using module defaults
$eligibleNames = @('SampleString','SampleInt','SamplePath','SampleArray','SampleSwitch','Mode')
$eligibleList = @()
foreach ($n in $eligibleNames) {
    $defaultVal = Get-DefaultForParam $n
    $t = switch ($n) {
        'SampleInt' { 'int' }
        'SampleArray' { 'string[]' }
        'SampleSwitch' { 'switch' }
        default { 'string' }
    }
    $eligibleList += [PSCustomObject]@{
        Name     = $n
        Default  = $defaultVal
        Type     = $t
        Provided = $false
    }
}

$invocationLine = "& $PSCommandPath"
if ($SampleString) { $invocationLine += " -SampleString `"$SampleString`"" }
if ($SamplePath)   { $invocationLine += " -SamplePath `"$SamplePath`"" }
if ($SampleArray)  { $invocationLine += " -SampleArray `"$SampleArray`"" }
if ($SampleSwitch) { $invocationLine += " -SampleSwitch" }
if ($Mode)         { $invocationLine += " -Mode `"$Mode`"" }

# Terminal/Logging output for auditability
Clear-Host
. "$PSScriptRoot/bordered-header.ps1"
Show-BorderedHeader -Message 'Prismata Sample Primitive' -BorderChar '=' -BorderColor Cyan -MessageColor Magenta -Width 80
Write-Host ""
# Print exact invocation (command + args) for auditability using invocation table primitive
. "$PSScriptRoot/show-invocation-table.ps1"
# Show invocation with eligible params derived from defaults
Show-InvocationTable -InvocationArgs $PSBoundParameters `
                     -Title 'Command Invocation' `
                     -InvocationLine $invocationLine `
                     -EligibleParams $eligibleList `
                     -Width 80 -ShowMode 'Both' -Format table -ShowTypes -ShowEmpty -ShowMeta
Write-Host ""

Write-Host ">>> Tooling root identified as: $toolingRoot" -ForegroundColor Gray
Write-Host ">>> Config imported from: $configPath" -ForegroundColor Cyan

# Show merged config breakdown using ConfigMerge (if available)
Write-Host "`n>>> Config Merge Table (layered view)" -ForegroundColor Cyan
$configMergePath = Join-Path $toolingRoot "modules/ConfigMerge/ConfigMerge.psm1"
if (Test-Path $configMergePath) {
    try {
        Import-Module $configMergePath -Force -ErrorAction Stop

        # Prepare Defaults (use SampleDefaults if available)
        $defaults = @{}
        if ($Global:SampleDefaults) {
            # use a shallow clone to avoid mutating global
            foreach ($k in $Global:SampleDefaults.Keys) { $defaults[$k] = $Global:SampleDefaults[$k] }
        }

        # Resolve Mode data (prefer Sample resolver, fallback to direct registry lookup)
        $modeData = @{}
        if ($Mode) {
            if (Get-Command -Name Resolve-SampleMode -ErrorAction SilentlyContinue) {
                $modeData = Resolve-SampleMode -Mode $Mode -Registry $modeRegistry
            } elseif ($modeRegistry -and $modeRegistry.ContainsKey($Mode)) {
                $modeData = $modeRegistry[$Mode]
            }
        }

        # Style is not used in this sample, leave empty
        $style = @{}

        # CLI overrides: include bound parameters (map ParamName -> camelCase key)
        $cli = @{}
        foreach ($p in $PSBoundParameters.Keys) {
            # map PowerShell param name (PascalCase) to lowercase-first key (sampleString -> sampleString)
            $mapped = ($p.Substring(0,1).ToLower() + $p.Substring(1))
            $cli[$mapped] = $PSBoundParameters[$p]
        }

        # Call the table display (keep empty values shown by default)
        Show-ConfigMergeTable -Defaults $defaults -Mode $modeData -Config $configData -Style $style -Cli $cli

    } catch {
        Write-Warning "Failed to load ConfigMerge module: $_"
    }
} else {
    Write-Host ">>> ConfigMerge module not found at: $configMergePath" -ForegroundColor Yellow
}
