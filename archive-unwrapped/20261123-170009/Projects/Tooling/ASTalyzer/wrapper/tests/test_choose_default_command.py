import shutil
from Prismata.Projects.Tooling.ASTalyzer.wrapper.astalyzer_cli import _choose_default_command, DEFAULT_CMD


def test_choose_default_command_prefers_python_when_npx_missing(monkeypatch):
    # Simulate missing external tools (npx, ts-node) so chooser falls back to Python
    monkeypatch.setattr(
        "Prismata.Projects.Tooling.ASTalyzer.wrapper.astalyzer_cli.shutil.which",
        lambda name: None,
    )
    cmd = _choose_default_command()
    assert cmd == DEFAULT_CMD
