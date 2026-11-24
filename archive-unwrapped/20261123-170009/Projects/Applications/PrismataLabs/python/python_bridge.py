"""
PrismataLabs Python Bridge
Dispatches preview and validation commands from TypeScript.
"""

from __future__ import annotations

from typing import Any, Dict

from .tuilkit_runtime import PrismataTuilKitRuntime

# Capability modules
from .preview_object import preview_object
from .validate_preview import validate_preview
from .select_load_objects import select_load_objects
from .configure_default_folders import configure_default_folders


_runtime = PrismataTuilKitRuntime()


# ---------------------------------------------------------------------------
# Command Dispatcher
# ---------------------------------------------------------------------------

def execute(command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch a command from TypeScript to the appropriate Python capability.

    Args:
        command: Name of the capability (string)
        payload: Arbitrary dict passed from TS

    Returns:
        Dict containing the capability result
    """

    # Preview selected object
    if command == "preview_object":
        return preview_object(payload)

    # Validate selected object
    if command == "validate_preview":
        return validate_preview(payload)

    # Select & load objects (colour-schemes, border-patterns, panes, menus, etc.)
    if command == "select_load_objects":
        return select_load_objects(payload)

    # Configure default folder paths
    if command == "configure_default_folders":
        return configure_default_folders(payload)

    if command == "tuilkit_status":
        return _runtime.status()

    if command == "tuilkit_capability_manifest":
        return _runtime.generate_capability_manifest()

    # Unknown command
    return {
        "error": f"Unknown command: {command}",
        "payload": payload,
    }

