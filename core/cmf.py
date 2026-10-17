from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CMFEnvelope:
    """Canonical CMF capsule envelope used throughout PrismataSDK."""

    id: str
    udi: str
    kind: str
    version: str
    tenant: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    relations: list[str] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    content: dict[str, Any] = field(default_factory=dict)

    def to_runtime(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "udi": self.udi,
            "kind": self.kind,
            "version": self.version,
            "tenant": self.tenant,
            "metadata": self.metadata,
            "relations": self.relations,
            "validation": self.validation,
            "notes": self.notes,
            "content": self.content,
        }


class CMFLoader:
    """Loads CMF capsules from a dictionary payload."""

    @staticmethod
    def load(payload: dict[str, Any]) -> CMFEnvelope:
        required = {"id", "udi", "kind", "version"}
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"CMF payload missing required fields: {', '.join(missing)}")

        return CMFEnvelope(
            id=str(payload["id"]),
            udi=str(payload["udi"]),
            kind=str(payload["kind"]),
            version=str(payload["version"]),
            tenant=payload.get("tenant"),
            metadata=dict(payload.get("metadata", {})),
            relations=list(payload.get("relations", [])),
            validation=dict(payload.get("validation", {})),
            notes=list(payload.get("notes", [])),
            content=dict(payload.get("content", {})),
        )


class PSOBuilder:
    """Builds runtime PSO objects from CMF envelopes."""

    @staticmethod
    def build(envelope: CMFEnvelope) -> dict[str, Any]:
        runtime = envelope.to_runtime()
        runtime["__pso__"] = True
        return runtime
