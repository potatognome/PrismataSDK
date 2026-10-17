# Copilot Instructions for PrismataSDK

## Created: 2026-10-15  Last Updated: 2026-10-16

PrismataSDK Copilot Instruction File

This instruction file defines how Copilot should behave when assisting with development inside the PrismataSDK repository. It references the PrismataSDK Migration Plan and the active migration checklist so that guidance, completions, and code suggestions stay aligned with the new CMF + PSO architecture. Copilot must prioritize UI subsystem migration, multi‑coloured pane rendering, UI framework stability, and menu functionality.

The authoritative migration plan is located at `.github/PrismataSDK-migration-plan.md` and the execution tracker is `.github/checklists/prismatasdk-migration-checklist.md`.

1. Purpose of This Instruction File

This file instructs Copilot to:

Follow the PrismataSDK Migration Plan as the authoritative reference.
Use the checklist at `.github/checklists/prismatasdk-migration-checklist.md` to track completed work and remaining migration items.
Prioritize UI subsystem migration and testing.
Accept breaking changes during migration.
Ensure all modules rely on CMF envelopes and PSO construction.
Provide structured, schema‑aligned suggestions.
Avoid referencing deprecated interfaces or legacy Prismata structures.

2. Core Behavioral Rules for Copilot

2.1 Always Reference the Migration Plan and Checklist

Copilot must treat the PrismataSDK Migration Plan as the primary source of truth for:

Migration order
Module responsibilities
Testing priorities
Breaking change policy
UI subsystem requirements

Copilot must also treat the checklist at `.github/checklists/prismatasdk-migration-checklist.md` as the live execution tracker for completed and outstanding migration work.
The checklist must be updated when scope, status, or implementation milestones change.

2.2 Prioritize UI Subsystem Migration

Copilot must focus on:

UI framework loader
Pane loader and runtime
Border-pattern loader
Chromascheme loader
Menu loader and resolver

Preview engine

These components must be migrated first.

2.3 Enforce CMF + PSO Architecture

Copilot must:

Suggest CMF envelope usage for all new modules.
Suggest PSO construction for all runtime objects.
Avoid legacy object formats.
Avoid legacy interface names.

2.4 Allow Breaking Changes

Copilot must not attempt backward compatibility with:

Old Prismata modules
Deprecated UI interfaces
Legacy pane/menu formats
Breaking changes are allowed and expected.

2.5 Maintain Schema Alignment

Copilot must:

Use canonical schemas as the source of truth.
Use `/PrismataCore/canonical` as the primary canonical schema reference path.
Suggest field names exactly as defined in schemas.
Respect rules: blocks (xor, at-least-one, etc.).
Suggest object registry entries that match schema definitions.

2.6 Maintain Folder Structure Alignment

Copilot must place new modules in:

PrismataSDK/core/
PrismataSDK/ui/
PrismataSDK/capabilities/
PrismataSDK/tenants/
PrismataSDK/cli/
PrismataSDK/apps/
PrismataSDK/examples/
PrismataSDK/tests/

### 2.7 UI Framework Loader Priority

Copilot must treat the UI Framework Loader as the single highest‑priority migration target until it is fully implemented and validated.

The UI Framework Loader is the foundation of the migrated UI subsystem and must be completed before any colour, chroma, ANSI, or styling features are addressed.

Copilot must prioritize:

- framework loading via CMF envelopes,
- framework → pane resolution,
- framework → menu routing,
- pane location resolution (fixed, relative, split, multi‑pane),
- menu dispatch and menu-item resolution,
- framework composition rules and runtime PSO construction.

Pane location and menu implementation are higher priority than:

- colour roles,
- chromaschemes,
- border colours,
- ANSI rendering,
- any visual styling or decoration.

Copilot must defer all colour‑related or ANSI‑related implementation until:

1. The UI Framework Loader is complete,
2. Pane location resolution is stable,
3. Menu routing is validated through tests.

Copilot must ensure all suggestions, completions, and architectural guidance reflect this priority ordering.


3. UI Migration Requirements

3.1 Multi‑Coloured Pane Support

Copilot must:

Suggest chroma integration.

Suggest colour role lookups.

Suggest chromaschemes for pane rendering.

3.2 UI Framework Stability

Copilot must:

Suggest framework loading via CMF.

Suggest PSO-based framework runtime.

Suggest menu routing inside frameworks.

3.3 Menu Functionality

Copilot must:

Suggest menu → pane dispatch.

Suggest menu → ui_framework routing.

Suggest menu-item registry usage.

4. Loader and Runtime Requirements

Copilot must:

Suggest CMF loaders for schemas, objects, manifests, and modules.

Suggest PSO builders for runtime objects.

Suggest runtime modules for panes, borders, chroma, menus, and frameworks.

5. Testing Requirements

Copilot must prioritize tests for:

UI framework composition

Multi‑coloured pane rendering

Menu routing

Pane positioning rules

CMF loader correctness

PSO builder correctness

6. Examples Requirements

Copilot must:

Suggest example objects for panes, menus, chromaschemes, borders, and frameworks.
Use `/PrismataCore/examples/registry` as the primary example object reference source.

Ensure examples follow CMF + PSO.

7. Apps Requirements (Vile, Vise, Universe)

Copilot must:

Suggest updates to Vile (VI-light editor) using CMF loaders.

Suggest updates to Vise (structured editor) using schema loaders.

Suggest updates to Universe (workspace generator, ingestion engine, previewer) using PSO runtime.

8. Prohibited Suggestions

Copilot must NOT:

Suggest legacy Prismata interfaces.

Suggest non-CMF object formats.

Suggest deprecated folder structures.

Suggest backward compatibility layers.

9. Completion Style Requirements

Copilot must:

Provide structured, schema-aligned completions.

Use CMF terminology consistently.

Use PSO terminology consistently.

Provide deterministic, architecture-driven suggestions.

10. Final Rule

Copilot must treat the PrismataSDK Migration Plan as the authoritative reference for all SDK development until migration is complete.

Copilot must also keep the checklist at `.github/checklists/prismatasdk-migration-checklist.md` aligned with actual implementation progress so the repository reflects both the migration strategy and the live status of migration work.