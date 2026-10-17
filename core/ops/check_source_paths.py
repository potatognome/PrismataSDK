#!/usr/bin/env python3
"""Validator: check CMF envelope `source.path` entries against actual filesystem paths.

Usage:
  python check_source_paths.py --folder PATH [--log logfile.txt]

Scans YAML files recursively under --folder. For each file containing a top-level
`source.path` entry, resolves the path (relative paths are resolved relative to
the CMF file's directory) and reports whether the referenced file exists.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import yaml
except Exception:
    yaml = None


def parse_source_path_from_text(text: str) -> Optional[str]:
    """Fallback parser to extract a `source.path:` value from YAML text.
    This is indentation-aware but simplistic: it finds the `source:` block and
    then looks for `path:` inside that block.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("source:"):
            base_indent = len(line) - len(line.lstrip())
            # search following lines for a `path:` with greater indent
            for j in range(i + 1, min(i + 50, len(lines))):
                l = lines[j]
                if not l.strip():
                    continue
                indent = len(l) - len(l.lstrip())
                if indent <= base_indent:
                    # left the source block
                    break
                if l.strip().startswith("path:"):
                    # naive split
                    _, _, val = l.partition(":")
                    return val.strip().strip('"').strip("'")
    return None


def extract_source_path(file_path: Path) -> Optional[str]:
    text = file_path.read_text(encoding="utf-8")
    if yaml:
        try:
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                src = data.get("source")
                if isinstance(src, dict):
                    p = src.get("path")
                    if isinstance(p, str):
                        return p
        except Exception:
            # fall back to text parse
            pass
    return parse_source_path_from_text(text)


def extract_udi(file_path: Path) -> Optional[str]:
    text = file_path.read_text(encoding="utf-8")
    if yaml:
        try:
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                u = data.get("udi")
                if isinstance(u, str):
                    return u
        except Exception:
            # fall back to text parse
            pass
    return parse_udi_from_text(text)

def parse_udi_from_text(text: str) -> Optional[str]:
    """Fallback parser to extract a `udi:` value from YAML text."""
    lines = text.splitlines()
    for line in lines:
        if line.strip().startswith("udi:"):
            _, _, val = line.partition(":")
            return val.strip().strip('"').strip("'")
    return None

def normalize_display_path(path_value: str) -> str:
    """Normalize resolved path display for CLI output."""
    text = str(path_value).replace("\\", "/")
    project_prefix = "C:/Repository/Daniel/dev_local/PrismataCore/"
    if text.startswith(project_prefix):
        text = text[len(project_prefix):]
    return text


def scan_folder(folder: Path) -> List[Tuple[str, str, str, bool]]:
    results: List[Tuple[str, str, str, bool]] = []
    for p in folder.rglob("*.yaml"):
        try:
            src = extract_source_path(p)
            if not src:
                continue
            udi_value = extract_udi(p) or ""
            # resolve source path relative to the CMF file if not absolute
            candidate = Path(src)
            resolved_candidate: Optional[Path] = None
            # Try multiple resolution strategies for relative paths
            try_paths = []
            if candidate.is_absolute():
                try_paths.append(candidate)
            else:
                # relative to the CMF file directory
                try_paths.append((p.parent / candidate))
                # try resolving by walking up ancestor directories and appending candidate
                for ancestor in [p.parent] + list(p.parents):
                    try_paths.append((ancestor / candidate))
                # relative to the current working directory (repo root when run from project)
                try_paths.append((Path.cwd() / candidate))
                # as-is (may be relative to CWD)
                try_paths.append(candidate)
            for c in try_paths:
                try:
                    cabs = c.resolve()
                except Exception:
                    cabs = c
                if cabs.exists():
                    resolved_candidate = cabs
                    break
            # if none found, pick the first strategy's resolved path for display
            resolved_display = resolved_candidate or (try_paths[0].resolve() if try_paths else candidate.resolve())
            exists = resolved_candidate is not None
            results.append((udi_value, src, normalize_display_path(str(resolved_display)), exists))
        except Exception as exc:
            print(f"Warning: failed parsing {p}: {exc}")
    return results


def print_table(rows: List[Tuple[str, str, str, bool]], out=sys.stdout) -> None:
    # columns: UDI, source_path, resolved_path, match
    col1 = "UDI"
    col2 = "Source Path"
    col3 = "Resolved Path"
    col4 = "Match"
    widths = [90, 60, 110, 8]
    fmt = f"{{:<{widths[0]}}}  {{:<{widths[1]}}}  {{:<{widths[2]}}}  {{:<{widths[3]}}}\n"
    out.write(fmt.format(col1, col2, col3, col4))
    out.write("-" * (sum(widths) + 12) + "\n")
    for udi, src, resolved, exists in rows:
        out.write(fmt.format(str(udi), str(src), str(resolved), "OK" if exists else "NO"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check CMF source.path entries against actual files")
    parser.add_argument("--folder", "-f", required=True, help="Folder to scan (recursive)")
    parser.add_argument("--log", "-l", help="Optional logfile path to write results to")
    args = parser.parse_args(argv)
    folder = Path(args.folder)
    if not folder.exists():
        print(f"Folder does not exist: {folder}")
        return 2
    rows = scan_folder(folder)
    # print to terminal
    print_table(rows, out=sys.stdout)
    # optionally write to log
    if args.log:
        with open(args.log, "w", encoding="utf-8") as fh:
            print_table(rows, out=fh)
        print(f"Wrote log to {args.log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
