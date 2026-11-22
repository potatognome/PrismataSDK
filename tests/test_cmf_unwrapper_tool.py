from __future__ import annotations

import hashlib
import json
from pathlib import Path

from core.ops.unwrap_cmf_archive import unwrap_archive


def _write_wrapped(path: Path, source_path: str, text: str, kind: str = "wrapped-document") -> None:
    payload = {
        "id": "example",
        "udi": "prismata.docs.wrapped-document.example",
        "kind": kind,
        "version": "1.0.0",
        "source": {
            "path": source_path,
            "encoding": "utf-8",
            "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "content": {"text": text},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def test_unwrap_writes_restored_file_without_datestamp(tmp_path: Path):
    input_root = tmp_path / "wrapped"
    output_root = tmp_path / "restored"
    _write_wrapped(input_root / "docs" / "guide.md.cmf.json", "docs/guide.md", "# Guide\n")

    report = unwrap_archive(
        input_root=input_root,
        output_root=output_root,
        include_globs=("**/*.cmf.json",),
        exclude_globs=(),
        datestamp_output=False,
    )

    assert report["restored_count"] == 1
    assert (output_root / "docs" / "guide.md").read_text(encoding="utf-8") == "# Guide\n"


def test_unwrap_dry_run_does_not_write(tmp_path: Path):
    input_root = tmp_path / "wrapped"
    output_root = tmp_path / "restored"
    _write_wrapped(input_root / "docs" / "note.md.cmf.json", "docs/note.md", "note\n")

    report = unwrap_archive(
        input_root=input_root,
        output_root=output_root,
        include_globs=("**/*.cmf.json",),
        exclude_globs=(),
        dry_run=True,
        datestamp_output=False,
    )

    assert report["restored_count"] == 1
    assert not (output_root / "docs" / "note.md").exists()


def test_unwrap_conflict_skip_policy(tmp_path: Path):
    input_root = tmp_path / "wrapped"
    output_root = tmp_path / "restored"
    _write_wrapped(input_root / "docs" / "existing.md.cmf.json", "docs/existing.md", "wrapped\n")
    (output_root / "docs").mkdir(parents=True)
    (output_root / "docs" / "existing.md").write_text("original\n", encoding="utf-8")

    report = unwrap_archive(
        input_root=input_root,
        output_root=output_root,
        include_globs=("**/*.cmf.json",),
        exclude_globs=(),
        on_conflict="skip",
        datestamp_output=False,
    )

    assert report["skipped_count"] == 1
    assert (output_root / "docs" / "existing.md").read_text(encoding="utf-8") == "original\n"


def test_unwrap_sanitizes_unsafe_source_path(tmp_path: Path):
    input_root = tmp_path / "wrapped"
    output_root = tmp_path / "restored"
    _write_wrapped(input_root / "x.cmf.json", "../../escape.txt", "safe\n")

    report = unwrap_archive(
        input_root=input_root,
        output_root=output_root,
        include_globs=("**/*.cmf.json",),
        exclude_globs=(),
        datestamp_output=False,
    )

    assert report["restored_count"] == 1
    assert (output_root / "escape.txt").read_text(encoding="utf-8") == "safe\n"


def test_unwrap_warns_on_digest_mismatch_by_default(tmp_path: Path):
    input_root = tmp_path / "wrapped"
    output_root = tmp_path / "restored"
    _write_wrapped(input_root / "x.cmf.json", "docs/x.md", "one\n")
    payload = json.loads((input_root / "x.cmf.json").read_text(encoding="utf-8"))
    payload["source"]["content_sha256"] = "00" * 32
    (input_root / "x.cmf.json").write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    report = unwrap_archive(
        input_root=input_root,
        output_root=output_root,
        include_globs=("**/*.cmf.json",),
        exclude_globs=(),
        datestamp_output=False,
    )

    assert report["restored_count"] == 1
    assert report["warning_count"] >= 1
