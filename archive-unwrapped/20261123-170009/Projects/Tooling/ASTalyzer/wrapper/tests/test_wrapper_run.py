import tempfile
import json
from pathlib import Path

from Prismata.Projects.Tooling.ASTalyzer.wrapper.astalyzer_cli import run_astalyzer


def test_run_astalyzer_on_small_sample(tmp_path: Path):
    # create a tiny sample project
    sample = tmp_path / "sample"
    sample.mkdir()
    (sample / "a.py").write_text("def foo(x: int) -> int:\n    return x * 2\n")

    temp_path, summary = run_astalyzer(str(sample))
    assert temp_path.exists()
    # summary should include either modules_count or preview_lines
    assert "modules_count" in summary or "preview_lines" in summary
    # cleanup
    temp_path.unlink(missing_ok=True)
