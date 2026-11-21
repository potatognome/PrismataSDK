# PrismataSDK Developer Guide

## Purpose

PrismataSDK is the tooling, runtime, composition, and application layer of the Prismata ecosystem.

PrismataSDK consumes the authoritative definitions provided by PrismataCore and provides:

- CMF loading
- PSO construction
- Manifest loading
- Capability resolution
- Registry loading
- UI framework runtime
- Pane runtime
- Menu runtime
- Preview runtime
- CLI tooling
- SDK applications

PrismataSDK must not redefine concepts owned by PrismataCore.

---

# Architecture Overview

## Ecosystem Layers

```text
PrismataCore
    ↓
PrismataSDK
    ↓
PrismataCorp
```

### PrismataCore

Owns:

- CMF
- PSO
- UDI
- Schemas
- Validators
- Example objects

### PrismataSDK

Owns:

- Runtime loading
- Capability execution
- Menu routing
- Pane routing
- Framework composition
- Output injection
- Preview systems
- SDK applications

### PrismataCorp

Owns:

- Tenant implementations
- Business-specific capabilities
- Workspace content
- Operational environments

---

# Core Dependency

PrismataCore is the source of truth.

PrismataSDK must consume and implement against:

```text
CMF
PSO
UDI
Schema Definitions
Validators
```

PrismataSDK must not redefine:

```text
CMF envelopes
PSO structures
UDI rules
Core schemas
Validator behavior
```

When uncertain:

```text
Core owns the definition.
SDK consumes the definition.
```

---

# Current Migration Goals

The SDK migration is focused on creating the smallest complete runtime path that demonstrates:

```text
Manifest
→ Capability Resolution
→ Framework Resolution
→ Menu Resolution
→ Pane Resolution
→ Output Injection
```

Everything else is secondary until this path works correctly.

---

# Migration Priority Order

## Priority 1

Documentation

Maintain:

```text
docs/guides/dev_guide.md
```

as the authoritative SDK onboarding document.

---

## Priority 2

Manifests

Implement:

```text
manifest.yaml
manifest.d/
```

and module discovery.

---

## Priority 3

Capability Resolution

Implement:

```text
Capability Registry
Capability Discovery
Capability Resolution
Capability Execution
```

using UDI identifiers.

---

## Priority 4

Structural UI

Implement:

```text
UI Framework Loader
Pane Loader
Menu Loader
Pane Location Resolution
Menu Routing
Pane Output Injection
```

before implementing any styling systems.

---

## Priority 5

Visual Systems

After structural UI is stable:

```text
Border Patterns
Colour Roles
Chromaschemes
ANSI Rendering
Preview Styling
```

---

## Deferred

The following are intentionally deferred until structural UI is complete:

```text
Tenant Overrides
Vile
Vise
Universe
Advanced Preview Features
```

---

# Repository Layout

## Core

```text
core/
```

Contains runtime support infrastructure.

### Loader

```text
core/loader/
```

Responsible for:

- CMF loading
- Manifest loading
- Object loading
- Capability loading

### Ops

```text
core/ops/
```

Contains operational tooling.

Examples:

```text
source_path_check.py
version_extract.py
version_set.py
cmf_wrapper.py
```

### PSO

```text
core/pso/
```

Responsible for:

```text
CMF → PSO
```

construction and validation.

### Utils

```text
core/utils/
```

Shared SDK helper libraries.

---

## UI

```text
ui/
```

Contains runtime presentation logic.

### Framework

```text
ui/framework/
```

Framework discovery and loading.

### Pane

```text
ui/pane/
```

Pane loading and pane location resolution.

### Menu

```text
ui/menu/
```

Menu loading and routing.

### Runtime

```text
ui/runtime/
```

Runtime execution layer.

Responsible for:

```text
Capability Execution
Pane Injection
Application Loop
```

### Future

Deferred UI systems:

```text
ui/border/
ui/chroma/
ui/preview/
```

---

## Capabilities

```text
capabilities/
```

Responsible for:

```text
Capability Registration
Capability Routing
Capability Resolution
```

All capability execution should originate from UDI resolution.

---

## Examples

```text
examples/
```

Contains working reference implementations.

Examples should always use:

```text
CMF Objects
PSOs
Manifests
Capability Resolution
```

Example scripts must never construct ad-hoc runtime objects bypassing the SDK pipeline.

---

## Tests

```text
tests/
```

Contains migration verification.

Tests should focus on:

```text
Manifest Discovery
Capability Resolution
Framework Loading
Menu Loading
Pane Resolution
Output Injection
```

before visual systems.

---

# Hello_UDI Reference Project

## Purpose

Hello_UDI is the canonical SDK proof-of-concept.

Its purpose is to validate the entire runtime path.

---

## Architecture

```text
Manifest
→ Capability
→ Framework
→ Menu
→ Pane
→ Output
```

---

## Example Layout

```text
+----------------------+----------------------+
| Menu / Left Pane     | Right Pane           |
+----------------------+----------------------+
```

---

## Menu

```text
1) Test LH Pane
2) Test RH Pane
0) Quit
```

---

## Capability

```text
prismata.example.capability.hello_udi
```

---

## Output

Example:

```text
Hello to menu_item prismata.example.menu_item.test_lh
from prismata.example.capability.hello_udi

Hello to menu prismata.example.menu.test_menu
from prismata.example.capability.hello_udi

Hello to pane prismata.example.pane.lh_test
from prismata.example.capability.hello_udi
```

---

## Runtime Goal

The capability must:

1. Resolve through manifests.
2. Resolve through the capability registry.
3. Execute through menu routing.
4. Inject output into the selected pane.
5. Return to the menu loop.

When this works, PrismataSDK has demonstrated a complete vertical slice of the runtime architecture.

---

# Legacy Migration Strategy

Legacy Prismata modules may be adapted but not reused verbatim.

Preferred workflow:

```text
Legacy Module
→ CMF Wrapper
→ CMF Object
→ PSO
→ SDK Runtime
```

---

## CMF Wrapper

Location:

```text
core/ops/cmf_wrapper.py
```

Purpose:

```text
Legacy
→ CMF
```

conversion.

Known metadata should be automatically populated.

Legacy implementation content should remain inside:

```yaml
content:
```

with minimal modification.

---

# Definition of Success

The SDK migration is considered structurally successful when:

```text
Manifest
→ Capability Resolution
→ UI Framework
→ Menu Selection
→ Target Pane Resolution
→ UDI-Based Output Injection
```

executes successfully using:

- CMF objects
- PSOs
- manifests
- capabilities
- loaders
- registries
- validators

with Hello_UDI acting as the reference implementation.
