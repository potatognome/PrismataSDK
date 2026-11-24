"""Fallback helpers for Prismata when tUilKit is unavailable or not yet ingested."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def resolve_prismata_root(start: Optional[Path] = None) -> Path:
    """Resolve the workspace root that contains both Meta and Projects."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "Meta").exists() and (candidate / "Projects").exists():
            return candidate
    return current


def bootstrap_tuilkit_factories() -> None:
    """Wire the local tUilKit config into the shared factories if present."""
    try:
        from tUilKit import factories as tuilkit_factories
        from tUilKit.utils.config import ConfigLoader

        config_path = Path(__file__).resolve().parents[5] / "tUilKit" / "config" / "tUilKit_CONFIG.json"
        if config_path.exists():
            tuilkit_factories._config_loader = ConfigLoader(config_path=str(config_path))
            tuilkit_factories._colour_manager = None
            tuilkit_factories._logger = None
    except Exception:
        pass


class NullLogger:
    """Minimal logger-compatible object used during bootstrap fallback."""

    def colour_log(self, *parts: Any, **_: Any) -> None:
        text = " ".join(str(part) for part in parts if not str(part).startswith("!"))
        if text:
            print(text)

    def log_exception(self, *parts: Any, **_: Any) -> None:
        text = " ".join(str(part) for part in parts)
        if text:
            print(text)


class NullConfigLoader:
    """Configuration fallback that mirrors the minimal API the apps consume."""

    def __init__(self, prismata_root: Optional[Path] = None):
        self._prismata_root = Path(prismata_root) if prismata_root else Path.cwd()
        self.global_config: Dict[str, Any] = {
            "ROOTS": {
                "WORKSPACE": str(self._prismata_root),
                "PROJECT": str(self._prismata_root),
            },
            "PATHS": {
                "GLOBAL_SHARED.d": ".workspace/.projects_config/GLOBAL_SHARED.d/",
            },
        }

    def load_colour_config(self) -> Dict[str, Any]:
        return {}


class NullMenuHandler:
    """Deterministic renderer used when interactive tUilKit handlers are unavailable."""

    def render_lines(self, title: str, options: Iterable[str], default: Optional[int] = None) -> List[str]:
        labels = [str(option) for option in options]
        lines: List[str] = [title, "=" * max(len(title), 12)]
        for index, item in enumerate(labels, start=1):
            lines.append(f"{index}. {item}")
        if default is not None:
            lines.append(f"default={default}")
        return lines

    def show_numbered_menu(self, title: str, options: Iterable[str], default: Optional[int] = None) -> List[str]:
        return self.render_lines(title, options, default)


def runtime_fallback_status(prismata_root: Path, reason: str) -> Dict[str, Any]:
    return {
        "runtime": "prismata-fallback",
        "package": "fallback",
        "prismata_root": str(prismata_root),
        "logger_ready": True,
        "menu_ready": True,
        "fallback": True,
        "reason": reason,
    }
