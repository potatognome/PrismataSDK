<#
Config Helpers - primitives/config-helpers.ps1

Provides lightweight helpers for converting JSON <-> YAML and
rendering configuration objects as clean, machine-friendly text.

Functions:
 - Convert-YamlToJson
 - Convert-JsonToYaml
 - Remove-MissingValuesText
 - Convert-ConfigToText

Designed to be dot-sourced from scripts or run interactively.
#>

Set-StrictMode -Version Latest
function Get-Yaml {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "YAML file not found: $Path"
    }

    $raw = Get-Content $Path -Raw
    Write-Host ">>> Loading YAML from: $Path" -ForegroundColor DarkGreen
    return ConvertFrom-Yaml $raw
}

function Import-PowerShellYamlIfNeeded {
    if (-not (Get-Command ConvertFrom-Yaml -ErrorAction SilentlyContinue)) {
        Try {
            Import-Module powershell-yaml -ErrorAction Stop
        } Catch {
            throw "Module 'powershell-yaml' is required for YAML conversion. Install it from PSGallery and retry."
        }
    }
}

function Convert-YamlToJson {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string] $YamlPath,
        [Parameter(Mandatory = $false)][string] $YamlString,
        [int] $Depth = 10
    )

    Import-PowerShellYamlIfNeeded

    if ($YamlPath) {
        $yaml = Get-Content -Raw -Path $YamlPath
    } elseif ($YamlString) {
        $yaml = $YamlString
    } else {
        throw 'Provide either -YamlPath or -YamlString.'
    }

    $obj = ConvertFrom-Yaml -Yaml $yaml
    return ($obj | ConvertTo-Json -Depth $Depth)
}

function Convert-JsonToYaml {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string] $JsonPath,
        [Parameter(Mandatory = $false)][string] $JsonString
    )

    Import-PowerShellYamlIfNeeded

    if ($JsonPath) {
        $json = Get-Content -Raw -Path $JsonPath
    } elseif ($JsonString) {
        $json = $JsonString
    } else {
        throw 'Provide either -JsonPath or -JsonString.'
    }

    $obj = $json | ConvertFrom-Json -ErrorAction Stop
    return (ConvertTo-Yaml -Data $obj)
}

function Get-TypeFullName {
    param($Value)
    if ($null -eq $Value) { return 'Null' }
    try { return $Value.GetType().FullName } catch { return 'Unknown' }
}

function Get-FlattenedConfigObject {
    param(
        [Parameter(Mandatory = $true)][object] $InputObject,
        [string] $Prefix = ''
    )

    $out = @()

    if ($InputObject -is [System.Collections.IEnumerable] -and -not ($InputObject -is [string])) {
        # Array / list: enumerate indices
        $idx = 0
        foreach ($item in $InputObject) {
            $key = if ($Prefix) { "$Prefix[$idx]" } else { "[$idx]" }
            if ($item -is [System.Management.Automation.PSObject] -or $item -is [hashtable]) {
                $out += Get-FlattenedConfigObject -InputObject $item -Prefix $key
            } else {
                $out += [pscustomobject]@{ Key = $key; Value = $item; Type = Get-TypeFullName $item }
            }
            $idx++
        }
        return $out
    }

    if ($InputObject -is [System.Management.Automation.PSObject] -or $InputObject -is [hashtable]) {
        foreach ($k in $InputObject.psobject.Properties.Name) {
            $v = $InputObject.$k
            $key = if ($Prefix) { "$Prefix.$k" } else { $k }
            if ($v -is [System.Management.Automation.PSObject] -or $v -is [hashtable] -or ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string]))) {
                $out += Get-FlattenedConfigObject -InputObject $v -Prefix $key
            } else {
                $out += [pscustomobject]@{ Key = $key; Value = $v; Type = Get-TypeFullName $v }
            }
        }
        return $out
    }

    # Scalar
    return [pscustomobject]@{ Key = $Prefix; Value = $InputObject; Type = Get-TypeFullName $InputObject }
}

function Remove-MissingValuesText {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string] $InputPath,
        [Parameter(Mandatory = $false)][string] $InputString,
        [ValidateSet('json','yaml')][string] $Format = 'json',
        [switch] $AsJson
    )

    if (-not $InputPath -and -not $InputString) { throw 'Provide -InputPath or -InputString' }

    if ($Format -eq 'json') {
        if ($InputPath) { $raw = Get-Content -Raw -Path $InputPath }
        else { $raw = $InputString }
        $obj = $raw | ConvertFrom-Json -ErrorAction Stop
    } else {
        Import-PowerShellYamlIfNeeded
        if ($InputPath) { $raw = Get-Content -Raw -Path $InputPath }
        else { $raw = $InputString }
        $obj = ConvertFrom-Yaml -Yaml $raw
    }

    $flat = Get-FlattenedConfigObject -InputObject $obj
    $filtered = $flat | Where-Object { ($null -ne $_.Value) -and ($_.Value -ne '') -and -not ($_.Value -is [System.Collections.ICollection] -and ($_.Value.Count -eq 0)) }

    if ($AsJson) {
        # Return structured JSON of flattened entries
        $struct = $filtered | ForEach-Object {
            [pscustomobject]@{
                Key = $_.Key
                Value = if ($_.Value -is [System.Collections.IEnumerable] -and -not ($_.Value -is [string])) { ($_.Value -join ', ') } else { $_.Value }
                Type = $_.Type
            }
        }
        return ($struct | ConvertTo-Json -Depth 10)
    }

    $lines = $filtered | ForEach-Object { "{0} : {1}" -f $_.Key, ($_.Value -join ', ') }
    return ($lines -join "`n")
}

function Convert-ConfigToText {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string] $InputPath,
        [Parameter(Mandatory = $false)][string] $InputString,
        [ValidateSet('json','yaml')][string] $Format = 'json',
        [switch] $RemovePunctuation = $true,
        [switch] $IncludeTypeNames = $true,
        [switch] $AsJson
    )

    if (-not $InputPath -and -not $InputString) { throw 'Provide -InputPath or -InputString' }

    if ($Format -eq 'json') {
        if ($InputPath) { $raw = Get-Content -Raw -Path $InputPath }
        else { $raw = $InputString }
        $obj = $raw | ConvertFrom-Json -ErrorAction Stop
    } else {
        Import-PowerShellYamlIfNeeded
        if ($InputPath) { $raw = Get-Content -Raw -Path $InputPath }
        else { $raw = $InputString }
        $obj = ConvertFrom-Yaml -Yaml $raw
    }

    $flat = Get-FlattenedConfigObject -InputObject $obj

    $lines = foreach ($item in $flat) {
        $val = if ($null -eq $item.Value) { '' } elseif ($item.Value -is [System.Collections.IEnumerable] -and -not ($item.Value -is [string])) { ($item.Value -join ', ') } else { [string]$item.Value }

        if ($RemovePunctuation) {
            $val = [regex]::Replace($val, "[^\w\s\.\-_]", '')
        }

        if ($IncludeTypeNames) {
            "$($item.Key) : $val (Type: $($item.Type))"
        } else {
            "$($item.Key) : $val"
        }
    }
    # If caller wants machine-friendly JSON, return structured JSON
    if ($PSBoundParameters.ContainsKey('AsJson') -and $PSBoundParameters['AsJson']) {
        $struct = $flat | ForEach-Object {
            [pscustomobject]@{
                Key = $_.Key
                Value = if ($_.Value -is [System.Collections.IEnumerable] -and -not ($_.Value -is [string])) { ($_.Value -join ', ') } else { $_.Value }
                Type = $_.Type
            }
        }
        return ($struct | ConvertTo-Json -Depth 10)
    }

    return ($lines -join "`n")
}

# End of config-helpers.ps1
