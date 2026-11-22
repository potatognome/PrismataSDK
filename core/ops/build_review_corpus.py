#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

DEFAULT_INCLUDE_GLOB = "**/*.cmf.json"


@dataclass(frozen=True)
class WrappedArtifact:
    wrapped_path: str
    source_path: str
    kind: str
    subtype: str
    owner: str
    disposition: str
    target_repo: str
    tags: tuple[str, ...]
    content_bytes: int


def _safe_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True)


def _derive_subtype(kind: str) -> str:
    if kind.startswith("wrapped-"):
        return kind[len("wrapped-") :]
    return "unknown"


def _classify_owner(source_path: str) -> str:
    if source_path.startswith("Meta/canonical/") or source_path.startswith("Meta/domain/"):
        return "core"
    if source_path.startswith("Projects/Tenant/"):
        return "corp"
    if source_path.startswith("Historical/"):
        return "historical"
    if source_path.startswith(".workspace/"):
        return "workspace-runtime"
    if source_path.startswith("Meta/registry/") or source_path.startswith("Meta/system/"):
        return "sdk"
    if source_path.startswith("Projects/"):
        return "sdk"
    if source_path.startswith(".github/"):
        return "sdk"
    return "review"


def _classify_disposition(source_path: str) -> str:
    if source_path.startswith("Meta/deprecated/"):
        return "deprecate"
    if source_path.startswith("Historical/"):
        return "preserve-historical"
    if source_path.startswith(".workspace/"):
        return "quarantine-runtime"
    if source_path.startswith("Meta/canonical/") or source_path.startswith("Meta/domain/"):
        return "transform-core-candidate"
    if source_path.startswith("Projects/Tenant/"):
        return "transform-corp-candidate"
    if source_path.startswith("Meta/registry/") or source_path.startswith("Meta/system/") or source_path.startswith("Projects/"):
        return "transform-sdk-candidate"
    return "review"


def _target_repo(owner: str) -> str:
    if owner == "core":
        return "PrismataCore"
    if owner == "sdk":
        return "PrismataSDK"
    if owner == "corp":
        return "PrismataCorp"
    if owner in {"historical", "workspace-runtime"}:
        return "ArchiveOnly"
    return "NeedsReview"


def _collect_tags(source_path: str, subtype: str) -> tuple[str, ...]:
    path = source_path.lower()
    tags: list[str] = []
    if any(token in path for token in ("plan", "roadmap", "migration", "checklist")):
        tags.append("planning")
    if "copilot-instructions" in path or "governance" in path:
        tags.append("instruction")
    if "schema" in path or subtype == "schema":
        tags.append("schema")
    if subtype in {"codeblock"} or source_path.endswith((".py", ".ts", ".js", ".go", ".ps1", ".sh", ".sql")):
        tags.append("code")
    if subtype in {"document", "plan", "checklist", "agent-instruction"}:
        tags.append("documentation")
    if "manifest" in path or subtype == "manifest":
        tags.append("manifest")
    if "registry" in path:
        tags.append("registry")
    if source_path.startswith(".workspace/"):
        tags.append("runtime-state")
    seen: set[str] = set()
    ordered: list[str] = []
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        ordered.append(tag)
    return tuple(ordered)


def _iter_wrapped_files(input_root: Path, include_glob: str) -> Iterable[Path]:
    for path in sorted(input_root.glob(include_glob)):
        if path.is_file():
            yield path


def _extract_source_path(payload: dict[str, Any], wrapped_rel: str) -> str:
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        rel = metadata.get("relative_path")
        if isinstance(rel, str) and rel.strip():
            return rel.strip().replace("\\", "/")
    source = payload.get("source")
    if isinstance(source, dict):
        rel = source.get("path")
        if isinstance(rel, str) and rel.strip():
            return rel.strip().replace("\\", "/")
    if wrapped_rel.endswith(".cmf.json"):
        return wrapped_rel[: -len(".cmf.json")]
    return wrapped_rel


def _extract_content_bytes(payload: dict[str, Any]) -> int:
    content = payload.get("content")
    if isinstance(content, dict) and isinstance(content.get("text"), str):
        return len(content["text"].encode("utf-8"))
    return len(_safe_json(content).encode("utf-8"))


def build_review_corpus(
    *,
    input_root: Path,
    output_root: Path,
    include_glob: str = DEFAULT_INCLUDE_GLOB,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not input_root.exists() or not input_root.is_dir():
        raise ValueError(f"Input root does not exist or is not a directory: {input_root}")

    artifacts: list[WrappedArtifact] = []
    invalid: list[dict[str, str]] = []
    planning_index: list[dict[str, Any]] = []

    for wrapped_path in _iter_wrapped_files(input_root, include_glob):
        wrapped_rel = wrapped_path.relative_to(input_root).as_posix()
        try:
            payload = json.loads(wrapped_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive for malformed archives
            invalid.append({"wrapped_path": wrapped_rel, "reason": f"invalid-json: {exc}"})
            continue

        kind = payload.get("kind")
        if not isinstance(kind, str):
            invalid.append({"wrapped_path": wrapped_rel, "reason": "missing-kind"})
            continue

        source_path = _extract_source_path(payload, wrapped_rel)
        subtype = _derive_subtype(kind)
        owner = _classify_owner(source_path)
        disposition = _classify_disposition(source_path)
        target_repo = _target_repo(owner)
        tags = _collect_tags(source_path, subtype)
        content_bytes = _extract_content_bytes(payload)

        item = WrappedArtifact(
            wrapped_path=wrapped_rel,
            source_path=source_path,
            kind=kind,
            subtype=subtype,
            owner=owner,
            disposition=disposition,
            target_repo=target_repo,
            tags=tags,
            content_bytes=content_bytes,
        )
        artifacts.append(item)

        if "planning" in tags or "instruction" in tags:
            planning_index.append(
                {
                    "source_path": source_path,
                    "wrapped_path": wrapped_rel,
                    "kind": kind,
                    "owner": owner,
                    "disposition": disposition,
                    "target_repo": target_repo,
                    "tags": list(tags),
                }
            )

    owner_counts = Counter(a.owner for a in artifacts)
    disposition_counts = Counter(a.disposition for a in artifacts)
    subtype_counts = Counter(a.subtype for a in artifacts)
    tag_counts = Counter(tag for a in artifacts for tag in a.tags)

    report = {
        "input_root": str(input_root),
        "output_root": str(output_root),
        "include_glob": include_glob,
        "artifact_count": len(artifacts),
        "invalid_count": len(invalid),
        "owner_counts": dict(sorted(owner_counts.items())),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "subtype_counts": dict(sorted(subtype_counts.items())),
        "tag_counts": dict(sorted(tag_counts.items())),
        "planning_index_count": len(planning_index),
        "total_content_bytes": sum(a.content_bytes for a in artifacts),
        "invalid": invalid,
    }

    if dry_run:
        return report

    output_root.mkdir(parents=True, exist_ok=True)

    (output_root / "review_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (output_root / "planning_index.json").write_text(
        json.dumps(sorted(planning_index, key=lambda row: row["source_path"]), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    with (output_root / "artifact_inventory.jsonl").open("w", encoding="utf-8") as fh:
        for item in sorted(artifacts, key=lambda a: a.source_path):
            row = {
                "source_path": item.source_path,
                "wrapped_path": item.wrapped_path,
                "kind": item.kind,
                "subtype": item.subtype,
                "owner": item.owner,
                "disposition": item.disposition,
                "target_repo": item.target_repo,
                "tags": list(item.tags),
                "content_bytes": item.content_bytes,
            }
            fh.write(_safe_json(row) + "\n")

    with (output_root / "compatibility_matrix.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=(
                "source_path",
                "wrapped_path",
                "kind",
                "owner",
                "disposition",
                "target_repo",
                "tags",
                "content_bytes",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        for item in sorted(artifacts, key=lambda a: a.source_path):
            writer.writerow(
                {
                    "source_path": item.source_path,
                    "wrapped_path": item.wrapped_path,
                    "kind": item.kind,
                    "owner": item.owner,
                    "disposition": item.disposition,
                    "target_repo": item.target_repo,
                    "tags": ";".join(item.tags),
                    "content_bytes": item.content_bytes,
                }
            )

    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a review corpus from wrapped CMF archive artifacts.")
    parser.add_argument("--input-root", required=True, help="Root directory containing wrapped *.cmf.json files.")
    parser.add_argument("--output-root", required=True, help="Output directory for review-corpus reports.")
    parser.add_argument("--include-glob", default=DEFAULT_INCLUDE_GLOB, help="Glob used to discover wrapped files.")
    parser.add_argument("--dry-run", action="store_true", help="Parse and classify without writing output files.")
    args = parser.parse_args(argv)

    report = build_review_corpus(
        input_root=Path(args.input_root),
        output_root=Path(args.output_root),
        include_glob=args.include_glob,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
