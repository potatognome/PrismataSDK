from core.manifests import Manifest, ManifestLoader
from core.schemas import SchemaRule, SchemaSpec, SchemaLoader
import json


def test_schema_loader_validates_required_fields():
    schema = {
        "kind": "pane",
        "fields": {"id": {"type": "string"}, "title": {"type": "string"}},
        "rules": [{"type": "at-least-one", "fields": ["id", "title"]}],
    }

    loaded = SchemaLoader.load(schema)

    assert loaded.kind == "pane"
    assert loaded.fields["id"]["type"] == "string"
    assert loaded.rules[0].type == "at-least-one"


def test_manifest_loader_loads_runtime_manifest():
    manifest_payload = {
        "name": "ui-core",
        "kind": "module",
        "version": "1.0.0",
        "capabilities": ["pane", "menu"],
        "interfaces": ["ui.framework"],
    }

    manifest = ManifestLoader.load(manifest_payload)

    assert isinstance(manifest, Manifest)
    assert manifest.name == "ui-core"
    assert manifest.capabilities == ["pane", "menu"]
    assert manifest.interfaces == ["ui.framework"]


def test_schema_loader_resolves_canonical_root_path():
    root = SchemaLoader.canonical_schema_root(r"C:\workspace")

    assert root.parts[-2:] == ("PrismataCore", "canonical")


def test_schema_loader_loads_schema_from_file(tmp_path):
    schema_file = tmp_path / "pane.schema.json"
    schema_payload = {
        "kind": "pane",
        "fields": {"id": {"type": "string"}, "title": {"type": "string"}},
        "rules": [{"type": "at-least-one", "fields": ["id", "title"]}],
    }
    schema_file.write_text(json.dumps(schema_payload), encoding="utf-8")

    loaded = SchemaLoader.load_from_file(schema_file)

    assert loaded.kind == "pane"
    assert loaded.rules[0].type == "at-least-one"


def test_schema_loader_rejects_unknown_rule_field():
    schema = {
        "kind": "pane",
        "fields": {"id": {"type": "string"}},
        "rules": [{"type": "at-least-one", "fields": ["missing"]}],
    }

    try:
        SchemaLoader.load(schema)
        assert False, "Expected ValueError for unknown schema field"
    except ValueError as exc:
        assert "unknown schema field" in str(exc)


def test_schema_loader_rejects_unsupported_rule_type():
    schema = {
        "kind": "pane",
        "fields": {"id": {"type": "string"}},
        "rules": [{"type": "all-of", "fields": ["id"]}],
    }

    try:
        SchemaLoader.load(schema)
        assert False, "Expected ValueError for unsupported rule type"
    except ValueError as exc:
        assert "Unsupported schema rule type" in str(exc)


def test_schema_loader_rejects_payload_unknown_field():
    schema = {
        "kind": "pane",
        "fields": {"id": {"type": "string"}},
        "rules": [{"type": "at-least-one", "fields": ["id"]}],
    }

    loaded = SchemaLoader.load(schema)

    try:
        SchemaLoader.validate_payload(loaded, {"id": "pane.main", "unexpected": True})
        assert False, "Expected ValueError for unknown payload field"
    except ValueError as exc:
        assert "unknown field" in str(exc)


def test_schema_loader_validates_payload_rules():
    schema = {
        "kind": "pane",
        "fields": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "left": {"type": "number"},
            "right": {"type": "number"},
        },
        "rules": [
            {"type": "at-least-one", "fields": ["id", "title"]},
            {"type": "xor", "fields": ["left", "right"]},
        ],
    }

    loaded = SchemaLoader.load(schema)

    SchemaLoader.validate_payload(loaded, {"id": "pane.main", "left": 1})

    try:
        SchemaLoader.validate_payload(loaded, {"left": 1})
        assert False, "Expected ValueError for at-least-one rule"
    except ValueError as exc:
        assert "at least one" in str(exc)

    try:
        SchemaLoader.validate_payload(loaded, {"id": "pane.main", "left": 1, "right": 2})
        assert False, "Expected ValueError for xor rule"
    except ValueError as exc:
        assert "exactly one" in str(exc)
