# Copilot Instructions - Prismata

## LAST UPDATED: 2024-07-21

## Purpose
Prismata is a development ecosystem for cybernetic applications and a living lab for best practices in AI-augmented development. This file defines general policies and rules for the repository, while modular copilot-instructions files in the `copilot-instructions.d/` directory provide targeted guidance for specific domains, file types, and agents.

This file is minimal by design. All general rules, agent edit policies, and centralized log/config options are defined in the modular copilot-instructions files.

Refer to:
- [Modular copilot-instructions](./copilot-instructions.d/*.md) for extensions to the general rules in this file.

## Repository Structure Awareness

Copilot must understand the following key Prismata folders and treat them according to their roles:

/Prismata/.workspace
- Contains configs, logs, input and outputs, samples, and test data, logs and configuration.
- Not visible on GitHub.  Include in .gitignore.
- Copilot should treat this as support infrastructure, not a source of architectural truth.
- Do not generate new global systems here.

/Prismata/Meta/Historical
- Contains architectural history, deprecated schemas, and prior iterations.
- Copilot must not modify Historical files unless explicitly instructed.  Use only as reference when clarifying intent or evolution.

/Prismata/Meta/canonical
- Contains canonical schemas, manifests, UDI definitions, and metadata rules.
- This is the single source of truth for schema and manifest structure.
- Copilot must not create alternate schema formats or duplicate canonical files elsewhere.

/Prismata/Projects/Tooling
- Contains shared tooling such as ASTalyzer, Vile, and menu primitives.
- Copilot should keep tooling modular, minimal, and deterministic.
- ASTalyzer is analysis‑only; do not add editing logic.

/Prismata/Projects/Applications
- Contains application‑level modules (e.g., Universe).
- Universe must rely on canonical schemas and ASTalyzer output.
- Avoid cross‑project coupling or global orchestration.

/Prismata/Projects/Services
- Contains service‑level modules and background helpers.
- Keep services small, focused, and free of unnecessary abstraction.


## Python / TypeScript implementation

Prismata is a Python-first system. TypeScript is a typed boundary layer for UI and tooling.
Copilot must follow the rules below when generating or modifying code.

1. Python for core logic
Copilot must implement the following exclusively in Python:

- schema processing (nodes, entries, compositions, metadata)
- dynamic composition resolution
- multi-parent sort-order logic
- metadata merging and inheritance
- agent logic and cognition models
- CLI systems (PCMS‑2026, UDI, menus, commands)
- file system operations
- runtime evaluation, dynamic behavior, state machines
- robotics / ROS2 integration
- ASTalyzer core logic
- network operations
- any algorithmic, dynamic, or runtime-dependent code

Rule: If a module performs logic, computation, resolution, or mutation, implement it in Python (not TypeScript).

2. TypeScript for boundary layers
Use TypeScript only for modules that act as an interface between Python and UI/tooling. Typical allowed domains:

- type definitions mirroring Python schemas
- boundary validation of Python-produced data
- UI-facing structures (React components, web components, schema editors, dashboards)
- developer tooling (inspectors, visualizers, metadata browsers)
- static shape guarantees for data entering the UI

Rule: If a module's job is to describe shape, validate structure, or provide typed props to UI, prefer TypeScript.

3. Keep TypeScript free of business logic
Do not implement business or runtime logic in TypeScript. Avoid placing the following responsibilities in TS:

- sorting, composition resolution, metadata evaluation
- dynamic field behavior or agent behavior
- CLI logic, file system logic, runtime decisions

Rule: TypeScript may describe and validate data, but must not interpret, transform, or own core logic.

4. Single source of truth
Python is the authoritative source for:

- schema definitions and metadata models
- composition rules and custom field definitions
- folder path configuration

TypeScript may mirror these structures only as static types for UI/tooling.

5. Minimal TypeScript footprint
Prefer Python unless the code is explicitly UI-facing, acts as a boundary layer, requires static typing for developer experience, or is part of schema-editor tooling.

Decision rule (mandatory)
When choosing a language, apply this decision tree:

- Does the module perform logic or runtime behavior? → Python
- Does it describe data shape for UI/tooling? → TypeScript
- Does it validate Python output before the UI? → TypeScript
- Does it interact with runtime systems? → Python
- Is it part of developer-facing visualization or editor tooling? → TypeScript