"""
PrismataLabs â€” configure_default_folders capability

Allows the user to configure default search paths for previewable objects.
Invoked by:

    prismata.prismatalabs.capability.default-folders
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from Projects.Tooling.primitives.python.path_helper import (
    select_folder,
    find_prismata_root,
)
from Projects.Tooling.primitives.python.settings_store import (
    load_mapping,
    resolve_app_root,
    save_mapping,
)


SETTINGS_FILE = "labs.settings.yaml"
LEGACY_SETTINGS_FILE = "labs2.settings.yaml"


def _resolve_app_root(payload: Dict[str, Any]) -> Path:
    app_root = payload.get("appRoot") if isinstance(payload, dict) else None
    if isinstance(app_root, str) and app_root.strip():
        return Path(app_root)

    prismata_root = find_prismata_root()
    return resolve_app_root(prismata_root, "PrismataLabs")


def load_settings(root: Path) -> Dict[str, Any]:
    path = root / "config" / SETTINGS_FILE
    legacy_path = root / "config" / LEGACY_SETTINGS_FILE
    return load_mapping(path, defaults={}, file_format="yaml", legacy_paths=[legacy_path])


def save_settings(root: Path, settings: Dict[str, Any]):
    path = root / "config" / SETTINGS_FILE
    save_mapping(path, settings, file_format="yaml")


def configure_default_folders(payload: Dict[str, Any]) -> Dict[str, Any]:
    app_root = _resolve_app_root(payload)
    settings = load_settings(app_root)

    payload_selected = payload.get("selectedFolder") if isinstance(payload, dict) else None
    picked = str(payload_selected) if isinstance(payload_selected, str) and payload_selected.strip() else select_folder()
    if not picked:
        return {
            "message": "No folder selected.",
            "settings": settings,
        }

    settings["default_folder"] = picked
    save_settings(app_root, settings)

    return {
        "message": f"Default folder set to: {picked}",
        "settings": settings,
    }

