@{
    # ---------------------------------------------------------------------
    # Identity
    # ---------------------------------------------------------------------
    RootModule        = 'Scraper.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = 'b7e1c1d5-4f3e-4c9a-9e2f-1a2b3c4d5e6f'
    Author            = 'Daniel'
    CompanyName       = 'Prismata'
    Copyright         = '(c) 2026 Prismata. All rights reserved.'

    # ---------------------------------------------------------------------
    # Description
    # ---------------------------------------------------------------------
    Description       = 'Prismata Scraper module providing multi-folder scraping, mode registry, YAML config loading, and output naming engine.'

    # ---------------------------------------------------------------------
    # PowerShell Compatibility
    # ---------------------------------------------------------------------
    PowerShellVersion = '5.1'
    CompatiblePSEditions = @('Desktop', 'Core')

    # ---------------------------------------------------------------------
    # Module Dependencies
    # ---------------------------------------------------------------------
    RequiredModules   = @(
        @{ ModuleName = 'powershell-yaml'; ModuleVersion = '0.4.2' }
    )

    # ---------------------------------------------------------------------
    # Initialization Scripts
    # These scripts DO execute at module import time.
    # ---------------------------------------------------------------------
    ScriptsToProcess  = @(
        'onload.ps1'
    )

    # ---------------------------------------------------------------------
    # Exported Members
    # (You can restrict this later if you want)
    # ---------------------------------------------------------------------
    FunctionsToExport = @(
        'Invoke-Scraper',
        'Invoke-ScraperFolder',
        'Start-Scrape',
        'Get-ScraperHelp',
        'Initialize-ScraperModule',
        'Test-ScraperModule',
        'Get-Yaml',
        'Get-ProjectsIndex',
        'Resolve-ProjectPaths',
        'Get-ModeRegistry',
        'Resolve-Mode',
        'Merge-ScraperSettings',
        'New-ScraperOutputName',
        'Get-WorkspaceRoot'
    )

    AliasesToExport   = @()
    CmdletsToExport   = @()
    VariablesToExport = @('*')

    # ---------------------------------------------------------------------
    # Private Data (optional)
    # ---------------------------------------------------------------------
    PrivateData = @{
        PSData = @{
            Tags = @('Prismata', 'Scraper', 'Tooling', 'YAML', 'Automation')
            ProjectUri = 'https://example.com/prismata'
            LicenseUri = 'https://example.com/prismata/license'
            IconUri    = 'https://example.com/prismata/icon'
        }
    }
}
