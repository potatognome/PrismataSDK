"""tUilKit runtime adapter for PrismataLabs.

This module intentionally wraps the canonical tUilKit factories and menu
helpers so the Python-first application layer can treat tUilKit as the core
UI runtime instead of hand-rolled terminal helpers.
"""
from __future__ import annotations

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


class PrismataTuilKitRuntime:
    """Thin adapter exposing the tUilKit runtime as the app's primary TUI backend."""

    def __init__(self, prismata_root: Optional[Path | str] = None):
        self.prismata_root = Path(prismata_root).resolve() if prismata_root else resolve_prismata_root()
        self._fallback_reason = ""
        self.logger = get_logger()
        self.config_loader = get_config_loader()
        self.colour_manager = get_colour_manager()
        self.menu_handler = get_cli_menu_handler()

        if not HAS_TUILKIT:
            self._fallback_reason = _IMPORT_ERROR or "tUilKit import failed"

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

    def _runtime_mode(self) -> str:
        if not HAS_TUILKIT:
            return "fallback-unavailable"
        return "tuilkit"

    def status(self) -> Dict[str, Any]:
        mode = self._runtime_mode()
        if mode.startswith("fallback"):
            status = runtime_fallback_status(
                self.prismata_root,
                self._fallback_reason or "tUilKit unavailable for PrismataLabs runtime",
            )
            status["mode"] = mode
            return status

        return {
            "runtime": "tUilKit",
            "package": "tUilKit",
            "prismata_root": str(self.prismata_root),
            "logger_ready": self.logger is not None,
            "menu_ready": self.menu_handler is not None,
            "fallback": False,
            "mode": mode,
        }

    def render_menu(self, title: str, options: Iterable[str], default: Optional[int] = None) -> List[str]:
        """Return deterministic menu lines without blocking on input.

        This keeps the adapter safe for automated preview/validation flows while
        still using tUilKit as the canonical menu runtime backend.
        """
        if self._runtime_mode() != "tuilkit":
            return self._render_with_fallback(title, options, default)
        return self._render_with_handler(title, options, default)

    def generate_capability_manifest(self) -> Dict[str, Any]:
        mode = self._runtime_mode()
        return {
            "metadata": {
                "udi": "module.tuilkit.capability.manifest",
                "name": "tUilKit Capability Manifest",
                "version": "0.4.1",
                "kind": "capability-manifest",
                "description": "Prismata-compliant runtime capabilities exposed by the Python tUilKit framework.",
                "package_name": "tUilKit",
                "runtimeMode": mode,
            },
            "kind": "capability-manifest",
            "capabilities": [
                {
                    "udi": "module.tuilkit.capability.logger",
                    "name": "Logger",
                    "kind": "capability",
                    "version": "0.4.1",
                    "action": "use",
                    "description": "Use the shared tUilKit logger for terminal output and diagnostics.",
                    "visibilityMode": "static",
                    "enableMode": "enabled",
                },
                {
                    "udi": "module.tuilkit.capability.menu.render",
                    "name": "Render Menu",
                    "kind": "capability",
                    "version": "0.4.1",
                    "action": "render",
                    "description": "Render menu entries through the canonical tUilKit CLI menu handler.",
                    "visibilityMode": "static",
                    "enableMode": "enabled",
                },
                {
                    "udi": "module.tuilkit.capability.config.loader",
                    "name": "Config Loader",
                    "kind": "capability",
                    "version": "0.4.1",
                    "action": "use",
                    "description": "Resolve shared config and workspace metadata via tUilKit config loading.",
                    "visibilityMode": "static",
                    "enableMode": "enabled",
                },
                {
                    "udi": "module.tuilkit.capability.runtime.ingest",
                    "name": "Runtime Ingest",
                    "kind": "capability",
                    "version": "0.4.1",
                    "action": "ingest",
                    "description": "Allow Universe to ingest the tUilKit runtime package as a Prismata capability source.",
                    "visibilityMode": "static",
                    "enableMode": "enabled",
                },
            ],
        }


__all__ = ["PrismataTuilKitRuntime", "_resolve_prismata_root"]

