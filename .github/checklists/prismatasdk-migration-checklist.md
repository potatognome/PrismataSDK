# PrismataSDK Migration Checklist

This checklist tracks the execution status of the PrismataSDK migration against the authoritative migration plan in `.github/PrismataSDK-migration-plan.md`. Items marked complete are verified against working scaffolding or tests. Items marked incomplete are still open migration work.

## Completed

- [x] Confirm migration scope is focused on the UI layer and CMF + PSO architecture.
- [x] Create the authoritative migration plan document for PrismataSDK.
- [x] Create a repo-level migration scaffold for the SDK package layout.
- [x] Establish core CMF envelope and PSO builder primitives.
- [x] Establish object registry contracts for runtime registration.
- [x] Implement schema specification and rule loader contracts.
- [x] Implement manifest loader contracts for module and root manifests.
- [x] Implement the registry-driven CMF + PSO loader pipeline for runtime object registration.
- [x] Create UI framework, pane, and menu runtime contracts.
- [x] Implement UI framework composition and menu route resolution logic for the migrated runtime.
- [x] Extend framework routing for split-pane, multi-pane, and grid-pane layouts beyond the initial route-table scaffold.
- [x] Add slot-based framework route resolution for split/grid layouts with pane membership validation.
- [x] Add initial migration verification tests for core CMF, schema, manifest, registry, UI composition, and UI routing behavior.
- [x] Validate the migration scaffold with pytest in the workspace virtual environment (30 passing tests).
- [x] Move operational version/source-path scripts from PrismataCore validators into PrismataSDK core ops for SDK-local migration operations.
- [x] Align schema loading references to use /PrismataCore/canonical for canonical schema source.
- [x] Define canonical schema validation contracts for pane, menu, border, chroma, and framework objects beyond the current scaffold.
- [x] Expand the schema loader to support richer canonical validation and rule semantics for UI objects.
- [x] Define and implement explicit UI gate acceptance criteria for framework loading, pane location resolution, and menu routing before colour work.
- [x] Expand automated tests for loader correctness, rule validation, rendering, and framework routing.
- [x] Add multi-coloured pane rendering behavior and role-based colour resolution.

## Incomplete

- [ ] Add border-pattern resolution and chromascheme application flow.
- [ ] Add preview engine integration for pane rendering, borders, and chroma composition.
- [ ] Add tenant override loading and resolution for panes, menus, borders, chroma, and frameworks.
- [ ] Add CLI commands for validate, build, preview, list, and inspect using CMF + PSO.
- [ ] Align example object references to use /PrismataCore/examples/registry as the migration reference set.
- [ ] Add examples for panes, menus, chroma, borders, and UI frameworks that match the migrated architecture.
- [ ] Add app migration tasks for Vile, Vise, and Universe integration.

## Execution Notes

- Source of truth: `.github/PrismataSDK-migration-plan.md`
- Execution tracker: this checklist should be updated as each migration phase is completed.
- Canonical schema source: `/PrismataCore/canonical`
- Example reference source: `/PrismataCore/examples/registry`
- UI-first gate: framework loader + pane resolution + menu routing must remain complete and validated before chroma/border/ANSI work proceeds.
- Breaking changes remain acceptable and expected until migration is complete.
