"""
Prismata Engine — Pane Renderer (Python)
Schema‑driven pane rendering using:
- border patterns (registry)
- colour roles + colour schemes (registry + manifests)
- pane geometry + layout (canonical object schemas)
- renderer pipeline (canonical engine schemas)

This module is the Python equivalent of pane-renderer.schema.yaml.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from pathlib import Path

import yaml

from .border_patterns import (
    load_border_pattern_registry,
    validate_border_pattern,
    get_border_pattern,
    get_border_characters,
    get_border_thickness,
    get_border_padding,
    is_pattern_visible,
    is_pattern_enabled,
)
from .menu_renderer import render_menu, _strip_ansi, _truncate_visible, _pad_visible

# ---------------------------------------------------------------------------
# ANSI Helpers
# ---------------------------------------------------------------------------
FG_RESET = "\033[39m"
BG_RESET = "\033[49m"

def ansi_rgb_to_escape(code: str, fg_bg: str):
    if not code:
        return ""

    raw = code
    code = code.strip()

    if not code.startswith("ansi:rgb("):
        return ""

    nums = code[len("ansi:rgb("):-1]
    r, g, b = map(int, nums.split(","))
    if fg_bg == "fg":
        return f"\033[38;2;{r};{g};{b}m"
    elif fg_bg == "bg":
        return f"\033[48;2;{r};{g};{b}m"
    return ""

# ---------------------------------------------------------------------------
# Registry Loaders
# ---------------------------------------------------------------------------

def load_colour_scheme_registry(registry_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load colour-scheme registry entries from /Meta/registry/colour-schemes/*.d
    """
    registry: Dict[str, Dict[str, Any]] = {}

    for file in registry_root.glob("*.yaml"):
        with file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict) and "id" in data:
                entry_id = str(data["id"]).strip()
                registry[entry_id] = data
                entry_udi = data.get("udi")
                if isinstance(entry_udi, str) and entry_udi.strip():
                    registry[entry_udi.strip()] = data

    if "default" not in registry:
        registry["default"] = {"id": "default", "palette": [""], "roles": {}}

    return registry


def load_colour_role_registry(registry_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load semantic colour roles from /Meta/registry/colour-roles/*.d
    """
    registry: Dict[str, Dict[str, Any]] = {}

    for file in registry_root.glob("*.yaml"):
        with file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict) and "id" in data:
                entry_id = str(data["id"]).strip()
                registry[entry_id] = data
                entry_udi = data.get("udi")
                if isinstance(entry_udi, str) and entry_udi.strip():
                    registry[entry_udi.strip()] = data

    if "default" not in registry:
        registry["default"] = {
            "id": "default",
            "layers": {"bg": "ansi:rgb(10,10,12)", "fg": "ansi:rgb(220,220,220)"},
        }
    if "primary-surface" not in registry:
        registry["primary-surface"] = {"id": "primary-surface", "layers": {"fg": "ansi:rgb(220,220,220)", "bg": "ansi:rgb(10,10,12)"}}
    if "secondary-surface" not in registry:
        registry["secondary-surface"] = {"id": "secondary-surface", "layers": {"fg": "ansi:rgb(200,200,200)", "bg": "ansi:rgb(18,18,20)"}}
    if "accent-surface" not in registry:
        registry["accent-surface"] = {"id": "accent-surface", "layers": {"fg": "ansi:rgb(120,220,255)", "bg": "ansi:rgb(12,22,34)"}}
    if "alert-surface" not in registry:
        registry["alert-surface"] = {"id": "alert-surface", "layers": {"fg": "ansi:rgb(255,160,120)", "bg": "ansi:rgb(38,12,10)"}}
    if "border" not in registry:
        registry["border"] = {"id": "border", "layers": {"fg": "ansi:rgb(160,160,160)", "bg": "ansi:rgb(10,10,12)"}}
    if "background" not in registry:
        registry["background"] = {"id": "background", "layers": {"bg": "ansi:rgb(10,10,12)", "fg": "ansi:rgb(220,220,220)"}}
    if "menu_surface" not in registry:
        registry["menu_surface"] = {"id": "menu_surface", "layers": {"bg": "ansi:rgb(10,10,12)", "fg": "ansi:rgb(220,220,220)"}}

    return registry


# ---------------------------------------------------------------------------
# Colour Resolution
# ---------------------------------------------------------------------------

def _canonical_key(value: Any) -> str:
    return str(value).strip().replace("-", "_").replace(" ", "_").lower()


def _lookup_mapping(mapping: Dict[str, Any], *keys: str) -> Any:
    if not isinstance(mapping, dict):
        return None

    for key in keys:
        if key in mapping:
            return mapping[key]

    normalized = { _canonical_key(k): v for k, v in mapping.items() }
    for key in keys:
        candidate = _canonical_key(key)
        if candidate in normalized:
            return normalized[candidate]
    return None


def _extract_role_colours(role_object: Dict[str, Any]) -> tuple[str, str]:
    if not isinstance(role_object, dict):
        return "", ""

    layers = role_object.get("layers")
    if isinstance(layers, dict):
        fg = layers.get("fg") or layers.get("foreground") or layers.get("text")
        bg = layers.get("bg") or layers.get("background") or layers.get("surface")
        if fg or bg:
            return (fg or ""), (bg or "")

    fg = role_object.get("fg") or role_object.get("foreground") or role_object.get("text")
    bg = role_object.get("bg") or role_object.get("background") or role_object.get("surface")
    if fg or bg:
        return (fg or ""), (bg or "")

    return "", ""


def resolve_colour(
    role: str,
    colour_roles: Dict[str, Dict[str, Any]],
    colour_schemes: Dict[str, Dict[str, Any]],
    active_scheme: str
) -> tuple[str, str]:
    """
    Resolve a semantic colour role to an actual colour value.

    The resolution order is:
    1. active scheme role mapping
    2. canonical registry role layers
    3. default role fallback
    4. no-colour fallback
    """

    requested_role = (role or "").strip()
    default_role = "default"

    role_obj = _lookup_mapping(colour_roles, requested_role, _canonical_key(requested_role), requested_role.replace("_", "-"))
    if not isinstance(role_obj, dict):
        role_obj = _lookup_mapping(colour_roles, default_role, _canonical_key(default_role), default_role.replace("_", "-"))

    if not isinstance(role_obj, dict):
        return "", ""

    scheme = _lookup_mapping(colour_schemes, active_scheme, _canonical_key(active_scheme), active_scheme.replace("_", "-"))
    if isinstance(scheme, dict):
        roles = scheme.get("roles") if isinstance(scheme.get("roles"), dict) else {}
        role_entry = _lookup_mapping(roles, requested_role, _canonical_key(requested_role), requested_role.replace("_", "-"))
        if isinstance(role_entry, dict):
            fg, bg = _extract_role_colours(role_entry)
            if fg or bg:
                return fg, bg

        default_entry = _lookup_mapping(roles, default_role, _canonical_key(default_role), default_role.replace("_", "-"))
        if isinstance(default_entry, dict):
            fg, bg = _extract_role_colours(default_entry)
            if fg or bg:
                return fg, bg

    fg, bg = _extract_role_colours(role_obj)
    if fg or bg:
        return fg, bg

    default_obj = _lookup_mapping(colour_roles, default_role, _canonical_key(default_role), default_role.replace("_", "-"))
    if isinstance(default_obj, dict):
        fg, bg = _extract_role_colours(default_obj)
        if fg or bg:
            return fg, bg

    return "", ""


# ---------------------------------------------------------------------------
# Pane Layouts
# ---------------------------------------------------------------------------

def _iter_child_panes(pane: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("children", "panes", "items"):
        value = pane.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]

    layout = pane.get("layout")
    if isinstance(layout, dict):
        children = layout.get("children") or layout.get("panes") or []
        if isinstance(children, list):
            return [item for item in children if isinstance(item, dict)]
        if isinstance(children, dict):
            return [children]

    return []


def _render_child_layout(
    pane: Dict[str, Any],
    children: List[Dict[str, Any]],
    border_registry: Dict[str, Dict[str, Any]],
    colour_roles: Dict[str, Dict[str, Any]],
    colour_schemes: Dict[str, Dict[str, Any]],
    ui_framework: Dict[str, Any],
    context: Dict[str, Any],
) -> List[str]:
    layout = pane.get("layout") if isinstance(pane.get("layout"), dict) else {}
    mode = str(layout.get("mode") or layout.get("type") or "vertical").lower()
    rendered_children = [
        render_pane(child, border_registry, colour_roles, colour_schemes, ui_framework, context)
        for child in children
        if isinstance(child, dict)
    ]
    rendered_children = [lines for lines in rendered_children if isinstance(lines, list) and len(lines) > 0]
    if not rendered_children:
        return []

    if mode in {"horizontal", "row", "side-by-side"}:
        max_lines = max(len(lines) for lines in rendered_children)
        widths = [max(len(line) for line in lines) for lines in rendered_children]
        combined: List[str] = []
        for idx in range(max_lines):
            parts = []
            for child_lines, width in zip(rendered_children, widths):
                if idx < len(child_lines):
                    parts.append(child_lines[idx].ljust(width))
                else:
                    parts.append(" " * width)
            combined.append(" ".join(parts))
        return combined

    combined: List[str] = []
    for child_lines in rendered_children:
        combined.extend(child_lines)
        combined.append("")
    if combined and combined[-1] == "":
        combined.pop()
    return combined


# ---------------------------------------------------------------------------
# Pane Rendering
# ---------------------------------------------------------------------------

def render_pane(
    pane: Dict[str, Any],
    border_registry: Dict[str, Dict[str, Any]],
    colour_roles: Dict[str, Dict[str, Any]],
    colour_schemes: Dict[str, Dict[str, Any]],
    ui_framework: Dict[str, Any],
    context: Dict[str, Any]
) -> List[str]:
    """
    Render a pane as a list of text lines.

    pane: canonical pane object
    border_registry: loaded border patterns
    colour_roles: semantic colour roles
    colour_schemes: colour scheme registry
    ui_framework: ui-framework manifest (bindings)
    context: runtime/editor context (for conditional visibility)
    """

    children = _iter_child_panes(pane)
    if children:
        return _render_child_layout(
            pane,
            children,
            border_registry,
            colour_roles,
            colour_schemes,
            ui_framework,
            context,
        )

    # -----------------------------------------------------------------------
    # 1. Resolve border pattern
    # -----------------------------------------------------------------------
    border_id = pane.get("border_pattern", pane.get("id", "default"))
    pattern = get_border_pattern(border_registry, border_id)

    if not validate_border_pattern(pattern):
        raise ValueError(f"Invalid border pattern: {border_id}")

    if not is_pattern_visible(pattern, context):
        return []  # invisible pane

    # -----------------------------------------------------------------------
    # 2. Resolve colours
    # -----------------------------------------------------------------------
    content_role = pane.get("content_role", pane.get("colour_role", "primary-surface"))
    border_role = pane.get("border_role", "border")
    active_scheme = ui_framework.get("colour_scheme", "default")

    content_fg, content_bg = resolve_colour(content_role, colour_roles, colour_schemes, active_scheme)
    border_fg, border_bg = resolve_colour(border_role, colour_roles, colour_schemes, active_scheme)
    if not (border_fg or border_bg):
        border_fg, border_bg = content_fg, content_bg

    content_fg_ansi = ansi_rgb_to_escape(content_fg, "fg")
    content_bg_ansi = ansi_rgb_to_escape(content_bg, "bg")
    border_fg_ansi = ansi_rgb_to_escape(border_fg, "fg")
    border_bg_ansi = ansi_rgb_to_escape(border_bg, "bg")

    # -----------------------------------------------------------------------
    # 3. Extract border characters, thickness, padding
    # -----------------------------------------------------------------------

    chars = get_border_characters(pattern)
    thickness = get_border_thickness(pattern)
    padding = get_border_padding(pattern)

    # -----------------------------------------------------------------------
    # 4. Pane geometry
    # -----------------------------------------------------------------------

    width = pane.get("width", 50)
    height = pane.get("height", 20)

    # -----------------------------------------------------------------------
    # 5. Build canvas
    # -----------------------------------------------------------------------
    canvas_width = width - (2 * thickness)
    canvas_height = height - (2 * thickness)

    canvas_line = " " * canvas_width
    canvas = [canvas_line for _ in range(canvas_height)]

    label = pane.get("label") or pane.get("title") or pane.get("name")
    if label and canvas:
        canvas[0] = f" {str(label)[: max(canvas_width - 2, 0)]} ".ljust(canvas_width)

    menu = pane.get("menu")
    if isinstance(menu, dict) and menu.get("items"):
        menu_spec = dict(menu)
        menu_spec["width"] = min(max(20, canvas_width), canvas_width)
        menu_lines = render_menu(
            menu_spec,
            border_registry,
            colour_roles,
            colour_schemes,
            ui_framework,
            context,
            preview_mode=True,
        )
        for idx, line in enumerate(menu_lines[: max(1, canvas_height)]):
            if idx >= len(canvas):
                break
            trimmed = _truncate_visible(line, max(canvas_width + 2, 0))
            inner = trimmed[1 : 1 + canvas_width] if len(_strip_ansi(trimmed)) >= 2 else ""
            canvas[idx] = _pad_visible(inner, canvas_width)

    # -----------------------------------------------------------------------
    # 6. Apply padding
    # -----------------------------------------------------------------------
    padded_canvas = (
        [" " * canvas_width] * padding["top"]
        + canvas
        + [" " * canvas_width] * padding["bottom"]
    )

    # -----------------------------------------------------------------------
    # 7. Build border lines
    # -----------------------------------------------------------------------


    top_border = border_fg_ansi + border_bg_ansi \
        + chars["corner_top_left"] \
        + chars["top"] * (canvas_width + padding["left"] + padding["right"]) \
        + chars["corner_top_right"] + FG_RESET + BG_RESET

    bottom_border = border_fg_ansi + border_bg_ansi \
        + chars["corner_bottom_left"] \
        + chars["bottom"] * (canvas_width + padding["left"] + padding["right"]) \
        + chars["corner_bottom_right"] + FG_RESET + BG_RESET

    # -----------------------------------------------------------------------
    # 8. Build final pane lines
    # -----------------------------------------------------------------------
    rendered_lines: List[str] = [top_border]

    for line in padded_canvas:
        rendered_lines.append(
            border_fg_ansi + border_bg_ansi
            + chars["left"] + FG_RESET + BG_RESET
            + content_fg_ansi + content_bg_ansi
            + line
            + border_fg_ansi + border_bg_ansi
            + chars["right"] + FG_RESET + BG_RESET
        )

    rendered_lines.append(bottom_border)

    return rendered_lines


# ---------------------------------------------------------------------------
# Convenience Loader
# ---------------------------------------------------------------------------

def load_and_render_pane(
    pane: Dict[str, Any],
    meta_root: Path,
    ui_framework: Dict[str, Any],
    context: Dict[str, Any]
) -> List[str]:
    """
    Convenience function:
    - Loads border patterns
    - Loads colour roles
    - Loads colour schemes
    - Renders pane
    """

    border_registry = load_border_pattern_registry(meta_root / "registry" / "border-pattern.d")
    colour_roles = load_colour_role_registry(meta_root / "registry" / "colour-role.d")
    colour_schemes = load_colour_scheme_registry(meta_root / "registry" / "colour-scheme.d")

    return render_pane(
        pane,
        border_registry,
        colour_roles,
        colour_schemes,
        ui_framework,
        context
    )
