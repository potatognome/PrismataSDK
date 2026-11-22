import pytest
from pathlib import Path

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

    with pytest.raises(ValueError, match=r"Manifest 'ui-core' references unknown capabilities: missing"):
        CapabilityResolver.resolve_manifest(manifest, registry)


def test_capability_registry_rejects_duplicate_registration():
    registry = CapabilityRegistry()
    registry.register(Capability(name="pane"))

    with pytest.raises(ValueError, match=r"Capability already registered: pane"):
        registry.register(Capability(name="pane"))


def test_hello_udi_capability_loads_as_cmf_capability():
    path = Path(__file__).resolve().parents[1] / "examples" / "capabilities" / "hello_udi" / "hello_udi.yaml"

    capability = Capability.load_from_file(path)
    registry = CapabilityRegistry()
    registry.register(capability)

    resolved = registry.resolve("prismata.example.capability.hello_udi")

    assert resolved.udi == "prismata.example.capability.hello_udi"
    assert resolved.execution_target == "hello_udi_runtime"
    assert resolved.content["max_depth"] == 10
