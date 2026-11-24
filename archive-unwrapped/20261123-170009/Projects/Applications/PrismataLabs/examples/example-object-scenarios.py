#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Projects.Tooling.primitives.python import enable_windows_vt, find_prismata_root, render_panes_to_terminal_frame, terminal_space

ROOT = find_prismata_root(ROOT)
OBJECTS = ROOT / "Projects" / "Applications" / "PrismataLabs" / "examples" / "objects"


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_group(name: str):
    group_dir = OBJECTS / name
    payload = {}
    if group_dir.exists():
        for path in sorted(group_dir.glob("*.yaml")):
            data = load_yaml(path)
            item_id = data.get("id") or data.get("name") or path.stem
            payload[item_id] = data
    return payload


def _canonicalize_role(role):
    return role or "default"


def _canonicalize_border(border):
    return border or "default"


def _renderable_pane(pane: dict, menu: dict | None = None) -> dict:
    pane_data = dict(pane)
    pane_data["label"] = pane_data.get("label") or pane_data.get("title") or pane_data.get("id") or "Pane"
    pane_data["title"] = pane_data.get("title") or pane_data.get("label") or pane_data.get("id") or "Pane"
    pane_data["colour_role"] = _canonicalize_role(pane_data.get("colour_role"))
    pane_data["border_role"] = _canonicalize_role(pane_data.get("border_role"))
    pane_data["content_role"] = _canonicalize_role(pane_data.get("content_role"))
    pane_data["border_pattern"] = _canonicalize_border(pane_data.get("border_pattern"))

    selected_menu = menu if isinstance(menu, dict) else pane_data.get("menu")
    if isinstance(selected_menu, dict):
        menu_data = dict(selected_menu)
        nested_menu = menu_data.get("menu") if isinstance(menu_data.get("menu"), dict) else None
        if nested_menu:
            menu_data = dict(nested_menu)
        menu_data["title"] = menu_data.get("title") or menu_data.get("label") or menu_data.get("id") or pane_data["title"]
        menu_data["label"] = menu_data.get("label") or menu_data.get("title") or menu_data.get("id") or pane_data["title"]
        menu_data["colour_role"] = _canonicalize_role(menu_data.get("colour_role"))
        menu_data["border_pattern"] = _canonicalize_border(menu_data.get("border_pattern"))

        items = menu_data.get("items")
        if not isinstance(items, list):
            raise ValueError("Menu object must define 'items' as a list.")
        for item in items:
            if not isinstance(item, dict):
                continue
            item["label"] = item.get("label") or item.get("title") or item.get("id") or "Item"
            item["colour_role"] = _canonicalize_role(item.get("colour_role"))
            item["border_pattern"] = _canonicalize_border(item.get("border_pattern"))
        menu_data["items"] = items
        pane_data["menu"] = menu_data

    return pane_data


def scenario_single_pane():
    pane = load_group("panes").get("example-single-pane", {})
    menu = load_group("menus").get("example-single-pane-menu", {})
    return {
        "name": "single-pane",
        "title": "Single Pane Functional Menu",
        "panes": [_renderable_pane(pane, menu)],
    }


def scenario_dual_pane():
    left_pane = load_group("panes").get("example-left-pane", {})
    right_pane = load_group("panes").get("example-right-pane", {})
    return {
        "name": "dual-pane",
        "title": "Dual Pane Active Menu",
        "panes": [
            _renderable_pane(left_pane),
            _renderable_pane(right_pane),
        ],
    }


def scenario_diagnostic():
    left_pane = load_group("panes").get("example-left-pane", {})
    right_pane = load_group("panes").get("example-right-pane", {})
    return {
        "name": "diagnostic",
        "title": "Diagnostic Pane Roles and Parameters",
        "panes": [
            _renderable_pane(left_pane),
            _renderable_pane(right_pane),
        ],
    }


def render_scenario(scenario):
    panes = scenario.get("panes") or []
    if not panes:
        return []
    rendered = render_panes_to_terminal_frame(
        panes,
        meta_root=ROOT / "Meta",
        colour_scheme="default",
        size=terminal_space((120, 38)),
    )
    return rendered[1:] if rendered and rendered[0].startswith("\x1b[2J") else rendered


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    enable_windows_vt()

    scenarios = [
        scenario_single_pane(),
        scenario_dual_pane(),
        scenario_diagnostic(),
    ]
    for scenario in scenarios:
        print(f"=== {scenario['title']} ===")
        for line in render_scenario(scenario):
            print(line)


if __name__ == "__main__":
    main()

