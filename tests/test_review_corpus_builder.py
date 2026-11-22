from __future__ import annotations

import json
from pathlib import Path

from core.ops.build_review_corpus import build_review_corpus


def _write_wrapped(path: Path, *, source_path: str, kind: str, text: str) -> None:
    payload = {
        "id": "sample",
        "udi": "prismata.sample.wrapped-document.sample",
        "kind": kind,
        "version": "1.0.0",
        "metadata": {"relative_path": source_path},
        "source": {"path": source_path, "encoding": "utf-8"},
        "content": {"text": text},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def test_build_review_corpus_writes_report_inventory_and_matrix(tmp_path: Path):
    input_root = tmp_path / "wrapped"
    output_root = tmp_path / "review"

    _write_wrapped(
        input_root / "Meta" / "canonical" / "object.schemas" / "pane.schema.yaml.cmf.json",
        source_path="Meta/canonical/object.schemas/pane.schema.yaml",
        kind="wrapped-schema",
        text="schema-content",
    )
    _write_wrapped(
        input_root / ".github" / "copilot-instructions.md.cmf.json",
        source_path=".github/copilot-instructions.md",
        kind="wrapped-agent-instruction",
        text="policy-content",
    )
    _write_wrapped(
        input_root / "Historical" / "plan-documents" / "migration-plan.md.cmf.json",
        source_path="Historical/plan-documents/migration-plan.md",
        kind="wrapped-plan",
        text="plan-content",
    )

    report = build_review_corpus(input_root=input_root, output_root=output_root)

    assert report["artifact_count"] == 3
    assert report["owner_counts"]["core"] == 1
    assert report["owner_counts"]["sdk"] == 1
    assert report["owner_counts"]["historical"] == 1
    assert (output_root / "review_report.json").exists()
    assert (output_root / "planning_index.json").exists()
    assert (output_root / "artifact_inventory.jsonl").exists()
    assert (output_root / "compatibility_matrix.csv").exists()


def test_build_review_corpus_classifies_workspace_as_quarantine(tmp_path: Path):
    input_root = tmp_path / "wrapped"
    output_root = tmp_path / "review"
    _write_wrapped(
        input_root / ".workspace" / "system" / "cache" / "state.json.cmf.json",
        source_path=".workspace/system/cache/state.json",
        kind="wrapped-object",
        text='{"ok": true}',
    )

    report = build_review_corpus(input_root=input_root, output_root=output_root)

    assert report["artifact_count"] == 1
    assert report["disposition_counts"]["quarantine-runtime"] == 1
    matrix = (output_root / "compatibility_matrix.csv").read_text(encoding="utf-8")
    assert "ArchiveOnly" in matrix
    assert "quarantine-runtime" in matrix
