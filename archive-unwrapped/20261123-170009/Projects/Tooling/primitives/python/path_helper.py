"""
Prismata Tooling â€” Path Helper Module
Shared path discovery utilities for Universe2, PrismataLabs, and PrismCommander.

Features:
- Native file/folder selection (via dialog_helpers)
- Schema-aware discovery of colour schemes, border patterns, ui-frameworks, panes
- Project menu discovery
- Manifest discovery
- Registry discovery (corrected to handle .d directories)
- Cross-platform safe
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Native dialog helpers
from .dialog_helpers import pick_native_path, pick_native_save_path


# ---------------------------------------------------------------------------
# Root Discovery
# ---------------------------------------------------------------------------

def find_prismata_root(start: Optional[Path] = None) -> Path:
    """
    Walk upward from the given path (or CWD) until a Prismata root is found.
    A Prismata root contains a 'Meta' folder and a 'Projects' folder.
    """
    current = Path(start or Path.cwd()).resolve()

    while True:
        meta = current / "Meta"
        projects = current / "Projects"

        if meta.exists() and projects.exists():
            return current

        if current.parent == current:
            # Reached filesystem root
            return Path.cwd()

        current = current.parent


def bootstrap_prismata_root(start: Optional[Path] = None) -> Path:
    """Resolve the Prismata root and ensure it is importable from the current process."""
    root = find_prismata_root(start)
    root_str = str(root)
    if root_str not in os.sys.path:
        os.sys.path.insert(0, root_str)
    return root


def app_root_for(prismata_root: Path | str, app_name: str) -> Path:
    """Return the canonical application root for a Prismata app."""
    root = Path(prismata_root)
    return root / "Projects" / "Applications" / app_name


# ---------------------------------------------------------------------------
# Registry Discovery (Corrected)
# ---------------------------------------------------------------------------

def registry_root(prismata_root: Optional[Path] = None) -> Path:
    root = prismata_root or find_prismata_root()
    return root / "Meta" / "registry"


def list_registry_entries(kind: str, prismata_root: Optional[Path] = None) -> List[Path]:
    """
    List all registry entries of a given kind.
    Registry structure:
        Meta/registry/<kind>.d/*.yaml
    Example:
        Meta/registry/colour-scheme.d/*.yaml
    """
    reg_root = registry_root(prismata_root)
    folder = reg_root / f"{kind}.d"

    if not folder.exists() or not folder.is_dir():
        return []

    # Load all YAML files inside the .d directory
    return sorted(folder.glob("*.yaml"))


def list_colour_schemes(prismata_root: Optional[Path] = None) -> List[Path]:
    return list_registry_entries("colour-scheme", prismata_root)


def list_border_patterns(prismata_root: Optional[Path] = None) -> List[Path]:
    return list_registry_entries("border-pattern", prismata_root)


def list_ui_frameworks(prismata_root: Optional[Path] = None) -> List[Path]:
    return list_registry_entries("ui-framework", prismata_root)


def list_panes(prismata_root: Optional[Path] = None) -> List[Path]:
    return list_registry_entries("pane", prismata_root)


def list_menus(prismata_root: Optional[Path] = None) -> List[Path]:
    return list_registry_entries("menu", prismata_root)


def list_menu_items(prismata_root: Optional[Path] = None) -> List[Path]:
    return list_registry_entries("menu-item", prismata_root)

# ---------------------------------------------------------------------------
# Manifest Discovery
# ---------------------------------------------------------------------------

def list_manifests(prismata_root: Optional[Path] = None) -> List[Path]:
    """
    List all manifests under Meta/domain/manifest.schemas and project manifests.
    """
    root = prismata_root or find_prismata_root()

    manifests = []

    # Canonical manifest schemas
    domain_manifests = root / "Meta" / "domain" / "manifest.schemas"
    if domain_manifests.exists():
        manifests.extend(sorted(domain_manifests.glob("*.yaml")))

    # Project manifests
    for project in (root / "Projects").glob("*"):
        cfg = project / "config"
        if cfg.exists():
            manifests.extend(sorted(cfg.glob("*.manifest.yaml")))

    return manifests


# ---------------------------------------------------------------------------
# Project Menu Discovery
# ---------------------------------------------------------------------------

def list_project_menus(prismata_root: Optional[Path] = None) -> Dict[str, List[Path]]:
    """
    Return a dict mapping project names â†’ list of menu files.
    Looks for: /Projects/<project>/config/project-menus/*.yaml
    """
    root = prismata_root or find_prismata_root()
    projects_root = root / "Projects"

    results: Dict[str, List[Path]] = {}

    for project in projects_root.glob("*"):
        menu_dir = project / "config" / "project-menus"
        if menu_dir.exists():
            results[project.name] = sorted(menu_dir.glob("*.yaml"))

    return results


# ---------------------------------------------------------------------------
# File/Folder Selection
# ---------------------------------------------------------------------------

def select_file() -> Optional[str]:
    """Native file picker."""
    return pick_native_path("file")


def select_folder() -> Optional[str]:
    """Native folder picker."""
    return pick_native_path("folder")


def select_save_file(default_filename: str = "output.yaml") -> Optional[str]:
    """Native save dialog."""
    return pick_native_save_path(default_filename)


# ---------------------------------------------------------------------------
# Preview Resource Discovery
# ---------------------------------------------------------------------------

def discover_preview_resources(prismata_root: Optional[Path] = None) -> Dict[str, List[Path]]:
    """
    Return all previewable resources:
    - colour schemes
    - border patterns
    - ui frameworks
    - panes
    - manifests
    - project menus
    - menus
    - menu-items
    """
    root = prismata_root or find_prismata_root()

    return {
        "colour_schemes": list_colour_schemes(root),
        "border_patterns": list_border_patterns(root),
        "ui_frameworks": list_ui_frameworks(root),
        "panes": list_panes(root),
        "manifests": list_manifests(root),
        "project_menus": list_project_menus(root),
        "menus": list_menus(root),
        "menu_items": list_menu_items(root),
    }


def load_registry(kind: str, prismata_root: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Load a registry directory keyed by canonical id/udi values."""
    root = registry_root(prismata_root) / f"{kind}.d"
    registry: Dict[str, Dict[str, Any]] = {}
    if not root.exists():
        return registry

    for path in sorted(root.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        entry_id = data.get("id")
        if not isinstance(entry_id, str) or not entry_id.strip():
            continue
        registry[entry_id] = data
        udi = data.get("udi")
        if isinstance(udi, str) and udi.strip():
            registry[udi] = data
    return registry


def resolve_registry_entry(registry: Dict[str, Dict[str, Any]], value: Optional[str]) -> Optional[Dict[str, Any]]:
    """Resolve a registry entry by canonical id, udi, or name."""
    if not isinstance(value, str) or not value.strip():
        return None
    entry = registry.get(value)
    if entry is not None:
        return entry
    for candidate in registry.values():
        if candidate.get("udi") == value or candidate.get("name") == value:
            return candidate
    return None

