from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    colour_roles: list[str] = field(default_factory=list)
    border_role: str | None = None


@dataclass(slots=True)
class PaneRuntime:
    """Runtime pane object used by preview and framework composition."""

    pane: Pane
    resolved_role_colours: dict[str, str] = field(default_factory=dict)

    def resolve_role_colours(self, role_palette: dict[str, str], default_colour: str = "#000000") -> dict[str, str]:
        resolved = apply_role_palette(self.pane, role_palette, default_colour=default_colour)
        self.resolved_role_colours = resolved
        return resolved

    def render(self, role_palette: dict[str, str] | None = None, default_colour: str = "#000000") -> dict[str, Any]:
        if role_palette is not None:
            resolved_role_colours = self.resolve_role_colours(role_palette, default_colour=default_colour)
        else:
            resolved_role_colours = self.resolved_role_colours

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
            "colour_roles": self.pane.colour_roles,
            "colour_segments": colour_segments,
            "border_role": self.pane.border_role,
            "resolved_role_colours": resolved_role_colours,
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
