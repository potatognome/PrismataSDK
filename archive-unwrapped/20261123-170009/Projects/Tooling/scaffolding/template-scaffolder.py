#!/usr/bin/env python3
"""
Prismata Schema Scaffolding Tool
Templated version that inserts real schema content.

Version: 0.4.0
"""

import os
from pathlib import Path

PRISMATA_ROOT = Path(__file__).resolve().parents[3]
  
# Canonical schema directories
SCHEMA_GROUPS = {
    "object": PRISMATA_ROOT / "Meta" / "canonical" / "object.schemas",
    "composition": PRISMATA_ROOT / "Meta" / "canonical" / "composition.schemas",
    "shared": PRISMATA_ROOT / "Meta" / "canonical" / "shared.schemas",
    "registry": PRISMATA_ROOT / "Meta" / "registry",
}

# ---------------------------------------------------------------------------
# TEMPLATES (real schema content)
# ---------------------------------------------------------------------------

TEMPLATES = {

    "pane.schema.yaml": """version: 0.4.0
kind: pane
schema_type: object

metadata:
  udi: prismata.meta.schema.pane
  name: pane.schema
  description: Canonical pane schema defining rectangular UI regions.

spec:
  target_kind: pane
  naming:
    file_suffix: .schema.yaml
  versioning:
    semver: true
  imports:
    - prismata.meta.schema.shared-styling
    - prismata.meta.schema.shared-control-structures

fields:
  - name: id
    path: id
    type: string
    required: true
  - name: role
    path: role
    type: string
    required: true
  - name: x
    path: x
    type: integer
    required: true
  - name: y
    path: y
    type: integer
    required: true
  - name: width
    path: width
    type: integer
    required: true
  - name: height
    path: height
    type: integer
    required: true

object:
  id: ""
  role: ""
  x: 0
  y: 0
  width: 100
  height: 100
""",

    "border-pattern.schema.yaml": """version: 0.4.0
kind: border-pattern
schema_type: object

metadata:
  udi: prismata.meta.schema.border-pattern
  name: border-pattern.schema
  description: Canonical border pattern schema.

spec:
  target_kind: border-pattern
  naming:
    file_suffix: .schema.yaml
  versioning:
    semver: true
  imports:
    - prismata.meta.schema.shared-styling

fields:
  - name: glyphs
    path: glyphs
    type: object
    required: true

object:
  glyphs:
    TL: "+"
    TR: "+"
    BL: "+"
    BR: "+"
    H: "-"
    V: "|"
""",

    "colour-scheme.schema.yaml": """version: 0.4.0
kind: colour-scheme
schema_type: object

metadata:
  udi: prismata.meta.schema.colour-scheme
  name: colour-scheme.schema
  description: Canonical colour scheme schema.

spec:
  target_kind: colour-scheme
  naming:
    file_suffix: .schema.yaml
  versioning:
    semver: true

fields:
  - name: colourSet
    path: colourSet
    type: array
    required: true

object:
  colourSet: []
""",

    "shared-styling.schema.yaml": """version: 0.4.0
kind: schema
schema_type: shared

metadata:
  udi: prismata.meta.schema.shared-styling
  name: shared-styling.schema
  description: Shared styling fields.

spec:
  target_kind: styling
  naming:
    file_suffix: .schema.yaml
  versioning:
    semver: true

fields:
  - name: colour_scheme
    path: colour_scheme
    type: string
    required: false
  - name: border_pattern
    path: border_pattern
    type: string
    required: false

object:
  colour_scheme: ""
  border_pattern: ""
""",

    "shared-control-structures.schema.yaml": """version: 0.4.0
kind: schema
schema_type: shared

metadata:
  udi: prismata.meta.schema.shared-control-structures
  name: shared-control-structures.schema
  description: Shared visibility and enablement control structures.

spec:
  target_kind: control
  naming:
    file_suffix: .schema.yaml
  versioning:
    semver: true

fields:
  - name: visibilityMode
    path: visibilityMode
    type: string
    required: false
  - name: enableMode
    path: enableMode
    type: string
    required: false

object:
  visibilityMode: static
  enableMode: enabled
""",

    "ui-framework.schema.yaml": """version: 0.4.0
kind: ui-framework
schema_type: object

metadata:
  udi: prismata.meta.schema.ui-framework
  name: ui-framework.schema
  description: Canonical UI framework schema.

spec:
  target_kind: ui-framework
  naming:
    file_suffix: .schema.yaml
  versioning:
    semver: true

fields:
  - name: panes
    path: panes
    type: array
    required: true

object:
  panes: []
""",

    "menu.schema.yaml": """version: 0.4.0
kind: menu
schema_type: composition

metadata:
  udi: prismata.meta.schema.menu
  name: menu.schema
  description: Canonical menu composition schema.

spec:
  target_kind: menu
  naming:
    file_suffix: .schema.yaml
  versioning:
    semver: true

fields:
  - name: items
    path: items
    type: array
    required: true

object:
  items: []
"""
}

# ---------------------------------------------------------------------------
# SCAFFOLDING LOGIC
# ---------------------------------------------------------------------------

def ensure_directories():
    for group, path in SCHEMA_GROUPS.items():
        os.makedirs(path, exist_ok=True)
        print(f"[ok] ensured directory: {path}")

def write_schema(group: str, filename: str):
    if group not in SCHEMA_GROUPS:
        raise ValueError(f"Unknown schema group: {group}")

    target_dir = SCHEMA_GROUPS[group]
    file_path = target_dir / filename

    if file_path.exists():
        print(f"[skip] {file_path} already exists")
        return

    content = TEMPLATES.get(filename)
    if not content:
        print(f"[warn] No template found for {filename}, skipping.")
        return

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[ok] created schema: {file_path}")

def scaffold():
    print("=== Prismata Schema Scaffolding Tool (v0.4.0) ===")
    ensure_directories()

    # Object schemas
    write_schema("object", "pane.schema.yaml")
    write_schema("object", "border-pattern.schema.yaml")
    write_schema("object", "colour-scheme.schema.yaml")
    write_schema("object", "ui-framework.schema.yaml")

    # Shared schemas
    write_schema("shared", "shared-styling.schema.yaml")
    write_schema("shared", "shared-control-structures.schema.yaml")

    # Composition schemas
    write_schema("composition", "menu.schema.yaml")

    print("=== scaffolding complete ===")

if __name__ == "__main__":
    scaffold()
