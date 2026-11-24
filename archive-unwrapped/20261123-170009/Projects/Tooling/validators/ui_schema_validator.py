from __future__ import annotations

import yaml
import os
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft7Validator
except Exception:  # pragma: no cover - environment may lack jsonschema
    jsonschema = None
    Draft7Validator = None


# Module-level cache for parsed schemas to avoid repeated file IO
_SCHEMA_CACHE: Dict[str, Dict[str, Any]] = {}


def _schema_dir(prismata_root: Optional[str] = None) -> str:
    base = prismata_root or os.path.join(os.path.dirname(__file__), "..", "..", "..")
    return os.path.join(base, "Meta", "canonical", "ui.schemas")


def _load_schema(schema_filename: str, prismata_root: Optional[str] = None) -> Dict[str, Any]:
    cache_key = f"{prismata_root or ''}:{schema_filename}"
    if cache_key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[cache_key]

    schema_path = os.path.join(_schema_dir(prismata_root), schema_filename)
    with open(schema_path, "r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)

    # Many schema files are wrapped with a single top-level key (e.g. 'pane: { ... }').
    if isinstance(loaded, dict) and len(loaded) == 1:
        loaded = next(iter(loaded.values()))

    _SCHEMA_CACHE[cache_key] = loaded
    return loaded


def _simple_fallback_validate(instance: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """A minimal validator used when jsonschema is unavailable or fails to initialize.

    It checks for 'required' top-level keys declared in the schema and reports missing ones.
    This provides a best-effort validation without external deps.
    """
    errors: List[str] = []
    required = schema.get("required") or []
    for key in required:
        if key not in instance:
            errors.append(f"<root>: missing required property '{key}'")
    return errors


def validate_instance(instance: Dict[str, Any], schema_filename: str, prismata_root: Optional[str] = None) -> List[str]:
    """Validate a Python dict against a YAML schema file under Meta/canonical/ui.schemas.

    Returns a list of human-readable error messages. If `jsonschema` is unavailable,
    returns best-effort errors from a lightweight fallback validator.
    """
    schema = _load_schema(schema_filename, prismata_root)

    # If jsonschema is not installed, provide a simple fallback validation
    if Draft7Validator is None:
        try:
            return _simple_fallback_validate(instance, schema)
        except Exception as exc:  # pragma: no cover - defensive
            return [f"validator-unavailable: {exc}"]

    # Build a resolver that preloads local YAML schemas so $ref resolution works
    schema_dir = _schema_dir(prismata_root)
    base_uri = Path(schema_dir).absolute().as_uri() + "/"

    # Build a referencing Registry with all local schema file contents so
    # cross-file and fragment resolution is handled by `referencing`.
    try:
        import referencing.jsonschema as rj
    except Exception:
        rj = None

    file_pairs = []
    for fname in os.listdir(schema_dir):
        if not fname.lower().endswith((".yaml", ".yml")):
            continue
        fpath = os.path.join(schema_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh)
            if isinstance(loaded, dict) and len(loaded) == 1:
                loaded = next(iter(loaded.values()))
            file_pairs.append((base_uri + fname, loaded))
        except Exception:
            continue

    store = {}
    registry = None
    if rj is not None:
        try:
            registry = rj.EMPTY_REGISTRY.with_contents(file_pairs)
        except Exception:
            registry = None
    # Fallback to legacy store dict for inline resolving if referencing not available
    if registry is None:
        for (uri, loaded) in file_pairs:
            store[uri] = loaded
            if isinstance(loaded, dict):
                sid = loaded.get("$id")
                if sid:
                    store[sid] = loaded
            store[os.path.basename(uri)] = loaded

    def _resolve_pointer(document: Any, pointer: str):
        # pointer expected like '/$defs/geometry' or '$defs/geometry'
        p = pointer.lstrip('#')
        if p.startswith('/'):
            p = p[1:]
        parts = [part for part in p.split('/') if part]
        cur = document
        for part in parts:
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return None
        return cur

    def _inline_local_refs(node: Any, base_uri: str, fname: str):
        # Walk the schema and inline simple local $ref targets where possible.
        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                ref = node["$ref"]
                # Handle same-file fragment refs: '#/...'
                if ref.startswith("#/"):
                    # same-file fragment
                    if registry is not None:
                        try:
                            target = registry.contents(base_uri + fname)
                            resolved = _resolve_pointer(target, ref)
                        except Exception:
                            resolved = None
                    else:
                        doc = store.get(base_uri + fname)
                        resolved = _resolve_pointer(doc, ref) if doc is not None else None
                    if resolved is not None:
                        return _inline_local_refs(resolved, base_uri, fname)
                # Handle filename-qualified refs: 'other.yaml#/<path>'
                if "#" in ref:
                    fname_part, frag = ref.split("#", 1)
                    if registry is not None:
                        target_uri = base_uri + fname_part if (base_uri + fname_part) in registry.keys() else fname_part
                        try:
                            target_doc = registry.contents(target_uri)
                            resolved = _resolve_pointer(target_doc, frag)
                        except Exception:
                            resolved = None
                    else:
                        target_doc = store.get(base_uri + fname_part) or store.get(fname_part)
                        resolved = _resolve_pointer(target_doc, frag) if target_doc is not None else None
                    if resolved is not None:
                        return _inline_local_refs(resolved, base_uri, fname)
            # otherwise recurse into children
            new = {}
            for k, v in node.items():
                new[k] = _inline_local_refs(v, base_uri, fname)
            return new
        elif isinstance(node, list):
            return [_inline_local_refs(v, base_uri, fname) for v in node]
        else:
            return node

    try:
        # Prefer validator_for so schema's declared draft/version is respected.
        # Inline simple local $ref targets to avoid fragment resolution edge-cases.
        try:
            schema = _inline_local_refs(schema, base_uri, schema_filename)
        except Exception:
            # Non-fatal: continue with original schema if inlining fails
            pass

        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)
        from jsonschema import RefResolver

        # Prefer to set the resolver's referrer to the schema's file URI entry
        referrer_candidate = store.get(base_uri + schema_filename, schema)
        resolver = RefResolver(base_uri=base_uri, referrer=referrer_candidate, store=store)
        validator = validator_cls(schema, resolver=resolver)
    except Exception as exc:
        # If initialization fails, fall back to simple checks rather than hard exception
        try:
            return _simple_fallback_validate(instance, schema)
        except Exception as exc2:  # pragma: no cover - defensive
            return [f"validator-init-failed: {exc}; fallback-failed: {exc2}"]

    errors: List[str] = []
    for err in validator.iter_errors(instance):
        path = ".".join([str(p) for p in err.path]) if err.path else "<root>"
        errors.append(f"{path}: {err.message}")
    return errors


def validate_pane(pane: Dict[str, Any], prismata_root: Optional[str] = None) -> List[str]:
    return validate_instance(pane, "pane.schema.yaml", prismata_root)


def validate_ui_framework(ui_framework: Dict[str, Any], prismata_root: Optional[str] = None) -> List[str]:
    return validate_instance(ui_framework, "ui-framework.schema.yaml", prismata_root)
