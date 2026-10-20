"""Minimal UI framework demonstration using the example registry.

This script demonstrates how a UI framework can be built from the example registry by:
- loading the default UI framework definition,
- selecting the default pane object it references,
- composing the framework runtime, and
- resolving menu routing with the SDK runtime API.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.frameworks import UIFramework, UIFrameworkRuntime
from ui.panes import Pane, PaneRuntime

EXAMPLES_ROOT = Path(__file__).resolve().parent
REGISTRY_ROOT = EXAMPLES_ROOT / "registry"


def load_registry_objects(kind: str) -> dict[str, dict[str, Any]]:
    """Load a registry collection and return entries keyed by name.

    Parameters:
        kind: registry folder name, for example "ui-framework" or "pane".

    Returns:
        Dictionary mapping metadata name or object id to the raw YAML payload.
    """
    directory = REGISTRY_ROOT / f"{kind}.d"
    entries: dict[str, dict[str, Any]] = {}

    for file_path in sorted(directory.glob("*.yaml")):
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            key = str(payload.get("metadata", {}).get("name") or payload.get("id") or file_path.stem)
            entries[key] = payload
    return entries


def build_default_framework() -> UIFrameworkRuntime:
    """Create a minimal framework runtime based on the default example entries.

    Parameters:
        None.

    Returns:
        An instantiated `UIFrameworkRuntime` containing a framework and the pane it owns.
    """
    framework_payload = load_registry_objects("ui-framework").get("default.ui-framework")
    if not isinstance(framework_payload, dict):
        raise ValueError("The default UI framework object was not found.")

    pane_payload = load_registry_objects("pane").get("default.pane")
    if not isinstance(pane_payload, dict):
        raise ValueError("The default pane object was not found.")

    pane = Pane(
        id=str(pane_payload.get("id", "default")),
        title="Framework Default Pane",
        position={"x": int(pane_payload.get("content", {}).get("x", 0)), "y": int(pane_payload.get("content", {}).get("y", 0))},
        size={"width": int(pane_payload.get("content", {}).get("width", 80)), "height": int(pane_payload.get("content", {}).get("height", 24))},
        colour_scheme=str(pane_payload.get("content", {}).get("colour_scheme", "default")),
        colour_roles=[str(pane_payload.get("content", {}).get("colour_role", "default"))],
        border_role=str(pane_payload.get("content", {}).get("border_role", "default")),
        border_pattern=str(pane_payload.get("content", {}).get("border_pattern", "single-line")),
    )

    pane_runtime = PaneRuntime(pane=pane)
    pane_runtime.resolve_role_colours({pane.colour_roles[0]: "#dcdcdc"})

    framework = UIFramework(
        id=str(framework_payload.get("id", "default")),
        panes=[pane.id],
        menu_routes={"default": pane.id},
        metadata={"layout": "default", "pane_slots": {"main": pane.id}},
    )
    return UIFrameworkRuntime(framework=framework, panes=[pane.id], menu_routes={"default": pane.id})


def main() -> None:
    """Run the framework demo and print the composed UI output."""
    runtime = build_default_framework()
    composed = runtime.compose()
    menu_target = runtime.resolve_menu_target("default")

    print(f"Framework: {composed['id']}")
    print(f"Layout: {composed['layout']}")
    print(f"Panes: {composed['panes']}")
    print(f"Menu route target: {menu_target}")
    print()

    demo_pane = Pane(
        id="default",
        title="Default Framework Pane",
        size={"width": 32, "height": 10},
        colour_roles=["default"],
        border_pattern="single-line",
    )
    print(PaneRuntime(pane=demo_pane).render_frame({"default": "#dcdcdc"}, width=32, height=10))


if __name__ == "__main__":
    main()
