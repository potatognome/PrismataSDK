import pytest

from capabilities import Capability, CapabilityRegistry, CapabilityResolver
from core.manifests import ManifestLoader


def test_capability_resolver_loads_manifest_capabilities():
    registry = CapabilityRegistry()
    registry.register(Capability(name="pane", interfaces=["ui.pane"]))
    registry.register(Capability(name="menu", interfaces=["ui.menu"]))

    manifest = ManifestLoader.load(
        {
            "name": "ui-core",
            "kind": "module",
            "version": "1.0.0",
            "capabilities": ["pane", "menu"],
        }
    )

    resolution = CapabilityResolver.resolve_manifest(manifest, registry)
    runtime = resolution.as_pso()

    assert resolution.manifest.name == "ui-core"
    assert [capability.name for capability in resolution.capabilities] == ["pane", "menu"]
    assert runtime["__pso__"] is True
    assert runtime["capabilities"][0]["interfaces"] == ["ui.pane"]


def test_capability_resolver_rejects_unknown_capability():
    registry = CapabilityRegistry()
    manifest = ManifestLoader.load(
        {
            "name": "ui-core",
            "kind": "module",
            "version": "1.0.0",
            "capabilities": ["missing"],
        }
    )

    with pytest.raises(ValueError, match="unknown capabilities"):
        CapabilityResolver.resolve_manifest(manifest, registry)
