from ui.frameworks import UIFramework, UIFrameworkRuntime, resolve_menu_target


def test_framework_resolves_menu_target_from_route_table():
    framework = UIFramework(
        id="framework.main",
        kind="ui-framework",
        panes=["pane.left", "pane.right"],
        menu_routes={"menu.home": "pane.left", "menu.settings": "framework.settings"},
        metadata={"layout": "split"},
    )

    runtime = UIFrameworkRuntime(framework=framework, panes=framework.panes, menu_routes=framework.menu_routes)

    assert runtime.resolve_menu_target("menu.home") == "pane.left"
    assert runtime.resolve_menu_target("menu.settings") == "framework.settings"


def test_framework_compose_includes_layout_and_routes():
    framework = UIFramework(
        id="framework.main",
        panes=["pane.left", "pane.right"],
        menu_routes={"menu.home": "pane.left"},
        metadata={"layout": "split"},
    )

    composed = UIFrameworkRuntime(framework=framework, panes=framework.panes, menu_routes=framework.menu_routes).compose()

    assert composed["layout"] == "split"
    assert composed["menu_routes"]["menu.home"] == "pane.left"


def test_top_level_resolver_matches_route_table():
    framework = UIFramework(
        id="framework.main",
        panes=["pane.left"],
        menu_routes={"menu.home": "pane.left"},
    )

    assert resolve_menu_target(framework, "menu.home") == "pane.left"


def test_framework_resolves_split_slot_route_to_pane():
    framework = UIFramework(
        id="framework.main",
        panes=["pane.left", "pane.right"],
        menu_routes={"menu.home": "slot:left"},
        metadata={
            "layout": "split",
            "pane_slots": {"left": "pane.left", "right": "pane.right"},
        },
    )

    runtime = UIFrameworkRuntime(framework=framework)

    assert runtime.resolve_menu_target("menu.home") == "pane.left"


def test_framework_resolves_grid_slot_route_to_pane():
    framework = UIFramework(
        id="framework.grid",
        panes=["pane.r0c0", "pane.r0c1", "pane.r1c0", "pane.r1c1"],
        menu_routes={"menu.details": "slot:r1c1"},
        metadata={
            "layout": "grid",
            "pane_slots": {
                "r0c0": "pane.r0c0",
                "r0c1": "pane.r0c1",
                "r1c0": "pane.r1c0",
                "r1c1": "pane.r1c1",
            },
        },
    )

    runtime = UIFrameworkRuntime(framework=framework)

    assert runtime.resolve_menu_target("menu.details") == "pane.r1c1"


def test_framework_returns_none_for_unknown_slot_or_invalid_target():
    framework = UIFramework(
        id="framework.multi",
        panes=["pane.primary", "pane.secondary"],
        menu_routes={"menu.unknown": "slot:missing", "menu.invalid": "slot:ghost"},
        metadata={
            "layout": "multi",
            "pane_slots": {"primary": "pane.primary", "ghost": "pane.not.in.framework"},
        },
    )

    runtime = UIFrameworkRuntime(framework=framework)

    assert runtime.resolve_menu_target("menu.unknown") is None
    assert runtime.resolve_menu_target("menu.invalid") is None
