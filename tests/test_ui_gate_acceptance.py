from core.cmf import CMFLoader
from ui.frameworks import UIFramework, UIFrameworkRuntime
from ui.panes import Pane, resolve_pane_location


def test_ui_gate_framework_loading_uses_cmf_envelope():
    payload = {
        "id": "framework.main",
        "udi": "prism://ui/framework.main@1.0.0",
        "kind": "ui-framework",
        "version": "1.0.0",
        "content": {
            "panes": ["pane.left", "pane.right"],
            "menu_routes": {"menu.home": "slot:left"},
            "metadata": {
                "layout": "split",
                "pane_slots": {"left": "pane.left", "right": "pane.right"},
            },
        },
    }

    envelope = CMFLoader.load(payload)

    framework = UIFramework(
        id=envelope.id,
        kind=envelope.kind,
        panes=envelope.content["panes"],
        menu_routes=envelope.content["menu_routes"],
        metadata=envelope.content["metadata"],
    )
    runtime = UIFrameworkRuntime(framework=framework)

    assert runtime.compose()["id"] == "framework.main"
    assert runtime.compose()["layout"] == "split"


def test_ui_gate_pane_location_resolution_fixed_relative_split():
    fixed = Pane(id="pane.fixed", position={"mode": "fixed", "x": 10, "y": 4})
    assert resolve_pane_location(fixed) == {"x": 10, "y": 4}

    relative = Pane(id="pane.relative", position={"mode": "relative", "anchor": "root", "dx": 2, "dy": 3})
    context = {"anchors": {"root": {"x": 7, "y": 8}}}
    assert resolve_pane_location(relative, context) == {"x": 9, "y": 11}

    split_left = Pane(id="pane.left", position={"mode": "split", "orientation": "horizontal", "index": 0, "ratio": 0.5})
    split_right = Pane(id="pane.right", position={"mode": "split", "orientation": "horizontal", "index": 1, "ratio": 0.5})
    split_context = {"width": 120, "height": 40}

    assert resolve_pane_location(split_left, split_context) == {"x": 0, "y": 0}
    assert resolve_pane_location(split_right, split_context) == {"x": 60, "y": 0}


def test_ui_gate_menu_routing_resolves_slot_targets():
    framework = UIFramework(
        id="framework.main",
        panes=["pane.left", "pane.right"],
        menu_routes={"menu.home": "slot:left", "menu.settings": "pane.right"},
        metadata={"pane_slots": {"left": "pane.left", "right": "pane.right"}},
    )

    runtime = UIFrameworkRuntime(framework=framework)

    assert runtime.resolve_menu_target("menu.home") == "pane.left"
    assert runtime.resolve_menu_target("menu.settings") == "pane.right"
