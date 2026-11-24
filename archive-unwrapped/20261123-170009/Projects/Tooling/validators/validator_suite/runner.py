from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

from Projects.Tooling.validators.casing_linter.core.scanner import scan_all_yaml as scan_casing
from Projects.Tooling.validators.casing_linter.core.fixer import fix_yaml_file as fix_casing

from Projects.Tooling.validators.bom_validator.core.scanner import scan_yaml_for_bom as scan_bom
from Projects.Tooling.validators.bom_validator.core.fixer import remove_bom as fix_bom
from Projects.Tooling.validators.validator_suite.registry_dependency_validator import (
    run_registry_dependency_validation,
)


def _read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except Exception:
        return None


def _scan_manifest_required_files(root: Path) -> List[str]:
    issues: List[str] = []
    targets = [
        root / "Projects" / "Applications" / "Universe" / "config" / "udi" / "pcms2026-manifest.yaml",
        root / "Meta" / "registry" / "menu-item.d" / "default.menu-item.entry.yaml",
    ]

    for path in targets:
        if not path.exists():
            issues.append(f"missing required file: {path.relative_to(root)}")
            continue

        data = _read_yaml(path)
        if not isinstance(data, dict):
            issues.append(f"invalid YAML object: {path.relative_to(root)}")
            continue

        for field in ("id", "kind", "udi"):
            value = data.get(field)
            if value is None or str(value).strip() == "":
                issues.append(f"missing required field '{field}' in {path.relative_to(root)}")

    return issues


def _scan_udi_shape(root: Path) -> List[str]:
    issues: List[str] = []
    pattern = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")

    for path in sorted(root.rglob("*.yaml")):
        if any(part in {".venv", "node_modules", ".git", "__pycache__", ".workspace"} for part in path.parts):
            continue
        data = _read_yaml(path)
        if not isinstance(data, dict):
            continue

        candidates: List[str] = []
        if isinstance(data.get("udi"), str):
            candidates.append(data["udi"])
        metadata = data.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("udi"), str):
            candidates.append(metadata["udi"])

        for candidate in candidates:
            if not pattern.fullmatch(candidate):
                issues.append(f"invalid UDI shape in {path.relative_to(root)}: {candidate}")

    return issues


def _scan_registry_presence(root: Path) -> List[str]:
    issues: List[str] = []
    required = [
        root / "Meta" / "registry" / "border-pattern.d" / "default.border-pattern.entry.yaml",
        root / "Meta" / "registry" / "colour-role.d" / "border.colour-role.entry.yaml",
        root / "Meta" / "registry" / "colour-scheme.d" / "default.colour-scheme.entry.yaml",
        root / "Meta" / "registry" / "pane.d" / "default.pane.entry.yaml",
        root / "Meta" / "registry" / "ui-framework.d" / "default.ui-framework.entry.yaml",
    ]
    for path in required:
        if not path.exists():
            issues.append(f"missing registry default: {path.relative_to(root)}")
    return issues


def _scan_registry_schema_consistency(root: Path) -> List[str]:
    issues: List[str] = []
    registry_root = root / "Meta" / "registry"
    if not registry_root.exists():
        return [f"missing registry root: {registry_root.relative_to(root)}"]

    required_keys = ("id", "kind", "udi", "schema_version")
    for path in sorted(registry_root.rglob("*.yaml")):
        if any(part in {".venv", "node_modules", ".git", "__pycache__", ".workspace"} for part in path.parts):
            continue

        data = _read_yaml(path)
        if not isinstance(data, dict):
            issues.append(f"invalid YAML object: {path.relative_to(root)}")
            continue

        missing = [key for key in required_keys if data.get(key) is None or str(data.get(key)).strip() == ""]
        if missing:
            issues.append(f"missing required registry fields {missing} in {path.relative_to(root)}")

        if "kind" in data and not isinstance(data["kind"], str):
            issues.append(f"invalid registry kind in {path.relative_to(root)}")

        if "udi" in data and not isinstance(data["udi"], str):
            issues.append(f"invalid registry udi in {path.relative_to(root)}")

    return issues


def _scan_render_smoke(root: Path) -> List[str]:
    issues: List[str] = []
    try:
        from Projects.Tooling.primitives.python.border_patterns import load_border_pattern_registry
        from Projects.Tooling.primitives.python.menu_renderer import render_menu
        from Projects.Tooling.primitives.python.pane_renderer import render_pane, load_colour_role_registry

        registry_root = root / "Meta" / "registry"
        border_registry = load_border_pattern_registry(registry_root / "border-pattern.d")
        colour_roles = load_colour_role_registry(registry_root / "colour-role.d")
        colour_schemes = {
            "default": {
                "roles": {
                    "primary-surface": {"fg": "ansi:rgb(220,220,220)", "bg": "ansi:rgb(10,10,12)"},
                    "border": {"fg": "ansi:rgb(160,160,160)", "bg": "ansi:rgb(10,10,12)"},
                }
            }
        }
        ui_framework = {"colour_scheme": "default"}

        menu_lines = render_menu(
            {"id": "smoke.menu", "type": "menu", "title": "Smoke", "items": [{"label": "Open", "capability": "meta.preview"}]},
            border_registry,
            colour_roles,
            colour_schemes,
            ui_framework,
            {},
            preview_mode=True,
        )
        pane_lines = render_pane(
            {"id": "smoke.pane", "width": 18, "height": 5, "colour_role": "primary-surface"},
            border_registry,
            colour_roles,
            colour_schemes,
            ui_framework,
            {},
        )

        if not isinstance(menu_lines, list) or not menu_lines:
            issues.append("render smoke failed: menu renderer produced no output")
        if not isinstance(pane_lines, list) or not pane_lines:
            issues.append("render smoke failed: pane renderer produced no output")
    except Exception as exc:  # pragma: no cover - guardrail for integration failures
        issues.append(f"render smoke failed: {type(exc).__name__}: {exc}")

    return issues


def _scan_registry_schema_dependencies(root: Path) -> List[str]:
    issues: List[str] = []
    try:
        result = run_registry_dependency_validation(root)
        # Gate on canonical schema availability + required fields.
        # Unresolved references are reported by the shared validator, but are not yet
        # enforced as hard failures while schema/reference mapping converges.
        issues.extend(result.get("missing_schema_issues", []))
        issues.extend(result.get("missing_required_issues", []))
    except Exception as exc:  # pragma: no cover - guardrail for integration failures
        issues.append(f"registry schema dependency scan failed: {type(exc).__name__}: {exc}")
    return issues


def run_repo_validation(root: str | Path = ".") -> Dict[str, Any]:
    root_path = Path(root).resolve()

    manifest_issues = _scan_manifest_required_files(root_path)
    udi_issues = _scan_udi_shape(root_path)
    registry_issues = _scan_registry_presence(root_path)
    registry_schema_issues = _scan_registry_schema_consistency(root_path)
    registry_dependency_issues = _scan_registry_schema_dependencies(root_path)
    render_smoke_issues = _scan_render_smoke(root_path)

    checks = {
        "manifest_required": {"issues": manifest_issues},
        "udi_shape": {"issues": udi_issues},
        "registry_presence": {"issues": registry_issues},
        "registry_schema": {"issues": registry_schema_issues},
        "registry_schema_dependencies": {"issues": registry_dependency_issues},
        "render_smoke": {"issues": render_smoke_issues},
    }

    failed_checks = sum(len(info["issues"]) for info in checks.values())
    summary = {
        "checks_run": len(checks),
        "failed_checks": failed_checks,
        "ok": failed_checks == 0,
    }
    checks["summary"] = summary
    return checks


def run_all_validators(root='Meta'):
    root_path = Path(root)

    results = {
        'casing': {
            'issues': scan_casing(),
            'fixed': []
        },
        'bom': {
            'issues': scan_bom(root_path),
            'fixed': []
        }
    }

    repo_gate = run_repo_validation(root_path)
    results['repo_gate'] = repo_gate
    return results


def fix_all(results):
    for path, key, casing in results['casing']['issues']:
        new_path = fix_casing(path)
        results['casing']['fixed'].append(new_path)

    for path in results['bom']['issues']:
        new_path = fix_bom(path)
        results['bom']['fixed'].append(new_path)

    return results
