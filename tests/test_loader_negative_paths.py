from core.cmf import CMFLoader
from core.registry import RegistryLoader
from ui.panes import Pane, resolve_pane_location


def test_cmf_loader_rejects_missing_required_fields():
    payload = {
        "id": "pane.main",
        "udi": "udi://cmf/pane/main",
        "kind": "pane",
    }

    try:
        CMFLoader.load(payload)
        assert False, "Expected ValueError when required fields are missing"
    except ValueError as exc:
        assert "missing required fields" in str(exc)


def test_registry_loader_rejects_non_dict_list_item():
    try:
        RegistryLoader.load_registry(["bad-entry"])
        assert False, "Expected TypeError for non-dictionary registry entry"
    except TypeError as exc:
        assert "must be dictionaries" in str(exc)


def test_registry_loader_rejects_missing_name_or_id_in_list_item():
    try:
        RegistryLoader.load_registry([{"kind": "pane", "source": "pane.d/x.yaml"}])
        assert False, "Expected ValueError for entry missing name/id"
    except ValueError as exc:
        assert "requires a name or id" in str(exc)


def test_registry_loader_build_pso_requires_registered_name_when_registry_provided():
    registry = RegistryLoader.load_registry({"pane.main": {"kind": "pane", "source": "pane.d/main.yaml"}})
    payload = {
        "id": "pane.main",
        "udi": "udi://cmf/pane/main",
        "kind": "pane",
        "version": "1.0",
        "content": {"title": "Main"},
    }

    try:
        RegistryLoader.build_pso("pane.missing", payload, registry)
        assert False, "Expected KeyError for unregistered object name"
    except KeyError as exc:
        assert "No object registry entry" in str(exc)


def test_resolve_pane_location_rejects_unknown_mode():
    pane = Pane(id="pane.main", position={"mode": "floating"})

    try:
        resolve_pane_location(pane)
        assert False, "Expected ValueError for unsupported pane mode"
    except ValueError as exc:
        assert "Unsupported pane position mode" in str(exc)
