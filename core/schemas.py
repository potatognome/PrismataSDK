from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
import json
from typing import Any


@dataclass(slots=True)
class SchemaRule:
    """Canonical validation rule for a schema definition."""

    type: str
    fields: list[str] = field(default_factory=list)
    message: str | None = None


@dataclass(slots=True)
class SchemaSpec:
    """A loaded schema specification."""

    kind: str
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)
    rules: list[SchemaRule] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


CANONICAL_SCHEMA_ROOT = Path("PrismataCore") / "canonical"


class SchemaLoader:
    """Loads canonical schema definitions into a schema spec."""

    _SUPPORTED_RULES = {"at-least-one", "xor"}

    @staticmethod
    def canonical_schema_root(workspace_root: str | Path | None = None) -> Path:
        if workspace_root is None:
            return (Path.cwd() / CANONICAL_SCHEMA_ROOT).resolve()

        if isinstance(workspace_root, str) and ("\\" in workspace_root or ":" in workspace_root):
            root = PureWindowsPath(workspace_root) / PureWindowsPath(*CANONICAL_SCHEMA_ROOT.parts)
            return Path(str(root)).resolve()

        base = Path(workspace_root)
        return (base / CANONICAL_SCHEMA_ROOT).resolve()

    @classmethod
    def load_from_file(cls, schema_file: str | Path, workspace_root: str | Path | None = None) -> SchemaSpec:
        schema_path = Path(schema_file)
        if not schema_path.is_absolute():
            schema_path = cls.canonical_schema_root(workspace_root) / schema_path

        payload = json.loads(schema_path.read_text(encoding="utf-8"))
        return cls.load(payload)

    @staticmethod
    def load(payload: dict[str, Any]) -> SchemaSpec:
        if "kind" not in payload:
            raise ValueError("Schema payload missing required field: kind")

        fields = dict(payload.get("fields", {}))
        raw_rules = payload.get("rules", [])
        rules = []
        for rule in raw_rules:
            if not isinstance(rule, dict):
                raise TypeError("Schema rule must be a dictionary payload")
            rule_type = str(rule.get("type", "unknown"))
            if rule_type not in SchemaLoader._SUPPORTED_RULES:
                raise ValueError(f"Unsupported schema rule type: {rule_type}")

            rule_fields = list(rule.get("fields", []))
            if not rule_fields:
                raise ValueError("Schema rule must declare at least one field")

            rules.append(
                SchemaRule(
                    type=rule_type,
                    fields=rule_fields,
                    message=rule.get("message"),
                )
            )

        spec = SchemaSpec(
            kind=str(payload["kind"]),
            fields=fields,
            rules=rules,
            metadata=dict(payload.get("metadata", {})),
        )
        SchemaLoader.validate_rule_contracts(spec)
        return spec

    @staticmethod
    def validate_rule_contracts(spec: SchemaSpec) -> None:
        schema_fields = set(spec.fields.keys())
        for rule in spec.rules:
            unknown_fields = [field for field in rule.fields if field not in schema_fields]
            if unknown_fields:
                fields = ", ".join(unknown_fields)
                raise ValueError(f"Rule references unknown schema field(s): {fields}")

            if rule.type == "xor" and len(rule.fields) < 2:
                raise ValueError("xor rule requires at least two fields")

    @staticmethod
    def validate_payload(spec: SchemaSpec, payload: dict[str, Any]) -> None:
        for field_name in payload.keys():
            if field_name not in spec.fields:
                raise ValueError(f"Payload includes unknown field: {field_name}")

        for rule in spec.rules:
            present_count = sum(1 for field in rule.fields if payload.get(field) not in (None, ""))

            if rule.type == "at-least-one" and present_count < 1:
                raise ValueError(rule.message or f"Expected at least one of: {', '.join(rule.fields)}")

            if rule.type == "xor" and present_count != 1:
                raise ValueError(rule.message or f"Expected exactly one of: {', '.join(rule.fields)}")
