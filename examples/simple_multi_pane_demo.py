"""Minimal multi-pane demonstration built from the example registry.

This script demonstrates a simple multi-pane layout by reading the exemplar UI
framework from the example registry and converting the referenced pane entries into
runtime `Pane` objects. The goal is to show how a few registry entries can be used
without any extra application-specific logic.
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
    """Load all objects under a registry collection for model assembly.

    Parameters:
        kind: registry collection name such as "pane" or "ui-framework".

    Returns:
        Dictionary keyed by registry object name.
    """
    directory = REGISTRY_ROOT / f"{kind}.d"
    entries: dict[str, dict[str, Any]] = {}
    for file_path in sorted(directory.glob("*.yaml")):
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            key = str(payload.get("metadata", {}).get("name") or payload.get("id") or file_path.stem)
            entries[key] = payload
    return entries


def build_exemplar_multi_pane() -> UIFrameworkRuntime:
    """Create a small multi-pane framework from the exemplar registry entries.

    Parameters:
        None.

    Returns:
        A composed `UIFrameworkRuntime` with pane descriptors and route metadata.
    """
    framework_payload = load_registry_objects("ui-framework").get("exemplar-multi-pane-menus.ui-framework")
    if not isinstance(framework_payload, dict):
        raise ValueError("The exemplar multi-pane UI framework was not found in the registry.")

    pane_payloads = load_registry_objects("pane")
    pane_refs = framework_payload.get("content", {}).get("panes", [])
    pane_ids: list[str] = []
    pane_objects: list[Pane] = []

    for ref in pane_refs:
        # The registry stores pane references using their full UDI values, so we look up
        # the matching object by its `udi` instead of assuming a simple name-based lookup.
        match = next(
            (
                payload
                for payload in pane_payloads.values()
                if payload.get("udi") == ref
            ),
            None,
        )
        if match is None:
            raise ValueError(f"No pane matching registry reference {ref!r} was found.")

        content = match.get("content", {})
        pane = Pane(
            id=str(match.get("id", "pane")),
            kind=str(match.get("kind", "pane")),
            title=str(match.get("metadata", {}).get("label", match.get("id", "pane"))),
            position={"x": int(content.get("x", 0)), "y": int(content.get("y", 0))},
            size={"width": int(content.get("width", 40)), "height": int(content.get("height", 20))},
            colour_scheme=str(content.get("colour_scheme", "default")),
            colour_roles=[str(content.get("colour_role", "default"))],
            border_role=str(content.get("border_role", "default")),
            border_pattern=str(content.get("border_pattern", "single-line")),
        )
        pane_objects.append(pane)
        pane_ids.append(pane.id)

    framework = UIFramework(
        id=str(framework_payload.get("id", "exemplar-multi-pane-menus")),
        panes=pane_ids,
        menu_routes={"main": pane_ids[0]},
        metadata={"layout": "split", "pane_slots": {"left": pane_ids[0], "right": pane_ids[1] if len(pane_ids) > 1 else pane_ids[0]}},
    )
    return UIFrameworkRuntime(framework=framework, panes=pane_ids, menu_routes={"main": pane_ids[0]})


def main() -> None:
    """Print the exemplar framework summary."""
    runtime = build_exemplar_multi_pane()
    composed = runtime.compose()
    print(f"Framework: {composed['id']}")
    print(f"Layout: {composed['layout']}")
    print(f"Pane order: {composed['panes']}")
    print(f"Menu target: {runtime.resolve_menu_target('main')}")
    print()

    pane_a = Pane(
        id="lh-pane",
        title="Left Pane",
        size={"width": 28, "height": 10},
        colour_roles=["default"],
        border_pattern="single-line",
    )
    pane_b = Pane(
        id="rh-pane",
        title="Right Pane",
        size={"width": 28, "height": 10},
        colour_roles=["default"],
        border_pattern="double-line",
    )
    left = PaneRuntime(pane=pane_a).render_frame({"default": "#dcdcdc"}, width=28, height=10)
    right = PaneRuntime(pane=pane_b).render_frame({"default": "#dcdcdc"}, width=28, height=10)
    left_lines = left.splitlines()
    right_lines = right.splitlines()
    for left_line, right_line in zip(left_lines, right_lines):
        print(left_line + "  " + right_line)


if __name__ == "__main__":
    main()
