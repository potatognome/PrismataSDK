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
