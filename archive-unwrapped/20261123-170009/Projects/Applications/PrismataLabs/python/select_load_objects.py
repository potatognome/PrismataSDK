"""
PrismataLabs â€” select_load_objects capability

Allows the user to select and load previewable objects using the shared
path_helper module. This is invoked by:

    prismata.prismatalabs.capability.select-load
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional

from Projects.Tooling.primitives.python.path_helper import (
    find_prismata_root,
    discover_preview_resources,
    select_file,
    select_folder,
)

import yaml


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def select_load_objects(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns:
        {
            "selected": {
                "colour_scheme": "<path or None>",
                "border_pattern": "<path or None>",
                "object": "<path or None>"
            },
            "message": "..."
        }
    """

    prismata_root = find_prismata_root()
    resources = discover_preview_resources(prismata_root)

    # Ask user to pick a file (colour-scheme, border-pattern, pane, menu, etc.)
    picked = select_file()
    if not picked:
        return {
            "selected": payload.get("selected", {}),
            "message": "No file selected."
        }

    picked_path = Path(picked)

    # Classify based on folder location
    selected = payload.get("selected", {}).copy()

    if picked_path in resources["colour_schemes"]:
        selected["colour_scheme"] = picked
        msg = f"Loaded colour scheme: {picked}"

    elif picked_path in resources["border_patterns"]:
        selected["border_pattern"] = picked
        msg = f"Loaded border pattern: {picked}"

    else:
        # Everything else is treated as a previewable object
        selected["object"] = picked
        msg = f"Loaded object: {picked}"

    return {
        "selected": selected,
        "message": msg,
    }

