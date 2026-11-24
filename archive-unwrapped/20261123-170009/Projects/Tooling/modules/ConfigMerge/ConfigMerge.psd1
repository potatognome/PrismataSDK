@{
    # Script module metadata
    RootModule        = 'ConfigMerge.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = 'b7c1e4b1-4e8f-4c9e-9f7a-2c8d1f4f9c11'

    Author            = 'Daniel'
    CompanyName       = 'Prismata Tooling'
    Copyright         = '(c) 2026 <the.potato.gnome@gmail.com> All rights reserved.'

    Description       = 'Deterministic configuration merge engine with conflictMode precedence.'

    # No ScriptsToProcess

    # Only export the public API
    FunctionsToExport = @(
        'Merge-Config'
        , 'Get-ConfigMergeHelp'
        , 'Invoke-ConfigMerge'
        , 'Show-ConfigMergeTable'
        , 'Get-ConflictModeRegistry'
        , 'Get-ConflictModeManifest'
        , 'Validate-ConflictMode'
        , 'Apply-ConflictMode'
        , 'Write-ConflictModeAuditEntry'
        , 'Get-ConflictModeAuditTrail'
        , 'Set-ConflictMode'
    )

    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()

    # PowerShell compatibility
    PowerShellVersion = '5.1'
    CompatiblePSEditions = @('Desktop','Core')

    # Private data for tooling or future metadata
    PrivateData = @{
        ConfigMerge = @{
            Schema = 'ConfigMerge.schema.yaml'
            Notes  = 'Primitive module providing deterministic merge semantics and conflictMode resolution.'
        }
    }
}
