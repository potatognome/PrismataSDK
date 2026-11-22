# PrismataSDK Developer Guide

## Purpose

PrismataSDK is the runtime, security, tooling, rendering, and composition layer of the Prismata ecosystem.

It consumes canonical definitions from PrismataCore and provides the implementation needed to load, validate, resolve,
execute, and present those definitions. PrismataSDK must not redefine concepts owned by PrismataCore.

The architectural intent comes from KADD:

- PrismataCore defines canonical knowledge, identity, schemas, laws, manifests, and validators.
- PrismataSDK implements runtime behavior, rendering, tooling, security, composition, and orchestration.
- PrismataCorp governs tenants, archives, policies, stewardship, and preservation.

See `PrismataCore/canonical/kadd/` for authoritative architectural intent. In particular:

- `1-definitions/` defines the vision, principles, and doctrines.
- `2-architecture/` defines systems, ownership, relationships, and decisions.
- `3-planning/` defines requirements, risks, and roadmap.
- `4-implementation/` defines interfaces and implementation guidance.
- `5-post-implementation/` defines lessons and retrospectives.
- `9-reference/` provides the glossary and references.

---

## Architectural Rules

### Core, SDK, and Corp boundaries

```text
PrismataCore
  canonical definitions and validation
        |
        v
PrismataSDK
  runtime implementation and tooling
        |
        v
PrismataCorp
  governance, tenants, archives, and preservation
```

PrismataSDK dependencies point inward toward PrismataCore. Canonical schemas and laws remain Core-owned:

- CMF is the persistent/capsule structural envelope.
- PSO is the mirrored runtime structural object.
- UDI is the identity mechanism.
- Schemas define structure.
- Laws define permitted behavior.
- Manifests describe artifacts and capabilities.
- Registries provide discovery infrastructure, not canonical truth.
- Validators verify conformance before operational use.

Do not duplicate Core types or definitions in SDK code. When the SDK needs a canonical rule or structure, load it from the
Core package or canonical data and translate it into runtime objects.

### Architectural principles that apply to SDK work

- Identity precedes interaction: expose UDIs wherever assets are governed or reused.
- Capability precedes composition: describe what an operation requires and produces before routing or combining it.
- Structure precedes behavior: stabilize contracts, loaders, and object models before presentation or automation.
- Metadata precedes implementation: use manifests and schemas to drive discoverable behavior.
- Knowledge precedes code: understand the problem and preserve the decision in documentation or tests.
- Reuse precedes duplication: share registries and loaders instead of creating parallel implementations.
- Accessibility precedes complexity: prefer clear, deterministic, and portable behavior.
- Preservation precedes replacement: adapt or migrate legacy behavior before discarding it.

### KADD interface principles

- Everything addressable is selectable and resolvable.
- Every addressable asset should be describable and previewable.
- Capabilities are addressable, but identity does not imply executability.
- Capability execution depends on manifest availability and authorization.
- Menus invoke capabilities.
- Renderers present results.
- UI frameworks define presentation topology.
- Capabilities do not define presentation or pane placement.
- Rendering and execution are separate concerns.
- Capability output is functional data, not presentation instructions.

---

## Repository Layout

```text
PrismataSDK/
  core/           canonical loading, CMF/PSO support, registries, manifests, schemas, and ops
  ui/             framework, pane, menu, border, chroma, preview, and runtime composition
  capabilities/   capability registration and resolution
  tenants/        tenant override entry points
  cli/            command-line validation and inspection entry points
  apps/           Vile, Vise, Universe, and future SDK applications
  examples/       executable reference implementations
  tests/          migration, loader, registry, capability, and UI verification
  docs/guides/    developer and operational documentation
```

### `core/`

Contains runtime support infrastructure:

- `cmf.py`: CMF envelope support.
- `manifests.py`: manifest loading and discovery.
- `schemas.py`: canonical schema loading.
- `registry.py`: object and asset registry primitives.
- `pso/`: CMF-to-PSO construction and runtime object support.
- `loader/`: narrow, testable loader implementations.
- `ops/`: source checks, version extraction, version setting, and migration helpers.
- `utils/`: shared SDK helpers.
- `border.py` and `chroma.py`: presentation primitives that may be resolved by UI subsystems.

Core support should remain deterministic and should fail before runtime work begins when a required definition,
schema, or manifest is invalid.

### `ui/`

Contains metadata-driven presentation and interaction support:

- `framework/` and `frameworks.py`: framework discovery and composition.
- `pane/` and `panes.py`: pane loading and location resolution.
- `menu/` and `menus.py`: menu loading and routing.
- `runtime/`: capability execution, pane injection, and application-loop support.
- `border/`, `chroma/`, and `preview/`: visual and preview systems.

Structural behavior is implemented before visual behavior. Border, colour, chroma, and ANSI rendering must not block
the framework, menu, pane, capability, or output-injection contracts.

### `capabilities/`

Contains capability registration and resolution. Capability execution must originate from:

```text
manifest declaration
  -> capability registry
  -> capability resolution
  -> invocation handler
  -> functional output
```

Capability implementations do not own menu placement or visual rendering.

### `tenants/`

Tenant behavior belongs behind explicit override and isolation boundaries. SDK code may load tenant overrides, but must
not change Core definitions or undermine tenant isolation. Tenant governance and archive ownership remain in PrismataCorp.

---

## Canonical Runtime Pipeline

The smallest complete SDK runtime path is:

```text
CMF/Manifest
  -> schema and definition validation
  -> capability resolution
  -> UI framework resolution
  -> menu resolution
  -> target pane resolution
  -> capability execution
  -> functional output
  -> pane rendering
```

Legacy migration follows the same direction:

```text
legacy module
  -> CMF wrapper
  -> CMF object
  -> PSO
  -> SDK runtime
```

The migration pipeline should remain ordered and narrow:

1. Load and validate the CMF envelope.
2. Load the governing schema.
3. Load the manifest.
4. Discover objects and registry entries.
5. Resolve capabilities through manifests and UDIs.
6. Resolve the UI framework, menu, pane, and output target.
7. Execute the capability and return functional output.
8. Render the output using a separate presentation layer.

### CMF and PSO

CMF is canonical input and carries identity, versioning, metadata, relations, notes, and content. PSO mirrors the
runtime model and represents validated, usable state.

The loader boundary is authoritative:

- Validate structure before constructing runtime objects.
- Preserve metadata instead of flattening it into ad hoc fields.
- Construct PSO objects only after Core validators accept the CMF input.
- Do not accept PSO objects that bypass their governing schema or registry.
- Keep CMF and PSO conversion explicit and testable.

### Manifests

Manifests describe module identity, kind, version, capabilities, interfaces, and metadata.

Use the repository convention:

- Root manifest: `manifest.yaml`
- Module manifests: `manifest.d/*.yaml`
- Relative and module-specific definitions: manifest-local data and canonical registry entries

Resolution must be manifest-driven. Missing required capabilities or definitions should fail fast and deterministically.

### Capabilities

Each capability should have a UDI and declare or resolve:

- Identity
- Purpose
- Inputs or target parameters
- Functional output
- Required manifests or dependencies
- Authorization or execution requirements, when applicable

A capability is not a renderer and does not own where or how its output appears.

### Registries

Registries are discovery infrastructure. They may index artifacts and capabilities, but they do not become authoritative
definitions. Core schemas, laws, examples, and validators remain the source of truth.

Resolution should be capable of answering:

- What artifacts or capabilities match this UDI?
- Which manifest declares this capability?
- What dependencies are required?
- Is execution available and authorized?
- What preview fallback applies when execution is unavailable?

---

## Structural UI Model

The UI subsystem is metadata-driven and separates topology, navigation, behavior, and presentation.

### Framework

A framework defines the pane composition and presentation topology. Framework resolution should:

1. Discover available frameworks.
2. Validate the framework definition.
3. Compose panes.
4. Route menus to targets.
5. Provide a runtime context for invocation and output injection.

### Pane

A pane is an addressable interface object. It has a structural role and may receive functional output.

Pane resolution must support:

- Fixed positioning
- Relative positioning
- Split or composed layouts
- Menu and capability output targets
- Adaptive presentation when display space changes

Pane implementation should not embed capability logic.

### Menu

Menus define invocation. Menu items select targets and may invoke capabilities.

Menu routing should remain explicit:

- Resolve menu and menu-item UDIs.
- Resolve the target pane or framework handler.
- Resolve and authorize the capability.
- Execute or preview.
- Inject only functional output into the pane.
- Return to the menu loop when applicable.

### Output and rendering

Execution produces functional output. Renderers convert that output and interface metadata into presentation.

Presentation may include:

- Pane layout
- Border patterns
- Colour roles
- Chromascheme data
- ANSI rendering
- Preview formatting

These visual systems are extensions of a stable structural runtime, not replacements for it.

---

## Hello_UDI Reference Project

Hello_UDI is the canonical SDK proof of concept. It validates the complete vertical slice:

```text
Manifest
  -> capability
  -> framework
  -> menu
  -> pane
  -> functional output
  -> rendered presentation
```

The milestone plan is defined in
`PrismataSDK/docs/plans/hello_udi_milestone_plan.yaml`. It is a phased implementation and verification plan; the guide
defines the architectural interpretation and working rules.

### Example menu

```text
1) Test LH Pane
2) Test RH Pane
0) Quit
```

### Expected capability identity

```text
prismata.example.capability.hello_udi
```

The capability should resolve through manifests and registries, execute through menu routing, and inject output into the
selected pane. It demonstrates discovery, resolution, execution, and presentation without coupling capability behavior
to pane placement or rendering.

### Runtime context

Menu invocation establishes an ordered runtime context:

```text
Menu Item UDI
  -> Menu UDI
  -> Pane UDI
  -> Framework UDI
  -> Capability UDI
```

The context structure should contain:

- `initiating_object`: the UDI that started the operation
- `related_objects`: an ordered list of UDIs related to the operation
- `execution_path`: an ordered list of UDIs traversed during resolution
- `metadata`: context data needed for execution

The context graph is bounded. It should resolve only valid and resolvable UDIs and should default to a maximum of 10
related objects.

Hello_UDI is a capability, not a context builder or renderer. Given a runtime context, it emits one greeting for each
related object, once per object:

```text
Hello to menu_item prismata.example.menu_item.test_lh
from prismata.example.capability.hello_udi

Hello to menu prismata.example.menu.test_menu
from prismata.example.capability.hello_udi

Hello to pane prismata.example.pane.lh_test
from prismata.example.capability.hello_udi

Hello to framework prismata.example.ui_framework.two_pane
from prismata.example.capability.hello_udi
```

The capability output is functional text. A pane output injector routes it to the target pane, and a pane renderer
applies borders, padding, and visual roles.

### Reference milestone sequence

The Hello_UDI implementation is organized as a sequential series of milestones:

| Milestone | Name | Required result |
| --- | --- | --- |
| M0 | Foundation Validation | Core CMF, PSO, UDI, schema, and validator infrastructure is usable |
| M1 | Documentation Scaffold | SDK concepts and the full runtime chain are documented |
| M2 | Manifest System MVP | A Hello_UDI manifest loads, validates, and is discoverable |
| M3 | Capability Resolution MVP | A capability UDI resolves to an executable capability PSO |
| M4 | Two-Pane Framework MVP | A discoverable two-pane framework converts to a valid runtime PSO |
| M5 | Pane Registry MVP | Left and right pane UDIs resolve to injectable pane PSOs |
| M6 | Menu Runtime MVP | Menus and menu items resolve capabilities and target panes |
| M7 | UDI Context Graph | Related-object and execution context is ordered and bounded |
| M8 | Hello_UDI Capability | The capability executes against context and emits greetings |
| M9 | Pane Output Injection | Functional output reaches the selected pane without changing other panes |
| M10 | Runtime Loop | The application remains interactive until Quit is selected |
| M11 | Structural Validation | The complete structural runtime chain passes together |

M0 is foundational and M11 is the final structural gate. Styling, tenant overrides, and advanced application features
must not become acceptance dependencies while M0-M10 are incomplete.

The interactive loop has the following deterministic behavior:

```text
Display framework and menu
  -> await a menu selection
  -> resolve the menu item
  -> Quit exits gracefully
  -> otherwise execute the capability
  -> inject output into the target pane
  -> re-render the framework
  -> repeat
```

Selecting left pane content replaces or updates the left pane without changing the right pane; selecting right pane
content has the inverse behavior. Quit is a menu action and is not itself a capability invocation.

### Hello_UDI definition of done

Hello_UDI is complete when:

- A manifest resolves to a capability, framework, menu, and target pane.
- The capability executes through UDI-based routing.
- Runtime context is complete, ordered, valid, and bounded.
- Selecting menu option 1 injects output into the left pane.
- Selecting menu option 2 injects output into the right pane.
- The menu and framework remain responsive across repeated selections.
- Selecting menu option 0 exits gracefully.
- All generated artifacts are CMF-enveloped and UDI-compliant.
- Loaded artifacts are discoverable and convertible to PSO.
- Core validators accept the full chain.
- The Core models do not require SDK-only modifications.
- The SDK test suite passes without regressions.

The structural acceptance scope explicitly excludes border pattern details, colour role styling, chromaschemes, ANSI
styling, tenant overrides, Vile, Vise, Universe, and advanced preview features.

The SDK migration is structurally successful when this flow executes using:

- CMF objects
- PSOs
- canonical schemas
- manifests
- registries
- capabilities
- loaders
- validators
- framework, menu, and pane resolution
- UDI-based output injection

---

## Migration and Implementation Workflow

### Priority order

1. Preserve or update documentation and architectural intent.
2. Complete manifests and module discovery.
3. Implement capability discovery, resolution, and execution.
4. Stabilize framework, pane, menu, and output-injection behavior.
5. Add border, colour, chroma, ANSI, and preview presentation.
6. Extend tenant overrides, preview, CLI tooling, and SDK applications.

Tenant overrides, Vile, Vise, Universe, advanced preview features, and other consumer-facing work remain later priorities
until the structural runtime path passes.

### Legacy migration

Legacy modules may be adapted, but they should not be copied verbatim.

For each legacy component:

1. Identify its responsibility and dependencies.
2. Identify canonical Core definitions it relies on.
3. Wrap the legacy content into CMF where appropriate.
4. Convert it through a narrow loader into a PSO.
5. Replace ad hoc lookups with manifests, UDIs, and registries.
6. Separate capability behavior from UI presentation.
7. Preserve lessons and migration decisions for later review.

Legacy implementation content should remain inside an explicit `content:` section when a CMF wrapper is used, with
metadata corrected or populated rather than inferred through runtime code.

### Validation and testing

Tests should prioritize the structural runtime path before visual polish:

- Manifest discovery
- Capability resolution
- Schema and CMF loading
- Registry consumption
- Framework loading
- Menu loading
- Pane resolution
- Output injection
- Negative and invalid loader paths
- Tenant override isolation
- Legacy migration contracts

Use the smallest deterministic test that exercises the contract. Testing is inquiry: it should seek falsification,
not only demonstrate success.

Run targeted tests from `PrismataSDK/`:

```powershell
python -m pytest tests/test_migration_contract.py
python -m pytest tests/test_registry_loader_pipeline.py
python -m pytest tests/test_capability_resolution.py
python -m pytest tests/test_ui_gate_acceptance.py
python -m pytest
```

Add focused tests for behavior introduced by a change. Update examples when they no longer demonstrate the supported
runtime path.

---

## Versioning and Operations

The SDK contains operational helpers under `core/ops/`:

- `check_source_paths.py`: source-path verification.
- `extract_versions.py`: version extraction.
- `set_versions_by_udi.py`: version updates associated with UDIs.

Use manifest and UDI metadata consistently. Do not add versioning, ownership, or source provenance through ad hoc
hardcoding when an existing metadata or registry mechanism is available.

Before publishing or packaging an SDK change:

1. Verify canonical source paths.
2. Validate manifests and schemas.
3. Run targeted loader and UI tests.
4. Run the complete SDK test suite.
5. Check examples and CLI entry points.
6. Record unresolved architectural questions and migration lessons.

---

## Definition of Success

PrismataSDK development is successful when it can:

1. Discover canonical and manifest-provided assets.
2. Construct validated CMF and PSO runtime objects.
3. Resolve capabilities by manifest and UDI.
4. Compose frameworks, menus, and panes from metadata.
5. Execute capabilities without controlling presentation.
6. Inject functional output into the correct pane.
7. Render output through separate, adaptive presentation services.
8. Preserve tenant isolation and canonical ownership boundaries.
9. Fail clearly on invalid structure or missing capabilities.
10. Produce reusable knowledge about migrations, failures, and lessons.

Prefer the smallest deterministic change that preserves the Core-to-SDK dependency, the CMF-to-PSO pipeline,
manifest-driven discovery, structural UI stability, and testable behavior.
