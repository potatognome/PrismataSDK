"""
PrismataLabs â€” preview_object capability

This module loads a selected object (colour-scheme, border-pattern, pane,
menu, menu-item, ui-framework) and renders a preview using the canonical
Python renderers.

It is invoked by the capability:
    prismata.prismatalabs.capability.preview-object
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict, List

# Shared helpers
from Projects.Tooling.primitives.python.path_helper import (
    find_prismata_root,
    discover_preview_resources,
)

# Canonical renderers
from Projects.Tooling.primitives.python.pane_renderer import load_and_render_pane
from Projects.Tooling.primitives.python.menu_renderer import load_and_render_menu

# Registry loaders (colour schemes, border patterns, ui frameworks)
from Projects.Tooling.primitives.python.border_patterns import load_border_pattern_registry
from Projects.Applications.PrismataLabs.python.preview_common import (
    load_colour_scheme_registry,
    load_colour_role_registry,
    load_ui_framework_registry,
)
from Projects.Applications.PrismataLabs.python.schema_validator import classify_object
from Projects.Applications.PrismataLabs.python.schema_validator import (
    validate_collection,
    validate_colour_scheme,
    validate_border_pattern,
    validate_pane,
    validate_menu,
    validate_menu_item,
    validate_ui_framework,
)
from Projects.Tooling.primitives.python.checklist import add_entries as checklist_add_entries


# ---------------------------------------------------------------------------
# Utility: Load YAML object
# ---------------------------------------------------------------------------

def load_yaml_object(path: Path) -> Dict[str, Any]:
    """Load a YAML file into a Python dict."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Preview Dispatcher
# ---------------------------------------------------------------------------

def preview_object(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main preview dispatcher.

    payload contains:
        {
            "selected": {
                "colour_scheme": "<path or None>",
                "border_pattern": "<path or None>",
                "object": "<path or None>"
            }
        }

    Returns:
        {
            "lines": [ "... rendered preview ..." ],
            "objectType": "pane | menu | ...",
            "path": "<object path>"
        }
    """

    selected = payload.get("selected", {})
    object_path = selected.get("object")

    if not object_path:
        return {
            "lines": ["No object selected for preview."],
            "objectType": "none",
            "path": None,
        }

    prismata_root = find_prismata_root()
    obj_path = Path(object_path)

    if not obj_path.exists():
        return {
            "lines": [f"Object path does not exist: {object_path}"],
            "objectType": "invalid",
            "path": object_path,
        }

    # Load object
    obj = load_yaml_object(obj_path)
    obj_type = classify_object(obj)

    # Load registries
    colour_roles = load_colour_role_registry(prismata_root / "Meta" / "registry" / "colour-role.d")
    colour_schemes = load_colour_scheme_registry(prismata_root / "Meta" / "registry" / "colour-scheme.d")
    border_registry = load_border_pattern_registry(prismata_root / "Meta" / "registry" / "border-patterns")
    ui_frameworks = load_ui_framework_registry(prismata_root / "Meta" / "registry" / "ui-framework.d")

    registries = {
        "colour_roles": colour_roles,
        "colour_schemes": colour_schemes,
        "ui_frameworks": ui_frameworks,
        "border_patterns": border_registry,
    }

    # Active UI framework lookup is UDI-first.
    active_framework = obj.get("ui_framework")
    ui_framework = ui_frameworks.get(active_framework, {}) if isinstance(active_framework, str) else {}

    # Runtime context for conditional visibility
    context = {
        "user_is_admin": True,
        "selected": selected,
    }

    # -----------------------------------------------------------------------
    # Run validation to capture schema issues prior to rendering
    # -----------------------------------------------------------------------
    validation_valid = True
    validation_errors: List[str] = []
    try:
        if obj_type == "pane":
            validation_valid, validation_errors = validate_pane(obj, registries=registries)
        elif obj_type == "menu":
            # load capability index for menu item validation
            capability_index = _load_capability_udi_index(prismata_root) if "_load_capability_udi_index" in globals() else None
            validation_valid, validation_errors = validate_menu(obj, capability_index=capability_index, registries=registries)
        elif obj_type == "menu-item":
            capability_index = _load_capability_udi_index(prismata_root) if "_load_capability_udi_index" in globals() else None
            validation_valid, validation_errors = validate_menu_item(obj, capability_index=capability_index, registries=registries)
        elif obj_type == "colour-scheme":
            validation_valid, validation_errors = validate_colour_scheme(obj, registries=registries)
        elif obj_type == "border-pattern":
            validation_valid, validation_errors = validate_border_pattern(obj, registries=registries)
        elif obj_type == "ui-framework":
            capability_index = _load_capability_udi_index(prismata_root) if "_load_capability_udi_index" in globals() else None
            validation_valid, validation_errors = validate_ui_framework(obj, capability_index=capability_index, registries=registries)
        elif obj_type.endswith("-collection"):
            base = obj_type.replace("-collection", "")
            validation_valid, validation_errors = validate_collection(obj, base)
    except Exception as e:
        validation_valid = False
        validation_errors.append(f"Validation exception: {e}")

    # -----------------------------------------------------------------------
    # Dispatch based on object type (rendering)
    # -----------------------------------------------------------------------

    if obj_type == "pane":
        try:
            lines = load_and_render_pane(
                pane=obj,
                meta_root=prismata_root / "Meta",
                ui_framework=ui_framework,
                context=context,
            )
        except Exception as e:
            return {
                "lines": [f"Renderer exception: {e}"],
                "objectType": "pane",
                "path": object_path,
                "valid": validation_valid,
                "errors": validation_errors + [f"Render exception: {e}"],
            }
        # If there were validation errors, prepend a concise warning block
        if validation_errors:
            warn_lines = ["VALIDATION WARNINGS:"] + [f"- {e}" for e in validation_errors] + [""]
            lines = warn_lines + lines
            # Log checklist entries for fixes
            try:
                checklist_entries = [f"{object_path}: {e}" for e in validation_errors]
                checklist_add_entries('validation-fixes', checklist_entries)
            except Exception:
                pass
        return {
            "lines": lines,
            "objectType": "pane",
            "path": object_path,
            "valid": validation_valid,
            "errors": validation_errors,
        }

    if obj_type == "menu":
        try:
            lines = load_and_render_menu(
                menu=obj,
                meta_root=prismata_root / "Meta",
                ui_framework=ui_framework,
                context=context,
                preview_mode=True,
            )
        except Exception as e:
            return {
                "lines": [f"Renderer exception: {e}"],
                "objectType": "menu",
                "path": object_path,
                "valid": validation_valid,
                "errors": validation_errors + [f"Render exception: {e}"],
            }
        if validation_errors:
            warn_lines = ["VALIDATION WARNINGS:"] + [f"- {e}" for e in validation_errors] + [""]
            lines = warn_lines + lines
            try:
                checklist_entries = [f"{object_path}: {e}" for e in validation_errors]
                checklist_add_entries('validation-fixes', checklist_entries)
            except Exception:
                pass
        return {
            "lines": lines,
            "objectType": "menu",
            "path": object_path,
            "valid": validation_valid,
            "errors": validation_errors,
        }

    if obj_type == "menu-item":
        # Wrap menu-item in a temporary menu for preview
        temp_menu = {
            "id": "preview-wrapper-menu",
            "udi": "prismata.prismatalabs.menu.preview-wrapper",
            "kind": "menu",
            "title": "Preview Menu",
            "items": [obj],
            "border_pattern": selected.get("border_pattern", "default"),
            "colour_role": "prismata.meta.colour-role.menu-surface",
            "width": 40,
            "height": 5,
        }

        try:
            lines = load_and_render_menu(
                menu=temp_menu,
                meta_root=prismata_root / "Meta",
                ui_framework=ui_framework,
                context=context,
                preview_mode=True,
            )
        except Exception as e:
            return {
                "lines": [f"Renderer exception: {e}"],
                "objectType": "menu-item",
                "path": object_path,
                "valid": validation_valid,
                "errors": validation_errors + [f"Render exception: {e}"],
            }
        if validation_errors:
            warn_lines = ["VALIDATION WARNINGS:"] + [f"- {e}" for e in validation_errors] + [""]
            lines = warn_lines + lines
            try:
                checklist_entries = [f"{object_path}: {e}" for e in validation_errors]
                checklist_add_entries('validation-fixes', checklist_entries)
            except Exception:
                pass
        return {
            "lines": lines,
            "objectType": "menu-item",
            "path": object_path,
            "valid": validation_valid,
            "errors": validation_errors,
        }

    if obj_type == "colour-scheme":
        roles = obj.get("roles", {})
        lines = ["Colour Scheme Preview:", ""] + [
            f"  - {role}: fg={layers.get('fg')} bg={layers.get('bg')}"
            for role, layers in roles.items()
            if isinstance(layers, dict)
        ]
        if validation_errors:
            warn_lines = ["VALIDATION WARNINGS:"] + [f"- {e}" for e in validation_errors] + [""]
            lines = warn_lines + lines
            try:
                checklist_entries = [f"{object_path}: {e}" for e in validation_errors]
                checklist_add_entries('validation-fixes', checklist_entries)
            except Exception:
                pass
        return {
            "lines": lines,
            "objectType": "colour-scheme",
            "path": object_path,
            "valid": validation_valid,
            "errors": validation_errors,
        }

    if obj_type == "colour-scheme-collection":
        entries = obj.get("entries", [])
        lines = ["Colour Scheme Collection:", ""] + [
            f"  - {entry.get('udi')}" for entry in entries if isinstance(entry, dict)
        ]
        if validation_errors:
            warn_lines = ["VALIDATION WARNINGS:"] + [f"- {e}" for e in validation_errors] + [""]
            lines = warn_lines + lines
            try:
                checklist_entries = [f"{object_path}: {e}" for e in validation_errors]
                checklist_add_entries('validation-fixes', checklist_entries)
            except Exception:
                pass
        return {
            "lines": lines,
            "objectType": "colour-scheme-collection",
            "path": object_path,
            "valid": validation_valid,
            "errors": validation_errors,
        }

    if obj_type == "border-pattern":
        chars = obj.get("glyphs", {})
        lines = [
            "Border Pattern Preview:",
            "",
            f"TL: {chars.get('corner_top_left')}",
            f"TR: {chars.get('corner_top_right')}",
            f"BL: {chars.get('corner_bottom_left')}",
            f"BR: {chars.get('corner_bottom_right')}",
            f"H:  {chars.get('top')}",
            f"V:  {chars.get('left')}",
        ]
        if validation_errors:
            warn_lines = ["VALIDATION WARNINGS:"] + [f"- {e}" for e in validation_errors] + [""]
            lines = warn_lines + lines
            try:
                checklist_entries = [f"{object_path}: {e}" for e in validation_errors]
                checklist_add_entries('validation-fixes', checklist_entries)
            except Exception:
                pass
        return {
            "lines": lines,
            "objectType": "border-pattern",
            "path": object_path,
            "valid": validation_valid,
            "errors": validation_errors,
        }

    if obj_type == "border-pattern-collection":
        entries = obj.get("entries", [])
        lines = ["Border Pattern Collection:", ""] + [
            f"  - {entry.get('udi')}" for entry in entries if isinstance(entry, dict)
        ]
        if validation_errors:
            warn_lines = ["VALIDATION WARNINGS:"] + [f"- {e}" for e in validation_errors] + [""]
            lines = warn_lines + lines
            try:
                checklist_entries = [f"{object_path}: {e}" for e in validation_errors]
                checklist_add_entries('validation-fixes', checklist_entries)
            except Exception:
                pass
        return {
            "lines": lines,
            "objectType": "border-pattern-collection",
            "path": object_path,
            "valid": validation_valid,
            "errors": validation_errors,
        }

    if obj_type == "ui-framework":
        lines = [
            "UI Framework Preview:",
            "",
            f"ID: {obj.get('id')}",
            f"UDI: {obj.get('udi')}",
            f"Panes: {len(obj.get('panes', []))}",
            f"Menus: {len(obj.get('menus', []))}",
        ]
        if validation_errors:
            warn_lines = ["VALIDATION WARNINGS:"] + [f"- {e}" for e in validation_errors] + [""]
            lines = warn_lines + lines
            try:
                checklist_entries = [f"{object_path}: {e}" for e in validation_errors]
                checklist_add_entries('validation-fixes', checklist_entries)
            except Exception:
                pass
        return {
            "lines": lines,
            "objectType": "ui-framework",
            "path": object_path,
            "valid": validation_valid,
            "errors": validation_errors,
        }

    # Unknown object type
    return {
        "lines": ["Unknown object type; cannot preview."],
        "objectType": "unknown",
        "path": object_path,
        "valid": False,
        "errors": ["Unknown object type; cannot preview."],
    }

if __name__ == "__main__":
    root = find_prismata_root()
    print("Prismata root:", root)

    resources = discover_preview_resources(root)
    for k, v in resources.items():
        print(k, "=>", len(v), "items")

