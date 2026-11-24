# Tooling Primitives

This directory is the canonical primitives root for Prismata tooling.

## Layout

- `powershell/` - active PowerShell primitives used by Scraper, Sample, and other tooling entrypoints.
- `python/` - active Python support modules for ASTalyzer and related wrappers.
- `typescript/` - active Typescript support modules and primitives for Universe and related wrappers.

## Rules

- New reusable PowerShell primitives and support code belong in `powershell/`.
- New reusable Python primitives and support code belongs in `python/`.
- New reusable Typscript primitives and support code belongs in `typescript/`.
- Avoid adding new active scripts at the root unless they are temporary shims.

## Current Consumers

- Scraper uses `powershell/config-helpers.ps1`, `powershell/folder-tree.ps1`, and related helpers.
- ConfigMerge uses `powershell/config-helpers.ps1`.
- ASTalyzer wrapper resolves `python/` directly.

## Migration Notes

- Keep path changes deterministic and update tests when moving an active primitive.
- Preserve compatibility wrappers until all direct callers are migrated
