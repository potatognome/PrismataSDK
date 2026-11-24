"""Shared menu loading helpers for Prismata Python frontends."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def load_yaml_mapping(path: Path) -> Dict[str, Any]:
    """Load a YAML file and always return a mapping."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(data, dict):
        return data
    return {}


def load_first_menu(path: Path) -> Dict[str, Any]:
    """Load the first menu object from a menu-list YAML file."""
    data = load_yaml_mapping(path)
    menus = data.get("menus", []) if isinstance(data, dict) else []
    if isinstance(menus, list) and menus:
        first = menus[0]
        if isinstance(first, dict):
            return first
    return {}


def load_menu_index(menu_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Index menus by top-level and metadata UDI values."""
    indexed: Dict[str, Dict[str, Any]] = {}

    for path in sorted(menu_dir.glob("*.yaml")):
        menu_obj = load_yaml_mapping(path)
        if not menu_obj:
            continue

        metadata = menu_obj.get("metadata") if isinstance(menu_obj.get("metadata"), dict) else {}
        top_udi = str(menu_obj.get("udi", "")).strip()
        meta_udi = str(metadata.get("udi", "")).strip()

        for key in [top_udi, meta_udi]:
            if key:
                indexed[key] = dict(menu_obj)

    return indexed
