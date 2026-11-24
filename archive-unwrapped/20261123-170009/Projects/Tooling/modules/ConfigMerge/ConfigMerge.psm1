Set-StrictMode -Version Latest

$script:ConflictModeRuntime = @{
    Manifest             = $null
    ManifestPath         = $null
    Registry             = $null
    RegistryPath         = $null
    LastMergeLayers      = $null
    LastMergeResult      = $null
    LastWinnerByParameter = @{}
    OverrideConflictMode  = $null
    BootLoaded           = $false
    LastBootError        = $null
}

function Join-Array {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [object[]] $Base,

        [Parameter(Mandatory = $false)]
        [object[]] $Overlay
    )

    if (-not $Base -and -not $Overlay) {
        return @()
    }

    if (-not $Base) {
        return @($Overlay | Select-Object -Unique)
    }

    if (-not $Overlay) {
        return @($Base | Select-Object -Unique)
    }

    return @($Base + $Overlay | Select-Object -Unique)
}

function Test-EnumerableValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [object] $Value
    )

    return ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string]))
}

function Get-ModuleFilePath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string] $FileName
    )

    return (Join-Path $PSScriptRoot $FileName)
}

function Get-ObjectPropertyValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object] $Object,

        [Parameter(Mandatory = $true)]
        [string] $Name
    )

    if ($null -eq $Object) {
        return $null
    }

    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) {
            return $Object[$Name]
        }
        return $null
    }

    $prop = $Object.PSObject.Properties[$Name]
    if ($prop) {
        return $prop.Value
    }

    return $null
}

function ConvertFrom-ConflictModeScalar {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [string] $RawValue
    )

    if ($null -eq $RawValue) {
        return $null
    }

    $value = $RawValue.Trim()

    if ($value -eq '') {
        return ''
    }

    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    if ($value -match '^(?i:true|false)$') {
        return [System.Convert]::ToBoolean($value)
    }

    if ($value -match '^\d+(\.\d+)?$') {
        if ($value -match '\.') {
            return [double]$value
        }
        return [int]$value
    }

    return $value
}

function ConvertFrom-ConflictModeInlineArray {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string] $RawValue
    )

    $trimmed = $RawValue.Trim()
    if (-not ($trimmed.StartsWith('[') -and $trimmed.EndsWith(']'))) {
        return @()
    }

    $inner = $trimmed.Substring(1, $trimmed.Length - 2)
    if ($inner.Trim() -eq '') {
        return @()
    }

    $parts = @()
    foreach ($part in ($inner -split ',')) {
        $parts += (ConvertFrom-ConflictModeScalar -RawValue $part)
    }

    return @($parts)
}

function ConvertFrom-ConflictModeRegistryYaml {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Content
    )

    $result = [ordered]@{
        version      = $null
        registryName = $null
        udiCompliant = $null
        modes        = @()
    }

    $inModes = $false
    $currentMode = $null
    $multilineField = $null
    $multilineBuffer = @()

    function Flush-MultilineValue {
        if ($null -eq $currentMode -or -not $multilineField) {
            return
        }

        $joined = ($multilineBuffer -join ' ').Trim()
        $currentMode[$multilineField] = $joined
        $multilineField = $null
        $multilineBuffer = @()
    }

    foreach ($raw in $Content) {
        $line = $raw

        if ($line -match '^\s*#') {
            continue
        }

        if ($line.Trim() -eq '') {
            if ($multilineField) {
                $multilineBuffer += ''
            }
            continue
        }

        if ($line -match '^modes:\s*$') {
            $inModes = $true
            continue
        }

        if (-not $inModes) {
            if ($line -match '^version:\s*(.+)$') {
                $result.version = ConvertFrom-ConflictModeScalar -RawValue $Matches[1]
                continue
            }
            if ($line -match '^registryName:\s*(.+)$') {
                $result.registryName = ConvertFrom-ConflictModeScalar -RawValue $Matches[1]
                continue
            }
            if ($line -match '^udiCompliant:\s*(.+)$') {
                $result.udiCompliant = ConvertFrom-ConflictModeScalar -RawValue $Matches[1]
                continue
            }
            continue
        }

        if ($line -match '^\s*-\s+name:\s*(.+)$') {
            Flush-MultilineValue
            if ($currentMode) {
                $result.modes += ,$currentMode
            }
            $currentMode = [ordered]@{}
            $currentMode.name = ConvertFrom-ConflictModeScalar -RawValue $Matches[1]
            continue
        }

        if (-not $currentMode) {
            continue
        }

        if ($multilineField) {
            if ($line -match '^\s{6}(.+)$') {
                $multilineBuffer += $Matches[1].Trim()
                continue
            }

            Flush-MultilineValue
        }

        if ($line -match '^\s{4}([a-zA-Z][a-zA-Z0-9]*):\s*(.*)$') {
            $key = $Matches[1]
            $rawValue = $Matches[2]

            if ($rawValue -eq '>') {
                $multilineField = $key
                $multilineBuffer = @()
                continue
            }

            if ($rawValue.Trim().StartsWith('[') -and $rawValue.Trim().EndsWith(']')) {
                $currentMode[$key] = ConvertFrom-ConflictModeInlineArray -RawValue $rawValue
                continue
            }

            $currentMode[$key] = ConvertFrom-ConflictModeScalar -RawValue $rawValue
            continue
        }
    }

    Flush-MultilineValue
    if ($currentMode) {
        $result.modes += ,$currentMode
    }

    return $result
}

function Resolve-ConflictModeRegistryPath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [hashtable] $ManifestData,

        [Parameter(Mandatory = $true)]
        [string] $ManifestPath
    )

    $declared = [string]$ManifestData.RegistryPath
    $candidatePaths = @()

    if ($declared) {
        if ([System.IO.Path]::IsPathRooted($declared)) {
            $candidatePaths += $declared
        } else {
            $candidatePaths += (Join-Path (Split-Path -Parent $ManifestPath) $declared)
            $candidatePaths += (Join-Path $PSScriptRoot $declared)
        }
    }

    $candidatePaths += (Join-Path $PSScriptRoot 'conflictMode.registry.yaml')

    foreach ($path in $candidatePaths) {
        if (Test-Path -LiteralPath $path) {
            return (Resolve-Path -LiteralPath $path).Path
        }
    }

    throw "ConflictModePathError: Unable to resolve registry path. Manifest declared '$declared'. Manifest path: '$ManifestPath'."
}

function Get-ConflictModeManifest {
    [CmdletBinding()]
    param(
        [switch] $Reload
    )

    if (-not $Reload -and $script:ConflictModeRuntime.Manifest) {
        return $script:ConflictModeRuntime.Manifest
    }

    $manifestPath = Get-ModuleFilePath -FileName 'ConfigMerge.conflictMode.psd1'
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw "ConflictModeManifestError: Manifest not found at '$manifestPath'."
    }

    $manifestData = Import-PowerShellDataFile -Path $manifestPath

    if (-not $manifestData.Validation) {
        throw "ConflictModeManifestError: Missing Validation section in '$manifestPath'."
    }

    if (-not $manifestData.Runtime) {
        throw "ConflictModeManifestError: Missing Runtime section in '$manifestPath'."
    }

    if (-not $manifestData.Visualization) {
        throw "ConflictModeManifestError: Missing Visualization section in '$manifestPath'."
    }

    $requiredFields = @($manifestData.Validation.RequiredFields)
    $allowedModes = @($manifestData.Validation.AllowedModes)
    $asciiIndicators = @{}
    if ($manifestData.Visualization.AsciiIndicators) {
        $asciiIndicators = @{} + $manifestData.Visualization.AsciiIndicators
    }

    $manifest = [pscustomobject]@{
        Path                = (Resolve-Path -LiteralPath $manifestPath).Path
        RegistryPath        = [string]$manifestData.RegistryPath
        DefaultConflictMode = [string]$manifestData.DefaultConflictMode
        Validation          = [pscustomobject]@{
            RequiredFields = $requiredFields
            AllowedModes   = $allowedModes
            EnforceUDI     = [bool]$manifestData.Validation.EnforceUDI
        }
        Visualization       = [pscustomobject]@{
            AsciiIndicators = $asciiIndicators
            ColourKeys      = $manifestData.Visualization.ColourKeys
            RequireColourKey = [bool]$manifestData.Visualization.RequireColourKey
        }
        Runtime             = [pscustomobject]@{
            LoadRegistryOnBoot = [bool]$manifestData.Runtime.LoadRegistryOnBoot
            ValidateBeforeApply = [bool]$manifestData.Runtime.ValidateBeforeApply
            AppliesTo          = @($manifestData.Runtime.AppliesTo)
            EnableAuditTrail   = [bool]$manifestData.Runtime.EnableAuditTrail
            AuditLogPath       = [string]$manifestData.Runtime.AuditLogPath
        }
        Raw                 = $manifestData
    }

    $script:ConflictModeRuntime.Manifest = $manifest
    $script:ConflictModeRuntime.ManifestPath = $manifest.Path

    return $manifest
}

function Get-ConflictModeRegistry {
    [CmdletBinding()]
    param(
        [switch] $Reload,

        [Parameter(Mandatory = $false)]
        [object] $Manifest
    )

    if (-not $Manifest) {
        $Manifest = Get-ConflictModeManifest
    }

    if (-not $Reload -and $script:ConflictModeRuntime.Registry) {
        return $script:ConflictModeRuntime.Registry
    }

    $resolvedRegistryPath = Resolve-ConflictModeRegistryPath -ManifestData $Manifest.Raw -ManifestPath $Manifest.Path

    $content = Get-Content -LiteralPath $resolvedRegistryPath -ErrorAction Stop

    $parsed = $null
    if (Get-Command -Name ConvertFrom-Yaml -ErrorAction SilentlyContinue) {
        $parsed = ($content -join "`n") | ConvertFrom-Yaml
    } else {
        $parsed = ConvertFrom-ConflictModeRegistryYaml -Content $content
    }

    if (-not $parsed -or -not $parsed.modes) {
        throw "ConflictModeRegistryError: No modes found in '$resolvedRegistryPath'."
    }

    $requiredFields = @($Manifest.Validation.RequiredFields)
    $typedModes = @()

    foreach ($mode in @($parsed.modes)) {
        $entry = [pscustomobject]@{
            name           = [string](Get-ObjectPropertyValue -Object $mode -Name 'name')
            description    = [string](Get-ObjectPropertyValue -Object $mode -Name 'description')
            behavior       = [string](Get-ObjectPropertyValue -Object $mode -Name 'behavior')
            appliesTo      = @((Get-ObjectPropertyValue -Object $mode -Name 'appliesTo'))
            precedence     = [string](Get-ObjectPropertyValue -Object $mode -Name 'precedence')
            asciiIndicator = [string](Get-ObjectPropertyValue -Object $mode -Name 'asciiIndicator')
            udiCompliant   = [bool](Get-ObjectPropertyValue -Object $mode -Name 'udiCompliant')
            colourKey      = (Get-ObjectPropertyValue -Object $mode -Name 'colourKey')
            notes          = (Get-ObjectPropertyValue -Object $mode -Name 'notes')
            examples       = (Get-ObjectPropertyValue -Object $mode -Name 'examples')
        }

        $missingFields = @()
        foreach ($field in $requiredFields) {
            $fieldValue = $entry.PSObject.Properties[$field].Value
            if ($null -eq $fieldValue -or ([string]$fieldValue).Trim() -eq '') {
                $missingFields += $field
            }
        }

        if ($missingFields.Count -gt 0) {
            $errorData = [ordered]@{
                errorType    = 'ConflictModeRegistryValidationError'
                mode         = $entry.name
                missingFields = $missingFields
                registryPath = $resolvedRegistryPath
                manifestPath = $Manifest.Path
            }
            throw ("ConflictModeRegistryValidationError: " + ($errorData | ConvertTo-Json -Compress))
        }

        $typedModes += ,$entry
    }

    $modeIndex = @{}
    foreach ($mode in $typedModes) {
        $modeIndex[$mode.name] = $mode
    }

    $registry = [pscustomobject]@{
        Path         = $resolvedRegistryPath
        Version      = $parsed.version
        RegistryName = $parsed.registryName
        UDICompliant = [bool]$parsed.udiCompliant
        Modes        = $typedModes
        ModeIndex    = $modeIndex
        Raw          = $parsed
    }

    $script:ConflictModeRuntime.Registry = $registry
    $script:ConflictModeRuntime.RegistryPath = $registry.Path

    return $registry
}

function Validate-ConflictMode {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string] $Mode,

        [Parameter(Mandatory = $true)]
        [object] $Registry,

        [Parameter(Mandatory = $true)]
        [object] $Manifest
    )

    $modeName = [string]$Mode
    $modeEntry = $null

    if ($Registry.ModeIndex.ContainsKey($modeName)) {
        $modeEntry = $Registry.ModeIndex[$modeName]
    }

    $missingFields = @()

    if (-not $modeEntry) {
        $errorData = [ordered]@{
            errorType    = 'ConflictModeValidationError'
            mode         = $modeName
            missingFields = @('mode-not-found-in-registry')
            registryPath = $Registry.Path
            manifestPath = $Manifest.Path
        }
        throw ("ConflictModeValidationError: " + ($errorData | ConvertTo-Json -Compress))
    }

    if (@($Manifest.Validation.AllowedModes) -notcontains $modeName) {
        $errorData = [ordered]@{
            errorType    = 'ConflictModeValidationError'
            mode         = $modeName
            missingFields = @('mode-not-allowed-by-manifest')
            registryPath = $Registry.Path
            manifestPath = $Manifest.Path
        }
        throw ("ConflictModeValidationError: " + ($errorData | ConvertTo-Json -Compress))
    }

    foreach ($requiredField in @($Manifest.Validation.RequiredFields)) {
        $value = $modeEntry.PSObject.Properties[$requiredField].Value
        if ($null -eq $value -or ([string]$value).Trim() -eq '') {
            $missingFields += $requiredField
        }
    }

    if ($Manifest.Validation.EnforceUDI -and -not $modeEntry.udiCompliant) {
        $missingFields += 'udiCompliant'
    }

    if ($missingFields.Count -gt 0) {
        $errorData = [ordered]@{
            errorType    = 'ConflictModeValidationError'
            mode         = $modeName
            missingFields = $missingFields
            registryPath = $Registry.Path
            manifestPath = $Manifest.Path
        }
        throw ("ConflictModeValidationError: " + ($errorData | ConvertTo-Json -Compress))
    }

    return $modeEntry
}

function Apply-ConflictMode {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string] $Mode,

        [Parameter(Mandatory = $false)]
        [object] $Value,

        [Parameter(Mandatory = $false)]
        [object] $Incoming
    )

    if ($null -eq $Incoming) {
        return $Value
    }

    $normalized = $Mode.ToLowerInvariant()

    switch ($normalized) {
        'unionwins' {
            if ((Test-EnumerableValue -Value $Value) -and (Test-EnumerableValue -Value $Incoming)) {
                return ,(Join-Array -Base $Value -Overlay $Incoming)
            }
            if ((Test-EnumerableValue -Value $Value) -and -not (Test-EnumerableValue -Value $Incoming)) {
                return ,(Join-Array -Base $Value -Overlay @($Incoming))
            }
            if (Test-EnumerableValue -Value $Incoming) {
                return ,(@($Incoming))
            }
            return $Incoming
        }
        'includewins' {
            if (Test-EnumerableValue -Value $Incoming) {
                return ,(@($Incoming))
            }
            if (Test-EnumerableValue -Value $Value) {
                return ,(@($Incoming))
            }
            return $Incoming
        }
        'cliwins' {
            if (Test-EnumerableValue -Value $Incoming) {
                return ,(@($Incoming))
            }
            if (Test-EnumerableValue -Value $Value) {
                return ,(@($Incoming))
            }
            return $Incoming
        }
        'removewins' {
            if ((Test-EnumerableValue -Value $Value) -and (Test-EnumerableValue -Value $Incoming)) {
                return ,(Join-Array -Base $Value -Overlay $Incoming)
            }
            if ((Test-EnumerableValue -Value $Value) -and -not (Test-EnumerableValue -Value $Incoming)) {
                return ,(Join-Array -Base $Value -Overlay @($Incoming))
            }
            if (Test-EnumerableValue -Value $Incoming) {
                return ,(@($Incoming))
            }
            return $Incoming
        }
        default {
            throw "Unknown conflictMode '$Mode'."
        }
    }
}

function Resolve-RemoveWins {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [hashtable] $Settings
    )

    if ($Settings.ContainsKey('includeTypes') -and $Settings.ContainsKey('excludeTypes')) {
        $include = $Settings['includeTypes']
        $exclude = $Settings['excludeTypes']

        if ($include -and $exclude) {
            $Settings['includeTypes'] = $include | Where-Object { $exclude -notcontains $_ }
        }
    }

    if ($Settings.ContainsKey('includeFolders') -and $Settings.ContainsKey('excludeFolders')) {
        $include = $Settings['includeFolders']
        $exclude = $Settings['excludeFolders']

        if ($include -and $exclude) {
            $Settings['includeFolders'] = $include | Where-Object { $exclude -notcontains $_ }
        }
    }

    if ($Settings.ContainsKey('includePatterns') -and $Settings.ContainsKey('excludePatterns')) {
        $include = $Settings['includePatterns']
        $exclude = $Settings['excludePatterns']

        if ($include -and $exclude) {
            $Settings['includePatterns'] = $include | Where-Object { $exclude -notcontains $_ }
        }
    }

    if ($Settings.ContainsKey('includeAttributes') -and $Settings.ContainsKey('excludeAttributes')) {
        $include = $Settings['includeAttributes']
        $exclude = $Settings['excludeAttributes']

        if ($include -and $exclude) {
            $Settings['includeAttributes'] = $include | Where-Object { $exclude -notcontains $_ }
        }
    }
}

function Resolve-IncludeWins {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [hashtable] $Settings
    )

    if ($Settings.ContainsKey('includeTypes') -and $Settings.ContainsKey('excludeTypes')) {
        $include = $Settings['includeTypes']
        $exclude = $Settings['excludeTypes']

        if ($include -and $exclude) {
            $Settings['excludeTypes'] = $exclude | Where-Object { $include -notcontains $_ }
        }
    }

    if ($Settings.ContainsKey('includeFolders') -and $Settings.ContainsKey('excludeFolders')) {
        $include = $Settings['includeFolders']
        $exclude = $Settings['excludeFolders']

        if ($include -and $exclude) {
            $Settings['excludeFolders'] = $exclude | Where-Object { $include -notcontains $_ }
        }
    }

    if ($Settings.ContainsKey('includePatterns') -and $Settings.ContainsKey('excludePatterns')) {
        $include = $Settings['includePatterns']
        $exclude = $Settings['excludePatterns']

        if ($include -and $exclude) {
            $Settings['excludePatterns'] = $exclude | Where-Object { $include -notcontains $_ }
        }
    }

    if ($Settings.ContainsKey('includeAttributes') -and $Settings.ContainsKey('excludeAttributes')) {
        $include = $Settings['includeAttributes']
        $exclude = $Settings['excludeAttributes']

        if ($include -and $exclude) {
            $Settings['excludeAttributes'] = $exclude | Where-Object { $include -notcontains $_ }
        }
    }
}

function Merge-Layers {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [array] $Layers,

        [Parameter(Mandatory = $true)]
        [string] $ConflictMode,

        [Parameter(Mandatory = $false)]
        [ref] $WinnerByParameter
    )

    $result = @{}
    $winners = @{}

    foreach ($layer in $Layers) {
        $layerValue = $layer.Value
        if (-not $layerValue) {
            continue
        }

        foreach ($key in $layerValue.Keys) {
            $incoming = $layerValue[$key]

            if (-not $result.ContainsKey($key)) {
                if ($null -ne $incoming) {
                    if (Test-EnumerableValue -Value $incoming) {
                        $result[$key] = @($incoming)
                    } else {
                        $result[$key] = $incoming
                    }
                    $winners[$key] = $layer.Name
                }
                continue
            }

            $existing = $result[$key]
            if ($null -eq $incoming) {
                continue
            }

            $effectiveMode = $ConflictMode
            if ($ConflictMode -eq 'cliWins' -and $layer.Name -ne 'Cli') {
                $effectiveMode = 'unionWins'
            }

            $updated = Apply-ConflictMode -Mode $effectiveMode -Value $existing -Incoming $incoming
            $result[$key] = $updated
            $winners[$key] = $layer.Name
        }
    }

    if ($WinnerByParameter) {
        $WinnerByParameter.Value = $winners
    }

    return $result
}

function Resolve-Conflicts {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [hashtable] $Settings,

        [Parameter(Mandatory = $true)]
        [string] $Mode
    )

    $Settings['conflictMode'] = $Mode

    switch ($Mode) {
        'removeWins' {
            Resolve-RemoveWins -Settings $Settings
        }
        'includeWins' {
            Resolve-IncludeWins -Settings $Settings
        }
        'unionWins' {
        }
        'cliWins' {
        }
        default {
            throw "Unknown conflictMode '$Mode'. Valid values are defined in conflictMode.registry.yaml."
        }
    }
}

function Get-EffectiveConflictMode {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [array] $Layers,

        [Parameter(Mandatory = $true)]
        [object] $Manifest
    )

    $mode = $null

    foreach ($layer in $Layers) {
        if ($layer.Value -and $layer.Value.ContainsKey('conflictMode') -and $null -ne $layer.Value['conflictMode']) {
            $mode = [string]$layer.Value['conflictMode']
        }
    }

    if (-not $mode -and $script:ConflictModeRuntime.OverrideConflictMode) {
        $mode = [string]$script:ConflictModeRuntime.OverrideConflictMode
    }

    if (-not $mode) {
        $mode = [string]$Manifest.DefaultConflictMode
    }

    return $mode
}

function Get-AuditLogPath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object] $Manifest
    )

    $configured = [string]$Manifest.Runtime.AuditLogPath
    if (-not $configured) {
        return (Join-Path $PSScriptRoot 'logs\conflictMode.audit.log')
    }

    if ([System.IO.Path]::IsPathRooted($configured)) {
        return $configured
    }

    return (Join-Path $PSScriptRoot $configured)
}

function Write-ConflictModeAuditEntry {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string] $Parameter,

        [Parameter(Mandatory = $true)]
        [string] $ConflictMode,

        [Parameter(Mandatory = $true)]
        [object] $RegistryEntry,

        [Parameter(Mandatory = $true)]
        [object] $Manifest,

        [Parameter(Mandatory = $true)]
        [hashtable] $LayerValues,

        [Parameter(Mandatory = $false)]
        [object] $FinalMergedValue,

        [Parameter(Mandatory = $false)]
        [string] $WinningLayer
    )

    $auditLogPath = Get-AuditLogPath -Manifest $Manifest
    $auditDir = Split-Path -Parent $auditLogPath
    if ($auditDir -and -not (Test-Path -LiteralPath $auditDir)) {
        New-Item -Path $auditDir -ItemType Directory -Force | Out-Null
    }

    $manifestEntry = [ordered]@{
        path                = $Manifest.Path
        registryPath        = $Manifest.RegistryPath
        defaultConflictMode = $Manifest.DefaultConflictMode
        validation          = $Manifest.Validation
        visualization       = $Manifest.Visualization
        runtime             = $Manifest.Runtime
    }

    $entry = [ordered]@{
        timestamp      = (Get-Date).ToString('o')
        parameter      = $Parameter
        conflictMode   = $ConflictMode
        registryEntry  = $RegistryEntry
        manifestEntry  = $manifestEntry
        layerValues    = [ordered]@{
            defaults = $LayerValues['Defaults']
            config   = $LayerValues['Config']
            mode     = $LayerValues['Mode']
            style    = $LayerValues['Style']
            cli      = $LayerValues['Cli']
        }
        finalMergedValue = $FinalMergedValue
        winningLayer     = $WinningLayer
    }

    $line = $entry | ConvertTo-Json -Depth 20 -Compress
    Add-Content -LiteralPath $auditLogPath -Value $line -Encoding UTF8

    return $entry
}

function Get-ConflictModeAuditTrail {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [string] $Parameter
    )

    $manifest = Get-ConflictModeManifest
    $auditLogPath = Get-AuditLogPath -Manifest $manifest

    if (-not (Test-Path -LiteralPath $auditLogPath)) {
        return @()
    }

    $entries = @()
    foreach ($line in (Get-Content -LiteralPath $auditLogPath)) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $item = $line | ConvertFrom-Json
        if ($Parameter -and $item.parameter -ne $Parameter) {
            continue
        }

        $entries += ,$item
    }

    return $entries
}

function Invoke-ConflictModeAuditForMerge {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [array] $Layers,

        [Parameter(Mandatory = $true)]
        [hashtable] $Merged,

        [Parameter(Mandatory = $true)]
        [hashtable] $WinnerByParameter,

        [Parameter(Mandatory = $true)]
        [string] $ConflictMode,

        [Parameter(Mandatory = $true)]
        [object] $Manifest,

        [Parameter(Mandatory = $true)]
        [object] $RegistryEntry
    )

    if (-not $Manifest.Runtime.EnableAuditTrail) {
        return
    }

    $layerMap = @{}
    foreach ($layer in $Layers) {
        $layerMap[$layer.Name] = $layer.Value
    }

    foreach ($parameter in $Merged.Keys) {
        $layerValues = @{
            Defaults = if ($layerMap.ContainsKey('Defaults') -and $layerMap['Defaults']) { $layerMap['Defaults'][$parameter] } else { $null }
            Config   = if ($layerMap.ContainsKey('Config') -and $layerMap['Config']) { $layerMap['Config'][$parameter] } else { $null }
            Mode     = if ($layerMap.ContainsKey('Mode') -and $layerMap['Mode']) { $layerMap['Mode'][$parameter] } else { $null }
            Style    = if ($layerMap.ContainsKey('Style') -and $layerMap['Style']) { $layerMap['Style'][$parameter] } else { $null }
            Cli      = if ($layerMap.ContainsKey('Cli') -and $layerMap['Cli']) { $layerMap['Cli'][$parameter] } else { $null }
        }

        $winner = if ($WinnerByParameter.ContainsKey($parameter)) { [string]$WinnerByParameter[$parameter] } else { '' }

        Write-ConflictModeAuditEntry -Parameter $parameter `
            -ConflictMode $ConflictMode `
            -RegistryEntry $RegistryEntry `
            -Manifest $Manifest `
            -LayerValues $layerValues `
            -FinalMergedValue $Merged[$parameter] `
            -WinningLayer $winner | Out-Null
    }
}

function Invoke-ConfigMergeInternal {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [array] $Layers
    )

    $manifest = Get-ConflictModeManifest
    $registry = Get-ConflictModeRegistry -Manifest $manifest

    $mode = Get-EffectiveConflictMode -Layers $Layers -Manifest $manifest
    if ($manifest.Runtime.ValidateBeforeApply) {
        $modeEntry = Validate-ConflictMode -Mode $mode -Registry $registry -Manifest $manifest
    } else {
        $modeEntry = if ($registry.ModeIndex.ContainsKey($mode)) { $registry.ModeIndex[$mode] } else { $null }
    }

    $winnerByParameter = @{}
    $merged = Merge-Layers -Layers $Layers -ConflictMode $mode -WinnerByParameter ([ref]$winnerByParameter)
    Resolve-Conflicts -Settings $merged -Mode $mode

    if ($manifest.Runtime.EnableAuditTrail -and $modeEntry) {
        Invoke-ConflictModeAuditForMerge -Layers $Layers -Merged $merged -WinnerByParameter $winnerByParameter -ConflictMode $mode -Manifest $manifest -RegistryEntry $modeEntry
    }

    $script:ConflictModeRuntime.LastMergeLayers = $Layers
    $script:ConflictModeRuntime.LastMergeResult = $merged
    $script:ConflictModeRuntime.LastWinnerByParameter = $winnerByParameter

    return $merged
}

function Merge-Config {
    [CmdletBinding()]
    param(
        [hashtable] $Defaults = @{},
        [hashtable] $Mode     = @{},
        [hashtable] $Config   = @{},
        [hashtable] $Style    = @{},
        [hashtable] $Cli      = @{}
    )

    $layers = @(
        @{ Name = 'Defaults'; Value = $Defaults },
        @{ Name = 'Config'  ; Value = $Config   },
        @{ Name = 'Mode'    ; Value = $Mode     },
        @{ Name = 'Style'   ; Value = $Style    },
        @{ Name = 'Cli'     ; Value = $Cli      }
    )

    return (Invoke-ConfigMergeInternal -Layers $layers)
}

function Set-ConflictMode {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string] $Mode
    )

    if (-not $script:ConflictModeRuntime.LastMergeLayers) {
        throw 'ConflictModeRuntimeError: No prior merge snapshot found. Run Merge-Config or Invoke-ConfigMerge before Set-ConflictMode.'
    }

    $manifest = Get-ConflictModeManifest
    $registry = Get-ConflictModeRegistry -Manifest $manifest
    Validate-ConflictMode -Mode $Mode -Registry $registry -Manifest $manifest | Out-Null

    $script:ConflictModeRuntime.OverrideConflictMode = $Mode

    $layers = @()
    foreach ($layer in $script:ConflictModeRuntime.LastMergeLayers) {
        $value = @{}
        if ($layer.Value) {
            foreach ($k in $layer.Value.Keys) {
                $value[$k] = $layer.Value[$k]
            }
        }

        if ($layer.Name -eq 'Cli') {
            $value['conflictMode'] = $Mode
        }

        $layers += @{ Name = $layer.Name; Value = $value }
    }

    $updated = Invoke-ConfigMergeInternal -Layers $layers

    $layerValues = @{}
    foreach ($layer in $layers) {
        $layerValues[$layer.Name] = $layer.Value
    }

    return (Show-ConfigMergeTable -Defaults $layerValues['Defaults'] -Mode $layerValues['Mode'] -Config $layerValues['Config'] -Style $layerValues['Style'] -Cli $layerValues['Cli'] -AsObjects)
}

function Get-ConfigMergeHelp {
    [CmdletBinding()]
    param(
        [switch]$VerboseOutput
    )

    $help = @()
    $help += 'ConfigMerge - Merge-Config(help):'
    $help += '- Function: Merge-Config - merges layers with precedence Defaults -> Config -> Mode -> Style -> Cli'
    $help += '- Parameters:'
    $help += '    -Defaults : hashtable of default settings (includeTypes, excludeTypes, includeFolders, excludeFolders, conflictMode, etc.)'
    $help += '    -Mode     : hashtable representing a mode (often from a mode registry)'
    $help += '    -Config   : hashtable loaded from a config YAML file'
    $help += '    -Style    : hashtable with style overrides (optional)'
    $help += '    -Cli      : hashtable for CLI overrides (highest precedence)'
    $help += '- Conflict resolution options for conflictMode: removeWins, includeWins, unionWins, cliWins'
    $help += '- ConflictMode APIs: Get-ConflictModeManifest, Get-ConflictModeRegistry, Validate-ConflictMode, Apply-ConflictMode, Write-ConflictModeAuditEntry, Get-ConflictModeAuditTrail, Set-ConflictMode'

    if ($VerboseOutput) {
        $help += ''
        $help += 'Example usage:'
        $help += '    $defaults = @{ includeTypes = @(''.ts''); excludeFolders = @(''node_modules'') }'
        $help += '    $mode = @{ includeTypes = @(''.ts'', ''.md'') }'
        $help += '    Merge-Config -Defaults $defaults -Mode $mode -Cli @{ conflictMode = ''unionWins'' }'
    }

    return ($help -join "`n")
}

function Invoke-ConfigMerge {
    [CmdletBinding()]
    param(
        [hashtable] $Defaults,
        [hashtable] $Mode,
        [hashtable] $Config,
        [hashtable] $Style,
        [hashtable] $Cli,
        [ValidateSet('psobject','json','yaml','text')]
        [string] $Format = 'psobject',
        [switch] $RemoveMissing,
        [switch] $TextAsJson,
        [string] $OutputPath
    )

    Write-Host ''
    Write-Host '=== ConfigMerge Invocation ===' -ForegroundColor Cyan

    Write-Host "`n-- Incoming Layers --" -ForegroundColor Yellow
    Write-Host 'Defaults:'; $Defaults | Format-List
    Write-Host 'Mode:';     $Mode     | Format-List
    Write-Host 'Config:';   $Config   | Format-List
    Write-Host 'Style:';    $Style    | Format-List
    Write-Host 'CLI:';      $Cli      | Format-List

    Write-Host "`n-- Merge Execution --" -ForegroundColor Yellow
    $merged = Merge-Config -Defaults $Defaults -Mode $Mode -Config $Config -Style $Style -Cli $Cli

    $helpersPath = Join-Path $PSScriptRoot '..\..\primitives\powershell\config-helpers.ps1'
    if (Test-Path $helpersPath) {
        . $helpersPath
    }

    Write-Host "`n-- Final conflictMode --" -ForegroundColor Yellow
    Write-Host $merged.conflictMode

    Write-Host "`n-- Final Merged Config --" -ForegroundColor Green
    $merged | Format-List

    Write-Host "`n=== End ConfigMerge Invocation ===`n" -ForegroundColor Cyan

    $resultOut = switch ($Format) {
        'psobject' { $merged }
        'json' {
            if (Get-Command Remove-MissingValuesText -ErrorAction SilentlyContinue -CommandType Function) {
                if ($RemoveMissing) {
                    Remove-MissingValuesText -InputString (ConvertTo-Json $merged -Depth 10) -Format json -AsJson | ConvertFrom-Json
                } else {
                    $merged | ConvertTo-Json -Depth 10 | ConvertFrom-Json
                }
            } else {
                $merged | ConvertTo-Json -Depth 10 | ConvertFrom-Json
            }
        }
        'yaml' {
            if (Get-Command Convert-JsonToYaml -ErrorAction SilentlyContinue -CommandType Function) {
                Convert-JsonToYaml -JsonString (ConvertTo-Json $merged -Depth 10)
            } else {
                $merged | ConvertTo-Json -Depth 10
            }
        }
        'text' {
            if ($RemoveMissing -and (Get-Command Remove-MissingValuesText -ErrorAction SilentlyContinue)) {
                if ($TextAsJson) { Remove-MissingValuesText -InputString (ConvertTo-Json $merged -Depth 10) -Format json -AsJson | ConvertFrom-Json }
                else { Remove-MissingValuesText -InputString (ConvertTo-Json $merged -Depth 10) -Format json }
            }

            if ($TextAsJson -and (Get-Command Convert-ConfigToText -ErrorAction SilentlyContinue)) {
                Convert-ConfigToText -InputString (ConvertTo-Json $merged -Depth 10) -Format json -RemovePunctuation -IncludeTypeNames -AsJson | ConvertFrom-Json
            }

            if (Get-Command Convert-ConfigToText -ErrorAction SilentlyContinue) {
                Convert-ConfigToText -InputString (ConvertTo-Json $merged -Depth 10) -Format json -RemovePunctuation -IncludeTypeNames
            } else {
                ($merged | Out-String)
            }
        }
        default { $merged }
    }

    if ($OutputPath) {
        try {
            if ($resultOut -is [string]) {
                $resultText = $resultOut
            } elseif ($resultOut -is [System.Management.Automation.PSObject] -or $resultOut -is [hashtable] -or ((Test-EnumerableValue -Value $resultOut) -and -not ($resultOut -is [string]))) {
                $resultText = $resultOut | ConvertTo-Json -Depth 10
            } else {
                $resultText = $resultOut | Out-String
            }

            $dir = Split-Path -Path $OutputPath -Parent
            if ($dir -and -not (Test-Path $dir)) {
                New-Item -Path $dir -ItemType Directory -Force | Out-Null
            }
            Set-Content -Path $OutputPath -Value $resultText -Encoding UTF8
            Write-Host "Wrote merged output to: $OutputPath" -ForegroundColor Cyan
        } catch {
            Write-Warning ("Failed to write output to {0}: {1}" -f $OutputPath, $_)
        }
    }

    return $resultOut
}

function Show-ConfigMergeTable {
    [CmdletBinding()]
    param(
        [hashtable] $Defaults = @{},
        [hashtable] $Mode     = @{},
        [hashtable] $Config   = @{},
        [hashtable] $Style    = @{},
        [hashtable] $Cli      = @{},
        [switch] $HideEmpty,
        [switch] $AsObjects
    )

    $merged = Merge-Config -Defaults $Defaults -Mode $Mode -Config $Config -Style $Style -Cli $Cli
    $conflictMode = if ($merged.ContainsKey('conflictMode')) { [string]$merged['conflictMode'] } else { 'removeWins' }

    $manifest = Get-ConflictModeManifest
    $registry = Get-ConflictModeRegistry -Manifest $manifest
    $modeEntry = if ($registry.ModeIndex.ContainsKey($conflictMode)) { $registry.ModeIndex[$conflictMode] } else { $null }

    $layersOrdered = @('Defaults','Mode','Config','Style','Cli')
    $layerValues = @{ Defaults = $Defaults; Mode = $Mode; Config = $Config; Style = $Style; Cli = $Cli }

    $keys = @()
    foreach ($lv in $layerValues.Values) {
        if ($lv) {
            foreach ($k in $lv.Keys) {
                if (-not ($keys -contains $k)) {
                    $keys += $k
                }
            }
        }
    }

    $rows = @()
    foreach ($k in ($keys | Sort-Object)) {
        $vals = @{}
        $presentAny = $false
        foreach ($ln in $layersOrdered) {
            $v = $null
            if ($layerValues[$ln] -and $layerValues[$ln].ContainsKey($k)) {
                $v = $layerValues[$ln][$k]
            }
            $vals[$ln] = $v
            if ($null -ne $v) {
                $presentAny = $true
            }
        }

        if ($HideEmpty -and -not $presentAny) {
            continue
        }

        $final = if ($merged.ContainsKey($k)) { $merged[$k] } else { $null }
        $winningLayer = if ($script:ConflictModeRuntime.LastWinnerByParameter.ContainsKey($k)) { [string]$script:ConflictModeRuntime.LastWinnerByParameter[$k] } else { '' }

        $winnerLayers = @()
        if ($winningLayer) {
            $winnerLayers = @($winningLayer)
        } elseif ($final -is [System.Collections.IEnumerable] -and -not ($final -is [string])) {
            foreach ($ln in $layersOrdered) {
                if ($vals[$ln]) {
                    $winnerLayers += $ln
                }
            }
        } else {
            foreach ($ln in @('Cli','Style','Config','Mode','Defaults')) {
                if ($vals[$ln] -ne $null) {
                    $winnerLayers = @($ln)
                    break
                }
            }
        }

        $display = @{}
        foreach ($ln in $layersOrdered) {
            $v = $vals[$ln]
            $s = if ((Test-EnumerableValue -Value $v)) { ($v -join ', ') } else { $v }
            if ($null -eq $s) {
                $s = ''
            }
            if ($winnerLayers -contains $ln) {
                if ($s -ne '') { $s = "* $s" } else { $s = '*' }
            }
            $display[$ln] = $s
        }

        $finalDisplay = if ((Test-EnumerableValue -Value $final)) { ($final -join ', ') } else { $final }
        $asciiIndicator = if ($manifest.Visualization.AsciiIndicators.ContainsKey($conflictMode)) { [string]$manifest.Visualization.AsciiIndicators[$conflictMode] } else { '' }
        $udiIndicator = if ($modeEntry) { [bool]$modeEntry.udiCompliant } else { $false }
        $overrideMarker = if ($winnerLayers.Count -gt 1) { 'inherit' } else { 'override' }

        $row = [PSCustomObject]@{
            Param                = $k
            ConflictMode         = $conflictMode
            ConflictModeName     = if ($modeEntry) { $modeEntry.name } else { $conflictMode }
            AsciiIndicator       = $asciiIndicator
            WinningLayer         = ($winnerLayers -join ', ')
            OverrideMarker       = $overrideMarker
            UDICompliant         = $udiIndicator
            Defaults             = $display['Defaults']
            Mode                 = $display['Mode']
            Config               = $display['Config']
            Style                = $display['Style']
            Cli                  = $display['Cli']
            FinalValue           = $finalDisplay
            FinalObject          = $final
            WinnerLayers         = ($winnerLayers -join ', ')
        }

        $rows += $row
    }

    if (-not $rows) {
        Write-Host '(no parameters found)'
        return
    }

    if ($AsObjects) {
        return $rows
    }

    $rows | Format-Table -AutoSize
}

function Initialize-ConflictModeRuntime {
    [CmdletBinding()]
    param()

    try {
        $manifest = Get-ConflictModeManifest
        if ($manifest.Runtime.LoadRegistryOnBoot) {
            Get-ConflictModeRegistry -Manifest $manifest | Out-Null
        }
        $script:ConflictModeRuntime.BootLoaded = $true
        $script:ConflictModeRuntime.LastBootError = $null
    } catch {
        $script:ConflictModeRuntime.BootLoaded = $false
        $script:ConflictModeRuntime.LastBootError = $_
        throw
    }
}

Initialize-ConflictModeRuntime

Export-ModuleMember -Function Merge-Config,Get-ConfigMergeHelp,Invoke-ConfigMerge,Show-ConfigMergeTable,Get-ConflictModeRegistry,Get-ConflictModeManifest,Validate-ConflictMode,Apply-ConflictMode,Write-ConflictModeAuditEntry,Get-ConflictModeAuditTrail,Set-ConflictMode
