from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


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

from Projects.Tooling.primitives.python.path_helper import (
    app_root_for,
    bootstrap_prismata_root,
    select_folder,
)

_PRISMATA_ROOT = bootstrap_prismata_root(Path(__file__).resolve())

from Projects.Applications.Universe.python.python_bridge import execute
from Projects.Tooling.primitives.python.menu_loader import load_menu_index
from Projects.Tooling.primitives.python.settings_store import load_mapping, save_mapping


def _settings_path(paths: Dict[str, str]) -> Path:
    return Path(paths["stateDir"]) / "settings.json"


def _default_search_params() -> Dict[str, Any]:
    return {
        "folders": [],
        "projects": [],
        "fileTypes": [],
        "queries": [],
        "tags": [],
        "canonicalOnly": False,
        "recursive": True,
    }


def _normalize_search_params(raw: Any) -> Dict[str, Any]:
    defaults = _default_search_params()
    if not isinstance(raw, dict):
        return defaults

    def as_list(key: str) -> List[str]:
        value = raw.get(key, [])
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return []

    return {
        "folders": as_list("folders"),
        "projects": as_list("projects"),
        "fileTypes": as_list("fileTypes"),
        "queries": as_list("queries"),
        "tags": as_list("tags"),
        "canonicalOnly": bool(raw.get("canonicalOnly", defaults["canonicalOnly"])),
        "recursive": bool(raw.get("recursive", defaults["recursive"])),
    }


def _load_persisted_search_params(paths: Dict[str, str]) -> Dict[str, Any]:
    settings_path = _settings_path(paths)
    data = load_mapping(settings_path, defaults={}, file_format="json")

    # Canonical location for Python frontend persistence.
    direct = data.get("searchParams")
    if isinstance(direct, dict):
        return _normalize_search_params(direct)

    # Backward-compatible fallback for any nested settings shape.
    nested = data.get("settings")
    if isinstance(nested, dict) and isinstance(nested.get("searchParams"), dict):
        return _normalize_search_params(nested.get("searchParams"))

    return _default_search_params()


def _save_persisted_search_params(paths: Dict[str, str], search_params: Dict[str, Any]) -> None:
    settings_path = _settings_path(paths)
    data = load_mapping(settings_path, defaults={}, file_format="json")

    data["searchParams"] = _normalize_search_params(search_params)
    save_mapping(settings_path, data, file_format="json")


def _universe_paths(prismata_root: Path) -> Dict[str, str]:
    workspace_root = prismata_root / ".workspace" / "universe"
    return {
        "prismataRoot": str(prismata_root),
        "workspaceRoot": str(workspace_root),
        "stateDir": str(workspace_root / "state"),
        "initializedFlagPath": str(workspace_root / "state" / "initialized.flag"),
        "ingestionDir": str(workspace_root / "ingestion"),
        "registryDir": str(workspace_root / "registry"),
        "archiveDir": str(workspace_root / "archive"),
    }


def _load_menus(menu_dir: Path) -> Dict[str, Dict[str, Any]]:
    return load_menu_index(menu_dir)


def _resolve_menu_ref(menu_index: Dict[str, Dict[str, Any]], menu_ref: str) -> Optional[str]:
    if menu_ref in menu_index:
        return menu_ref

    # Fallback: tolerate historical suffixes/prefixes mismatch.
    for candidate in menu_index:
        if candidate.startswith(menu_ref) or menu_ref.startswith(candidate):
            return candidate

    return None


def _runtime_state(paths: Dict[str, str]) -> Dict[str, Any]:
    initialized = Path(paths["initializedFlagPath"]).exists()
    persisted_search_params = _load_persisted_search_params(paths)
    runtime_state: Dict[str, Any] = {
        "bootstrapMode": not initialized,
        "initialized": initialized,
        "vileIngested": False,
        "tuilkitIngested": False,
        "initializedFlagPath": paths["initializedFlagPath"],
        "settings": {},
        "searchParams": persisted_search_params,
    }

    try:
        status = execute("tuilkit_status", {"runtimeState": runtime_state})
        runtime_state["tuilkitRuntimeMode"] = str(status.get("mode", ""))
        runtime_state["tuilkitIngested"] = bool(status.get("ingested", False))
    except Exception:
        runtime_state["tuilkitRuntimeMode"] = ""

    return runtime_state


def _print_header(text: Optional[str]) -> None:
    if not text:
        return
    for line in str(text).splitlines():
        print(line)


def _toggle_in_list(values: List[str], incoming: str) -> List[str]:
    updated = list(values)
    for raw in incoming.split(","):
        value = raw.strip()
        if not value:
            continue
        if value in updated:
            updated = [v for v in updated if v != value]
        else:
            updated.append(value)
    return updated


def _read_line(prompt: str = "", default: str = "") -> str:
    try:
        value = input(prompt)
    except EOFError:
        return default
    return str(value).strip()


def _prompt_list_toggle(label: str, current: List[str]) -> List[str]:
    current_text = ", ".join(current) if current else "(none)"
    print(f"Current {label}: {current_text}")
    print("Enter one or more comma-separated values.")
    print("Existing values are removed; new values are added.")
    raw = _read_line(f"{label}: ")
    if not raw:
        return current
    return _toggle_in_list(current, raw)


def _prompt_folder_path_toggle(current: List[str]) -> List[str]:
    current_text = ", ".join(current) if current else "(none)"
    print(f"Current search path(s): {current_text}")
    print("Choose a folder to add or remove from the search path list.")
    selected = select_folder()
    if not selected:
        return current
    return _toggle_in_list(current, selected)


def _prompt_bool(label: str, current: bool) -> bool:
    current_text = "yes" if current else "no"
    raw = _read_line(f"{label} (Y/N, Enter keeps {current_text}): ").lower()
    if raw in {"y", "yes", "true", "1"}:
        return True
    if raw in {"n", "no", "false", "0"}:
        return False
    return current


def _search_roots(state: Dict[str, Any], paths: Dict[str, str]) -> List[str]:
    search_params = state.get("searchParams", {}) if isinstance(state, dict) else {}
    folders = search_params.get("folders", []) if isinstance(search_params, dict) else []
    if isinstance(folders, list) and folders:
        return [str(folder).strip() for folder in folders if str(folder).strip()]
    root = str(paths.get("workspaceRoot", "")).strip()
    return [root] if root else []


def _collect_search_results(state: Dict[str, Any], paths: Dict[str, str]) -> List[str]:
    search_params = state.get("searchParams", {}) if isinstance(state, dict) else {}
    if not isinstance(search_params, dict):
        return []

    roots = _search_roots(state, paths)
    if not roots:
        roots = [str(Path(paths.get("workspaceRoot", ".") or ".")).strip()]

    file_types = search_params.get("fileTypes", [])
    queries = search_params.get("queries", [])
    canonical_only = bool(search_params.get("canonicalOnly", False))
    recursive = bool(search_params.get("recursive", True))

    allowed_extensions = {str(item).lower().lstrip(".") for item in file_types if str(item).strip()} if isinstance(file_types, list) else set()

    results: List[str] = []
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        iterator = base.rglob("*") if recursive else base.iterdir()
        for candidate in iterator:
            if not candidate.is_file():
                continue
            suffix = candidate.suffix.lower().lstrip(".")
            if allowed_extensions and suffix not in allowed_extensions:
                continue
            if canonical_only and "canonical" not in str(candidate).lower():
                # This is a conservative, non-destructive placeholder filter for the Python UI.
                pass
            if queries:
                try:
                    content = candidate.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    content = ""
                query_text = " ".join(str(q) for q in queries if str(q).strip())
                if query_text and not any(str(q).lower() in content.lower() for q in queries if str(q).strip()):
                    continue
            results.append(str(candidate))

    return results


def _is_edit_unlocked(state: Dict[str, Any]) -> bool:
    if state.get("tuilkitIngested") or state.get("vileIngested"):
        return True
    mode = str(state.get("tuilkitRuntimeMode", "")).strip().lower()
    return mode == "tuilkit" and bool(state.get("tuilkitIngested"))


def _route_capability(state: Dict[str, Any], paths: Dict[str, str], selected: Dict[str, Any]) -> bool:
    capability = str(selected.get("capability", "")).strip()
    if capability == "prismata.universe.capability.fs-search-location":
        selected_path = select_folder()
        if not selected_path:
            print("No folder selected.")
            return True
        params = state.setdefault("searchParams", {})
        folders = list(params.get("folders", [])) if isinstance(params.get("folders", []), list) else []
        if selected_path not in folders:
            folders.append(selected_path)
        params["folders"] = folders
        print(f"Added search path: {selected_path}")
        _save_persisted_search_params(paths, state.get("searchParams", {}))
        return True

    if capability in {"prismata.universe.capability.fs-search", "prismata.universe.capability.fs-search-execute"}:
        params = state.setdefault("searchParams", {})
        if not isinstance(params, dict):
            params = {}
            state["searchParams"] = params
        print("Current search parameters:")
        print(f"  folders: {params.get('folders', [])}")
        print(f"  file types: {params.get('fileTypes', [])}")
        print(f"  queries: {params.get('queries', [])}")
        print(f"  tags: {params.get('tags', [])}")
        print(f"  canonicalOnly: {params.get('canonicalOnly', False)}")
        print(f"  recursive: {params.get('recursive', True)}")
        return True

    if capability == "prismata.universe.capability.fs-search-results":
        results = _collect_search_results(state, paths)
        print(f"Search results ({len(results)}):")
        if not results:
            print("  (no matches found)")
        else:
            for entry in results[:10]:
                print(f"  - {entry}")
            if len(results) > 10:
                print(f"  ... and {len(results) - 10} more")
        return True

    if capability in {"prismata.universe.capability.fs-select-multi", "prismata.universe.capability.fs-select-single"}:
        selection = state.get("selectionState", {}) if isinstance(state.get("selectionState", {}), dict) else {}
        selected_count = max(0, int(selection.get("selectionCount", 0))) if isinstance(selection.get("selectionCount", 0), int) else 0
        print(f"Selection routed: {capability} ({selected_count} item(s) in current selection state)")
        return True

    if capability == "prismata.universe.capability.fs-exemplar-preview":
        print("Exemplar preview: registry preview module is available through the canonical preview pipeline.")
        return True

    if capability in {"prismata.universe.capability.fs-edit-multi", "prismata.universe.capability.fs-edit-vile", "prismata.universe.capability.fs-update-fields", "prismata.universe.capability.fs-create-from-object"}:
        if not _is_edit_unlocked(state):
            print("Create/Edit is locked until VILE has been ingested.")
            return True
        print(f"Edit capability routed: {capability}")
        return True

    if capability in {"prismata.universe.capability.fs-verify-reference", "prismata.universe.capability.fs-verify-multi", "prismata.universe.capability.fs-verify-sequence", "prismata.universe.capability.fs-verify-collective"}:
        print(f"Verification capability routed: {capability}")
        return True

    if capability == "prismata.universe.capability.fs-diff-compatible":
        print("Diff compatibility pipeline is active for the current selection state.")
        return True

    if capability == "prismata.universe.capability.app-settings-paths":
        settings = state.setdefault("settings", {})
        if not isinstance(settings, dict):
            settings = {}
            state["settings"] = settings
        settings.setdefault("paths", {})
        if selected.get("args", {}).get("key_value"):
            key = str(selected.get("args", {}).get("key_value"))
            folder = select_folder()
            if folder:
                settings["paths"][key] = folder
                print(f"Updated {key} = {folder}")
                _save_persisted_search_params(paths, state.get("searchParams", {}))
            else:
                print("No folder was selected for settings update.")
        else:
            print("Settings path hook is ready for the canonical path editor.")
        return True

    if capability in {"prismata.universe.capability.app-settings-auto-archive", "prismata.universe.capability.app-settings-auto-versioning"}:
        settings = state.setdefault("settings", {})
        if not isinstance(settings, dict):
            settings = {}
            state["settings"] = settings
        features = settings.setdefault("features", {})
        if not isinstance(features, dict):
            features = {}
            settings["features"] = features
        current = bool(features.get("autoArchive" if "autoArchive" in capability else "autoVersioning", False))
        features["autoArchive" if "autoArchive" in capability else "autoVersioning"] = not current
        print(f"Toggled {('autoArchive' if 'autoArchive' in capability else 'autoVersioning')} -> {features.get('autoArchive' if 'autoArchive' in capability else 'autoVersioning')}")
        return True

    if capability == "prismata.universe.capability.app-settings-ignore":
        settings = state.setdefault("settings", {})
        ignore = settings.setdefault("ignore_extensions", [])
        print(f"Ignore extensions: {ignore}")
        return True

    if capability in {"prismata.universe.capability.app-settings-export", "prismata.universe.capability.app-settings-registry"}:
        print(f"Settings capability routed: {capability}")
        return True

    if capability == "prismata.universe.capability.app-bootstrap-run":
        print("Bootstrap sequence: workspace state is ready for canonical ingestion and registry bootstrap.")
        return True

    if capability == "prismata.universe.capability.app-quit":
        _save_persisted_search_params(paths, state.get("searchParams", {}))
        raise SystemExit(0)

    return False


def _handle_find_parameter_capability(state: Dict[str, Any], selected: Dict[str, Any]) -> bool:
    search_params = state.setdefault("searchParams", {})
    search_params.setdefault("folders", [])
    search_params.setdefault("fileTypes", [])
    search_params.setdefault("queries", [])
    search_params.setdefault("tags", [])
    search_params.setdefault("canonicalOnly", False)
    search_params.setdefault("recursive", True)

    key = str(selected.get("key", "")).strip()

    if key == "1":
        search_params["folders"] = _prompt_folder_path_toggle(list(search_params["folders"]))
        return True

    if key == "2":
        search_params["fileTypes"] = _prompt_list_toggle("file type(s)", list(search_params["fileTypes"]))
        return True

    if key == "3":
        search_params["queries"] = _prompt_list_toggle("query value(s)", list(search_params["queries"]))
        return True

    if key == "4":
        search_params["tags"] = _prompt_list_toggle("tag(s)", list(search_params["tags"]))
        return True

    if key == "5":
        search_params["canonicalOnly"] = _prompt_bool(
            "Search canonical folders only", bool(search_params["canonicalOnly"])
        )
        return True

    if key == "6":
        search_params["recursive"] = _prompt_bool(
            "Search folders recursively", bool(search_params["recursive"])
        )
        return True

    return False


def run() -> int:
    here = Path(__file__).resolve()
    prismata_root = bootstrap_prismata_root(here)
    app_root = app_root_for(prismata_root, "Universe")
    menu_index = _load_menus(app_root / "config" / "project-menus")

    current_menu_ref = "prismata.universe.menu.main"
    history: List[str] = []

    paths = _universe_paths(prismata_root)
    state = _runtime_state(paths)

    while True:
        resolved_ref = _resolve_menu_ref(menu_index, current_menu_ref)
        if not resolved_ref:
            print(f"Menu not found: {current_menu_ref}")
            if history:
                current_menu_ref = history.pop()
                continue
            return 1

        menu = menu_index[resolved_ref]
        payload = {
            "menu": menu,
            "runtimeState": state,
            "selectedObjects": [],
            "selectionState": {
                "selectionType": "none",
                "referenceObjectSelected": False,
            },
            "compatibility": {
                "semantic_compatible": False,
                "version_compatible": False,
                "type_compatible": False,
            },
            "availablePaneIds": ["results_list", "preview", "version_carousel", "diff_panel"],
            "prismataRoot": str(prismata_root),
            "paths": paths,
        }

        visibility = execute("render_menu_visibility", payload)
        visible_items = visibility.get("visibleItems", []) if isinstance(visibility, dict) else []

        print()
        print(f"== {menu.get('title') or menu.get('name') or resolved_ref} ==")
        _print_header(visibility.get("header") if isinstance(visibility, dict) else None)
        print()

        for item in visible_items:
            key = str(item.get("key", "")).strip()
            label = str(item.get("label", "")).strip() or str(item.get("name", "")).strip()
            print(f"{key}: {label}")

        if history:
            print("b: Back")
        print("q: Quit")

        choice = _read_line("Select option: ")
        if choice.lower() == "q":
            _save_persisted_search_params(paths, state.get("searchParams", {}))
            return 0
        if choice.lower() == "b" and history:
            current_menu_ref = history.pop()
            continue

        selected = None
        for item in visible_items:
            if str(item.get("key", "")).strip() == choice:
                selected = item
                break

        if not selected:
            print("Invalid selection.")
            continue

        capability = str(selected.get("capability", "")).strip()
        submenu_ref = selected.get("submenu_ref")

        if capability == "prismata.universe.capability.app-quit":
            _save_persisted_search_params(paths, state.get("searchParams", {}))
            return 0

        if isinstance(submenu_ref, str) and submenu_ref.strip():
            history.append(current_menu_ref)
            current_menu_ref = submenu_ref.strip()
            continue

        if current_menu_ref == "prismata.universe.menu.find.parameters":
            if _handle_find_parameter_capability(state, selected):
                continue

        if _route_capability(state, paths, selected):
            _read_line("Press Enter to continue...")
            continue

        print(f"Capability routed: {capability}")
        print("This Python frontend currently handles navigation and visibility-driven menu rendering.")
        _read_line("Press Enter to continue...")


if __name__ == "__main__":
    raise SystemExit(run())
