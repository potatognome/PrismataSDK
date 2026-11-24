"""
PrismataLabs â€” preview_common

Shared registry loaders for preview_object and validate_preview.
"""

from __future__ import annotations

from pathlib import Path
import yaml
from typing import Dict, Any


def _load_registry_entries(root: Path) -> list[Dict[str, Any]]:
    """Load registry entries from canonical registry files.

    Supports both:
    - Directory of yaml entries (e.g. Meta/registry/colour-role.d/*.yaml)
    - Single yaml file with entries[] (used in examples/shared)
    """
    entries: list[Dict[str, Any]] = []
    if not root.exists():
        return entries

    files: list[Path] = []
    if root.is_file() and root.suffix.lower() in {".yaml", ".yml"}:
        files = [root]
    elif root.is_dir():
        files = sorted(root.glob("*.yaml")) + sorted(root.glob("*.yml"))

    for file in files:
        try:
            data = yaml.safe_load(file.read_text(encoding="utf-8"))
        except Exception:
            continue

        if isinstance(data, dict):
            data_entries = data.get("entries")
            if isinstance(data_entries, list):
                for entry in data_entries:
                    if isinstance(entry, dict):
                        entries.append(entry)
                continue
            if "udi" in data:
                entries.append(data)

    return entries


def _build_udi_index(entries: list[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build a strict UDI index for registry entries."""
    registry: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        udi = entry.get("udi")
        if isinstance(udi, str) and udi.strip():
            registry[udi.strip()] = entry
    return registry


def load_colour_scheme_registry(root: Path) -> Dict[str, Dict[str, Any]]:
    return _build_udi_index(_load_registry_entries(root))


def load_colour_role_registry(root: Path) -> Dict[str, Dict[str, Any]]:
    return _build_udi_index(_load_registry_entries(root))


def load_ui_framework_registry(root: Path) -> Dict[str, Dict[str, Any]]:
    return _build_udi_index(_load_registry_entries(root))

