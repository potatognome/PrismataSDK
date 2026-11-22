from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml

from core.manifests import Manifest


class CapabilityNotFoundError(LookupError):
    """Raised when a manifest references an unknown capability."""


@dataclass(slots=True)
class Capability:
    """A capability definition exposed by a module manifest."""

    name: str
    udi: str | None = None
    interfaces: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_target: str | None = None
    content: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def load_from_file(path: str | Path) -> "Capability":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("Capability file must contain a YAML mapping")

        udi = payload.get("udi")
        name = payload.get("id") or udi
        if not name:
            raise ValueError("Capability payload missing required field: udi")

        content = payload.get("content")
        if not isinstance(content, dict):
            content = {}

        return Capability(
            name=str(name),
            udi=str(udi) if udi else None,
            interfaces=list(content.get("interfaces", [])),
            dependencies=list(content.get("dependencies", [])),
            metadata=dict(payload.get("metadata", content)),
            execution_target=str(content.get("execution_target") or content.get("action") or ""),
            content=content,
        )


@dataclass(slots=True)
class CapabilityResolution:
    """Resolved capability set for a manifest."""

    manifest: Manifest
    capabilities: list[Capability] = field(default_factory=list)

    def as_pso(self) -> dict[str, Any]:
        return {
            "__pso__": True,
            "kind": "capability-resolution",
            "manifest": self.manifest.name,
            "capabilities": [
                {
                    "name": capability.name,
                    "udi": capability.udi,
                    "interfaces": capability.interfaces,
                    "dependencies": capability.dependencies,
                    "metadata": capability.metadata,
                    "execution_target": capability.execution_target,
                    "content": capability.content,
                }
                for capability in self.capabilities
            ],
        }


class CapabilityRegistry:
    """Registry for capability definitions declared by manifests."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> Capability:
        if capability.name in self._capabilities:
            raise ValueError(f"Capability already registered: {capability.name}")
        self._capabilities[capability.name] = capability
        return capability

    def resolve(self, name: str) -> Capability:
        if name in self._capabilities:
            return self._capabilities[name]
        for capability in self._capabilities.values():
            if capability.udi == name:
                return capability
        try:
            return self._capabilities[name]
        except KeyError as exc:
            raise CapabilityNotFoundError(name) from exc

    def list_capabilities(self) -> list[Capability]:
        return list(self._capabilities.values())


class CapabilityResolver:
    """Manifest-aware capability resolution helpers."""

    @staticmethod
    def resolve_manifest(manifest: Manifest, registry: CapabilityRegistry) -> CapabilityResolution:
        capabilities: list[Capability] = []
        missing: list[str] = []

        for capability_name in manifest.capabilities:
            try:
                capabilities.append(registry.resolve(capability_name))
            except CapabilityNotFoundError:
                missing.append(capability_name)

        if missing:
            raise ValueError(f"Manifest '{manifest.name}' references unknown capabilities: {', '.join(missing)}")

        return CapabilityResolution(manifest=manifest, capabilities=capabilities)
