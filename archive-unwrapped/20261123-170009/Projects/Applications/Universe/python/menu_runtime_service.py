"""Python-first menu runtime service for the canonical Universe runtime.

This service determines which items and panes are visible for a given menu,
selection state, and runtime state. It is intentionally deterministic and keeps
TypeScript behaviour minimal by deferring visibility evaluation to Python.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List


def _evaluate_condition(
    condition: str | None,
    runtime_state: Dict[str, Any],
    selection_state: Dict[str, Any],
    compatibility: Dict[str, Any],
) -> bool:
    if not condition:
        return True

    bootstrap_mode = bool(runtime_state.get("bootstrapMode", False))
    runtime_mode = str(runtime_state.get("tuilkitRuntimeMode", ""))
    tuilkit_ingested = bool(runtime_state.get("tuilkitIngested", False))
    tuilkit_ready = runtime_mode == "tuilkit" and tuilkit_ingested

    if condition == "bootstrap_mode":
        return bootstrap_mode
    if condition == "initialized":
        return not bootstrap_mode
    if condition == "vile_ingested":
        return tuilkit_ready
    if condition == "vile_not_ingested":
        return not tuilkit_ready
    if condition == "initialized_and_vile_ingested":
        return (not bootstrap_mode) and tuilkit_ready
    if condition == "initialized_and_vile_not_ingested":
        return (not bootstrap_mode) and (not tuilkit_ready)

    if condition == "single_file_selected":
        return str(selection_state.get("selectionType", "")) == "single"
    if condition == "reference_object_selected":
        return bool(selection_state.get("referenceObjectSelected", False))
    if condition == "heterogeneous_selection":
        return str(selection_state.get("selectionType", "")) == "heterogeneous"
    if condition == "homogeneous_selection":
        return str(selection_state.get("selectionType", "")) == "homogeneous"
    if condition == "semantic_compatible":
        return bool(compatibility.get("semantic_compatible", False))
    if condition == "version_compatible":
        return bool(compatibility.get("version_compatible", False))
    if condition == "type_compatible":
        return bool(compatibility.get("type_compatible", False))

    return True


def _compute_visible_panes(
    selection_count: int,
    compatibility: Dict[str, Any],
    available_pane_ids: Iterable[str] | None,
) -> List[str]:
    panes: List[str] = []
    available = set(str(pane) for pane in available_pane_ids) if available_pane_ids else None

    def include(pane_id: str) -> None:
        if available is None or pane_id in available:
            panes.append(pane_id)

    include("results_list")
    include("preview")

    if selection_count >= 1 and bool(compatibility.get("version_compatible", False)):
        include("version_carousel")

    if selection_count >= 2 and bool(compatibility.get("semantic_compatible", False)):
        include("diff_panel")

    return panes


def _render_search_params_header(runtime_state: Dict[str, Any]) -> str:
    search_params = runtime_state.get("searchParams", {}) if isinstance(runtime_state, dict) else {}
    if not isinstance(search_params, dict) or not search_params:
        return "Search Parameters: (none configured)"

    folders = search_params.get("folders", [])
    file_types = search_params.get("fileTypes", [])
    queries = search_params.get("queries", [])
    tags = search_params.get("tags", [])
    canonical_only = bool(search_params.get("canonicalOnly", False))
    recursive = bool(search_params.get("recursive", True))

    folder_text = ", ".join(str(v) for v in folders) if isinstance(folders, list) and folders else "(default)"
    file_type_text = ", ".join(str(v) for v in file_types) if isinstance(file_types, list) and file_types else "(all)"
    query_text = ", ".join(str(v) for v in queries) if isinstance(queries, list) and queries else "(none)"
    tag_text = ", ".join(str(v) for v in tags) if isinstance(tags, list) and tags else "(none)"

    lines: List[str] = []
    lines.append(f"folders:      {folder_text}")
    lines.append(f"file types:   {file_type_text}")
    lines.append(f"queries:      {query_text}")
    lines.append(f"tags:         {tag_text}")
    lines.append(f"canonical:    {'yes' if canonical_only else 'no'}   recursive: {'yes' if recursive else 'no'}")
    return "\n".join(lines)


def _render_settings_features_header(runtime_state: Dict[str, Any]) -> str:
    settings = runtime_state.get("settings", {}) if isinstance(runtime_state, dict) else {}
    features = settings.get("features", {}) if isinstance(settings, dict) else {}

    auto_archive = "ON" if bool(features.get("autoArchive", False)) else "OFF"
    auto_versioning = "ON" if bool(features.get("autoVersioning", False)) else "OFF"

    lines: List[str] = []
    lines.append(f"Auto-Archive: {auto_archive}")
    lines.append(f"Auto-Versioning: {auto_versioning}")
    return "\n".join(lines)


def _as_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _render_search_location_header(runtime_state: Dict[str, Any], payload: Dict[str, Any]) -> str:
    paths_payload = payload.get("paths", {}) if isinstance(payload, dict) else {}
    workspace_default = str(paths_payload.get("workspaceRoot", "")) if isinstance(paths_payload, dict) else ""

    settings = runtime_state.get("settings", {}) if isinstance(runtime_state, dict) else {}
    settings_paths = settings.get("paths", {}) if isinstance(settings, dict) else {}
    search_params = runtime_state.get("searchParams", {}) if isinstance(runtime_state, dict) else {}

    workspace = str(settings_paths.get("workspace_root", workspace_default))
    configured_project_scope = _as_string_list(settings_paths.get("project_scope", []))
    runtime_projects = _as_string_list(search_params.get("projects", []))

    project_scope = list(dict.fromkeys([*runtime_projects, *configured_project_scope]))
    tag_scope = str(
        settings_paths.get(
            "tag_scope_file",
            ", ".join(_as_string_list(search_params.get("tags", []))),
        )
    )
    canonical = str(settings_paths.get("canonical_folder", ""))

    lines: List[str] = []
    lines.append(f"Workspace Root: {workspace or '(not set)'}")
    lines.append("Search Path(s):")
    if project_scope:
        for item in project_scope:
            lines.append(f"  - {item}")
    else:
        lines.append("  (not set)")
    lines.append(f"Tag Scope: {tag_scope or '(not set)'}")
    lines.append(f"Canonical Registry: {canonical or '(not set)'}")
    return "\n".join(lines)


def _resolve_shared_ui_config_files(prismata_root: str) -> Dict[str, str | None]:
    if not prismata_root:
        return {"coloursJson": None, "borderPatternsJson": None}

    root_path = Path(prismata_root)
    candidates = [
        root_path / ".workspace" / ".projects_config" / "GLOBAL_SHARED.d",
        root_path.parent / "tUilKit" / ".workspace" / ".projects_config" / "GLOBAL_SHARED.d",
    ]

    config_dir: Path | None = None
    for candidate in candidates:
        if candidate.exists():
            config_dir = candidate
            break

    if config_dir is None:
        return {"coloursJson": None, "borderPatternsJson": None}

    colours = config_dir / "COLOURS.json"
    border = config_dir / "BORDER_PATTERNS.json"

    return {
        "coloursJson": str(colours) if colours.exists() else None,
        "borderPatternsJson": str(border) if border.exists() else None,
    }


def _render_runtime_state_header(runtime_state: Dict[str, Any], payload: Dict[str, Any]) -> str:
    paths = payload.get("paths", {}) if isinstance(payload, dict) else {}
    prismata_root = str(payload.get("prismataRoot", "")) if isinstance(payload, dict) else ""

    state_dir = str(paths.get("stateDir", "")) if isinstance(paths, dict) else ""
    initialized_flag = str(paths.get("initializedFlagPath", "")) if isinstance(paths, dict) else ""
    settings_path = str(Path(state_dir) / "settings.json") if state_dir else ""

    shared = _resolve_shared_ui_config_files(prismata_root)
    colours = shared.get("coloursJson")
    border = shared.get("borderPatternsJson")

    lines: List[str] = []

    settings_exists = bool(settings_path and Path(settings_path).exists())
    lines.append(
        f"settings.json: {'✓' if settings_exists else '✗'}"
        + ("" if settings_exists else (f"  ({settings_path})" if settings_path else ""))
    )

    initialized_exists = bool(initialized_flag and Path(initialized_flag).exists())
    lines.append(
        f"initialized.flag: {'✓' if initialized_exists else '✗'}"
        + ("" if initialized_exists else (f"  ({initialized_flag})" if initialized_flag else ""))
    )

    colours_exists = bool(colours and Path(str(colours)).exists())
    lines.append(
        f"COLOURS.json: {'✓' if colours_exists else '✗'}"
        + ("" if colours_exists else (f"  ({colours})" if colours else ""))
    )

    border_exists = bool(border and Path(str(border)).exists())
    lines.append(
        f"BORDER_PATTERNS.json: {'✓' if border_exists else '✗'}"
        + ("" if border_exists else (f"  ({border})" if border else ""))
    )

    return "\n".join(lines)


def _render_header(menu: Dict[str, Any], runtime_state: Dict[str, Any], payload: Dict[str, Any]) -> str | None:
    header = menu.get("header", {}) if isinstance(menu, dict) else {}
    if not isinstance(header, dict):
        return None

    header_type = str(header.get("type", "")).strip()
    if header_type == "search_params":
        return _render_search_params_header(runtime_state)
    if header_type == "settings_features":
        return _render_settings_features_header(runtime_state)
    if header_type == "runtime_state":
        return _render_runtime_state_header(runtime_state, payload)
    if header_type == "search_location_state":
        return _render_search_location_header(runtime_state, payload)

    return None


def render_menu_visibility(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return visible menu items using Python runtime conditions."""
    menu = payload.get("menu", {}) if isinstance(payload, dict) else {}
    items = menu.get("items", []) if isinstance(menu, dict) else []

    selected_objects = payload.get("selectedObjects", []) if isinstance(payload, dict) else []
    compat_payload = payload.get("compatibility", {}) if isinstance(payload, dict) else {}
    selection_payload = payload.get("selectionState", {}) if isinstance(payload, dict) else {}
    available_pane_ids = payload.get("availablePaneIds", []) if isinstance(payload, dict) else []

    selection_count = len(selected_objects) if isinstance(selected_objects, list) else 0

    selection_state = {
        "selectionType": str(selection_payload.get("selectionType", "")),
        "referenceObjectSelected": bool(selection_payload.get("referenceObjectSelected", False)),
    }

    compatibility = {
        "semantic_compatible": bool(compat_payload.get("semantic_compatible", selection_count >= 2)),
        "version_compatible": bool(compat_payload.get("version_compatible", selection_count >= 1)),
        "type_compatible": bool(compat_payload.get("type_compatible", selection_count >= 1)),
    }

    visible_items: List[Dict[str, Any]] = []
    active_capabilities: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        condition = item.get("visibility_condition")
        if _evaluate_condition(condition, payload.get("runtimeState", {}), selection_state, compatibility):
            visible_items.append(item)
            capability = item.get("capability")
            if isinstance(capability, str) and capability.strip():
                active_capabilities.append(capability.strip())

    visible_panes = _compute_visible_panes(selection_count, compatibility, available_pane_ids)
    header = _render_header(menu, payload.get("runtimeState", {}), payload)

    return {
        "visibleItems": visible_items,
        "visibleCount": len(visible_items),
        "visiblePanes": visible_panes,
        "activeCapabilities": active_capabilities,
        "selectionState": selection_state,
        "compatibility": compatibility,
        "selectionCount": selection_count,
        "header": header,
        "runtimeMode": payload.get("runtimeState", {}).get("tuilkitRuntimeMode"),
    }
