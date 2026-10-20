from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class BorderSpec:
    name: str
    style: str


class BorderLoader:
    """Minimal border loader stub to start border-pattern integration.

    Provides a simple loader that captures border metadata; the preview
    integration will expand on rendering semantics later in the migration.
    """

    @staticmethod
    def load(payload: dict[str, Any]) -> BorderSpec:
        name = str(payload.get("id", payload.get("name", "default")))
        style = str(payload.get("style", payload.get("pattern", "single-line")))
        return BorderSpec(name=name, style=style)

    @staticmethod
    def apply_to_runtime(runtime: dict[str, Any], border: BorderSpec) -> dict[str, Any]:
        runtime = dict(runtime)
        runtime.setdefault("_border_applied", {})
        runtime["_border_applied"][border.name] = border.style
        return runtime
