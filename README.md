# PrismataSDK

This repository is the migration scaffold for PrismataSDK under the CMF + PSO architecture.

## Current status

The project is being migrated in phases aligned to the PrismataSDK migration plan:

1. CMF envelope and registry primitives
2. UI framework, pane, and menu contracts
3. schema-aligned runtime builders
4. preview and tenant overrides
5. CLI validation and inspection flows

## Package layout

- `core/` — CMF envelopes, schema loaders, registry primitives, and runtime builders
- `ui/` — panes, menus, and UI framework composition objects
- `capabilities/` — capability registry entry points
- `tenants/` — tenant override loading and resolution
- `cli/` — command-line validation and inspection
- `apps/` — Vile, Vise, and Universe app entry points
- `examples/` — reference manifests and runtime examples
- `tests/` — migration-focused tests for loaders and UI runtime

## Migration principle

All runtime objects are expected to be built from CMF capsules and validated against canonical schema definitions. Old Prismata-specific interfaces are intentionally not preserved during this migration.
