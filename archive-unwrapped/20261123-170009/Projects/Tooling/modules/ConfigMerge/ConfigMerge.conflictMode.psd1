@{
    # ==================================================================
    #  ConflictMode Manifest (UDI-Compliant)
    #  Provides module-level configuration for conflictMode behavior.
    #  Loaded during boot and cached during runtime/duty cycle.
    # ==================================================================

    ManifestVersion = '1.0.0'
    ManifestName    = 'ConfigMerge ConflictMode Manifest'
    UDICompliant    = $true

    # ------------------------------------------------------------------
    #  Registry Path
    #  Points to the authoritative conflictMode.registry.yaml
    # ------------------------------------------------------------------
    RegistryPath = 'conflictMode.registry.yaml'

    # ------------------------------------------------------------------
    #  Default Conflict Mode
    #  Used when no mode is specified in defaults, config, mode, style,
    #  or CLI. Must exist in the registry.
    # ------------------------------------------------------------------
    DefaultConflictMode = 'unionWins'

    # ------------------------------------------------------------------
    #  Validation Rules
    #  Ensures all conflictModes are schema-valid and UDI-compliant.
    # ------------------------------------------------------------------
    Validation = @{
        RequiredFields = @(
            'name',
            'description',
            'behavior',
            'appliesTo',
            'precedence',
            'asciiIndicator',
            'udiCompliant'
        )

        # Allowed modes must match registry entries
        AllowedModes = @(
            'removeWins',
            'unionWins',
            'includeWins',
            'cliWins'
        )

        # Optional: enforce UDI compliance at manifest level
        EnforceUDI = $true
    }

    # ------------------------------------------------------------------
    #  Visualization Settings
    #  Used by ConfigMerge.Visualize to render merge tables.
    # ------------------------------------------------------------------
    Visualization = @{
        AsciiIndicators = @{
            removeWins  = '-'
            unionWins   = '='
            includeWins = '+'
            cliWins     = '!'
        }

        # Optional: colourKey integration (future PR)
        ColourKeys = @{
            removeWins  = 'conflict.remove'
            unionWins   = 'conflict.union'
            includeWins = 'conflict.include'
            cliWins     = 'conflict.cli'
        }

        # Whether colourKeyPath is required (currently false)
        RequireColourKey = $false
    }

    # ------------------------------------------------------------------
    #  Runtime Integration
    #  Defines how conflictMode is applied during merge operations.
    # ------------------------------------------------------------------
    Runtime = @{
        # Load registry at boot
        LoadRegistryOnBoot = $true

        # Validate conflictMode before applying merge logic
        ValidateBeforeApply = $true

        # Apply conflictMode to both arrays and scalars
        AppliesTo = @('array', 'scalar')

        # Enable audit trail logging
        EnableAuditTrail = $true

        # Log file path (optional)
        AuditLogPath = './logs/conflictMode.audit.log'
    }

    # ------------------------------------------------------------------
    #  Notes
    # ------------------------------------------------------------------
    Notes = @(
        'This manifest ensures conflictMode behavior is deterministic,',
        'UDI-compliant, and portable across all modules.',
        'ColourKey integration is optional and will be enabled in a future PR.'
    )
}
