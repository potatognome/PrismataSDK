# PrismataSDK Migration Plan

## Created: 2026-10-15  Last Updated: 2026-10-17

This document outlines the complete migration strategy for transitioning PrismataSDK into its new architecture, fully aligned with PrismataCore’s CMF capsule model, PSO construction rules, and updated schema system. It prioritizes user interface elements, multi‑coloured pane rendering, UI framework stability, and menu functionality. Breaking changes are permitted and expected.

1. Migration Philosophy

PrismataSDK is entering a new era where all modules must:
Rely on CMF envelopes for identity and structure.
Construct PSO objects for runtime behavior.
Load objects from registry folders (pane.d, menu.d, chroma.d, etc.).
Validate objects using canonical schemas.
Support multi‑coloured panes, UI frameworks, and menu routing.
Breaking changes are allowed and encouraged during this migration. The goal is correctness, clarity, and alignment with PrismataCore.
Create several example scripts in the examples folder demonstrating progressive complexity of UI frameworks, panes, multi pane layouts, menu functions, visibility and enablement conditions.
Encourage use of multi-coloured terminal backgrounds

2. Migration Priorities

2.1 UI Frameworks (Highest Priority)

UI frameworks define how panes, menus, borders, and their respective colour scheme and object roles contribute to ui object colours. Migration tasks:
Implement new ui_framework_loader using CMF + PSO.
Support multi‑pane, split‑pane, grid‑pane, and conditional visibility and enablement settings.
Validate frameworks against ui-framework.schema.yaml.
Ensure menu routing works inside panes and multi pane frameworks.

2.2 Pane System

Panes must support both fixed and relative positioning, multi‑coloured rendering, and border/chroma integration.
Implement pane_loader using object registry entries.
Support rules: blocks (xor, at-least-one) for positioning.
Integrate border-pattern and chromascheme lookups.
Validate against pane.schema.yaml.

2.3 Menu System

Menus, menu-items and headers define interactive UI behavior.
Implement menu_loader and menu_item_loader.
Support menu → pane dispatch.
Support menu → ui_framework routing.
Validate against menu.schema.yaml, menu-item.schema.yaml and header.schema.yaml.

2.4 Chroma System

Colour roles, border roles and colour schemes define multi‑coloured pane behavior.
Implement chroma_loader.
Support chroma application inside UI frameworks.
Validate against colour-scheme.schema.yaml.

2.5 Border Pattern System

Borders define pane edges and visual structure.
Implement border_loader.
Support border roles and metadata.
Validate against border-pattern.schema.yaml.

3. Core Loader Migration

3.1 CMF Loader

All SDK modules must load CMF capsules using the new envelope rules.
Support id, udi, kind, version, tenant, metadata, relations, validation, notes, content.

3.2 Schema Loader

Schemas must be loaded from canonical schema folders.
Primary schema reference path: /PrismataCore/canonical.
Support content: at end of schema.
Support rules: blocks.

3.3 Object Loader

Registry entries must be loaded from type-specific folders.

pane.d
menu.d
menu-item.d
colour-scheme.d
border-pattern.d
border-role.d
ui-framework.d

3.4 Manifest Loader

Support both root manifest and module manifests.
*.manifest.yaml
manifest.d/*.yaml

4. PSO Migration

4.1 PSO Builder

All CMF capsules must be converted into PSO objects.
Enforce schema validation.
Enforce rule validation.
Enforce UDI correctness.

4.2 PSO Runtime

PSO objects must be used by:

UI frameworks
Pane runtime
Menu runtime
Preview engine

5. Preview Engine Migration

The preview engine must:
Render multi‑coloured panes.
Apply chromaschemes.
Apply border patterns.
Render menus.
Render UI frameworks.
This is the final integration layer.

6. Capability + Module Migration

6.1 Capability Registry

Capabilities must be loaded from module manifests.

6.2 Module Manifest Loader

Modules must be loaded from manifest.d/.
Each module defines capabilities, interfaces, dependencies.

7. Tenant Override Migration

Tenants may override:
panes
menus
chromaschemes
borders
ui frameworks

Overrides must be loaded from tenants/overrides/.

8. CLI Migration

CLI commands must be updated to use CMF + PSO:

validate
build
preview
list
inspect

9. Testing Strategy

9.1 UI Testing (Highest Priority)

Multi‑coloured pane rendering.
UI framework composition.
Menu routing.

9.2 Loader Testing

CMF loader
schema loader
object loader
manifest loader

9.3 PSO Testing

PSO builder
PSO validator

9.4 Preview Testing

pane rendering
chroma application
border rendering

10. Examples Folder Migration

Examples must include:
example manifests
example panes
example menus
example colour-schemes
example colour-roles
example border-roles
example border patterns
example ui frameworks

Primary example object reference path: /PrismataSDK/examples/registry.

These examples serve as reference objects for testing and development.

11. Apps Migration (Vile, Vise, Universe)

Vile - VI-light editor for CMF capsules.
Vise - Structured editor aware of schemas and rules.
Universe - Workspace generator, ingestion engine, scaffolder, registry browser, and previewer.
These apps must be updated to use CMF + PSO.
All applications being migrated into PrismataSDK must have a valid manifest in the new app folder root.
All tooling modules, primitives and helpers must have valid manifest entries contained in a tooling manifest.

12. Breaking Changes Policy

Breaking changes within PrismataSDK are allowed and expected.
Old modules may stop working.
Old interfaces may be removed.
All modules must migrate to CMF + PSO.
This migration is foundational and transformative.

13. Completion Criteria

PrismataSDK migration is complete when:
UI frameworks load and render correctly.
Multi‑coloured panes work.
Menus route correctly.
All loaders use CMF.
All runtimes use PSO.
Preview engine works.

Vile, Vise, Universe run on the new SDK.

14. Next Steps

After this document, create the Copilot instruction file that references this migration plan and guides Copilot in assisting with SDK development.