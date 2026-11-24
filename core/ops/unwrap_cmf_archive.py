#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence

DEFAULT_INCLUDE_GLOBS = ("**/*.cmf.json",)
DEFAULT_EXCLUDE_GLOBS = (".git/**", "__pycache__/**", ".venv/**", ".pytest_cache/**")
CONFLICT_POLICIES = ("fail", "overwrite", "skip")


def matches_any(path_text: str, patterns: Sequence[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(path_text, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(path_text, pattern[3:]):
            return True
    return False


def parse_csv_list(raw: str | None, default_values: Sequence[str]) -> tuple[str, ...]:
    if raw is None:
        return tuple(default_values)
    values = [v.strip() for v in raw.split(",")]
    return tuple(v for v in values if v)


def datestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def iter_wrapped_files(input_root: Path, include_globs: Sequence[str], exclude_globs: Sequence[str]) -> Iterable[Path]:
    all_files = [p for p in input_root.rglob("*.cmf.json") if p.is_file()]
    for path in sorted(all_files):
        rel = path.relative_to(input_root).as_posix()
        if not matches_any(rel, include_globs):
            continue
        if matches_any(rel, exclude_globs):
            continue
        yield path


def sanitize_relative_path(path_text: str) -> str:
    normalized = str(path_text).replace("\\", "/")
    if ":" in normalized:
        normalized = normalized.split(":", 1)[1]
    normalized = normalized.lstrip("/")
    parts = []
    for part in PurePosixPath(normalized).parts:
        if part in ("", "."):
            continue
        if part == "..":
            continue
        parts.append(part)
    if not parts:
        return "recovered/unnamed.txt"
    return PurePosixPath(*parts).as_posix()


def derive_fallback_source_path(wrapped_rel: str) -> str:
    if wrapped_rel.endswith(".cmf.json"):
        return wrapped_rel[: -len(".cmf.json")]
    return f"recovered/{PurePosixPath(wrapped_rel).name}"


def should_accept_subtype(kind: str, allowed_subtypes: set[str] | None) -> bool:
    if not kind.startswith("wrapped-"):
        return False
    if allowed_subtypes is None:
        return True
    subtype = kind[len("wrapped-") :]
    return subtype in allowed_subtypes


def unwrap_archive(
    *,
    input_root: Path,
    output_root: Path,
    include_globs: Sequence[str],
    exclude_globs: Sequence[str],
    on_conflict: str = "overwrite",
    verify_digest: bool = True,
    strict: bool = False,
    allowed_subtypes: Sequence[str] | None = None,
    datestamp_output: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    if on_conflict not in CONFLICT_POLICIES:
        raise ValueError(f"Invalid conflict policy: {on_conflict}")
    if not input_root.exists() or not input_root.is_dir():
        raise ValueError(f"Input root does not exist or is not a directory: {input_root}")

    effective_output_root = output_root / datestamp() if datestamp_output else output_root
    allowed = set(allowed_subtypes) if allowed_subtypes else None

    restored: list[str] = []
    skipped: list[str] = []
    invalid: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    conflicts: list[str] = []

    for wrapped_path in iter_wrapped_files(input_root, include_globs, exclude_globs):
        wrapped_rel = wrapped_path.relative_to(input_root).as_posix()
        try:
            payload = json.loads(wrapped_path.read_text(encoding="utf-8"))
        except Exception as exc:
            invalid.append({"file": wrapped_rel, "reason": f"invalid-json: {exc}"})
            if strict:
                raise ValueError(f"Invalid JSON in wrapped artifact: {wrapped_rel}")
            continue

        kind = payload.get("kind")
        if not isinstance(kind, str) or not should_accept_subtype(kind, allowed):
            invalid.append({"file": wrapped_rel, "reason": "invalid-or-disallowed-kind"})
            if strict:
                raise ValueError(f"Invalid or disallowed wrapped kind: {wrapped_rel}")
            continue

        source = payload.get("source")
        source_path = ""
        if isinstance(source, dict) and isinstance(source.get("path"), str):
            source_path = source["path"]
        else:
            source_path = derive_fallback_source_path(wrapped_rel)
            warnings.append({"file": wrapped_rel, "warning": "missing-source-path-fallback-used"})

        content = payload.get("content")
        text: str | None = None
        if isinstance(content, dict) and isinstance(content.get("text"), str):
            text = content["text"]
        elif isinstance(content, dict):
            text = json.dumps(content, ensure_ascii=True, indent=2)
            warnings.append({"file": wrapped_rel, "warning": "missing-content-text-recovered-from-content-object"})
        else:
            invalid.append({"file": wrapped_rel, "reason": "missing-recoverable-content"})
            if strict:
                raise ValueError(f"Missing recoverable content in wrapped artifact: {wrapped_rel}")
            continue

        if verify_digest and isinstance(source, dict) and isinstance(source.get("content_sha256"), str):
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if digest != source["content_sha256"]:
                warnings.append({"file": wrapped_rel, "warning": "digest-mismatch"})
                if strict:
                    invalid.append({"file": wrapped_rel, "reason": "digest-mismatch"})
                    continue

        safe_rel = sanitize_relative_path(source_path)
        destination = effective_output_root / Path(safe_rel)
        destination_rel = destination.relative_to(effective_output_root).as_posix()

        if destination.exists():
            conflicts.append(destination_rel)
            if on_conflict == "fail":
                raise ValueError(f"Destination conflict: {destination}")
            if on_conflict == "skip":
                skipped.append(destination_rel)
                continue

        restored.append(destination_rel)
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with open(destination, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)

    report = {
        "mode": "snapshot",
        "input_root": str(input_root),
        "output_root": str(output_root),
        "effective_output_root": str(effective_output_root),
        "on_conflict": on_conflict,
        "verify_digest": verify_digest,
        "strict": strict,
        "datestamp_output": datestamp_output,
        "dry_run": dry_run,
        "restored_count": len(restored),
        "skipped_count": len(skipped),
        "invalid_count": len(invalid),
        "warning_count": len(warnings),
        "conflict_count": len(conflicts),
        "restored": restored,
        "skipped": skipped,
        "invalid": invalid,
        "warnings": warnings,
        "conflicts": conflicts,
    }
    if not dry_run:
        effective_output_root.mkdir(parents=True, exist_ok=True)
        report_path = effective_output_root / "_cmf_unwrap_report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Restore files from wrapped CMF archive artifacts.")
    parser.add_argument("--input-root", required=True, help="Root containing wrapped *.cmf.json artifacts.")
    parser.add_argument("--output-root", required=True, help="Root for restored output files.")
    parser.add_argument("--include", help="Comma-separated include globs. Default: **/*.cmf.json")
    parser.add_argument("--exclude", help="Comma-separated exclude globs.")
    parser.add_argument(
        "--on-conflict",
        choices=CONFLICT_POLICIES,
        default="overwrite",
        help="Conflict policy when destination file exists. Default: overwrite.",
    )
    parser.add_argument(
        "--allow-subtypes",
        help="Optional comma-separated wrapped subtypes to restore (e.g., document,codeblock).",
    )
    parser.add_argument("--strict", action="store_true", help="Treat recoverable warnings as strict failures.")
    parser.add_argument("--dry-run", action="store_true", help="Plan restore without writing files.")
    parser.add_argument(
        "--no-verify-digest",
        action="store_true",
        help="Disable digest verification against source.content_sha256.",
    )
    parser.add_argument(
        "--no-datestamp-output",
        action="store_true",
        help="Disable datestamped output folder suffix.",
    )

    args = parser.parse_args(argv)
    include_globs = parse_csv_list(args.include, DEFAULT_INCLUDE_GLOBS)
    exclude_globs = parse_csv_list(args.exclude, DEFAULT_EXCLUDE_GLOBS)
    allowed_subtypes = parse_csv_list(args.allow_subtypes, ()) if args.allow_subtypes else None

    report = unwrap_archive(
        input_root=Path(args.input_root),
        output_root=Path(args.output_root),
        include_globs=include_globs,
        exclude_globs=exclude_globs,
        on_conflict=args.on_conflict,
        verify_digest=not args.no_verify_digest,
        strict=args.strict,
        allowed_subtypes=allowed_subtypes,
        datestamp_output=not args.no_datestamp_output,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
