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

## Review corpus builder

To review a wrapped legacy Prismata corpus and generate migration-oriented inventory artifacts:

```powershell
python core/ops/build_review_corpus.py --input-root ./archive-wrapped/Prismata --output-root ./archive-wrapped/review-corpus
```

The report set includes:

- `review_report.json` with owner/disposition/subtype/tag counts
- `artifact_inventory.jsonl` with one row per wrapped artifact
- `compatibility_matrix.csv` for Core/SDK/Corp/Archive routing review
- `planning_index.json` for plans, checklists, and instruction-focused artifacts

## Staged migration corpus assembler

After generating the review corpus inventory, route wrapped artifacts into Core/SDK/Corp lanes for integration review:

```powershell
python core/ops/assemble_staged_migration_corpus.py --wrapped-root ./archive-wrapped/Prismata --review-root ./archive-wrapped/review-corpus --output-root ./archive-wrapped/staged-migration
```

Outputs:

- `artifacts/PrismataCore`, `artifacts/PrismataSDK`, `artifacts/PrismataCorp`, and `artifacts/NeedsReview`
- `reports/staging_report.json`
- `reports/compatibility_gaps.json`
- `reports/planning_instruction_digest.json`
- `reports/missing_sources.json`

`ArchiveOnly` runtime/workspace artifacts remain represented in reports but are not copied into the staged payload.
