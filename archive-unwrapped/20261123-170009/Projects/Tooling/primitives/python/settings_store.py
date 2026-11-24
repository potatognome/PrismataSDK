"""Shared settings persistence helpers for Prismata applications.

This module centralizes small, safe settings-file operations so applications
can keep app-specific defaults/shape logic while sharing file I/O behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml

from Projects.Tooling.primitives.python.path_helper import app_root_for


def detect_file_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    return "json"


def _read_mapping(path: Path, file_format: str) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if file_format == "yaml":
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)

    if isinstance(data, dict):
        return data
    return {}


def _write_mapping(path: Path, data: Dict[str, Any], file_format: str) -> None:
    if file_format == "yaml":
        payload = yaml.safe_dump(data, sort_keys=False)
    else:
        payload = json.dumps(data, indent=2) + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    tmp_path.replace(path)


def load_mapping(
    path: Path,
    *,
    defaults: Optional[Dict[str, Any]] = None,
    file_format: Optional[str] = None,
    legacy_paths: Optional[Iterable[Path]] = None,
) -> Dict[str, Any]:
    default_data = dict(defaults or {})
    selected: Optional[Path] = None

    if path.exists():
        selected = path
    elif legacy_paths:
        for legacy in legacy_paths:
            if legacy.exists():
                selected = legacy
                break

    if selected is None:
        return default_data

    resolved_format = file_format or detect_file_format(selected)
    try:
        loaded = _read_mapping(selected, resolved_format)
    except Exception:
        return default_data

    merged = dict(default_data)
    merged.update(loaded)
    return merged


def save_mapping(path: Path, data: Dict[str, Any], *, file_format: Optional[str] = None) -> None:
    resolved_format = file_format or detect_file_format(path)
    _write_mapping(path, dict(data), resolved_format)


def resolve_app_root(prismata_root: Path, app_name: str) -> Path:
    return app_root_for(prismata_root, app_name)
