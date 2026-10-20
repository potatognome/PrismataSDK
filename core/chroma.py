from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ChromaSpec:
    name: str
    palette: dict[str, str]


class ChromaLoader:
    """Minimal chroma loader / applier stub for migration work.

    This file provides a small API to begin integrating chromascheme
    application into the preview/pane runtime. It intentionally keeps
    behaviour minimal so tests and higher-level integration can iterate.
    """

    @staticmethod
    def load(payload: dict[str, Any]) -> ChromaSpec:
        name = str(payload.get("id", payload.get("name", "default")))
        palette = dict(payload.get("palette", {}))
        return ChromaSpec(name=name, palette=palette)

    @staticmethod
    def apply_to_runtime(runtime: dict[str, Any], chroma: ChromaSpec) -> dict[str, Any]:
        runtime = dict(runtime)
        runtime.setdefault("_chroma_applied", {})
        runtime["_chroma_applied"][chroma.name] = chroma.palette
        return runtime
