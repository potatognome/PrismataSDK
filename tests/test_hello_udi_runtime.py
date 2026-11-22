from ui.runtime import (
    ContextGraphBuilder,
    HelloUDICapability,
    HelloUDIRuntimeEngine,
    PaneOutputInjector,
)


def test_hello_udi_context_graph_is_ordered_and_bounded():
    context = ContextGraphBuilder.build(
        initiating_object="prismata.example.menu_item.test_lh",
        menu_item_udi="prismata.example.menu_item.test_lh",
        menu_udi="prismata.example.menu.test_menu",
        pane_udi="prismata.example.pane.lh_test",
        framework_udi="prismata.example.ui_framework.two_pane",
        capability_udi="prismata.example.capability.hello_udi",
    )

    assert context.related_objects == [
        "prismata.example.menu_item.test_lh",
        "prismata.example.menu.test_menu",
        "prismata.example.pane.lh_test",
        "prismata.example.ui_framework.two_pane",
        "prismata.example.capability.hello_udi",
    ]
    assert len(context.related_objects) <= 10


def test_hello_udi_capability_greets_each_related_object_once():
    context = ContextGraphBuilder.build(
        initiating_object="prismata.example.menu_item.test_lh",
        menu_item_udi="prismata.example.menu_item.test_lh",
        menu_udi="prismata.example.menu.test_menu",
        pane_udi="prismata.example.pane.lh_test",
        framework_udi="prismata.example.ui_framework.two_pane",
        capability_udi="prismata.example.capability.hello_udi",
    )

    output = HelloUDICapability.execute(context)

    assert "Hello to menu_item prismata.example.menu_item.test_lh" in output
    assert "Hello to menu prismata.example.menu.test_menu" in output
    assert "Hello to pane prismata.example.pane.lh_test" in output
    assert "Hello to ui_framework prismata.example.ui_framework.two_pane" in output
    assert output.count("from prismata.example.capability.hello_udi") == 5


def test_pane_output_injector_preserves_other_pane_states():
    pane_states = {
        "prismata.example.pane.lh_test": "",
        "prismata.example.pane.rh_test": "existing",
    }

    updated = PaneOutputInjector.inject(
        pane_states,
        "prismata.example.pane.lh_test",
        "left output",
    )

    assert updated["prismata.example.pane.lh_test"] == "left output"
    assert updated["prismata.example.pane.rh_test"] == "existing"
    assert pane_states["prismata.example.pane.lh_test"] == ""


def test_hello_udi_engine_routes_left_right_and_quit():
    engine = HelloUDIRuntimeEngine()

    left_running, left_output = engine.select("1")
    assert left_running is True
    assert "Hello to pane prismata.example.pane.lh_test" in str(left_output)
    assert engine.pane_states["prismata.example.pane.lh_test"]
    assert engine.pane_states["prismata.example.pane.rh_test"] == ""

    right_running, right_output = engine.select("2")
    assert right_running is True
    assert "Hello to pane prismata.example.pane.rh_test" in str(right_output)
    assert engine.pane_states["prismata.example.pane.lh_test"]
    assert engine.pane_states["prismata.example.pane.rh_test"]

    quit_running, quit_output = engine.select("0")
    assert quit_running is False
    assert quit_output is None
