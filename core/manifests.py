from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Manifest:
    """Canonical module manifest representation."""

    name: str
    kind: str
    version: str
    capabilities: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ManifestLoader:
    """Loads module and root manifests into runtime objects."""

    @staticmethod
    def load(payload: dict[str, Any]) -> Manifest:
        required = {"name", "kind", "version"}
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"Manifest payload missing required fields: {', '.join(missing)}")

        return Manifest(
            name=str(payload["name"]),
            kind=str(payload["kind"]),
            version=str(payload["version"]),
            capabilities=list(payload.get("capabilities", [])),
            interfaces=list(payload.get("interfaces", [])),
            metadata=dict(payload.get("metadata", {})),
        )
