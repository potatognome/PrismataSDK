import importlib.util
import sys
from pathlib import Path
import tempfile


def load_module_from_path(path: Path):
    spec = importlib.util.spec_from_file_location("astalyzer_cli", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    base = Path(__file__).resolve().parent.parent
    module_path = base / "astalyzer_cli.py"
    if not module_path.exists():
        print(f"Module not found: {module_path}")
        sys.exit(2)

    # ensure the canonical Tooling/primitives/python folder is on sys.path so local modules can be imported
    tooling_dir = module_path.resolve().parents[2]
    primitives_python_dir = tooling_dir / "primitives" / "python"
    if str(primitives_python_dir) not in sys.path:
        sys.path.insert(0, str(primitives_python_dir))

    # provide a minimal yaml shim if PyYAML isn't installed in this environment
    if 'yaml' not in sys.modules:
        import types

        def _safe_load(x):
            return {}

        yaml_stub = types.SimpleNamespace(safe_load=_safe_load)
        sys.modules['yaml'] = yaml_stub

    mod = load_module_from_path(module_path)

    # create tiny sample
    tmp = Path(tempfile.mkdtemp())
    sample = tmp / "sample"
    sample.mkdir()
    (sample / "a.py").write_text('def foo(x: int) -> int:\n    return x * 2\n')

    print(f"Running run_astalyzer on: {sample}")
    # call with explicit python + absolute main.py to avoid PATH issues
    main_py = module_path.resolve().parent.parent / "main.py"
    explicit_cmd = [sys.executable, str(main_py)]
    temp_path, summary = mod.run_astalyzer(str(sample), cmd=explicit_cmd, timeout=10)
    print("Summary:")
    print(summary)
    print("Temp file:", temp_path)
    sys.exit(0)


if __name__ == '__main__':
    main()
