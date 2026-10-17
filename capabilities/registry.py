from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.manifests import Manifest


@dataclass(slots=True)
class Capability:
    """A capability definition exposed by a module manifest."""

    name: str
    interfaces: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


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
                    "interfaces": capability.interfaces,
                    "dependencies": capability.dependencies,
                    "metadata": capability.metadata,
                }
                for capability in self.capabilities
            ],
        }


class CapabilityRegistry:
    """Registry for capability definitions declared by manifests."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> Capability:
        self._capabilities[capability.name] = capability
        return capability

    def resolve(self, name: str) -> Capability:
        try:
            return self._capabilities[name]
        except KeyError as exc:
            raise KeyError(f"Unknown capability: {name}") from exc

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
            except KeyError:
                missing.append(capability_name)

        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(f"Manifest {manifest.name!r} references unknown capabilities: {missing_list}")

        return CapabilityResolution(manifest=manifest, capabilities=capabilities)
