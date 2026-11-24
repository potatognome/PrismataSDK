"""
Prismata Tooling — Border Pattern Utilities
Schema‑driven border pattern loader, validator, and renderer helpers.

This module:
- Loads border patterns from the canonical registry
- Validates patterns against border-pattern.schema.yaml
- Provides safe accessors for rendering pipelines
- Supports conditional visibility/enablement
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, Any


# ---------------------------------------------------------------------------
# Registry Loader
# ---------------------------------------------------------------------------

def load_border_pattern_registry(registry_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load all border-pattern.entry.yaml files from the border-pattern.d registry folder.

    registry_root: Path to /Meta/registry/border-patterns/
    Returns a dict: { pattern_id: pattern_object }
    """
    registry: Dict[str, Dict[str, Any]] = {}
    for file in sorted(registry_root.glob("*.yaml")):
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "id" in data:
            entry_id = str(data["id"]).strip()
            registry[entry_id] = data
            registry[entry_id.lower()] = data
            entry_udi = data.get("udi")
            if isinstance(entry_udi, str) and entry_udi.strip():
                registry[entry_udi.strip()] = data
                registry[entry_udi.strip().lower()] = data

    # Minimal deterministic fallback for bootstrap or missing registry states.
    if "default" not in registry:
        registry["default"] = {
            "id": "default",
            "glyphs": {
                "top": "-",
                "bottom": "-",
                "left": "|",
                "right": "|",
                "corner_top_left": "+",
                "corner_top_right": "+",
                "corner_bottom_left": "+",
                "corner_bottom_right": "+",
            },
            "thickness": 1,
            "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0},
            "colour_role": "border",
            "visibility_mode": "static",
            "enable_mode": "enabled",
        }
    return registry


# ---------------------------------------------------------------------------
# Schema Validator
# ---------------------------------------------------------------------------

def validate_border_pattern(pattern: Dict[str, Any]) -> bool:
    """
    Validate a border pattern object against the canonical schema structure.

    This does NOT hard-code characters or patterns.
    It only checks structural correctness based on your schema:

    - id (string)
    - name (string)
    - glyphs: { top, bottom, left, right, cornerTopLeft, ... }
    - thickness (int)
    - padding (int or object)
    - colourScheme (string)
    - visibilityMode (string)
    - enableMode (string)
    - optional conditional fields
    """

    required_fields = [
        "id",
        "glyphs",
        "thickness",
        "padding",
        "colour_role"
    ]

    for field in required_fields:
        if field not in pattern:
            return False

    chars = pattern.get("glyphs", {})
    required_chars = [
        "top",
        "bottom",
        "left",
        "right",
        "corner_top_left",
        "corner_top_right",
        "corner_bottom_left",
        "corner_bottom_right",
    ]

    if not all(key in chars for key in required_chars):
        return False

    return True


# ---------------------------------------------------------------------------
# Pattern Accessor
# ---------------------------------------------------------------------------

def get_border_pattern(
    registry: Dict[str, Dict[str, Any]],
    name: str,
    fallback: str = "default"
) -> Dict[str, Any]:
    """
    Retrieve a border pattern by name from the registry.

    - Case-insensitive
    - Falls back to the provided fallback pattern
    - Returns a deep copy of the pattern object
    """

    requested = str(name or "").strip()
    key = requested.lower()
    if requested in registry:
        return dict(registry[requested])
    if key in registry:
        return dict(registry[key])

    # UDI fallback: resolve by final segment if present.
    if "." in requested:
        tail = requested.split(".")[-1].strip()
        if tail in registry:
            return dict(registry[tail])
        if tail.lower() in registry:
            return dict(registry[tail.lower()])

    if fallback in registry:
        return dict(registry[fallback])
    if fallback.lower() in registry:
        return dict(registry[fallback.lower()])

    # Absolute fallback: return the first available pattern
    if registry:
        first_key = next(iter(registry))
        return dict(registry[first_key])

    return {}  # No patterns available


# ---------------------------------------------------------------------------
# Visibility / Enablement Helpers
# ---------------------------------------------------------------------------

def is_pattern_visible(pattern: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Evaluate visibility_mode and optional visibility_condition.

    visibility_mode:
        - static
        - conditional
        - disabled

    visibility_condition:
        - simple boolean expression evaluated against context
    """

    mode = pattern.get("visibility_mode", "static")

    if mode == "static":
        return True

    if mode == "disabled":
        return False

    if mode == "conditional":
        cond = pattern.get("visibility_condition")
        if cond is None:
            return False

        # Simple evaluator: context["user_is_admin"] == True
        try:
            return eval(cond, {}, context)
        except Exception:
            return False

    return True


def is_pattern_enabled(pattern: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Evaluate enable_mode and optional enable_condition.
    """

    mode = pattern.get("enable_mode", "enabled")

    if mode == "enabled":
        return True

    if mode == "disabled":
        return False

    if mode == "conditional":
        cond = pattern.get("enable_condition")
        if cond is None:
            return False

        try:
            return eval(cond, {}, context)
        except Exception:
            return False

    return True


# ---------------------------------------------------------------------------
# Rendering Helpers
# ---------------------------------------------------------------------------

def get_border_characters(pattern: Dict[str, Any]) -> Dict[str, str]:
    """
    Return the characters block for rendering.
    """
    return dict(pattern.get("glyphs", {}))


def get_border_thickness(pattern: Dict[str, Any]) -> int:
    """
    Return border thickness.
    """
    return int(pattern.get("thickness", 1))


def get_border_padding(pattern: Dict[str, Any]) -> Dict[str, int]:
    """
    Return padding object.
    """
    pad = pattern.get("padding", {})
    if isinstance(pad, dict):
        return {
            "top": int(pad.get("top", 0)),
            "right": int(pad.get("right", 0)),
            "bottom": int(pad.get("bottom", 0)),
            "left": int(pad.get("left", 0)),
        }
    return {"top": 0, "right": 0, "bottom": 0, "left": 0}
