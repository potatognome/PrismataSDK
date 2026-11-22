from __future__ import annotations

import json
from pathlib import Path

from core.ops.wrap_repository_to_cmf import WrapperSubtypeRule, wrap_repository


def test_wrap_repository_writes_mirrored_outputs_with_wrapped_kind(tmp_path: Path):
    input_root = tmp_path / "Prismata"
    output_root = tmp_path / "archive"
    (input_root / "docs").mkdir(parents=True)
    (input_root / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")

    report = wrap_repository(
        input_root=input_root,
        output_root=output_root,
        namespace="prismata",
        subtype_rules=[],
        allowed_subtypes=("document", "artifact"),
        include_globs=("**/*",),
        exclude_globs=(),
    )

    assert report["wrapped_count"] == 1
    wrapped_file = output_root / "docs" / "guide.md.cmf.json"
    payload = json.loads(wrapped_file.read_text(encoding="utf-8"))
    assert payload["kind"] == "wrapped-document"
    assert payload["udi"].startswith("prismata.docs.wrapped-document.")


def test_wrap_repository_is_deterministic_for_same_input(tmp_path: Path):
    input_root = tmp_path / "Prismata"
    out_a = tmp_path / "archive_a"
    out_b = tmp_path / "archive_b"
    (input_root / "core").mkdir(parents=True)
    source = input_root / "core" / "module.py"
    source.write_text("print('ok')\n", encoding="utf-8")

    report_a = wrap_repository(
        input_root=input_root,
        output_root=out_a,
        namespace="prismata",
        subtype_rules=[],
        allowed_subtypes=("codeblock", "artifact"),
        include_globs=("**/*",),
        exclude_globs=(),
    )
    report_b = wrap_repository(
        input_root=input_root,
        output_root=out_b,
        namespace="prismata",
        subtype_rules=[],
        allowed_subtypes=("codeblock", "artifact"),
        include_globs=("**/*",),
        exclude_globs=(),
    )

    path_a = out_a / report_a["written"][0]
    path_b = out_b / report_b["written"][0]
    payload_a = json.loads(path_a.read_text(encoding="utf-8"))
    payload_b = json.loads(path_b.read_text(encoding="utf-8"))
    assert payload_a["udi"] == payload_b["udi"]
    assert payload_a["source"]["content_sha256"] == payload_b["source"]["content_sha256"]


def test_wrap_repository_skips_binary_files(tmp_path: Path):
    input_root = tmp_path / "Prismata"
    output_root = tmp_path / "archive"
    input_root.mkdir(parents=True)
    (input_root / "image.bin").write_bytes(b"\x00\x01\x02\x03")

    report = wrap_repository(
        input_root=input_root,
        output_root=output_root,
        namespace="prismata",
        subtype_rules=[],
        allowed_subtypes=("artifact",),
        include_globs=("**/*",),
        exclude_globs=(),
    )

    assert report["wrapped_count"] == 0
    assert report["skipped_binary_count"] == 1
    assert report["skipped_binary"] == ["image.bin"]


def test_wrap_repository_applies_custom_subtype_rule(tmp_path: Path):
    input_root = tmp_path / "Prismata"
    output_root = tmp_path / "archive"
    (input_root / ".github" / "copilot-instructions.d").mkdir(parents=True)
    path = input_root / ".github" / "copilot-instructions.d" / "policy.md"
    path.write_text("rules\n", encoding="utf-8")

    wrap_repository(
        input_root=input_root,
        output_root=output_root,
        namespace="prismata",
        subtype_rules=[WrapperSubtypeRule(pattern=".github/copilot-instructions.d/*", subtype="agent-instruction")],
        allowed_subtypes=("agent-instruction", "document", "artifact"),
        include_globs=("**/*",),
        exclude_globs=(),
    )

    payload = json.loads((output_root / ".github" / "copilot-instructions.d" / "policy.md.cmf.json").read_text(encoding="utf-8"))
    assert payload["kind"] == "wrapped-agent-instruction"


def test_wrap_repository_dry_run_reports_planned_wrapped_count(tmp_path: Path):
    input_root = tmp_path / "Prismata"
    output_root = tmp_path / "archive"
    (input_root / "docs").mkdir(parents=True)
    (input_root / "docs" / "one.md").write_text("one\n", encoding="utf-8")
    (input_root / "docs" / "two.md").write_text("two\n", encoding="utf-8")

    report = wrap_repository(
        input_root=input_root,
        output_root=output_root,
        namespace="prismata",
        subtype_rules=[],
        allowed_subtypes=("document", "artifact"),
        include_globs=("**/*",),
        exclude_globs=(),
        dry_run=True,
    )

    assert report["wrapped_count"] == 2
    assert sorted(report["written"]) == ["docs/one.md.cmf.json", "docs/two.md.cmf.json"]
    assert not output_root.exists()


def test_wrap_repository_numeric_filename_still_generates_valid_udi_slug(tmp_path: Path):
    input_root = tmp_path / "Prismata"
    output_root = tmp_path / "archive"
    (input_root / "docs").mkdir(parents=True)
    (input_root / "docs" / "2026-note.md").write_text("note\n", encoding="utf-8")

    wrap_repository(
        input_root=input_root,
        output_root=output_root,
        namespace="prismata",
        subtype_rules=[],
        allowed_subtypes=("document", "artifact"),
        include_globs=("**/*",),
        exclude_globs=(),
    )

    payload = json.loads((output_root / "docs" / "2026-note.md.cmf.json").read_text(encoding="utf-8"))
    slug = payload["udi"].split(".")[-1]
    assert slug[0].isalpha()
