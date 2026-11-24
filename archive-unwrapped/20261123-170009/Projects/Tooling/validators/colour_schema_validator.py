from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from pathlib import Path

import yaml

try:
    import jsonschema
    from jsonschema import Draft7Validator
except ImportError:  # pragma: no cover - environment may lack jsonschema
    jsonschema = None
    Draft7Validator = None


_SCHEMA_CACHE: Dict[str, Dict[str, Any]] = {}


def _colour_schema_dir(prismata_root: Optional[str] = None) -> str:
    base = prismata_root or os.path.join(os.path.dirname(__file__), "..", "..", "..")
    return os.path.join(base, "Meta", "canonical", "colour")


def _load_colour_schema(schema_filename: str, prismata_root: Optional[str] = None) -> Dict[str, Any]:
    cache_key = f"colour:{prismata_root or ''}:{schema_filename}"
    if cache_key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[cache_key]

    schema_path = os.path.join(_colour_schema_dir(prismata_root), schema_filename)
    with open(schema_path, "r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)

    # Some schema files use a single top-level wrapper key — unwrap if present.
    if isinstance(loaded, dict) and len(loaded) == 1 and not any(
        k in loaded for k in ("type", "properties", "$defs", "required", "$id", "title")
    ):
        loaded = next(iter(loaded.values()))

    _SCHEMA_CACHE[cache_key] = loaded
    return loaded


def validate_colour_instance(
    instance: Dict[str, Any],
    schema_filename: str,
    prismata_root: Optional[str] = None,
) -> List[str]:
    """Validate a Python dict against the canonical colour schema set.

    This validator intentionally does not accept deprecated compatibility fallbacks.
    """
    schema = _load_colour_schema(schema_filename, prismata_root)
    if Draft7Validator is None:
        return ["validator-unavailable: jsonschema is not installed"]

    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)

    errors: List[str] = []
    for err in validator.iter_errors(instance):
        path = ".".join([str(p) for p in err.path]) if err.path else "<root>"
        errors.append(f"{path}: {err.message}")
    return errors


def validate_chromascheme_output(
    instance: Dict[str, Any], prismata_root: Optional[str] = None
) -> List[str]:
    return validate_colour_instance(instance, "chromascheme-output.schema.yaml", prismata_root)


def validate_colour_roles(
    instance: Dict[str, Any], prismata_root: Optional[str] = None
) -> List[str]:
    return validate_colour_instance(instance, "colour-roles.schema.yaml", prismata_root)


def validate_multipane_preview(
    instance: Dict[str, Any], prismata_root: Optional[str] = None
) -> List[str]:
    return validate_colour_instance(instance, "colour-preview-multipane.schema.yaml", prismata_root)
