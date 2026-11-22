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

## CMF wrapper tool

PrismataSDK includes a repository wrapper utility for converting existing text artifacts into CMF-compatible backup artifacts:

```powershell
python core/ops/wrap_repository_to_cmf.py --input-root ../Prismata --output-root ./wrapped-archive
```

- Emits one wrapped output per source file in a mirrored directory tree.
- Assigns deterministic Prismata-compliant UDI values.
- Uses `kind=wrapped-<subtype>` classification.
- Skips binary/unreadable files and reports them explicitly.

## CMF unwrapper tool

PrismataSDK also includes an unwrap utility for restoring snapshot/reference files from wrapped CMF archive artifacts:

```powershell
python core/ops/unwrap_cmf_archive.py --input-root ./wrapped-archive --output-root ./unwrapped
```

- Restores from `*.cmf.json` artifacts.
- Uses snapshot-oriented restore semantics.
- Defaults to datestamped output roots to reduce collisions.
- Sanitizes unsafe source paths into safe relative destinations.
- Verifies digests by default when provided.
