"""
Prismata Engine — Menu Renderer (Python)
Schema‑driven menu rendering using:
- border patterns (registry)
- colour roles + colour schemes (registry + manifests)
- menu objects (canonical object.schemas)
- renderer pipeline (canonical engine.schemas)
- placeholder capability for preview mode

This module is the Python equivalent of menu-renderer.schema.yaml.
"""

from __future__ import annotations

from typing import Dict, Any, List
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
    is_pattern_enabled
)

# ---------------------------------------------------------------------------
# Registry Loaders
# ---------------------------------------------------------------------------

def load_colour_scheme_registry(registry_root: Path) -> Dict[str, Dict[str, Any]]:
    registry = {}
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
    registry = {}
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
            "layers": {
                "bg": "ansi:rgb(10,10,12)",
                "fg": "ansi:rgb(220,220,220)"
            }
        }

    if "menu_surface" not in registry:
        registry["menu_surface"] = {"id": "menu_surface", "layers": {"bg": "ansi:rgb(10,10,12)", "fg": "ansi:rgb(220,220,220)"}}
    if "background" not in registry:
        registry["background"] = {"id": "background", "layers": {"bg": "ansi:rgb(10,10,12)", "fg": "ansi:rgb(220,220,220)"}}
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


def _extract_role_value(role_object: Dict[str, Any], layer: str = "fg") -> str:
    if not isinstance(role_object, dict):
        return ""

    target = (layer or "fg").lower()
    preferred = "bg" if target.startswith("bg") or target in {"background", "surface"} else "fg"

    layers = role_object.get("layers")
    if isinstance(layers, dict):
        fg = layers.get("fg") or layers.get("foreground") or layers.get("text")
        bg = layers.get("bg") or layers.get("background") or layers.get("surface")
        if preferred == "bg":
            if bg:
                return bg
            if fg:
                return fg
            return ""
        if fg:
            return fg
        if bg:
            return bg
        return ""

    fg = role_object.get("fg") or role_object.get("foreground") or role_object.get("text")
    bg = role_object.get("bg") or role_object.get("background") or role_object.get("surface")
    if preferred == "bg":
        if bg:
            return bg
        if fg:
            return fg
        return ""
    if fg:
        return fg
    if bg:
        return bg
    return ""


def resolve_colour(
    role: str,
    colour_roles: Dict[str, Dict[str, Any]],
    colour_schemes: Dict[str, Dict[str, Any]],
    active_scheme: str
) -> str:
    requested_role = (role or "").strip()
    fallback_role = "default"
    preferred_layer = "bg" if requested_role.lower() in {"background", "bg", "surface", "menu_surface"} else "fg"

    role_obj = _lookup_mapping(colour_roles, requested_role, _canonical_key(requested_role), requested_role.replace("_", "-"))
    if not isinstance(role_obj, dict):
        role_obj = _lookup_mapping(colour_roles, fallback_role, _canonical_key(fallback_role), fallback_role.replace("_", "-"))

    if not isinstance(role_obj, dict):
        return ""

    scheme = _lookup_mapping(colour_schemes, active_scheme, _canonical_key(active_scheme), active_scheme.replace("_", "-"))
    if isinstance(scheme, dict):
        roles = scheme.get("roles") if isinstance(scheme.get("roles"), dict) else {}
        if roles:
            role_entry = _lookup_mapping(roles, requested_role, _canonical_key(requested_role), requested_role.replace("_", "-"))
            if isinstance(role_entry, dict):
                value = _extract_role_value(role_entry, preferred_layer)
                if value:
                    return value

            default_entry = _lookup_mapping(roles, fallback_role, _canonical_key(fallback_role), fallback_role.replace("_", "-"))
            if isinstance(default_entry, dict):
                value = _extract_role_value(default_entry, preferred_layer)
                if value:
                    return value

    return _extract_role_value(role_obj, preferred_layer)


# ---------------------------------------------------------------------------
# Menu Rendering
# ---------------------------------------------------------------------------

FG_RESET = "\033[39m"
BG_RESET = "\033[49m"
ANSI_ESCAPE_RE = __import__("re").compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(value: str) -> str:
    return ANSI_ESCAPE_RE.sub("", str(value))


def _visible_width(value: str) -> int:
    return len(_strip_ansi(value))


def _truncate_visible(value: str, width: int) -> str:
    if width <= 0:
        return ""

    result: List[str] = []
    visible = 0
    i = 0
    while i < len(value) and visible < width:
        if value.startswith("\x1b[", i):
            end = value.find("m", i)
            if end != -1:
                result.append(value[i : end + 1])
                i = end + 1
                continue
        result.append(value[i])
        visible += 1
        i += 1
    return "".join(result)


def _pad_visible(value: str, width: int) -> str:
    visible = _visible_width(value)
    if visible >= width:
        return _truncate_visible(value, width)
    return value + (" " * (width - visible))


def _ansi_rgb_to_escape(code: str, fg_bg: str) -> str:
    if not code:
        return ""

    raw = code.strip()
    if not raw.startswith("ansi:rgb("):
        return ""

    nums = raw[len("ansi:rgb("):-1]
    try:
        r, g, b = map(int, nums.split(","))
    except ValueError:
        return ""

    if fg_bg == "fg":
        return f"\033[38;2;{r};{g};{b}m"
    if fg_bg == "bg":
        return f"\033[48;2;{r};{g};{b}m"
    return ""


def _style_text(text: str, fg: str, bg: str) -> str:
    if not fg and not bg:
        return str(text)
    escape_prefix = (
        _ansi_rgb_to_escape(fg, "fg")
        + _ansi_rgb_to_escape(bg, "bg")
    )
    if not escape_prefix:
        return str(text)
    return escape_prefix + str(text) + FG_RESET + BG_RESET


def _normalize_header_text(header: Any, fallback: str = "") -> str:
    if isinstance(header, dict):
        text = header.get("text") or header.get("label") or header.get("title") or fallback
        return str(text) if text else fallback
    if header is None:
        return fallback
    return str(header)


def render_menu(
    menu: Dict[str, Any],
    border_registry: Dict[str, Dict[str, Any]],
    colour_roles: Dict[str, Dict[str, Any]],
    colour_schemes: Dict[str, Dict[str, Any]],
    ui_framework: Dict[str, Any],
    context: Dict[str, Any],
    preview_mode: bool = False
) -> List[str]:
    """
    Render a menu as a list of text lines.

    preview_mode:
        - True: items may use placeholder capability
        - False: items must pass full validation
    """

    menu = menu.get("menu") if isinstance(menu, dict) and isinstance(menu.get("menu"), dict) else menu

    # -----------------------------------------------------------------------
    # 1. Resolve border pattern
    # -----------------------------------------------------------------------
    border_id = menu.get("border_pattern", "default")
    pattern = get_border_pattern(border_registry, border_id)

    if not validate_border_pattern(pattern):
        raise ValueError(f"Invalid border pattern: {border_id}")

    if not is_pattern_visible(pattern, context):
        return []  # invisible menu

    # -----------------------------------------------------------------------
    # 2. Resolve colours
    # -----------------------------------------------------------------------
    colour_role = menu.get("colour_role", "default")
    active_scheme = ui_framework.get("colour_scheme", "default")

    fg = resolve_colour(colour_role, colour_roles, colour_schemes, active_scheme)
    bg = resolve_colour("background", colour_roles, colour_schemes, active_scheme)

    # -----------------------------------------------------------------------
    # 3. Extract border characters, thickness, padding
    # -----------------------------------------------------------------------
    chars = get_border_characters(pattern)
    thickness = get_border_thickness(pattern)
    padding = get_border_padding(pattern)

    # -----------------------------------------------------------------------
    # 4. Menu geometry
    # -----------------------------------------------------------------------
    width = menu.get("width", 40)
    height = menu.get("height", None)  # dynamic height based on items

    # -----------------------------------------------------------------------
    # 5. Build menu item lines
    # -----------------------------------------------------------------------
    item_lines: List[str] = []

    if "items" not in menu:
        raise ValueError("Menu must define canonical 'items' key.")
    items = menu.get("items")
    if not isinstance(items, list):
        raise ValueError("Menu 'items' must be a list.")
    for item in items:
        if isinstance(item, str):
            item = {"label": item}

        label = item.get("label") or item.get("name") or item.get("id") or ""

        capability = item.get("capability", None)

        # Preview mode: allow placeholder capability
        if preview_mode:
            if capability is None:
                capability = "prismata.meta.capability.preview|noop"

        # Publish mode: require full validation
        else:
            if capability is None:
                # Skip invalid items in publish mode
                continue

        # Conditional visibility
        visibility_mode = item.get("visibility_mode")
        if visibility_mode == "conditional":
            cond = item.get("visibility_condition")
            if cond:
                try:
                    if not eval(cond, {}, context):
                        continue
                except Exception:
                    continue

        item_colour_role = item.get("colour_role", colour_role)
        item_fg = resolve_colour(item_colour_role, colour_roles, colour_schemes, active_scheme)
        item_bg = resolve_colour("background", colour_roles, colour_schemes, active_scheme)

        item_lines_for_block: List[str] = []
        item_header_text = _normalize_header_text(item.get("header"), "")
        if item_header_text:
            header_text = f" {item_header_text[: max(width - 4, 0)]} "
            item_lines_for_block.append(_pad_visible(header_text, width))

        item_border_id = item.get("border_pattern")
        if item_border_id:
            item_pattern = get_border_pattern(border_registry, str(item_border_id))
            if validate_border_pattern(item_pattern):
                item_chars = get_border_characters(item_pattern)
                left_char = item_chars.get("left", "|")
                right_char = item_chars.get("right", "|")
                item_top = (
                    item_chars.get("corner_top_left", "+")
                    + item_chars.get("top", "-") * max(width - 2, 0)
                    + item_chars.get("corner_top_right", "+")
                )
                item_bottom = (
                    item_chars.get("corner_bottom_left", "+")
                    + item_chars.get("bottom", "-") * max(width - 2, 0)
                    + item_chars.get("corner_bottom_right", "+")
                )
                item_lines_for_block.insert(0, item_top)
                item_body = _style_text(f" {label[: max(width - 4, 0)]} ", item_fg, item_bg)
                item_lines_for_block.append(left_char + _pad_visible(item_body, max(width - 2, 0)) + right_char)
                item_lines_for_block.append(item_bottom)
            else:
                item_lines_for_block.append(_pad_visible(f" {label} ", width))
        else:
            item_lines_for_block.append(_pad_visible(f" {label} ", width))

        if item_lines_for_block:
            item_lines.extend(item_lines_for_block)

    # -----------------------------------------------------------------------
    # 6. Determine final height
    # -----------------------------------------------------------------------
    canvas_height = len(item_lines) + padding["top"] + padding["bottom"]

    # -----------------------------------------------------------------------
    # 7. Build border lines
    # -----------------------------------------------------------------------
    def border_char(*names: str) -> str:
        for name in names:
            if name in chars:
                return str(chars[name])
        return " "

    top_border = (
        border_char("corner_top_left", "cornerTopLeft")
        + border_char("top", "topBorder") * max(width - 2, 0)
        + border_char("corner_top_right", "cornerTopRight")
    )

    bottom_border = (
        border_char("corner_bottom_left", "cornerBottomLeft")
        + border_char("bottom", "bottomBorder") * max(width - 2, 0)
        + border_char("corner_bottom_right", "cornerBottomRight")
    )

    # -----------------------------------------------------------------------
    # 8. Build final menu lines
    # -----------------------------------------------------------------------
    rendered_lines: List[str] = [top_border]

    left_char = border_char("left", "leftBorder")
    right_char = border_char("right", "rightBorder")

    menu_header_text = _normalize_header_text(menu.get("header"), menu.get("title") or menu.get("label") or "Menu")
    if menu_header_text:
        header_line = _style_text(f" {menu_header_text[: max(width - 4, 0)]} ", fg, bg)
        rendered_lines.append(left_char + _pad_visible(header_line, max(width - 2, 0)) + right_char)

    # Padding top
    for _ in range(padding["top"]):
        rendered_lines.append(left_char + " " * max(width - 2, 0) + right_char)

    # Items
    for line in item_lines:
        rendered_lines.append(left_char + _pad_visible(line, max(width - 2, 0)) + right_char)

    # Padding bottom
    for _ in range(padding["bottom"]):
        rendered_lines.append(left_char + " " * max(width - 2, 0) + right_char)

    rendered_lines.append(bottom_border)

    return rendered_lines


# ---------------------------------------------------------------------------
# Convenience Loader
# ---------------------------------------------------------------------------

def load_and_render_menu(
    menu: Dict[str, Any],
    meta_root: Path,
    ui_framework: Dict[str, Any],
    context: Dict[str, Any],
    preview_mode: bool = False
) -> List[str]:
    """
    Convenience function:
    - Loads border patterns
    - Loads colour roles
    - Loads colour schemes
    - Renders menu
    """

    border_registry = load_border_pattern_registry(meta_root / "registry" / "border-pattern.d")
    colour_roles = load_colour_role_registry(meta_root / "registry" / "colour-role.d")
    colour_schemes = load_colour_scheme_registry(meta_root / "registry" / "colour-scheme.d")

    return render_menu(
        menu,
        border_registry,
        colour_roles,
        colour_schemes,
        ui_framework,
        context,
        preview_mode=preview_mode
    )
