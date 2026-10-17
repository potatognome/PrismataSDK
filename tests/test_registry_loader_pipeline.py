from core.cmf import CMFLoader, PSOBuilder
from core.registry import ObjectRegistry, RegistryEntry, RegistryLoader


def test_registry_pipeline_builds_pso_runtime_objects():
    registry = ObjectRegistry()
    registry.register(RegistryEntry(name="pane.main", kind="pane", source="pane.d/pane.main.yaml"))
    registry.register(RegistryEntry(name="menu.actions", kind="menu", source="menu.d/menu.actions.yaml"))

    payload = {
        "id": "pane.main",
        "udi": "udi://cmf/pane/main",
        "kind": "pane",
        "version": "1.0",
        "content": {"title": "Main"},
    }

    loaded = RegistryLoader.load_registry({
        "pane.main": {"kind": "pane", "source": "pane.d/pane.main.yaml"},
        "menu.actions": {"kind": "menu", "source": "menu.d/menu.actions.yaml"},
    })

    envelope = CMFLoader.load(payload)
    runtime = PSOBuilder.build(envelope)

    entry = loaded.resolve("pane.main")
    assert entry.kind == "pane"
    assert runtime["id"] == "pane.main"
    assert runtime["content"]["title"] == "Main"

    pso_runtime = RegistryLoader.build_pso("pane.main", payload, loaded)
    assert pso_runtime["__pso__"] is True
    assert pso_runtime["content"]["title"] == "Main"
