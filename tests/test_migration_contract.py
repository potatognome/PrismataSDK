from core.cmf import CMFEnvelope, CMFLoader, PSOBuilder
from ui.frameworks import UIFramework, UIFrameworkRuntime
from ui.menus import Menu, MenuItem, route_menu


def test_cmf_loader_builds_envelope():
    payload = {
        "id": "pane.alpha",
        "udi": "udi://cmf/pane/alpha",
        "kind": "pane",
        "version": "1.0",
        "tenant": "tenant-a",
        "metadata": {"role": "main"},
        "content": {"title": "Alpha"},
    }

    envelope = CMFLoader.load(payload)
    assert isinstance(envelope, CMFEnvelope)
    assert envelope.id == "pane.alpha"

    runtime = PSOBuilder.build(envelope)
    assert runtime["__pso__"] is True
    assert runtime["content"]["title"] == "Alpha"


def test_ui_framework_runtime_is_composable():
    framework = UIFramework(
        id="framework.main",
        panes=["pane.left", "pane.right"],
        menu_routes={"menu.home": "pane.left"},
        metadata={"layout": "split"},
    )

    runtime = UIFrameworkRuntime(framework=framework, panes=framework.panes, menu_routes=framework.menu_routes)
    composed = runtime.compose()

    assert composed["id"] == "framework.main"
    assert composed["panes"] == ["pane.left", "pane.right"]
    assert composed["menu_routes"]["menu.home"] == "pane.left"


def test_menu_router_targets_frame_or_pane():
    menu = Menu(
        id="menu.actions",
        title="Actions",
        items=[
            MenuItem(id="open", label="Open", target="pane.left"),
            MenuItem(id="settings", label="Settings", action="framework.settings"),
        ],
    )

    route = route_menu(menu, "settings")

    assert route["menu_id"] == "menu.actions"
    assert route["target"] == "framework.settings"
