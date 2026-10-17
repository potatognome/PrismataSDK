#!/usr/bin/env python3
"""Validator: extract version fields from CMF YAML objects.

Usage:
  python extract_versions.py --folder PATH [--log logfile.txt]

Scans YAML files recursively under --folder. For each file that contains a
`udi` value, extracts the top-level `version` and any `metadata` fields that
contain version-like keys (e.g., `schema_version`). Outputs a table with
`udi`, `version`, and discovered metadata version fields.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except Exception:
    yaml = None


def parse_yaml_text_for_versions(text: str) -> Optional[Dict]:
    if yaml:
        try:
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    # fallback very small parser: look for `udi:` and `version:` and `metadata:` blocks
    # Not perfect; best-effort only.
    return None


def scan_folder(folder: Path) -> List[Tuple[str, Optional[str], Dict[str, str]]]:
    results: List[Tuple[str, Optional[str], Dict[str, str]]] = []
    for p in folder.rglob("*.yaml"):
        try:
            text = p.read_text(encoding="utf-8")
            data = parse_yaml_text_for_versions(text)
            if not data:
                # if YAML not available or parse failed, try simple regex for udi
                m = re.search(r"^udi:\s*(\S+)", text, flags=re.M)
                udi = m.group(1) if m else None
                # try top-level version
                mv = re.search(r"^version:\s*(\S+)", text, flags=re.M)
                version = mv.group(1) if mv else None
                meta_versions = {}
                # crude metadata schema_version search
                ms = re.search(r"schema_version:\s*(\S+)", text)
                if ms:
                    meta_versions["schema_version"] = ms.group(1)
                if udi:
                    results.append((udi, version, meta_versions))
                continue
            udi = data.get("udi")
            if not udi:
                continue
            top_version = data.get("version")
            meta = data.get("metadata") or {}
            meta_versions: Dict[str, str] = {}
            if isinstance(meta, dict):
                for k, v in meta.items():
                    if "version" in k.lower() or k.lower().endswith("_version"):
                        # convert to string
                        meta_versions[k] = str(v)
            results.append((udi, top_version, meta_versions))
        except Exception as exc:
            print(f"Warning: failed parsing {p}: {exc}")
    return results


def print_table(rows: List[Tuple[str, Optional[str], Dict[str, str]]], out=sys.stdout) -> None:
    # columns: udi, version, metadata_versions (joined)
    col1 = "UDI"
    col2 = "version"
    col3 = "metadata_versions"
    widths = [60, 12, 40]
    fmt = f"{{:<{widths[0]}}}  {{:<{widths[1]}}}  {{:<{widths[2]}}}\n"
    out.write(fmt.format(col1, col2, col3))
    out.write("-" * (sum(widths) + 4) + "\n")
    for udi, version, meta_versions in rows:
        mv = ", ".join(f"{k}={v}" for k, v in meta_versions.items()) if meta_versions else ""
        out.write(fmt.format(udi[:widths[0]], str(version) if version is not None else "", mv[:widths[2]]))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract version fields from CMF YAML files")
    parser.add_argument("--folder", "-f", required=True, help="Folder to scan (recursive)")
    parser.add_argument("--log", "-l", help="Optional logfile path to write results to")
    args = parser.parse_args(argv)
    folder = Path(args.folder)
    if not folder.exists():
        print(f"Folder does not exist: {folder}")
        return 2
    rows = scan_folder(folder)
    print_table(rows, out=sys.stdout)
    if args.log:
        with open(args.log, "w", encoding="utf-8") as fh:
            print_table(rows, out=fh)
        print(f"Wrote log to {args.log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
