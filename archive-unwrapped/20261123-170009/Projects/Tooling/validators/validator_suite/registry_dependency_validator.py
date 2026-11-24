from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class RegistryEntry:
    entry_id: str
    folder: str
    file_path: Path
    data: Dict[str, Any]


REFERENCE_POLICY: Dict[str, Dict[str, str]] = {
    "border-pattern": {
        "colour_role": "colour-role",
    },
    "colour-scheme": {
        "roles": "colour-role",
    },
    "pane": {
        "content_role": "colour-role",
        "colour_role": "colour-role",
        "border_pattern": "border-pattern",
        "colour_scheme": "colour-scheme",
    },
    "menu-item": {
        "colour_role": "colour-role",
        "semantic_role": "semantic-role",
        "colour_scheme": "colour-scheme",
        "border_pattern": "border-pattern",
    },
    "menu": {
        "items": "menu-item",
    },
    "ui-framework": {
        "panes": "pane",
        "menus": "menu",
        "colour_scheme": "colour-scheme",
        "border_pattern": "border-pattern",
    },
}


def _read_yaml(path: Path) -> Dict[str, Any] | None:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return loaded if isinstance(loaded, dict) else None


def _folder_to_kind(folder_name: str) -> str:
    return folder_name[:-2] if folder_name.endswith(".d") else folder_name


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def load_registry_entries(registry_root: Path) -> tuple[List[RegistryEntry], Dict[str, RegistryEntry]]:
    entries: List[RegistryEntry] = []
    by_id: Dict[str, RegistryEntry] = {}

    for folder in sorted(registry_root.glob("*.d")):
        if not folder.is_dir():
            continue

        for file_path in sorted(folder.glob("*.yaml")):
            data = _read_yaml(file_path)
            if not data:
                continue

            entry_id = data.get("id")
            if not isinstance(entry_id, str) or not entry_id.strip():
                continue

            entry = RegistryEntry(
                entry_id=entry_id,
                folder=folder.name,
                file_path=file_path,
                data=data,
            )
            entries.append(entry)
            by_id[entry_id] = entry

    return entries, by_id


def _build_registry_lookups(entries: List[RegistryEntry]) -> Dict[str, Dict[str, Dict[str, RegistryEntry]]]:
    lookups: Dict[str, Dict[str, Dict[str, RegistryEntry]]] = {}
    for entry in entries:
        kind = str(entry.data.get("kind") or _folder_to_kind(entry.folder))
        kind_key = _normalize_token(kind)
        kind_map = lookups.setdefault(kind_key, {"id": {}, "name": {}, "udi": {}})

        entry_id = entry.entry_id
        if isinstance(entry_id, str) and entry_id.strip():
            kind_map["id"][entry_id] = entry

        entry_name = entry.data.get("name")
        if isinstance(entry_name, str) and entry_name.strip():
            kind_map["name"][entry_name] = entry

        entry_udi = entry.data.get("udi")
        if isinstance(entry_udi, str) and entry_udi.strip():
            kind_map["udi"][entry_udi] = entry

    return lookups


def load_schema_index(prismata_root: Path) -> Dict[str, Dict[str, Any]]:
    schema_index: Dict[str, Dict[str, Any]] = {}
    schema_dirs = [
        prismata_root / "Meta" / "canonical" / "object.schemas",
        prismata_root / "Meta" / "canonical" / "composition.schemas",
    ]

    for schema_dir in schema_dirs:
        if not schema_dir.exists():
            continue
        for path in sorted(schema_dir.glob("*.yaml")):
            schema_doc = _read_yaml(path)
            if not schema_doc:
                continue

            kind = schema_doc.get("kind")
            fields = schema_doc.get("fields")
            if isinstance(kind, str) and isinstance(fields, list):
                schema_index[kind] = {
                    "path": path,
                    "fields": fields,
                }

    return schema_index


def _find_path_value(data: Dict[str, Any], dotted_path: str) -> Any:
    if dotted_path in data:
        return data[dotted_path]

    cur: Any = data
    for part in dotted_path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
            continue
        cur = None
        break
    if cur is not None:
        return cur

    target = _normalize_token(dotted_path.split(".")[-1])

    def _token_matches(candidate: str, expected: str) -> bool:
        if candidate == expected:
            return True
        return candidate.endswith(f"_{expected}") or expected.endswith(f"_{candidate}")

    def _search(node: Any) -> Any:
        if isinstance(node, dict):
            for key, value in node.items():
                if _token_matches(_normalize_token(str(key)), target):
                    return value
            for value in node.values():
                nested = _search(value)
                if nested is not None:
                    return nested
        elif isinstance(node, list):
            for value in node:
                nested = _search(value)
                if nested is not None:
                    return nested
        return None

    return _search(data)


def _required_schema_paths(schema_fields: List[Dict[str, Any]]) -> List[str]:
    paths: List[str] = []
    for field in schema_fields:
        if not isinstance(field, dict):
            continue
        if field.get("required") is not True:
            continue
        path = field.get("path")
        if isinstance(path, str) and path.strip():
            paths.append(path)
    return paths


def _kind_reference_paths(kind: str) -> Dict[str, str]:
    return REFERENCE_POLICY.get(_normalize_token(kind), {})


def _collect_reference_values(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]

    if isinstance(value, list):
        refs: List[str] = []
        for item in value:
            if isinstance(item, str):
                refs.append(item)
        return refs

    if isinstance(value, dict):
        refs: List[str] = []
        for key in value.keys():
            if isinstance(key, str):
                refs.append(key)
        return refs

    return []


def validate_registry_entry_against_schema(
    entry: RegistryEntry,
    kind: str,
    schema: Dict[str, Any],
    kind_lookups: Dict[str, Dict[str, Dict[str, RegistryEntry]]],
) -> Dict[str, Any]:
    fields = schema.get("fields", [])
    required_paths = _required_schema_paths(fields)

    missing_required: List[str] = []
    for path in required_paths:
        if _find_path_value(entry.data, path) is None:
            missing_required.append(path)

    references_for_kind = _kind_reference_paths(kind)
    reference_checks: List[Dict[str, str]] = []
    for field in fields:
        if not isinstance(field, dict):
            continue

        path = field.get("path")
        if not isinstance(path, str) or not path:
            continue

        target_kind = references_for_kind.get(path)
        if not target_kind:
            continue

        value = _find_path_value(entry.data, path)
        if value is None:
            continue

        lookup = kind_lookups.get(_normalize_token(target_kind), {"id": {}, "name": {}, "udi": {}})
        for ref in _collect_reference_values(value):
            if ref in lookup["udi"] or ref in lookup["id"] or ref in lookup["name"]:
                reference_checks.append({"field": path, "reference": ref, "status": "found"})
            else:
                reference_checks.append({"field": path, "reference": ref, "status": "missing"})

    return {
        "missing_required": missing_required,
        "reference_checks": reference_checks,
    }


def run_registry_dependency_validation(prismata_root: Path) -> Dict[str, Any]:
    registry_root = prismata_root / "Meta" / "registry"
    schema_index = load_schema_index(prismata_root)
    entries, _by_id = load_registry_entries(registry_root)
    kind_lookups = _build_registry_lookups(entries)

    results: List[Dict[str, Any]] = []
    missing_schema: List[str] = []

    for entry in entries:
        kind = entry.data.get("kind") or _folder_to_kind(entry.folder)
        schema = schema_index.get(str(kind))
        if not schema:
            missing_schema.append(f"{entry.folder}: no canonical schema for kind '{kind}'")
            continue

        validation = validate_registry_entry_against_schema(entry, str(kind), schema, kind_lookups)
        results.append(
            {
                "id": entry.entry_id,
                "kind": kind,
                "file": entry.file_path,
                "schema": schema["path"],
                "missing_required": validation["missing_required"],
                "reference_checks": validation["reference_checks"],
            }
        )

    missing_schema_issues: List[str] = list(missing_schema)
    missing_required_issues: List[str] = []
    unresolved_reference_issues: List[str] = []

    for result in results:
        rel_file = result["file"].relative_to(prismata_root)
        for missing in result["missing_required"]:
            missing_required_issues.append(f"{rel_file}: missing required schema field '{missing}'")
        for ref in result["reference_checks"]:
            if ref["status"] == "missing":
                unresolved_reference_issues.append(
                    f"{rel_file}: unresolved reference {ref['field']} -> {ref['reference']}"
                )

    issues: List[str] = []
    issues.extend(missing_schema_issues)
    issues.extend(missing_required_issues)
    issues.extend(unresolved_reference_issues)

    return {
        "registry_root": registry_root,
        "entries": results,
        "missing_schema": missing_schema,
        "missing_schema_issues": missing_schema_issues,
        "missing_required_issues": missing_required_issues,
        "unresolved_reference_issues": unresolved_reference_issues,
        "issues": issues,
    }
