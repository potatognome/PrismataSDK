from __future__ import annotations

from pathlib import Path
from typing import Iterable, List
import tempfile

from .path_helper import find_prismata_root


def _checklists_dir() -> Path:
    root = find_prismata_root()
    return root / ".workspace" / ".artifacts" / ".checklists"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _normalize_entry(e: str) -> str:
    return str(e).strip()


def add_entries(checklist_name: str, entries: Iterable[str]) -> None:
    """Append entries to a checklist file, dedupe and sort the file.

    checklist_name: logical name, stored as <name>.txt
    entries: iterable of text lines; they will be normalized.
    """
    d = _checklists_dir()
    _ensure_dir(d)
    path = d / f"{checklist_name}.list"

    # Migrate legacy .txt checklist if present
    legacy = d / f"{checklist_name}.txt"
    if legacy.exists() and not path.exists():
        try:
            legacy.replace(path)
        except Exception:
            try:
                legacy.rename(path)
            except Exception:
                pass

    existing: List[str] = []
    if path.exists():
        try:
            existing = [line.rstrip('\n') for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        except Exception:
            existing = []

    new = [ _normalize_entry(e) for e in entries if _normalize_entry(e) ]
    combined = list(dict.fromkeys(existing + new))  # preserve order then dedupe

    # Sort by file path (lexicographic)
    combined_sorted = sorted(set(combined))

    # Atomic write
    fd, tmp = tempfile.mkstemp(prefix=checklist_name, suffix='.tmp', dir=str(d))
    try:
        # close the low-level fd before opening by name
        try:
            import os

            os.close(fd)
        except Exception:
            pass
        with open(tmp, 'w', encoding='utf-8') as f:
            for line in combined_sorted:
                f.write(f"{line}\n")
        Path(tmp).replace(path)
    finally:
        try:
            Path(tmp).unlink(missing_ok=True)
        except Exception:
            pass


def get_entries(checklist_name: str) -> List[str]:
    d = _checklists_dir()
    path = d / f"{checklist_name}.list"

    if not path.exists():
        return []
    try:
        return [line.rstrip('\n') for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    except Exception:
        return []
