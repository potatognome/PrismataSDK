#!/usr/bin/env python3
"""Update CMF object versions by UDI pattern.

Usage:
  python set_versions_by_udi.py --folder PATH --version VALUE --udi PATTERN [PATTERN ...]
                                [--recursive] [--meta META_VERSION]
                                [--patch | --minor | --break]

Scans YAML files in --folder, finds CMF-eligible objects (top-level mapping with a
string `udi` field), and updates:
- top-level `version` to --version OR bumped version
- optional `metadata.schema_version` to --meta when provided

Wildcard UDI matching supports:
- `*` for zero or more characters
- `?` for a single character
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

try:
    import yaml
except Exception:
    yaml = None


def is_cmf_eligible_object(data: object) -> bool:
    """Return True for top-level mappings that expose a string UDI."""
    return isinstance(data, dict) and isinstance(data.get("udi"), str)


def iter_yaml_files(folder: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        for pattern in ("*.yaml", "*.yml"):
            yield from folder.rglob(pattern)
    else:
        for pattern in ("*.yaml", "*.yml"):
            yield from folder.glob(pattern)


def udi_matches(udi_value: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatchcase(udi_value, pattern) for pattern in patterns)


def bump_version(old: str, mode: str) -> str:
    """Return a bumped semantic version string."""
    try:
        major, minor, patch = map(int, old.split("."))
    except Exception:
        raise ValueError(f"Invalid semantic version: {old}")

    if mode == "patch":
        patch += 1
    elif mode == "minor":
        minor += 1
        patch = 0
    elif mode == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Unknown bump mode: {mode}")

    return f"{major}.{minor}.{patch}"


def update_file_versions(
    file_path: Path,
    target_version: str | None,
    udi_patterns: List[str],
    metadata_version: str | None,
    bump_mode: str | None,
) -> Tuple[bool, str]:
    """Update one file if it contains a matching CMF object.

    Returns:
      (changed, reason)
    """
    text = file_path.read_text(encoding="utf-8")

    try:
        assert yaml is not None
        data = yaml.safe_load(text)
    except Exception as exc:
        return False, f"parse-error: {exc}"

    if not is_cmf_eligible_object(data):
        return False, "not-cmf-eligible"

    udi_value = data["udi"]
    if not udi_matches(udi_value, udi_patterns):
        return False, "udi-no-match"

    changed = False

    # Determine new version
    current_version = data.get("version")

    if bump_mode is not None:
        try:
            new_version = bump_version(current_version, bump_mode)
        except Exception as exc:
            return False, f"version-bump-error: {exc}"
    else:
        new_version = target_version

    if current_version != new_version:
        data["version"] = new_version
        changed = True

    # Metadata version update
    if metadata_version is not None:
        metadata = data.get("metadata")
        if metadata is None:
            metadata = {}
            data["metadata"] = metadata
        if not isinstance(metadata, dict):
            return False, "metadata-not-mapping"
        if metadata.get("schema_version") != metadata_version:
            metadata["schema_version"] = metadata_version
            changed = True

    if not changed:
        return False, "already-up-to-date"

    rendered = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=False,
        default_flow_style=False,
    )
    file_path.write_text(rendered, encoding="utf-8")
    return True, "updated"


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update CMF object versions by UDI pattern")

    parser.add_argument("--folder", "-f", required=True, help="Folder path to scan")

    parser.add_argument("--version", "-v", help="Version value to set (x.y.z)")

    parser.add_argument(
        "--udi",
        "-u",
        required=True,
        nargs="+",
        help="One or more UDI patterns (supports * and ? wildcards)",
    )

    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recursively search under --folder",
    )

    parser.add_argument(
        "--meta",
        "-m",
        help="Optional metadata schema version value to set at metadata.schema_version",
    )

    # New bump arguments
    parser.add_argument(
        "--patch", "-p",
        action="store_true",
        help="Bump patch version (x.y.z → x.y.z+1). Smallest bump."
    )
    parser.add_argument(
        "--minor", "-m2",
        action="store_true",
        help="Bump minor version (x.y.z → x.y+1.0). Middle bump."
    )
    parser.add_argument(
        "--breaking", "-b",
        action="store_true",
        help="Bump major version (x.y.z → x+1.0.0). Largest bump."
    )

    args = parser.parse_args(argv)

    if yaml is None:
        print("PyYAML is required to run this script.", file=sys.stderr)
        return 2

    # Validate version/bump requirements
    bump_modes = [args.patch, args.minor, args.breaking]

    if args.version is None and not any(bump_modes):
        print("ERROR: Must specify --version or one of -p/--patch, -m2/--minor, -b/--break")
        return 2

    if sum(bump_modes) > 1:
        print("ERROR: Only one bump mode may be used at a time.")
        return 2

    # Resolve bump mode
    if args.patch:
        bump_mode = "patch"
    elif args.minor:
        bump_mode = "minor"
    elif args.breaking:
        bump_mode = "major"
    else:
        bump_mode = None

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        print(f"Folder does not exist or is not a directory: {folder}", file=sys.stderr)
        return 2

    scanned = 0
    updated = 0
    matched = 0
    parse_errors = 0
    metadata_errors = 0

    for file_path in iter_yaml_files(folder, args.recursive):
        scanned += 1
        changed, reason = update_file_versions(
            file_path=file_path,
            target_version=args.version,
            udi_patterns=args.udi,
            metadata_version=args.meta,
            bump_mode=bump_mode,
        )

        if reason == "parse-error":
            parse_errors += 1
            print(f"WARN {file_path}: {reason}")
            continue

        if reason == "metadata-not-mapping":
            metadata_errors += 1
            print(f"WARN {file_path}: {reason}")
            continue

        if reason in ("updated", "already-up-to-date"):
            matched += 1

        if changed:
            updated += 1
            print(f"UPDATED {file_path}")

    print("\nSummary")
    print(f"  scanned files : {scanned}")
    print(f"  matched UDI   : {matched}")
    print(f"  updated files : {updated}")
    print(f"  parse errors  : {parse_errors}")
    print(f"  meta errors   : {metadata_errors}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
