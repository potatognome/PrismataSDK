Write-Host ">>> Scraper module LOADED (manifest initialization)" -ForegroundColor Cyan
Write-Host ">>> Module root: $PSScriptRoot" -ForegroundColor Gray

# Define global defaults here so they ALWAYS load
$Global:ScraperDefaults = @{
    includeType   = @("*")
    ignoreType    = @()
    includeFolders = @("*")
    excludeFolders = @()
    mode = @("default")
}

Write-Host ">>> Scraper defaults initialized" -ForegroundColor Green
Write-Host ""

# Import ConfigMerge for canonical config merging (optional: fail loudly)
$configMergePath = Join-Path $PSScriptRoot '..\ConfigMerge\ConfigMerge.psd1'
if (Test-Path $configMergePath) {
    try {
        Import-Module $configMergePath -Force -ErrorAction Stop
        Write-Host ">>> ConfigMerge imported from: $configMergePath" -ForegroundColor Cyan
    } catch {
            Write-Host ">>> Failed to import ConfigMerge: $_ - continuing without it" -ForegroundColor Yellow
    }
} else {
        Write-Host ">>> ConfigMerge not found at: $configMergePath - continuing without it" -ForegroundColor Yellow
}
