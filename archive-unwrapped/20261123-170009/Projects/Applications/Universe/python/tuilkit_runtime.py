"""Canonical tUilKit adapter for the Universe runtime.

This runtime supplies the same fallback and capability metadata used by the
Universe and Universe2 code paths while avoiding a dependency on the older
Universe2 module layout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from Projects.Tooling.primitives.python.tuilkit_fallbacks import (
    NullConfigLoader,
    NullLogger,
    NullMenuHandler,
    bootstrap_tuilkit_factories,
    resolve_prismata_root,
    runtime_fallback_status,
)


_tuilkit_src = Path(__file__).resolve().parents[5] / "tUilKit" / "src"
if _tuilkit_src.exists() and str(_tuilkit_src) not in sys.path:
    sys.path.insert(0, str(_tuilkit_src))


bootstrap_tuilkit_factories()

HAS_TUILKIT = True
_IMPORT_ERROR = ""

try:
    from tUilKit import (
        get_cli_menu_handler,
        get_colour_manager,
        get_config_loader,
        get_logger,
    )
except Exception as exc:  # pragma: no cover - fallback path
    HAS_TUILKIT = False
    _IMPORT_ERROR = str(exc)

    def get_cli_menu_handler() -> NullMenuHandler:  # type: ignore[override]
        return NullMenuHandler()

    def get_colour_manager() -> Dict[str, Any]:  # type: ignore[override]
        return {}

    def get_config_loader() -> NullConfigLoader:  # type: ignore[override]
        return NullConfigLoader()

    def get_logger() -> NullLogger:  # type: ignore[override]
        return NullLogger()


class UniverseTuilKitRuntime:
    """Adapter wrapper used by the canonical Universe runtime."""

    def __init__(self, prismata_root: Optional[Path | str] = None):
        self.prismata_root = Path(prismata_root).resolve() if prismata_root else resolve_prismata_root()
        self._fallback_reason = ""
        self.logger = get_logger()
        self.config_loader = get_config_loader()
        self.colour_manager = get_colour_manager()
        self.menu_handler = get_cli_menu_handler()

        if not HAS_TUILKIT:
            self._fallback_reason = _IMPORT_ERROR or "tUilKit import failed"

    def _registry_file(self) -> Path:
        return self.prismata_root / ".workspace" / "universe" / "registry" / "registry.jsonl"

    def detect_ingested(self) -> bool:
        reg_file = self._registry_file()
        if not reg_file.exists():
            return False

        try:
            for line in reg_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("udi") == "module.tuilkit":
                    return True
        except Exception:
            return False

        return False

    def _render_with_fallback(self, title: str, options: Iterable[str], default: Optional[int]) -> List[str]:
        return NullMenuHandler().render_lines(title, options, default)

    def _render_with_handler(self, title: str, options: Iterable[str], default: Optional[int]) -> List[str]:
        labels = [str(option) for option in options]
        try:
            rendered = self.menu_handler.show_numbered_menu(title, labels, default)
            if isinstance(rendered, list):
                return [str(line) for line in rendered]
        except Exception:
            pass
        return self._render_with_fallback(title, labels, default)

    def _runtime_mode(self, ingested: bool) -> str:
        if not HAS_TUILKIT:
            return "fallback-unavailable"
        if not ingested:
            return "fallback-not-ingested"
        return "tuilkit"

    def status(self, *, ingested: Optional[bool] = None) -> Dict[str, Any]:
        effective_ingested = self.detect_ingested() if ingested is None else ingested
        mode = self._runtime_mode(effective_ingested)

        if mode.startswith("fallback"):
            reason = self._fallback_reason if not HAS_TUILKIT else "tUilKit not ingested yet"
            status = runtime_fallback_status(self.prismata_root, reason)
            status["ingested"] = effective_ingested
            status["mode"] = mode
            return status

        return {
            "runtime": "tUilKit",
            "package": "tUilKit",
            "prismata_root": str(self.prismata_root),
            "logger_ready": self.logger is not None,
            "menu_ready": self.menu_handler is not None,
            "ingested": effective_ingested,
            "ingest_ready": effective_ingested,
            "fallback": False,
            "mode": mode,
        }

    def render_menu(self, title: str, options: Iterable[str], default: Optional[int] = None) -> List[str]:
        if self._runtime_mode(self.detect_ingested()) != "tuilkit":
            return self._render_with_fallback(title, options, default)
        return self._render_with_handler(title, options, default)

    def generate_capability_manifest(self) -> Dict[str, Any]:
        ingested = self.detect_ingested()
        mode = self._runtime_mode(ingested)
        return {
            "metadata": {
                "udi": "module.tuilkit.capability.manifest",
                "name": "tUilKit Capability Manifest",
                "version": "0.4.1",
                "kind": "capability-manifest",
                "description": "Defines Prismata's shared tUilKit runtime capabilities for terminal UI and logging.",
                "package_name": "tUilKit",
                "runtimeMode": mode,
                "ingested": ingested,
            },
            "kind": "capability-manifest",
            "capabilities": [
                {
                    "udi": "module.tuilkit.capability.menu.render",
                    "name": "Render Menu",
                    "kind": "capability",
                    "version": "0.4.1",
                    "action": "render",
                    "description": "Renders menu output using the tUilKit CLI menu handler.",
                    "visibilityMode": "static",
                    "enableMode": "enabled",
                },
                {
                    "udi": "module.tuilkit.capability.logger",
                    "name": "Logger",
                    "kind": "capability",
                    "version": "0.4.1",
                    "action": "use",
                    "description": "Use the shared logger for TUI diagnostics and user-facing output.",
                    "visibilityMode": "static",
                    "enableMode": "enabled",
                },
                {
                    "udi": "module.tuilkit.capability.runtime.ingest",
                    "name": "Runtime Ingest",
                    "kind": "capability",
                    "version": "0.4.1",
                    "action": "ingest",
                    "description": "Universe can ingest the tUilKit runtime package and record its capability contract.",
                    "visibilityMode": "static",
                    "enableMode": "enabled",
                },
            ],
        }


__all__ = ["UniverseTuilKitRuntime", "_resolve_prismata_root"]
