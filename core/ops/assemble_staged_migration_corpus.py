#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence


def _sanitize_rel_path(path_text: str) -> str:
    path_text = path_text.replace("\\", "/").strip()
    path_text = path_text.lstrip("/")
    parts: list[str] = []
    for part in PurePosixPath(path_text).parts:
        if part in ("", "."):
            continue
        if part == "..":
            continue
        parts.append(part)
    if not parts:
        return "recovered/unknown"
    return PurePosixPath(*parts).as_posix()


def _iter_inventory_rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"Invalid row type at {path}:{line_no}")
            yield obj


def assemble_staged_migration_corpus(
    *,
    wrapped_root: Path,
    review_root: Path,
    output_root: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    inventory_path = review_root / "artifact_inventory.jsonl"
    if not wrapped_root.exists() or not wrapped_root.is_dir():
        raise ValueError(f"wrapped_root does not exist: {wrapped_root}")
    if not inventory_path.exists():
        raise ValueError(f"Missing inventory file: {inventory_path}")

    rows = list(_iter_inventory_rows(inventory_path))
    lane_counts: Counter[str] = Counter()
    disposition_counts: Counter[str] = Counter()
    copied_count = 0
    indexed_only_count = 0
    missing_sources: list[str] = []
    gaps: list[dict[str, Any]] = []
    planning_and_instruction: list[dict[str, Any]] = []

    for row in rows:
        wrapped_path = str(row.get("wrapped_path", "")).strip()
        source_path = str(row.get("source_path", "")).strip()
        target_repo = str(row.get("target_repo", "NeedsReview")).strip() or "NeedsReview"
        disposition = str(row.get("disposition", "review")).strip() or "review"
        tags = row.get("tags")
        tags_list = [str(t) for t in tags] if isinstance(tags, list) else []

        lane_counts[target_repo] += 1
        disposition_counts[disposition] += 1

        if target_repo == "NeedsReview" or disposition in {"review", "deprecate", "quarantine-runtime"}:
            gaps.append(
                {
                    "source_path": source_path,
                    "wrapped_path": wrapped_path,
                    "target_repo": target_repo,
                    "disposition": disposition,
                    "tags": tags_list,
                }
            )

        if "planning" in tags_list or "instruction" in tags_list:
            planning_and_instruction.append(
                {
                    "source_path": source_path,
                    "wrapped_path": wrapped_path,
                    "target_repo": target_repo,
                    "disposition": disposition,
                    "tags": tags_list,
                }
            )

        if target_repo == "ArchiveOnly":
            indexed_only_count += 1
            continue

        source_file = wrapped_root / wrapped_path
        if not source_file.exists():
            missing_sources.append(wrapped_path)
            continue

        safe_source_path = _sanitize_rel_path(source_path or wrapped_path)
        lane_root = output_root / "artifacts" / target_repo
        destination = lane_root / f"{safe_source_path}.cmf.json"
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, destination)
        copied_count += 1

    report = {
        "wrapped_root": str(wrapped_root),
        "review_root": str(review_root),
        "output_root": str(output_root),
        "inventory_count": len(rows),
        "copied_count": copied_count,
        "indexed_only_count": indexed_only_count,
        "missing_source_count": len(missing_sources),
        "lane_counts": dict(sorted(lane_counts.items())),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "gap_count": len(gaps),
        "planning_instruction_count": len(planning_and_instruction),
        "dry_run": dry_run,
    }

    if dry_run:
        return report

    reports_root = output_root / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    (reports_root / "staging_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (reports_root / "compatibility_gaps.json").write_text(
        json.dumps(sorted(gaps, key=lambda item: item["source_path"]), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (reports_root / "planning_instruction_digest.json").write_text(
        json.dumps(sorted(planning_and_instruction, key=lambda item: item["source_path"]), indent=2, ensure_ascii=True)
        + "\n",
        encoding="utf-8",
    )
    (reports_root / "missing_sources.json").write_text(
        json.dumps(sorted(missing_sources), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble a staged migration corpus routed by Core/SDK/Corp ownership from review inventory."
    )
    parser.add_argument("--wrapped-root", required=True, help="Root of wrapped artifacts (e.g. archive-wrapped/Prismata).")
    parser.add_argument(
        "--review-root",
        required=True,
        help="Root containing artifact_inventory.jsonl (e.g. archive-wrapped/review-corpus).",
    )
    parser.add_argument("--output-root", required=True, help="Output root for staged migration corpus.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and summarize without writing staged files.")
    args = parser.parse_args(argv)

    report = assemble_staged_migration_corpus(
        wrapped_root=Path(args.wrapped_root),
        review_root=Path(args.review_root),
        output_root=Path(args.output_root),
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
