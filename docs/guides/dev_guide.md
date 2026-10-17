# PrismataSDK Developer Guide

## Repository layout

- `core/` — CMF envelopes, PSO builders, schema loaders, manifest loaders, registry primitives, and ops
- `ui/` — panes, menus, UI frameworks, and runtime composition helpers
- `capabilities/` — capability registry and manifest-aware resolution
- `tenants/` — tenant override entry points
- `cli/` — command-line entry points for validation and inspection
- `apps/` — Vile, Vise, and Universe scaffolding
- `examples/` — reference manifests and runtime examples
- `tests/` — migration-focused verification

## CMF + PSO architecture

PrismataSDK migration work uses CMF envelopes as the canonical input format and PSO objects as the runtime output format.

- CMF envelopes carry identity, versioning, metadata, relations, notes, and content.
- PSO objects represent validated runtime state.
- Loaders should validate structure early and produce schema-aligned runtime objects.

## Manifests

Manifests define module identity, kind, version, capabilities, interfaces, and metadata.

- Root manifest support belongs in `manifest.yaml`.
- Module manifests belong in `manifest.d/*.yaml`.
- Capability resolution should be driven from manifest declarations rather than ad hoc lookups.

## Capabilities

Capabilities are the bridge between module manifests and runtime features.

- A capability registry stores named capability definitions.
- A resolver reads manifest capability declarations and matches them against the registry.
- Missing capabilities should fail fast so migration scaffolding stays deterministic.

## Loaders

The migration order keeps loaders narrow and testable:

1. CMF loader
2. schema loader
3. manifest loader
4. object registry loader
5. capability resolver
6. UI loaders and runtimes

All loaders should remain aligned with canonical schema source data and the object registry layout.

## UI subsystem

The UI migration prioritizes structure before styling.

- UI frameworks define pane composition and menu routing.
- Panes resolve fixed, relative, and split positioning.
- Menus route actions or targets to panes or framework-level handlers.
- Colour, chroma, borders, and ANSI rendering remain deferred until structural UI behavior is stable.

## Migration flow

1. Establish docs and migration guidance.
2. Complete manifest and capability scaffolding.
3. Finish UI framework, pane, and menu loaders.
4. Add border and chroma resolution after structural UI stabilizes.
5. Extend preview, tenant overrides, CLI, and apps last.

## Working rule

Prefer the smallest deterministic change that preserves the CMF + PSO migration direction and keeps tests focused on structural behavior.
