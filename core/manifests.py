from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass(slots=True)
class Manifest:
    """Canonical module manifest representation."""

    name: str
    kind: str
    version: str
    udi: str | None = None
    capabilities: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    content: dict[str, Any] = field(default_factory=dict)


class ManifestLoader:
    """Loads module and root manifests into runtime objects."""

    @staticmethod
    def load(payload: dict[str, Any]) -> Manifest:
        content = payload.get("content")
        if not isinstance(content, dict):
            content = {}

        required = {"kind", "version"}
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"Manifest payload missing required fields: {', '.join(missing)}")

        name = payload.get("name")
        if name is None:
            name = payload.get("id") or payload.get("udi") or content.get("module_udi")
        if name is None:
            raise ValueError("Manifest payload missing required field: name")

        raw_capabilities = payload.get("capabilities", content.get("capabilities", content.get("declared_capabilities", [])))
        capabilities: list[str] = []
        for capability in raw_capabilities:
            if isinstance(capability, str):
                capabilities.append(capability)
            elif isinstance(capability, dict):
                capability_udi = capability.get("udi") or capability.get("name")
                if capability_udi:
                    capabilities.append(str(capability_udi))
            else:
                raise TypeError("Manifest capabilities must contain strings or dictionaries")

        return Manifest(
            name=str(name),
            udi=payload.get("udi"),
            kind=str(payload["kind"]),
            version=str(payload["version"]),
            capabilities=capabilities,
            interfaces=list(payload.get("interfaces", [])),
            metadata=dict(payload.get("metadata", {})),
            dependencies=list(payload.get("dependencies", content.get("dependencies", []))),
            content=content,
        )

    @staticmethod
    def load_from_file(path: str | Path) -> Manifest:
        manifest_path = Path(path)
        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("Manifest file must contain a YAML mapping")
        return ManifestLoader.load(payload)

    @staticmethod
    def discover(directory: str | Path) -> list[Manifest]:
        manifest_directory = Path(directory)
        if not manifest_directory.exists():
            return []

        manifests: list[Manifest] = []
        for manifest_path in sorted(manifest_directory.glob("manifest*.yaml")):
            manifests.append(ManifestLoader.load_from_file(manifest_path))
        for manifest_path in sorted(manifest_directory.glob("manifest.d/*.yaml")):
            manifests.append(ManifestLoader.load_from_file(manifest_path))
        return manifests
