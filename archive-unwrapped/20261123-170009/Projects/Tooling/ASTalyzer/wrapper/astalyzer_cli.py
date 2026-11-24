import sys
import os
import subprocess
import tempfile
import json
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from dataclasses import asdict
import importlib.util

# Ensure the canonical primitives/python folder is on `sys.path` so local modules
# can be imported when running the wrapper directly.
from pathlib import Path as _Path
_this_file = _Path(__file__).resolve()
# parents: 0=wrapper, 1=ASTalyzer, 2=Tooling
_primitives_python_dir = _this_file.parents[2] / "primitives" / "python"
if str(_primitives_python_dir) not in sys.path:
    sys.path.insert(0, str(_primitives_python_dir))

# import menu helpers from local primitives (optional)
try:
    from Prismata.Projects.Tooling.primitives.python import menu_helpers as mh
    from Prismata.Projects.Tooling.primitives.python.dialog_helpers import select_scan_path, select_save_path
except Exception as e:  # pragma: no cover - optional dependency
    mh = None
    select_scan_path = None
    select_save_path = None
    print(f"Warning: could not import menu_helpers ({e}). YAML menus will be disabled.")


# Simple wrapper skeleton for running the project's ASTalyzer safely
# - Runs the existing `main.py` scanner in the ASTalyzer project root
# - Captures stdout/stderr to a temporary file
# - Provides summary (count + top paths) and actions to view/save output


AST_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CMD = [sys.executable, "main.py"]


def _choose_default_command() -> list:
    """Prefer running the TypeScript entrypoint if available, else Python main.py.

    Returns a command list (to be executed with subprocess.run) relative to AST_ROOT.
    """
    ts_entry = AST_ROOT / "src" / "astalyzer" / "main.ts"
    # Prefer npx+tsx when available
    if ts_entry.exists() and shutil.which("npx"):
        return ["npx", "tsx", str(Path("src/astalyzer/main.ts"))]
    # Fallback to ts-node if present
    if ts_entry.exists() and shutil.which("ts-node"):
        return ["ts-node", str(Path("src/astalyzer/main.ts"))]
    # Else use python implementation
    return DEFAULT_CMD




def run_astalyzer(scan_path: str = ".",
                  cmd: Optional[list] = None,
                  timeout: int = 300) -> Tuple[Path, Dict[str, Any]]:
    """Run the AST analyzer (project main.py) and save output to a temp file.

    Returns (temp_path, summary_dict).
    Summary contains at least: `modules_count` and `top_paths`.
    """
    cmd = cmd or _choose_default_command()
    # Ensure working directory is AST_ROOT
    cwd = AST_ROOT

    # Build command: always append the scan path argument
    run_cmd = list(cmd) + [scan_path]

    with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".json") as tf:
        temp_path = Path(tf.name)
        try:
            # If we're running the Python fallback (DEFAULT_CMD), inline the analyzer
            if cmd == DEFAULT_CMD:
                # Import the project's main.py in-process and call scan_project
                main_path = AST_ROOT / "main.py"
                if main_path.exists():
                    try:
                        spec = importlib.util.spec_from_file_location("astalyzer_main", str(main_path))
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)  # type: ignore[attr-defined]
                        results = module.scan_project(scan_path)
                        # Convert dataclasses to dicts
                        out = [asdict(m) for m in results]
                        tf.write(json.dumps(out, indent=2, default=str).encode("utf-8"))
                    except Exception as e:
                        tf.write(f"In-process analyzer failed: {e}\n".encode("utf-8"))
                else:
                    # Fall back to subprocess if main.py missing
                    proc = subprocess.run(run_cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
                    tf.write(proc.stdout)
                    if proc.stderr:
                        tf.write(b"\n\n--- STDERR ---\n\n")
                        tf.write(proc.stderr)
            else:
                proc = subprocess.run(run_cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
                # Write both stdout and stderr for completeness
                tf.write(proc.stdout)
                if proc.stderr:
                    tf.write(b"\n\n--- STDERR ---\n\n")
                    tf.write(proc.stderr)

        except FileNotFoundError as fnf:
            # Command executable not found (e.g. `npx`/`tsx` missing). Record the error
            msg = f"Command not found: {run_cmd[0]} -- {fnf}\n"
            tf.write(msg.encode("utf-8"))
            # If the attempted command wasn't the Python fallback, try running the Python `main.py`
            if cmd != DEFAULT_CMD:
                try:
                    fallback_cmd = list(DEFAULT_CMD) + [scan_path]
                    tf.write(b"\nAttempting fallback to Python main.py...\n")
                    proc = subprocess.run(fallback_cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
                    tf.write(proc.stdout)
                    if proc.stderr:
                        tf.write(b"\n\n--- STDERR (fallback) ---\n\n")
                        tf.write(proc.stderr)
                except FileNotFoundError:
                    tf.write(b"\nFallback Python executable not found.\n")
            temp_path = Path(tf.name)

        except subprocess.TimeoutExpired:
            tf.write(f"TIMEOUT after {timeout}s\n".encode("utf-8"))
            temp_path = Path(tf.name)

    # Try to load JSON summary if possible
    summary: Dict[str, Any] = {"modules_count": None, "top_paths": []}
    try:
        with open(temp_path, "r", encoding="utf-8") as fh:
            text = fh.read()

            def _load_first_json_blob(raw: str):
                starts = []
                for i, ch in enumerate(raw):
                    if ch in "[{":
                        starts.append(i)
                for idx in starts:
                    try:
                        return json.loads(raw[idx:])
                    except Exception:
                        continue
                raise ValueError("No JSON payload found")

            data = _load_first_json_blob(text)
            if isinstance(data, list):
                summary["modules_count"] = len(data)
                # collect top file paths
                paths = []
                for m in data[:20]:
                    p = m.get("file_path") if isinstance(m, dict) else None
                    if p:
                        paths.append(p)
                summary["top_paths"] = paths
            elif isinstance(data, dict):
                scanned = data.get("files_scanned")
                if isinstance(scanned, list):
                    summary["modules_count"] = len(scanned)
                    summary["top_paths"] = scanned[:20]

    except Exception:
        # Could not parse JSON (maybe stderr appended) — provide a best-effort summary
        try:
            with open(temp_path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
                summary["preview_lines"] = lines[:50]
        except Exception:
            summary["error"] = "Could not read output file"

    return temp_path, summary


def view_output(path: Path) -> None:
    """Open the output file in a pager or print a preview if no pager available."""
    if os.name == "nt":
        # Windows: try `more`, else open in notepad
        if shutil.which("more"):
            os.system(f"more {str(path)}")
            return
        try:
            os.startfile(str(path))
            return
        except Exception:
            # fallback to printing preview
            pass
    else:
        pager = shutil.which("less") or shutil.which("more")
        if pager:
            os.execvp(pager, [pager, str(path)])
        else:
            # Fallback: print first 200 lines
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh):
                    if i >= 200:
                        break
                    print(line, end="")


def save_output(temp_path: Path, dest: str) -> Path:
    dest_path = Path(dest).expanduser()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(temp_path), str(dest_path))
    return dest_path


def load_menu_yaml(menu_path: Optional[str] = None):
    """Load a single YAML menu as a dict, fallback to None.

    Prefer using the menu registry loader from `menu_helpers` for full registry support.
    """
    menu_file = menu_path or (AST_ROOT / "config" / "project.menus")
    if not Path(menu_file).exists():
        return None
    # Use menu_helpers to load registry
    try:
        registry, default_id = mh.load_yaml_menu_registry(Path(menu_file))
        return registry, default_id
    except Exception:
        return None


def simple_console_menu():
    last_output: Optional[Path] = None

    while True:
        print("\nASTalyzer — Menu")
        print("1) Run ASTalyzer (default main.py)")
        print("2) View last output")
        print("3) Save last output to file")
        print("4) Exit")
        choice = input("Choose: ").strip()
        if choice == "1":
            scan = select_scan_path(lambda msg: input(f"{msg}: ").strip())
            print("Running ASTalyzer — this may take a while...")
            temp_path, summary = run_astalyzer(scan)
            last_output = temp_path
            print("Summary:")
            print(json.dumps(summary, indent=2, default=str))
        elif choice == "2":
            if last_output and last_output.exists():
                view_output(last_output)
            else:
                print("No output available. Run ASTalyzer first.")
        elif choice == "3":
            if last_output and last_output.exists():
                default_name = last_output.name if last_output else "astalyzer-output.json"
                dest = select_save_path(lambda msg: input(f"{msg}: ").strip(), default_name)
                if dest:
                    out = save_output(last_output, dest)
                    print(f"Saved to {out}")
            else:
                print("No output available. Run ASTalyzer first.")
        elif choice == "4":
            break
        else:
            print("Unknown choice")


def run_menu_registry_loop(registry: Dict[str, Dict[str, Any]], default_menu_id: Optional[str]):
    last_output: Optional[Path] = None
    menu_stack = [default_menu_id] if default_menu_id else []

    # helpers expected by menu_helpers.render_external_menu
    def clog(*parts: object, **kwargs: Any) -> None:
        # first arg is colour token in this codebase
        try:
            mh.colour_log_safe(None, *parts, **kwargs)
        except Exception:
            print(" ".join(str(p) for p in parts))

    def border(title: str) -> None:
        try:
            mh.apply_bordered_header(None, title)
        except Exception:
            print(f"== {title} ==")

    prompt = mh.prompt_input

    current_menu = default_menu_id
    import ast as _ast

    while True:
        action = mh.render_external_menu(current_menu, registry, border=border, clog=clog, prompt=prompt)
        if not action:
            break

        # Try to interpret action: it may be a plain string or a stringified dict
        capability_id = None
        action_val = action
        try:
            maybe = _ast.literal_eval(action)
            if isinstance(maybe, dict):
                capability_id = maybe.get("capability_id") or maybe.get("id")
                action_val = capability_id or str(maybe)
        except Exception:
            # not a literal dict, keep as string
            action_val = str(action)

        action_lower = (action_val or "").strip().lower()
        if action_lower in ("quit", "exit"):
            break
        if action_lower in ("back", "menu_back"):
            if len(menu_stack) > 1:
                menu_stack.pop()
                current_menu = menu_stack[-1]
                continue
            break
        if action_lower in registry and action_lower != current_menu:
            menu_stack.append(action_lower)
            current_menu = action_lower
            continue
        # Map known capability IDs from YAML to actions
        if action_lower in ("prismata.astalyzer.capability.scan-api-recursive", "astalyzer.scan_api_recursive", "scan_api_recursive", "run_astalyzer"):
            scan = select_scan_path(prompt)
            temp_path, summary = run_astalyzer(scan)
            last_output = temp_path
            clog("!info", "Summary:")
            clog("!info", json.dumps(summary, indent=2, default=str))
            continue
        if capability_id:
            clog("!warn", f"Capability not implemented: {capability_id}")
            continue
        if action_lower in ("view_last_output", "view_output"):
            if last_output and last_output.exists():
                view_output(last_output)
            else:
                clog("!warn", "No output available. Run ASTalyzer first.")
            continue
        if action_lower in ("save_last_output", "save_output"):
            if last_output and last_output.exists():
                default_name = last_output.name if last_output else "astalyzer-output.json"
                dest = select_save_path(prompt, default_name)
                if dest:
                    out = save_output(last_output, dest)
                    clog("!info", f"Saved to {out}")
            else:
                clog("!warn", "No output available. Run ASTalyzer first.")
            continue

        # Unknown actions are ignored gracefully
        clog("!warn", f"Unknown action: {action}")


def main():
    # Attempt to load YAML menu (not required) — else fallback to simple console menu
    result = load_menu_yaml()
    if not result:
        simple_console_menu()
        return

    registry, default_id = result
    if registry:
        run_menu_registry_loop(registry, default_id)
    else:
        simple_console_menu()


if __name__ == "__main__":
    main()
