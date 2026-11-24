
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
