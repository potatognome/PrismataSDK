ASTalyzer wrapper (tUilKit / pcms-2026 menus)
==========================================

Purpose
-------
Lightweight Python wrapper that exposes the ASTalyzer tooling via the project's YAML menus (pcms-2026/tUilKit style) and provides safe execution of the analyzer so very large JSON output is captured to a temporary file and presented via a pager or saved to disk.

Location
--------
- Wrapper: `wrapper/astalyzer_cli.py`
- Menu YAML: `config/project.menus/astalyzer-main-menu.yaml`
- Smoke runner: `wrapper/tests/run_smoke.py`

Quick start
-----------
From the ASTalyzer project root run the interactive wrapper (falls back to a simple console menu when YAML/pyyaml is missing):

```bash
python wrapper/astalyzer_cli.py
```

Run the smoke script (no external deps required):

```bash
python wrapper/tests/run_smoke.py
```

Notes / dependencies
--------------------
- Python 3.8+ (used to run the wrapper).  
- Optional: `PyYAML` (`yaml`) to enable full YAML registry parsing. If not installed the wrapper falls back to a simple console menu.  
- Optional: `node` + `npx` + `tsx` (or `ts-node`) if you want the wrapper to prefer the TypeScript entrypoint in `src/astalyzer/main.ts`. If those are not available the wrapper will call the bundled `main.py`.

Behavior
--------
- `run_astalyzer()` executes the analyzer subprocess, captures stdout/stderr into a temporary JSON file, and returns a small summary (module count, top file paths) plus the tempfile path.  
- Use the menu actions `View last output` / `Save last output` to inspect or persist the full JSON output.

Extending
---------
- To integrate with an existing tUilKit runtime, replace the simple console fallback with calls into the project's menu factory.  
- The YAML menu loader uses `menu_helpers.load_yaml_menu_registry()` to discover menus under `config/project.menus/`.

License
-------
Follow the repository licensing (no new license added here).
