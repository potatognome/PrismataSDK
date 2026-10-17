from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .cmf import CMFLoader, PSOBuilder


@dataclass(slots=True)
class RegistryEntry:
    """A canonical registry entry for a type-specific object definition."""

    name: str
    kind: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ObjectRegistry:
    """Minimal registry for pane, menu, chroma, border, and framework objects."""

    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}

    def register(self, entry: RegistryEntry) -> RegistryEntry:
        self._entries[entry.name] = entry
        return entry

    def resolve(self, name: str) -> RegistryEntry:
        try:
            return self._entries[name]
        except KeyError as exc:
            raise KeyError(f"Unknown object registry entry: {name}") from exc

    def list_entries(self) -> list[RegistryEntry]:
        return list(self._entries.values())


class RegistryLoader:
    """Registers object definitions and builds PSO runtime objects from CMF payloads."""

    @staticmethod
    def load_registry(registry_data: dict[str, Any] | list[dict[str, Any]]) -> ObjectRegistry:
        registry = ObjectRegistry()

        if isinstance(registry_data, dict):
            items = registry_data.items()
        else:
            items = []
            for item in registry_data:
                if not isinstance(item, dict):
                    raise TypeError("Registry entries must be dictionaries")
                raw_name = item.get("name") or item.get("id")
                if raw_name in (None, ""):
                    raise ValueError("Registry entry requires a name or id")
                name = str(raw_name)
                items.append((name, item))

        for name, entry_data in items:
            if isinstance(entry_data, RegistryEntry):
                registry.register(entry_data)
                continue

            if not isinstance(entry_data, dict):
                raise TypeError(f"Registry entry for {name!r} must be a dictionary or RegistryEntry")

            kind = str(entry_data.get("kind", "unknown"))
            source = str(entry_data.get("source", name))
            metadata = dict(entry_data.get("metadata", {}))
            entry = RegistryEntry(name=name, kind=kind, source=source, metadata=metadata)
            registry.register(entry)

        return registry

    @staticmethod
    def build_pso(name: str, payload: dict[str, Any], registry: ObjectRegistry | None = None) -> dict[str, Any]:
        if registry is not None and name not in registry._entries:
            raise KeyError(f"No object registry entry found for {name!r}")

        envelope = CMFLoader.load(payload)
        return PSOBuilder.build(envelope)
