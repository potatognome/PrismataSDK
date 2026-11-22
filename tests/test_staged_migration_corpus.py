from __future__ import annotations

import json
from pathlib import Path

from core.ops.assemble_staged_migration_corpus import assemble_staged_migration_corpus


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_inventory(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def test_assemble_staged_corpus_routes_files_and_writes_reports(tmp_path: Path):
    wrapped_root = tmp_path / "wrapped"
    review_root = tmp_path / "review"
    output_root = tmp_path / "staged"

    _write_json(wrapped_root / "Meta" / "canonical" / "pane.schema.yaml.cmf.json", {"ok": True})
    _write_json(wrapped_root / ".github" / "copilot-instructions.md.cmf.json", {"ok": True})
    _write_json(wrapped_root / ".workspace" / "state.json.cmf.json", {"ok": True})

    _write_inventory(
        review_root / "artifact_inventory.jsonl",
        [
            {
                "source_path": "Meta/canonical/pane.schema.yaml",
                "wrapped_path": "Meta/canonical/pane.schema.yaml.cmf.json",
                "target_repo": "PrismataCore",
                "disposition": "transform-core-candidate",
                "tags": ["schema"],
            },
            {
                "source_path": ".github/copilot-instructions.md",
                "wrapped_path": ".github/copilot-instructions.md.cmf.json",
                "target_repo": "PrismataSDK",
                "disposition": "transform-sdk-candidate",
                "tags": ["instruction", "planning"],
            },
            {
                "source_path": ".workspace/state.json",
                "wrapped_path": ".workspace/state.json.cmf.json",
                "target_repo": "ArchiveOnly",
                "disposition": "quarantine-runtime",
                "tags": ["runtime-state"],
            },
        ],
    )

    report = assemble_staged_migration_corpus(
        wrapped_root=wrapped_root,
        review_root=review_root,
        output_root=output_root,
    )

    assert report["inventory_count"] == 3
    assert report["copied_count"] == 2
    assert (output_root / "artifacts" / "PrismataCore" / "Meta" / "canonical" / "pane.schema.yaml.cmf.json").exists()
    assert (output_root / "artifacts" / "PrismataSDK" / ".github" / "copilot-instructions.md.cmf.json").exists()
    assert not (output_root / "artifacts" / "ArchiveOnly").exists()
    assert (output_root / "reports" / "staging_report.json").exists()
    assert (output_root / "reports" / "compatibility_gaps.json").exists()
    assert (output_root / "reports" / "planning_instruction_digest.json").exists()

    gaps = json.loads((output_root / "reports" / "compatibility_gaps.json").read_text(encoding="utf-8"))
    assert len(gaps) == 1
    assert gaps[0]["disposition"] == "quarantine-runtime"
    assert report["indexed_only_count"] == 1


def test_assemble_staged_corpus_dry_run_does_not_write_output(tmp_path: Path):
    wrapped_root = tmp_path / "wrapped"
    review_root = tmp_path / "review"
    output_root = tmp_path / "staged"

    _write_json(wrapped_root / "docs" / "plan.md.cmf.json", {"ok": True})
    _write_inventory(
        review_root / "artifact_inventory.jsonl",
        [
            {
                "source_path": "docs/plan.md",
                "wrapped_path": "docs/plan.md.cmf.json",
                "target_repo": "NeedsReview",
                "disposition": "review",
                "tags": ["planning"],
            }
        ],
    )

    report = assemble_staged_migration_corpus(
        wrapped_root=wrapped_root,
        review_root=review_root,
        output_root=output_root,
        dry_run=True,
    )

    assert report["inventory_count"] == 1
    assert report["copied_count"] == 1
    assert report["gap_count"] == 1
    assert not output_root.exists()
