#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

UDI_PATTERN = r"^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.[a-z][a-z0-9-]+$"
ALLOWED_SUBTYPES = (
    "codeblock",
    "document",
    "plan",
    "agent-instruction",
    "artifact",
    "checklist",
    "manifest",
    "object",
    "schema",
)
DEFAULT_INCLUDE_GLOBS = ("**/*",)
DEFAULT_EXCLUDE_GLOBS = (".git/**", "__pycache__/**", ".venv/**", ".pytest_cache/**")


@dataclass(frozen=True)
class WrapperSubtypeRule:
    pattern: str
    subtype: str


def slugify(value: str, max_len: int = 64) -> str:
    cleaned = []
    last_dash = False
    for ch in value.lower():
        if ch.isalnum():
            cleaned.append(ch)
            last_dash = False
            continue
        if not last_dash:
            cleaned.append("-")
            last_dash = True
    out = "".join(cleaned).strip("-")
    if not out:
        out = "item"
    return out[:max_len].strip("-") or "item"


def normalize_udi_segment(value: str, max_len: int = 64) -> str:
    segment = slugify(value, max_len=max_len)
    if not segment[0].isalpha():
        segment = f"x-{segment}"
    return segment[:max_len].strip("-") or "x-item"


def derive_namespace(namespace_arg: str | None, input_root: Path) -> str:
    if namespace_arg:
        return normalize_udi_segment(namespace_arg)
    return normalize_udi_segment(input_root.name)


def derive_scope(relative_parent: Path) -> str:
    if str(relative_parent) in ("", "."):
        return "root"
    return normalize_udi_segment("-".join(relative_parent.parts))


def derive_slug(relative_path: Path) -> str:
    stable = str(relative_path).replace("\\", "/").lower()
    base = slugify(relative_path.stem)
    digest = hashlib.sha1(stable.encode("utf-8")).hexdigest()[:10]
    return normalize_udi_segment(f"{base}-{digest}")


def matches_any(path_text: str, patterns: Sequence[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(path_text, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(path_text, pattern[3:]):
            return True
    return False


def is_probably_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    sample = data[:2048]
    return sample.decode("utf-8", errors="ignore").encode("utf-8", errors="ignore") is not None


def detect_subtype_from_path(relative_path: Path) -> str:
    name = relative_path.name.lower()
    suffix = relative_path.suffix.lower()
    posix = relative_path.as_posix().lower()

    if "copilot-instructions" in posix or "agent-instruction" in posix:
        return "agent-instruction"
    if "checklist" in posix or "checklist" in name:
        return "checklist"
    if "plan" in posix or "roadmap" in posix:
        return "plan"
    if "manifest" in name:
        return "manifest"
    if "schema" in name or "/schema" in posix:
        return "schema"
    if suffix in (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cs", ".c", ".cpp", ".h", ".hpp", ".ps1", ".sh", ".bat", ".cmd", ".sql"):
        return "codeblock"
    if suffix in (".json", ".yaml", ".yml"):
        return "object"
    if suffix in (".md", ".txt", ".rst", ".adoc"):
        return "document"
    return "artifact"


def resolve_subtype(relative_path: Path, rules: Sequence[WrapperSubtypeRule], allowed: set[str]) -> str:
    rel_posix = relative_path.as_posix().lower()
    for rule in rules:
        if fnmatch.fnmatch(rel_posix, rule.pattern.lower()):
            if rule.subtype not in allowed:
                raise ValueError(f"Subtype rule resolved disallowed subtype: {rule.subtype}")
            return rule.subtype
    detected = detect_subtype_from_path(relative_path)
    if detected not in allowed:
        return "artifact"
    return detected


def build_udi(namespace: str, scope: str, kind: str, slug: str) -> str:
    udi = f"{namespace}.{scope}.{kind}.{slug}"
    import re

    if re.match(UDI_PATTERN, udi) is None:
        raise ValueError(f"Generated invalid UDI: {udi}")
    return udi


def build_cmf_payload(
    *,
    path: Path,
    input_root: Path,
    namespace: str,
    version: str,
    subtype: str,
    text: str,
    wrapper_version: str,
) -> dict[str, Any]:
    relative_path = path.relative_to(input_root)
    relative_parent = relative_path.parent
    scope = derive_scope(relative_parent)
    kind = f"wrapped-{subtype}"
    slug = derive_slug(relative_path)
    udi = build_udi(namespace, scope, kind, slug)
    source_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "id": slugify(relative_path.as_posix(), max_len=128),
        "udi": udi,
        "kind": kind,
        "version": version,
        "tenant": None,
        "metadata": {
            "name": relative_path.name,
            "source_file_type": path.suffix.lower().lstrip("."),
            "wrapped_subtype": subtype,
            "relative_path": relative_path.as_posix(),
            "wrapper_version": wrapper_version,
        },
        "source": {
            "path": relative_path.as_posix(),
            "encoding": "utf-8",
            "content_sha256": source_sha256,
        },
        "relations": [],
        "validation": {
            "udi_pattern": UDI_PATTERN,
            "deterministic": True,
            "immutable_identity": True,
        },
        "notes": [
            "Wrapped from existing Prismata repository artifact.",
            "Preserves source metadata for future unwrap support.",
        ],
        "content": {
            "text": text,
            "classification": {
                "subtype": subtype,
                "rationale": "path_and_filetype_inference",
            },
        },
    }


def iter_input_files(
    input_root: Path,
    include_globs: Sequence[str],
    exclude_globs: Sequence[str],
) -> Iterable[Path]:
    all_files = [p for p in input_root.rglob("*") if p.is_file()]
    for path in sorted(all_files):
        rel = path.relative_to(input_root).as_posix()
        if not matches_any(rel, include_globs):
            continue
        if matches_any(rel, exclude_globs):
            continue
        yield path


def write_payload_json(output_root: Path, input_root: Path, source_path: Path, payload: dict[str, Any]) -> Path:
    rel = source_path.relative_to(input_root)
    target = output_root / rel.parent / f"{rel.name}.cmf.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return target


def wrap_repository(
    *,
    input_root: Path,
    output_root: Path,
    namespace: str | None,
    subtype_rules: Sequence[WrapperSubtypeRule],
    allowed_subtypes: Sequence[str],
    include_globs: Sequence[str],
    exclude_globs: Sequence[str],
    version: str = "1.0.0",
    wrapper_version: str = "1.0.0",
    dry_run: bool = False,
) -> dict[str, Any]:
    if not input_root.exists() or not input_root.is_dir():
        raise ValueError(f"Input root does not exist or is not a directory: {input_root}")

    ns = derive_namespace(namespace, input_root)
    allowed = set(allowed_subtypes)
    unknown = [item for item in allowed if item not in ALLOWED_SUBTYPES]
    if unknown:
        raise ValueError(f"Unknown allowed subtype values: {', '.join(sorted(unknown))}")

    udi_seen: dict[str, str] = {}
    written: list[str] = []
    skipped_binary: list[str] = []
    skipped_decode: list[str] = []
    collisions: list[str] = []

    for source_path in iter_input_files(input_root, include_globs, exclude_globs):
        rel = source_path.relative_to(input_root).as_posix()
        raw = source_path.read_bytes()
        if not is_probably_text(raw):
            skipped_binary.append(rel)
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            skipped_decode.append(rel)
            continue

        subtype = resolve_subtype(source_path.relative_to(input_root), subtype_rules, allowed)
        payload = build_cmf_payload(
            path=source_path,
            input_root=input_root,
            namespace=ns,
            version=version,
            subtype=subtype,
            text=text,
            wrapper_version=wrapper_version,
        )
        if payload["udi"] in udi_seen:
            collisions.append(payload["udi"])
            continue
        udi_seen[payload["udi"]] = rel
        rel_output = (source_path.relative_to(input_root).parent / f"{source_path.name}.cmf.json").as_posix()
        written.append(rel_output)
        if not dry_run:
            output_path = write_payload_json(output_root, input_root, source_path, payload)
            written[-1] = output_path.relative_to(output_root).as_posix()

    if collisions:
        raise ValueError(f"UDI collisions detected: {len(collisions)}")

    report = {
        "input_root": str(input_root),
        "output_root": str(output_root),
        "namespace": ns,
        "wrapped_count": len(written),
        "skipped_binary_count": len(skipped_binary),
        "skipped_decode_count": len(skipped_decode),
        "skipped_binary": skipped_binary,
        "skipped_decode": skipped_decode,
        "written": written,
    }
    if not dry_run:
        output_root.mkdir(parents=True, exist_ok=True)
        report_path = output_root / "_cmf_wrap_report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return report


def parse_subtype_rule(raw: str) -> WrapperSubtypeRule:
    if "=" not in raw:
        raise ValueError(f"Invalid subtype rule format: {raw}")
    pattern, subtype = raw.split("=", 1)
    pattern = pattern.strip()
    subtype = subtype.strip()
    if not pattern or not subtype:
        raise ValueError(f"Invalid subtype rule format: {raw}")
    return WrapperSubtypeRule(pattern=pattern, subtype=subtype)


def parse_csv_list(raw: str | None, default_values: Sequence[str]) -> tuple[str, ...]:
    if raw is None:
        return tuple(default_values)
    values = [v.strip() for v in raw.split(",")]
    return tuple(v for v in values if v)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wrap repository text files into CMF artifacts.")
    parser.add_argument("--input-root", required=True, help="Source repository root to wrap.")
    parser.add_argument("--output-root", required=True, help="Archive output root.")
    parser.add_argument("--namespace", help="UDI namespace segment. Defaults to input root name.")
    parser.add_argument("--version", default="1.0.0", help="CMF version field value.")
    parser.add_argument("--wrapper-version", default="1.0.0", help="Wrapper tool version metadata.")
    parser.add_argument(
        "--allow-subtypes",
        help="Comma-separated allowed subtypes. Defaults to full supported list.",
    )
    parser.add_argument(
        "--subtype-rule",
        action="append",
        default=[],
        help="Custom subtype mapping rule in format '<glob>=<subtype>'. Can be repeated.",
    )
    parser.add_argument(
        "--include",
        help="Comma-separated include globs relative to input root. Default: **/*",
    )
    parser.add_argument(
        "--exclude",
        help="Comma-separated exclude globs relative to input root.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run classification without writing files.")

    args = parser.parse_args(argv)
    include_globs = parse_csv_list(args.include, DEFAULT_INCLUDE_GLOBS)
    exclude_globs = parse_csv_list(args.exclude, DEFAULT_EXCLUDE_GLOBS)
    allowed_subtypes = parse_csv_list(args.allow_subtypes, ALLOWED_SUBTYPES)
    subtype_rules = [parse_subtype_rule(item) for item in args.subtype_rule]

    report = wrap_repository(
        input_root=Path(args.input_root),
        output_root=Path(args.output_root),
        namespace=args.namespace,
        subtype_rules=subtype_rules,
        allowed_subtypes=allowed_subtypes,
        include_globs=include_globs,
        exclude_globs=exclude_globs,
        version=args.version,
        wrapper_version=args.wrapper_version,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
