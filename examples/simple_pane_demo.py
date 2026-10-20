"""Minimal pane demonstration using the SDK example registry.

This script is intentionally small and does three things:
1. loads the default pane object from the example registry,
2. resolves its default colour palette from the example colour-scheme registry,
3. renders a single pane using PrismataSDK runtime objects.

The script is designed to be a simple reference for how to build a basic pane from
real registry objects while keeping the implementation readable and minimal.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.border import BorderLoader
from core.chroma import ChromaLoader
from ui.panes import Pane, PaneRuntime

EXAMPLES_ROOT = Path(__file__).resolve().parent
REGISTRY_ROOT = EXAMPLES_ROOT / "registry"


def load_registry_objects(kind: str) -> dict[str, dict[str, Any]]:
    """Load all YAML entries under a registry folder and return them by name.

    Parameters:
        kind: registry collection name such as "pane", "menu", or "ui-framework".

    Returns:
        A dictionary keyed by the object's metadata name or object id, so callers can
        directly select a known example without walking the filesystem manually.
    """
    directory = REGISTRY_ROOT / f"{kind}.d"
    entries: dict[str, dict[str, Any]] = {}

    for file_path in sorted(directory.glob("*.yaml")):
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            key = str(payload.get("metadata", {}).get("name") or payload.get("id") or file_path.stem)
            entries[key] = payload

    return entries


def ansi_rgb_to_hex(value: str) -> str:
    """Convert an ANSI-style rgb string into an HTML-style hex colour.

    Parameters:
        value: a string like "ansi:rgb(220,220,220)".

    Returns:
        A hex string such as "#dcdcdc".
    """
    if not value.startswith("ansi:rgb("):
        return value

    inner = value[len("ansi:rgb(") : -1]
    red, green, blue = (int(part.strip()) for part in inner.split(","))
    return "#{:02x}{:02x}{:02x}".format(red, green, blue)


def default_palette_from_registry() -> dict[str, str]:
    """Read the default colour scheme from the registry and convert it to a palette.

    The registry stores values like "ansi:rgb(220,220,220)". This helper normalises
    those values into a usable mapping for the pane runtime.
    """
    scheme_payload = load_registry_objects("colour-scheme").get("default.colour-scheme")
    if not isinstance(scheme_payload, dict):
        raise ValueError("The default colour-scheme object was not found in the registry.")

    palette: dict[str, str] = {}
    for role_name, colours in scheme_payload.get("content", {}).get("roles", {}).items():
        foreground = colours.get("fg")
        if isinstance(foreground, str):
            palette[role_name] = ansi_rgb_to_hex(foreground)
    return palette


def build_default_pane() -> Pane:
    """Create a `Pane` object from the default pane registry entry.

    This demonstrates how to take a YAML object from the example registry and map it
    into the runtime `Pane` dataclass used by the SDK.
    """
    pane_data = load_registry_objects("pane").get("default.pane")
    if not isinstance(pane_data, dict):
        raise ValueError("The default pane object was not found in the registry.")

    content = pane_data.get("content", {})
    return Pane(
        id=str(pane_data.get("id", "default")),
        kind=str(pane_data.get("kind", "pane")),
        title="Default Example Pane",
        position={"x": int(content.get("x", 0)), "y": int(content.get("y", 0))},
        size={"width": int(content.get("width", 80)), "height": int(content.get("height", 24))},
        colour_scheme=str(content.get("colour_scheme", "default")),
        colour_roles=[str(content.get("colour_role", "default"))],
        border_role=str(content.get("border_role", "default")),
        border_pattern=str(content.get("border_pattern", "single-line")),
    )


def main() -> None:
    """Run the demonstration and print a concise pane summary."""
    palette = default_palette_from_registry()
    pane = build_default_pane()

    # ChromaLoader accepts an input palette dictionary and keeps the API consistent
    # with the registry-driven migration model.
    chroma = ChromaLoader.load({"id": "default", "palette": palette})
    border = BorderLoader.load({"id": "single-line", "style": pane.border_pattern})

    runtime = PaneRuntime(pane=pane)
    rendered = runtime.render(chroma.palette)
    runtime.apply_chroma(chroma)
    runtime.apply_border(border)

    print(f"Pane: {rendered['id']}")
    print(f"Location: {rendered['position']}")
    print(f"Size: {rendered['size']}")
    print(f"Colours: {rendered['resolved_role_colours']}")
    print(f"Border: {rendered['border_pattern']}")
    print()
    print(runtime.render_frame(chroma.palette, width=80, height=24))


if __name__ == "__main__":
    main()
