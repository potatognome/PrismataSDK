from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.border import BorderSpec
from core.chroma import ChromaSpec


@dataclass(slots=True)
class Pane:
    """Schema-friendly pane descriptor for the migrated UI runtime."""

    id: str
    kind: str = "pane"
    title: str = ""
    position: dict[str, Any] | None = None
    size: dict[str, Any] | None = None
    visible: bool = True
    enabled: bool = True
    colour_scheme: str | None = None
    colour_roles: list[str] = field(default_factory=list)
    border_role: str | None = None
    border_pattern: str | None = None


@dataclass(slots=True)
class PaneRuntime:
    """Runtime pane object used by preview and framework composition."""

    pane: Pane
    resolved_role_colours: dict[str, str] = field(default_factory=dict)
    applied_chroma: dict[str, dict[str, str]] = field(default_factory=dict)
    applied_border: dict[str, str] = field(default_factory=dict)

    def resolve_role_colours(self, role_palette: dict[str, str], default_colour: str = "#000000") -> dict[str, str]:
        resolved = apply_role_palette(self.pane, role_palette, default_colour=default_colour)
        self.resolved_role_colours = resolved
        return resolved

    def apply_chroma(self, chroma: ChromaSpec | dict[str, Any], default_colour: str = "#000000") -> dict[str, Any]:
        if isinstance(chroma, dict):
            palette = dict(chroma.get("palette", {}))
            name = str(chroma.get("name") or chroma.get("id") or "default")
        else:
            palette = dict(getattr(chroma, "palette", {}))
            name = str(getattr(chroma, "name", getattr(chroma, "id", "default")))

        resolved_role_colours = self.resolve_role_colours(palette, default_colour=default_colour)
        self.applied_chroma[name] = palette
        return {
            "id": self.pane.id,
            "kind": self.pane.kind,
            "resolved_role_colours": resolved_role_colours,
            "applied_chroma": self.applied_chroma,
            "border_pattern": self.pane.border_pattern or self.pane.border_role,
            "applied_border": self.applied_border,
        }

    def apply_border(self, border: BorderSpec | dict[str, Any]) -> dict[str, Any]:
        if isinstance(border, dict):
            name = str(border.get("name") or border.get("id") or "default")
            style = str(border.get("style") or border.get("pattern") or "single-line")
        else:
            name = str(getattr(border, "name", getattr(border, "id", "default")))
            style = str(getattr(border, "style", getattr(border, "pattern", "single-line")))

        self.applied_border[name] = style
        self.pane.border_pattern = style
        if self.pane.border_role is None:
            self.pane.border_role = name

        return {
            "id": self.pane.id,
            "kind": self.pane.kind,
            "border_pattern": style,
            "border_role": self.pane.border_role,
            "applied_border": self.applied_border,
            "resolved_role_colours": self.resolved_role_colours,
            "applied_chroma": self.applied_chroma,
        }

    def render_frame(
        self,
        role_palette: dict[str, str] | None = None,
        default_colour: str = "#000000",
        chroma: ChromaSpec | dict[str, Any] | None = None,
        border: BorderSpec | dict[str, Any] | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> str:
        """Render a minimal ASCII-style pane frame for terminal demo output."""
        if role_palette is not None:
            resolved_role_colours = self.resolve_role_colours(role_palette, default_colour=default_colour)
        else:
            resolved_role_colours = self.resolved_role_colours

        if chroma is not None:
            render_payload = self.apply_chroma(chroma, default_colour=default_colour)
            resolved_role_colours = render_payload["resolved_role_colours"]

        if border is not None:
            self.apply_border(border)

        size = self.pane.size or {"width": 40, "height": 12}
        pane_width = int(width or size.get("width", 40))
        pane_height = int(height or size.get("height", 12))

        border_pattern = str(self.pane.border_pattern or self.pane.border_role or "single-line")
        glyphs = {
            "single-line": {
                "top_left": "+",
                "top_right": "+",
                "bottom_left": "+",
                "bottom_right": "+",
                "horizontal": "-",
                "vertical": "|",
            },
            "double-line": {
                "top_left": "+",
                "top_right": "+",
                "bottom_left": "+",
                "bottom_right": "+",
                "horizontal": "=",
                "vertical": "|",
            },
        }
        choice = glyphs.get(border_pattern, glyphs["single-line"])
        pad = max(0, pane_width - 2)
        title_text = self.pane.title or self.pane.id
        header = f" {title_text[: max(0, pad - 1)]}".ljust(pane_width - 1)

        lines: list[str] = []
        top = choice["top_left"] + (choice["horizontal"] * max(0, pane_width - 2)) + choice["top_right"]
        lines.append(top)

        for row in range(1, pane_height - 1):
            if row == 1:
                content = header[: max(0, pane_width - 2)]
                row_text = choice["vertical"] + content.ljust(max(0, pane_width - 2)) + choice["vertical"]
            else:
                row_text = choice["vertical"] + (" " * max(0, pane_width - 2)) + choice["vertical"]
            lines.append(row_text)

        bottom = choice["bottom_left"] + (choice["horizontal"] * max(0, pane_width - 2)) + choice["bottom_right"]
        lines.append(bottom)
        return "\n".join(lines)

    def render(
        self,
        role_palette: dict[str, str] | None = None,
        default_colour: str = "#000000",
        chroma: ChromaSpec | dict[str, Any] | None = None,
        border: BorderSpec | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if role_palette is not None:
            resolved_role_colours = self.resolve_role_colours(role_palette, default_colour=default_colour)
        else:
            resolved_role_colours = self.resolved_role_colours

        if chroma is not None:
            render_payload = self.apply_chroma(chroma, default_colour=default_colour)
            resolved_role_colours = render_payload["resolved_role_colours"]

        if border is not None:
            render_payload = self.apply_border(border)
            border_style = render_payload["border_pattern"]
        else:
            border_style = self.pane.border_pattern or self.pane.border_role

        colour_segments = [
            {"role": role, "colour": resolved_role_colours.get(role, default_colour)} for role in self.pane.colour_roles
        ]

        return {
            "id": self.pane.id,
            "kind": self.pane.kind,
            "title": self.pane.title,
            "position": self.pane.position or {"x": 0, "y": 0},
            "size": self.pane.size or {"width": 0, "height": 0},
            "visible": self.pane.visible,
            "enabled": self.pane.enabled,
            "colour_scheme": self.pane.colour_scheme,
            "colour_roles": self.pane.colour_roles,
            "colour_segments": colour_segments,
            "border_role": self.pane.border_role,
            "border_pattern": border_style,
            "resolved_role_colours": resolved_role_colours,
            "applied_chroma": self.applied_chroma,
            "applied_border": self.applied_border,
        }


def apply_role_palette(pane: Pane, role_palette: dict[str, str], default_colour: str = "#000000") -> dict[str, str]:
    return {role: role_palette.get(role, default_colour) for role in pane.colour_roles}


def resolve_pane_location(pane: Pane, context: dict[str, Any] | None = None) -> dict[str, int]:
    """Resolve pane location using fixed, relative, or split rules."""

    position = pane.position or {}
    mode = str(position.get("mode", "fixed"))
    context = context or {}

    if mode == "fixed":
        return {
            "x": int(position.get("x", 0)),
            "y": int(position.get("y", 0)),
        }

    if mode == "relative":
        anchors = context.get("anchors", {})
        anchor_id = position.get("anchor")
        anchor = anchors.get(anchor_id, {"x": 0, "y": 0})
        return {
            "x": int(anchor.get("x", 0)) + int(position.get("dx", 0)),
            "y": int(anchor.get("y", 0)) + int(position.get("dy", 0)),
        }

    if mode == "split":
        orientation = str(position.get("orientation", "horizontal"))
        index = int(position.get("index", 0))
        ratio = float(position.get("ratio", 0.5))
        width = int(context.get("width", 0))
        height = int(context.get("height", 0))

        if orientation == "horizontal":
            split_x = int(width * ratio)
            return {"x": 0 if index == 0 else split_x, "y": 0}

        split_y = int(height * ratio)
        return {"x": 0, "y": 0 if index == 0 else split_y}

    raise ValueError(f"Unsupported pane position mode: {mode}")
