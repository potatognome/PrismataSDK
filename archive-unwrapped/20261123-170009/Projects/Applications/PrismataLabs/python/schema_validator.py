"""PrismataLabs schema validation helpers.

This module validates canonical object shapes used by PrismataLabs
preview/validation capabilities.
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Tuple

UDI_PATTERN = re.compile(r"^prismata\.[a-z0-9-]+\.[a-z0-9-]+\.[a-z0-9-|]+$")
VISIBILITY_MODES = {"static", "conditional", "hidden"}
ENABLE_MODES = {"enabled", "conditional", "disabled"}
BORDER_GLYPH_KEYS = {
    "top",
    "bottom",
    "left",
    "right",
    "corner_top_left",
    "corner_top_right",
    "corner_bottom_left",
    "corner_bottom_right",
}


def _require_string_field(obj: Dict[str, Any], key: str, errors: List[str]) -> None:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"Missing or invalid '{key}'.")


def _validate_udi(value: Any, field_name: str, errors: List[str], registries: Dict[str, Any] | None = None) -> None:
    """
    Validate that `value` is a UDI or can be resolved via provided registries.

    If `registries` is provided, a non-UDI token will be considered valid
    if it resolves to an entry in any of the registries (id, udi tail, or key).
    """
    if not isinstance(value, str) or not value.strip():
        errors.append(f"Missing or invalid '{field_name}'.")
        return
    v = value.strip()
    # Accept strict UDI first
    if UDI_PATTERN.match(v):
        return

    # Try to resolve short name in provided registries
    if registries:
        token = v
        token_lower = token.lower()
        # Capability manifest may be provided as a set of UDIs
        caps = registries.get("capabilities")
        if isinstance(caps, (set, list)):
            if token in caps or token_lower in (c.lower() for c in caps):
                return

        # For dict-like registries, check direct keys and entry fields
        for reg in registries.values():
            if isinstance(reg, dict):
                # Direct key match (ids and UDIs loaded by registry loaders)
                if token in reg or token_lower in reg:
                    return
                # Try tail of UDI (last segment)
                if "." in token:
                    tail = token.split(".")[-1]
                    if tail in reg or tail.lower() in reg:
                        return
                # Finally, try scanning entry objects for id/slug/udi tail
                for entry_key, entry in reg.items():
                    if not isinstance(entry, dict):
                        continue
                    entry_id = entry.get("id")
                    entry_udi = entry.get("udi")
                    entry_slug = entry.get("slug") or entry.get("name")
                    if isinstance(entry_id, str) and token == entry_id:
                        return
                    if isinstance(entry_id, str) and token_lower == entry_id.lower():
                        return
                    if isinstance(entry_slug, str) and token_lower == entry_slug.lower():
                        return
                    if isinstance(entry_udi, str) and entry_udi.strip().endswith(token):
                        return

    errors.append(f"Invalid UDI format for '{field_name}': {value}")


def _validate_identity(obj: Dict[str, Any], errors: List[str]) -> None:
    _require_string_field(obj, "id", errors)
    _validate_udi(obj.get("udi"), "udi", errors)


def _is_rgb_ansi(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(re.match(r"^ansi:rgb\((\d{1,3}),(\d{1,3}),(\d{1,3})\)$", value.strip()))


def classify_object(obj: Dict[str, Any]) -> str:
    """Classify canonical object instances and entry collections."""
    kind = obj.get("kind")
    if isinstance(kind, str):
        normalized = kind.strip().lower()
        if normalized in {
            "colour-scheme",
            "border-pattern",
            "pane",
            "menu",
            "menu-item",
            "ui-framework",
        }:
            return normalized
        if normalized == "colour-schemes":
            return "colour-scheme-collection"
        if normalized == "border-patterns":
            return "border-pattern-collection"
        if normalized == "menus":
            return "menu-collection"
        if normalized == "menu-items":
            return "menu-item-collection"
        if normalized == "panes":
            return "pane-collection"
        if normalized == "ui-frameworks":
            return "ui-framework-collection"

    if isinstance(obj.get("entries"), list):
        entries = [entry for entry in obj.get("entries", []) if isinstance(entry, dict)]
        if entries:
            inferred = classify_object(entries[0])
            if inferred != "unknown":
                return f"{inferred}-collection"

    if "items" in obj:
        return "menu"
    if {"x", "y", "width", "height"}.issubset(obj):
        return "pane"
    if "capability" in obj and "label" in obj:
        return "menu-item"
    if "panes" in obj:
        return "ui-framework"
    if "glyphs" in obj and "thickness" in obj:
        return "border-pattern"
    if "roles" in obj:
        return "colour-scheme"

    return "unknown"


def validate_colour_scheme(obj: Dict[str, Any], registries: Dict[str, Any] | None = None) -> Tuple[bool, List[str]]:
    errors = []
    _validate_identity(obj, errors)
    if obj.get("kind") != "colour-scheme":
        errors.append("Missing or invalid 'kind'; expected 'colour-scheme'.")
    roles = obj.get("roles")
    if not isinstance(roles, dict) or not roles:
        errors.append("Missing or invalid 'roles'.")
        return (False, errors)
    for role_name, layers in roles.items():
        if not isinstance(role_name, str) or not role_name.strip():
            errors.append("Invalid role key in 'roles'.")
            continue
        if not isinstance(layers, dict):
            errors.append(f"Invalid layers for role '{role_name}'.")
            continue
        fg = layers.get("fg")
        bg = layers.get("bg")
        if not _is_rgb_ansi(fg):
            errors.append(f"Role '{role_name}' has invalid fg colour: {fg}")
        if not _is_rgb_ansi(bg):
            errors.append(f"Role '{role_name}' has invalid bg colour: {bg}")
    return (len(errors) == 0, errors)


def validate_border_pattern(obj: Dict[str, Any], registries: Dict[str, Any] | None = None) -> Tuple[bool, List[str]]:
    errors = []
    _validate_identity(obj, errors)
    if obj.get("kind") != "border-pattern":
        errors.append("Missing or invalid 'kind'; expected 'border-pattern'.")
    glyphs = obj.get("glyphs")
    if not isinstance(glyphs, dict):
        errors.append("Missing or invalid 'glyphs'.")
    else:
        missing = sorted(BORDER_GLYPH_KEYS - set(glyphs.keys()))
        if missing:
            errors.append(f"Missing glyph keys: {', '.join(missing)}")
    thickness = obj.get("thickness")
    if not isinstance(thickness, int) or thickness < 1:
        errors.append("Missing or invalid 'thickness'; expected integer >= 1.")
    if "padding" not in obj:
        errors.append("Missing 'padding'.")
    _validate_udi(obj.get("colour_role"), "colour_role", errors, registries=registries)
    return (len(errors) == 0, errors)


def validate_pane(obj: Dict[str, Any], registries: Dict[str, Any] | None = None) -> Tuple[bool, List[str]]:
    errors = []
    _validate_identity(obj, errors)
    if obj.get("kind") != "pane":
        errors.append("Missing or invalid 'kind'; expected 'pane'.")
    _validate_udi(obj.get("content_role"), "content_role", errors, registries=registries)
    for key in ("x", "y", "width", "height"):
        value = obj.get(key)
        if not isinstance(value, int):
            errors.append(f"Missing or invalid '{key}'; expected integer.")
        elif key in {"width", "height"} and value < 1:
            errors.append(f"Invalid '{key}'; expected >= 1.")
        elif key in {"x", "y"} and value < 0:
            errors.append(f"Invalid '{key}'; expected >= 0.")
    if "colour_role" in obj:
        _validate_udi(obj.get("colour_role"), "colour_role", errors, registries=registries)
    if "border_pattern" in obj:
        _validate_udi(obj.get("border_pattern"), "border_pattern", errors, registries=registries)
    if "colour_scheme" in obj:
        _validate_udi(obj.get("colour_scheme"), "colour_scheme", errors, registries=registries)
    return (len(errors) == 0, errors)


def validate_menu(obj: Dict[str, Any], capability_index: set[str] | None = None, registries: Dict[str, Any] | None = None) -> Tuple[bool, List[str]]:
    errors = []
    _validate_identity(obj, errors)
    if obj.get("kind") != "menu":
        errors.append("Missing or invalid 'kind'; expected 'menu'.")
    items = obj.get("items")
    if not isinstance(items, list) or not items:
        errors.append("Missing or invalid 'items'.")
    else:
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"Invalid menu item at index {idx}; expected object.")
                continue
            valid, item_errors = validate_menu_item(item, capability_index=capability_index, registries=registries)
            if not valid:
                errors.extend(f"items[{idx}]: {err}" for err in item_errors)
    return (len(errors) == 0, errors)


def validate_menu_item(obj: Dict[str, Any], capability_index: set[str] | None = None, registries: Dict[str, Any] | None = None) -> Tuple[bool, List[str]]:
    errors = []
    _validate_identity(obj, errors)
    if obj.get("kind") != "menu-item":
        errors.append("Missing or invalid 'kind'; expected 'menu-item'.")
    _require_string_field(obj, "label", errors)
    _validate_udi(obj.get("capability"), "capability", errors, registries=registries)

    visibility_mode = obj.get("visibility_mode", "static")
    if visibility_mode not in VISIBILITY_MODES:
        errors.append(f"Invalid 'visibility_mode': {visibility_mode}")

    enable_mode = obj.get("enable_mode", "enabled")
    if enable_mode not in ENABLE_MODES:
        errors.append(f"Invalid 'enable_mode': {enable_mode}")

    if capability_index is not None:
        capability = obj.get("capability")
        if isinstance(capability, str) and capability not in capability_index:
            errors.append(f"Capability not declared in manifest: {capability}")

    return (len(errors) == 0, errors)


def validate_ui_framework(obj: Dict[str, Any], capability_index: set[str] | None = None, registries: Dict[str, Any] | None = None) -> Tuple[bool, List[str]]:
    errors = []
    _validate_identity(obj, errors)
    if obj.get("kind") != "ui-framework":
        errors.append("Missing or invalid 'kind'; expected 'ui-framework'.")

    panes = obj.get("panes")
    if not isinstance(panes, list) or not panes:
        errors.append("Missing or invalid 'panes'.")
    else:
        pane_ids: set[str] = set()
        for idx, pane in enumerate(panes):
            if not isinstance(pane, dict):
                errors.append(f"Invalid pane at index {idx}; expected object.")
                continue
            valid, pane_errors = validate_pane(pane, registries=registries)
            if not valid:
                errors.extend(f"panes[{idx}]: {err}" for err in pane_errors)
            pane_id = pane.get("id")
            if isinstance(pane_id, str):
                pane_ids.add(pane_id)

    active_pane = obj.get("active_pane")
    if active_pane is not None and isinstance(active_pane, str):
        if panes and isinstance(panes, list):
            if active_pane not in {p.get("id") for p in panes if isinstance(p, dict)}:
                errors.append(f"active_pane '{active_pane}' does not match any pane id.")

    menus = obj.get("menus")
    if menus is not None:
        if not isinstance(menus, list):
            errors.append("Invalid 'menus'; expected a list.")
        else:
            for idx, menu in enumerate(menus):
                if not isinstance(menu, dict):
                    errors.append(f"Invalid menu at index {idx}; expected object.")
                    continue
                valid, menu_errors = validate_menu(menu, capability_index=capability_index, registries=registries)
                if not valid:
                    errors.extend(f"menus[{idx}]: {err}" for err in menu_errors)

    return (len(errors) == 0, errors)


def validate_collection(obj: Dict[str, Any], entry_kind: str) -> Tuple[bool, List[str]]:
    """Validate collection objects with an entries list."""
    errors: List[str] = []
    entries = obj.get("entries")
    if not isinstance(entries, list) or not entries:
        return (False, ["Missing or invalid 'entries'."])

    validators = {
        "colour-scheme": validate_colour_scheme,
        "border-pattern": validate_border_pattern,
        "pane": validate_pane,
        "menu": validate_menu,
        "menu-item": validate_menu_item,
        "ui-framework": validate_ui_framework,
    }
    validator = validators.get(entry_kind)
    if validator is None:
        return (False, [f"Unsupported collection kind: {entry_kind}"])

    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entries[{idx}] is not an object.")
            continue
        valid, entry_errors = validator(entry)  # type: ignore[misc]
        if not valid:
            errors.extend(f"entries[{idx}]: {err}" for err in entry_errors)
    return (len(errors) == 0, errors)

