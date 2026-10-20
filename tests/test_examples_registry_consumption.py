import yaml
from pathlib import Path
from core.registry import RegistryLoader


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_examples_registry_build_pso():
    # Look for examples/registry in several candidate locations to be robust
    candidates = []
    p = Path(__file__).resolve()
    candidates.append(p.parents[2] / "examples" / "registry")
    candidates.append(p.parents[3] / "PrismataSDK" / "examples" / "registry")
    candidates.append(Path.cwd() / "examples" / "registry")
    candidates.append(Path.cwd() / "PrismataSDK" / "examples" / "registry")

    files = []
    for base in candidates:
        if base.exists():
            files = list(base.rglob("*.yaml"))
            if files:
                break

    assert files, f"No example YAML files found in candidates: {candidates}"

    count = 0
    for f in files:
        payload = _load_yaml(f)
        if not isinstance(payload, dict):
            continue
        # only attempt to build PSO for CMF-like objects
        if not all(k in payload for k in ("id", "udi", "kind", "version")):
            continue

        runtime = RegistryLoader.build_pso(payload["id"], payload)
        assert isinstance(runtime, dict)
        assert runtime.get("__pso__") is True
        assert runtime.get("kind") == str(payload.get("kind"))
        count += 1

    assert count > 0, "No CMF-style example objects were exercised"
