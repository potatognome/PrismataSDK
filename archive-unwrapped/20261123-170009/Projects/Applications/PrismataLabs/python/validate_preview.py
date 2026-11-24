"""
PrismataLabs â€” validate_preview capability

This module validates a selected object (colour-scheme, border-pattern,
pane, menu, menu-item, ui-framework) using canonical schema rules.

It is invoked by the capability:
    prismata.prismatalabs.capability.validate-preview
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict, List

# Shared helpers
from Projects.Tooling.primitives.python.path_helper import find_prismata_root

# Canonical registry loaders
from Projects.Applications.PrismataLabs.python.preview_common import (
    load_colour_scheme_registry,
    load_colour_role_registry,
    load_ui_framework_registry,
)
from Projects.Tooling.primitives.python.border_patterns import load_border_pattern_registry

# Canonical validators (you will expand these later)
from Projects.Applications.PrismataLabs.python.schema_validator import (
    classify_object,
    validate_collection,
    validate_colour_scheme,
    validate_border_pattern,
    validate_pane,
    validate_menu,
    validate_menu_item,
    validate_ui_framework,
)


# ---------------------------------------------------------------------------
# Utility: Load YAML object
# ---------------------------------------------------------------------------

def load_yaml_object(path: Path) -> Dict[str, Any]:
    """Load a YAML file into a Python dict."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_capability_udi_index(prismata_root: Path) -> set[str]:
    manifest = prismata_root / "Projects" / "Applications" / "PrismataLabs" / "config" / "capability-manifest.yaml"
    if not manifest.exists():
        return set()

    data = load_yaml_object(manifest)
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list):
        return set()

    index: set[str] = set()
    for capability in capabilities:
        if not isinstance(capability, dict):
            continue
        udi = capability.get("udi")
        if isinstance(udi, str) and udi.strip():
            index.add(udi.strip())
    return index


# ---------------------------------------------------------------------------
# Validation Dispatcher
# ---------------------------------------------------------------------------

def validate_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the selected object using canonical schema rules.

    payload contains:
        {
            "selected": {
                "object": "<path or None>"
            }
        }

    Returns:
        {
            "valid": True/False,
            "errors": [ ... ],
            "objectType": "pane | menu | ...",
            "path": "<object path>"
        }
    """

    selected = payload.get("selected", {})
    object_path = selected.get("object")

    if not object_path:
        return {
            "valid": False,
            "errors": ["No object selected for validation."],
            "objectType": "none",
            "path": None,
        }

    prismata_root = find_prismata_root()
    obj_path = Path(object_path)

    if not obj_path.exists():
        return {
            "valid": False,
            "errors": [f"Object path does not exist: {object_path}"],
            "objectType": "invalid",
            "path": object_path,
        }

    # Load object
    obj = load_yaml_object(obj_path)
    obj_type = classify_object(obj)

    # Load registries
    colour_roles = load_colour_role_registry(prismata_root / "Meta" / "registry" / "colour-role.d")
    colour_schemes = load_colour_scheme_registry(prismata_root / "Meta" / "registry" / "colour-scheme.d")
    ui_frameworks = load_ui_framework_registry(prismata_root / "Meta" / "registry" / "ui-framework.d")
    border_registry = load_border_pattern_registry(prismata_root / "Meta" / "registry" / "border-pattern.d")
    capability_index = _load_capability_udi_index(prismata_root)

    registries = {
        "colour_roles": colour_roles,
        "colour_schemes": colour_schemes,
        "ui_frameworks": ui_frameworks,
        "border_patterns": border_registry,
        "capabilities": capability_index,
    }

    # -----------------------------------------------------------------------
    # Dispatch based on object type
    # -----------------------------------------------------------------------

    if obj_type == "colour-scheme":
        valid, errors = validate_colour_scheme(obj, registries=registries)
        return {
            "valid": valid,
            "errors": errors,
            "objectType": "colour-scheme",
            "path": object_path,
        }

    if obj_type == "colour-scheme-collection":
        valid, errors = validate_collection(obj, "colour-scheme")
        return {
            "valid": valid,
            "errors": errors,
            "objectType": "colour-scheme-collection",
            "path": object_path,
        }

    if obj_type == "border-pattern":
        valid, errors = validate_border_pattern(obj, registries=registries)
        return {
            "valid": valid,
            "errors": errors,
            "objectType": "border-pattern",
            "path": object_path,
        }

    if obj_type == "border-pattern-collection":
        valid, errors = validate_collection(obj, "border-pattern")
        return {
            "valid": valid,
            "errors": errors,
            "objectType": "border-pattern-collection",
            "path": object_path,
        }

    if obj_type == "pane":
        valid, errors = validate_pane(obj, registries=registries)
        return {
            "valid": valid,
            "errors": errors,
            "objectType": "pane",
            "path": object_path,
        }

    if obj_type == "menu":
        valid, errors = validate_menu(obj, capability_index=capability_index, registries=registries)
        return {
            "valid": valid,
            "errors": errors,
            "objectType": "menu",
            "path": object_path,
        }

    if obj_type == "menu-item":
        valid, errors = validate_menu_item(obj, capability_index=capability_index, registries=registries)
        return {
            "valid": valid,
            "errors": errors,
            "objectType": "menu-item",
            "path": object_path,
        }

    if obj_type == "menu-item-collection":
        valid, errors = validate_collection(obj, "menu-item")
        return {
            "valid": valid,
            "errors": errors,
            "objectType": "menu-item-collection",
            "path": object_path,
        }

    if obj_type == "ui-framework":
        valid, errors = validate_ui_framework(obj, capability_index=capability_index, registries=registries)
        return {
            "valid": valid,
            "errors": errors,
            "objectType": "ui-framework",
            "path": object_path,
        }

    # Unknown object type
    return {
        "valid": False,
        "errors": ["Unknown object type; cannot validate."],
        "objectType": "unknown",
        "path": object_path,
    }

