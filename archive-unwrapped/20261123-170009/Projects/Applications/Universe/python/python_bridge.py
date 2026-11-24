"""Canonical Python bridge for the Universe runtime.

TypeScript shells stay thin while the actual runtime logic lives in Python.
"""

from __future__ import annotations

from .tuilkit_runtime import UniverseTuilKitRuntime
from .menu_runtime_service import render_menu_visibility


_runtime = UniverseTuilKitRuntime()


def _requested_ingested(payload: dict) -> bool:
    if isinstance(payload, dict):
        runtime_state = payload.get("runtimeState", {})
        if isinstance(runtime_state, dict):
            if "vileIngested" in runtime_state:
                return bool(runtime_state.get("vileIngested"))
            if "tuilkitIngested" in runtime_state:
                return bool(runtime_state.get("tuilkitIngested"))
    return _runtime.detect_ingested()


def execute(command: str, payload: dict):
    if command == "tuilkit_status":
        return _runtime.status(ingested=_requested_ingested(payload or {}))

    if command == "tuilkit_capability_manifest":
        return _runtime.generate_capability_manifest()

    if command == "ingest_tuilkit_package":
        ingested = _requested_ingested(payload or {})
        return {
            "command": command,
            "payload": payload,
            "manifest": _runtime.generate_capability_manifest(),
            "status": "ingested" if ingested else "pending-bootstrap",
            "runtime": _runtime.status(ingested=ingested),
        }

    if command == "render_menu_visibility":
        return render_menu_visibility(payload or {})

    return {"command": command, "payload": payload}
