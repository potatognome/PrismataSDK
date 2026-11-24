#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import yaml


def _locate_prismata_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [here.parent, Path.cwd(), Path.home() / ".copilot" / "repos" / "Prismata"]
    candidates.extend(here.parents)
    for candidate in candidates:
        if (candidate / "Projects" / "Tooling" / "primitives" / "python").exists():
            return candidate
    raise RuntimeError(
        "Could not locate Prismata root. Set your working directory inside Prismata "
        "or place this script where C:\\...\\Prismata\\Projects exists."
    )


ROOT = _locate_prismata_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Projects.Tooling.primitives.python import enable_windows_vt, render_panes_to_terminal_frame, terminal_space


def _canonical_role(role: str | None) -> str:
    return role or "default"


def _canonical_border(border: str | None) -> str:
    return border or "default"


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _normalize_menu(menu: dict | None, pane_title: str) -> dict | None:
    if not isinstance(menu, dict):
        return None
    data = dict(menu.get("menu") if isinstance(menu.get("menu"), dict) else menu)
    data["title"] = data.get("title") or data.get("label") or data.get("id") or pane_title
    data["label"] = data.get("label") or data.get("title") or data.get("id") or pane_title
    data["colour_role"] = _canonical_role(data.get("colour_role"))
    data["border_pattern"] = _canonical_border(data.get("border_pattern"))

    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("Menu object must define 'items' as a list.")
    normalized_items: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_data = dict(item)
        item_data["label"] = item_data.get("label") or item_data.get("title") or item_data.get("id") or "Item"
        item_data["colour_role"] = _canonical_role(item_data.get("colour_role"))
        item_data["border_pattern"] = _canonical_border(item_data.get("border_pattern"))
        normalized_items.append(item_data)
    data["items"] = normalized_items
    return data


def _build_panes_from_framework(ui_framework_file: str) -> tuple[list[dict], str]:
    framework_path = (
        ROOT
        / "Projects"
        / "Applications"
        / "PrismataLabs"
        / "examples"
        / "objects"
        / "ui_frameworks"
        / ui_framework_file
    )
    framework = _load_yaml(framework_path)
    menus = framework.get("menus") or []
    menu_index = {
        m.get("udi"): m
        for m in menus
        if isinstance(m, dict) and isinstance(m.get("udi"), str) and m.get("udi")
    }
    pane_bindings = {
        b.get("pane"): b.get("menu")
        for b in (framework.get("pane_bindings") or [])
        if isinstance(b, dict) and b.get("pane") and b.get("menu")
    }

    panes: list[dict] = []
    for pane in framework.get("panes") or []:
        if not isinstance(pane, dict):
            continue
        pane_data = dict(pane)
        pane_data["title"] = pane_data.get("title") or pane_data.get("label") or pane_data.get("id") or "Pane"
        pane_data["label"] = pane_data.get("label") or pane_data.get("title") or pane_data.get("id") or "Pane"
        pane_data["colour_role"] = _canonical_role(pane_data.get("colour_role"))
        pane_data["border_role"] = _canonical_role(pane_data.get("border_role"))
        pane_data["content_role"] = _canonical_role(pane_data.get("content_role"))
        pane_data["border_pattern"] = _canonical_border(pane_data.get("border_pattern"))

        pane_udi = pane_data.get("udi")
        bound_menu_ref = pane_bindings.get(pane_udi) if isinstance(pane_udi, str) else None

        selected_menu = menu_index.get(bound_menu_ref) if isinstance(bound_menu_ref, str) else None
        if not isinstance(selected_menu, dict):
            selected_menu = pane_data.get("menu")
            if isinstance(selected_menu, dict):
                selected_menu = selected_menu
            elif isinstance(selected_menu, str):
                selected_menu = menu_index.get(selected_menu)
            else:
                selected_menu = None
        normalized = _normalize_menu(selected_menu, pane_data["title"])
        if normalized:
            pane_data["menu"] = normalized

        panes.append(pane_data)

    return panes, framework.get("colour_scheme", "default")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    enable_windows_vt()

    panes, colour_scheme = _build_panes_from_framework("single-pane.ui-framework.yaml")
    lines = render_panes_to_terminal_frame(
        panes,
        meta_root=ROOT / "Meta",
        colour_scheme=colour_scheme,
        size=terminal_space((120, 38)),
    )
    for line in lines[1:] if lines and lines[0].startswith("\x1b[2J") else lines:
        print(line)


if __name__ == "__main__":
    main()

