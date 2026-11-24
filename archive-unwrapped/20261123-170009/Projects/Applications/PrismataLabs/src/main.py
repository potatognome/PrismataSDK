from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List


def _ensure_prismata_root_on_path() -> Path:
    current = Path(__file__).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "Meta").exists() and (candidate / "Projects").exists():
            root = candidate.resolve()
            root_str = str(root)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)
            return root
    return current.parents[0].resolve()


_PRISMATA_ROOT = _ensure_prismata_root_on_path()

from Projects.Tooling.primitives.python.path_helper import app_root_for, bootstrap_prismata_root

_PRISMATA_ROOT = bootstrap_prismata_root(Path(__file__).resolve())

from Projects.Applications.PrismataLabs.python.python_bridge import execute
from Projects.Tooling.primitives.python.menu_loader import load_first_menu
from Projects.Tooling.primitives.python.settings_store import load_mapping, save_mapping


def _load_main_menu(path: Path) -> Dict[str, Any]:
    return load_first_menu(path)


def _render_header(template: str, selected: Dict[str, Any]) -> str:
    text = template
    replacements = {
        "{{selected.colour_scheme}}": str(selected.get("colour_scheme")),
        "{{selected.border_pattern}}": str(selected.get("border_pattern")),
        "{{selected.object}}": str(selected.get("object")),
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def run() -> int:
    here = Path(__file__).resolve()
    prismata_root = bootstrap_prismata_root(here)
    app_root = app_root_for(prismata_root, "PrismataLabs")

    menu = _load_main_menu(app_root / "config" / "project-menus" / "main-menu.yaml")
    if not menu:
        print("Unable to load PrismataLabs main menu.")
        return 1

    # Load persisted settings (if any)
    SETTINGS_FILE = "labs.settings.yaml"
    settings_path = app_root / "config" / SETTINGS_FILE
    settings = load_mapping(settings_path, defaults={})

    # Seed selected values from persisted state
    persisted_selected = settings.get("lastSelected") if isinstance(settings.get("lastSelected"), dict) else {}
    selected: Dict[str, Any] = {
        "colour_scheme": persisted_selected.get("colour_scheme") if isinstance(persisted_selected.get("colour_scheme"), str) else None,
        "border_pattern": persisted_selected.get("border_pattern") if isinstance(persisted_selected.get("border_pattern"), str) else None,
        "object": persisted_selected.get("object") if isinstance(persisted_selected.get("object"), str) else None,
    }

    items = menu.get("items", []) if isinstance(menu.get("items"), list) else []

    while True:
        print()
        print(f"== {menu.get('title') or menu.get('name') or 'PrismataLabs'} ==")

        header = menu.get("header", {}) if isinstance(menu.get("header"), dict) else {}
        header_text = str(header.get("text", "")).strip()
        if header_text:
            print(_render_header(header_text, selected))
            print()

        for item in sorted(items, key=lambda i: int(i.get("order", 999)) if str(i.get("order", "")).isdigit() else 999):
            key = str(item.get("key", "")).strip()
            label = str(item.get("label", "")).strip() or str(item.get("name", "")).strip()
            if key and label:
                print(f"{key}: {label}")

        choice = input("Select option: ").strip()
        picked = None
        for item in items:
            if str(item.get("key", "")).strip() == choice:
                picked = item
                break

        if not picked:
            print("Invalid selection.")
            continue

        action = str(picked.get("action", "")).strip().lower()
        if action == "exit":
            # Persist selections and settings on exit
            try:
                settings["lastSelected"] = {k: v for k, v in selected.items()}
                save_mapping(settings_path, settings)
            except Exception:
                pass
            return 0

        command = str(picked.get("executeTarget", "")).strip()
        if not command:
            print("Menu item has no execute target.")
            continue

        payload: Dict[str, Any] = {
            "selected": dict(selected),
            "prismataRoot": str(prismata_root),
            "appRoot": str(app_root),
            "menuItem": {
                "udi": picked.get("udi"),
                "capability": picked.get("capability"),
            },
        }

        result = execute(command, payload)
        if isinstance(result, dict):
            if isinstance(result.get("selected"), dict):
                selected.update(result["selected"])

            lines = result.get("lines")
            if isinstance(lines, list):
                print()
                for line in lines:
                    print(str(line))

            message = result.get("message")
            if isinstance(message, str) and message.strip():
                print(message.strip())

            # Handle validation result (validate_preview capability)
            if "valid" in result:
                valid = bool(result.get("valid"))
                obj_path = result.get("path")
                obj_type = result.get("objectType")
                if valid:
                    print()
                    print(f"Object Valid for Preview: {obj_path} ({obj_type})")
                else:
                    print()
                    print("Object NOT valid for preview:")
                    errors = result.get("errors")
                    if isinstance(errors, list) and errors:
                        for err in errors:
                            print(f"- {err}")
                    else:
                        print("- Unknown validation error.")

            error = result.get("error")
            if isinstance(error, str) and error.strip():
                print(f"Error: {error.strip()}")

        input("Press Enter to continue...")


if __name__ == "__main__":
    raise SystemExit(run())
