"""VILE: VI-like terminal editor shared primitive.

This module provides a compact VI-like multiline text editor that uses
`tUilKit` Canvas/Cursor rendering when available.

Stage 1 baseline
----------------
- Preserve the existing raw VILE render/input flow by default.
- Expose `mode` plumbing for the staged VISE overlay as `vile|vise`.
- Keep the runtime mapping explicit so the editor can be upgraded to the
  shared pane/render/input toolkit without changing default behavior.
"""

from __future__ import annotations

import shutil
import sys
from typing import Any, Dict, List, Optional

try:
    import msvcrt
    HAS_MSVCRT = True
except Exception:
    HAS_MSVCRT = False

try:
    from tUilKit.terminal.canvas import Canvas
    from tUilKit.terminal.cursor import Cursor
    HAS_TUILKIT = True
except Exception:
    HAS_TUILKIT = False


VALID_EDITOR_MODES = ("vile", "vise")


def _read_file_text(file_path: Optional[str]) -> str:
    if not file_path:
        return ""
    try:
        with open(str(file_path), "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def _normalize_editor_mode(mode: Optional[str]) -> str:
    """Normalize the VILE/VISE mode flag without changing the legacy editor state."""
    normalized = (mode or "vile").strip().lower()
    if normalized not in VALID_EDITOR_MODES:
        raise ValueError(f"Unsupported editor mode {mode!r}; expected one of {VALID_EDITOR_MODES}")
    return normalized


def _safe_write(text: str) -> None:
    print(text, end="", file=sys.stdout, flush=True)


class VILEditor:
    """Simple VI-like multiline editor with NORMAL/INSERT modes.

    Runtime compatibility map for Stage 1:
    - render path: `_build_frame()` -> terminal canvas/ANSI output
    - input path: `edit()` -> `msvcrt`/stdin event loop
    - pane helpers: intentionally not used yet; `mode` is plumbed for future
      VISE overlay integration while preserving the raw VILE implementation.
    """

    def __init__(self, initial_text: str = "", *, mode: str = "vile", feature_flags: Optional[Dict[str, Any]] = None, file_path: Optional[str] = None):
        loaded_text = initial_text if initial_text else _read_file_text(file_path)
        lines = loaded_text.split("\n") if loaded_text else []
        self.lines: List[str] = lines if lines else [""]
        self.cursor_row: int = 0
        self.cursor_col: int = 0
        self.top: int = 0
        self.mode: str = "NORMAL"
        self.editor_mode: str = _normalize_editor_mode(mode)
        self.file_path: Optional[str] = str(file_path) if file_path else None
        self.feature_flags: Dict[str, Any] = {
            "raw_text_render": self.editor_mode == "vile",
            "structured_overlay": self.editor_mode == "vise",
            "pane_runtime": False,
            "input_runtime": "msvcrt" if HAS_MSVCRT else "stdin",
            "render_runtime": "tUilKit" if HAS_TUILKIT else "stdout",
        }
        if isinstance(feature_flags, dict):
            self.feature_flags.update(feature_flags)
        self.dirty: bool = False
        self.pending_discard: bool = False
        self.status: str = "i=INSERT  hjkl/arrows=move  Ctrl+S/D=save  Ctrl+K=del line  Esc=cancel"

    def _clamp(self) -> None:
        self.cursor_row = max(0, min(self.cursor_row, len(self.lines) - 1))
        self.cursor_col = max(0, min(self.cursor_col, len(self.lines[self.cursor_row])))

    def _move_left(self) -> None:
        if self.cursor_col > 0:
            self.cursor_col -= 1
        elif self.cursor_row > 0:
            self.cursor_row -= 1
            self.cursor_col = len(self.lines[self.cursor_row])

    def _move_right(self) -> None:
        if self.cursor_col < len(self.lines[self.cursor_row]):
            self.cursor_col += 1
        elif self.cursor_row < len(self.lines) - 1:
            self.cursor_row += 1
            self.cursor_col = 0

    def _insert_text(self, text: str) -> None:
        line = self.lines[self.cursor_row]
        self.lines[self.cursor_row] = line[:self.cursor_col] + text + line[self.cursor_col:]
        self.cursor_col += len(text)
        self.dirty = True

    def _delete_line(self) -> None:
        if len(self.lines) == 1:
            self.lines[0] = ""
            self.cursor_col = 0
            self.dirty = True
            return
        self.lines.pop(self.cursor_row)
        self.cursor_row = max(0, min(self.cursor_row, len(self.lines) - 1))
        self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_row]))
        self.dirty = True

    def _result(self, allow_empty: bool) -> Optional[str]:
        text = "\n".join(self.lines).rstrip()
        if text or allow_empty:
            return text
        return None

    def _runtime_mapping(self) -> Dict[str, Any]:
        """Expose the active render/input mapping without switching Stage 1 behavior.

        This is the compatibility bridge to the shared pane/render/input toolkit.
        Today it intentionally resolves to the legacy raw VILE implementation as
        the default and keeps the structured VISE overlay disabled until Stage 2.
        """
        self.feature_flags["raw_text_render"] = self.editor_mode == "vile"
        self.feature_flags["structured_overlay"] = self.editor_mode == "vise"
        self.feature_flags["file_path"] = self.file_path
        return {
            "mode": self.editor_mode,
            "render": self.feature_flags["render_runtime"],
            "input": self.feature_flags["input_runtime"],
            "pane_runtime": self.feature_flags["pane_runtime"],
            "raw_text_render": self.feature_flags["raw_text_render"],
            "structured_overlay": self.feature_flags["structured_overlay"],
            "file_path": self.file_path,
        }

    def _build_frame(self) -> List[str]:
        term = shutil.get_terminal_size(fallback=(120, 36))
        visible_rows = max(8, term.lines - 8)
        content_width = max(40, term.columns - 10)

        self._clamp()
        if self.cursor_row < self.top:
            self.top = self.cursor_row
        elif self.cursor_row >= self.top + visible_rows:
            self.top = self.cursor_row - visible_rows + 1

        out: List[str] = []
        out.append("=== VILE (VI-like editor) ===")
        out.append("Esc=Normal/Cancel  i=Insert  Ctrl+S/D=Save  Ctrl+K=Delete Line")
        out.append(f"Mode: {self.mode} {'*' if self.dirty else ''} | {self.status}")
        out.append("-" * min(term.columns, 120))

        end = min(len(self.lines), self.top + visible_rows)
        for idx in range(self.top, end):
            raw = self.lines[idx].expandtabs(4)
            if idx == self.cursor_row:
                col = max(0, min(self.cursor_col, len(raw)))
                marker = "█" if self.mode == "NORMAL" else "▌"
                visual = (raw[:col] + marker + raw[col:])[:content_width]
                out.append(f"> {idx + 1:>4} | {visual}")
            else:
                out.append(f"  {idx + 1:>4} | {raw[:content_width]}")

        out.append("-" * min(term.columns, 120))
        out.append(f"Ln {self.cursor_row + 1}, Col {self.cursor_col + 1}")
        return out

    def edit(self, *, allow_empty: bool = False) -> Optional[str]:
        # Stage 1 intentionally preserves the legacy raw-text VILE path while
        # exposing the active mode to the shared runtime primitives.
        self._runtime_mapping()
        if not HAS_MSVCRT:
            return self._fallback(allow_empty=allow_empty)

        canvas = Canvas() if HAS_TUILKIT else None

        try:
            if HAS_TUILKIT:
                _safe_write(Cursor.hide())
                _safe_write(canvas.draw(self._build_frame()))
            else:
                for line in self._build_frame():
                    print(line)

            while True:
                key = msvcrt.getch()

                if key in (b"\xe0", b"\x00"):
                    key2 = msvcrt.getch()
                    if key2 == b"H":
                        self.cursor_row -= 1
                        self._clamp()
                    elif key2 == b"P":
                        self.cursor_row += 1
                        self._clamp()
                    elif key2 == b"K":
                        self._move_left()
                    elif key2 == b"M":
                        self._move_right()
                    elif key2 == b"G":
                        self.cursor_col = 0
                    elif key2 == b"O":
                        self.cursor_col = len(self.lines[self.cursor_row])
                elif key in (b"\x13", b"\x04"):
                    return self._result(allow_empty)
                elif key == b"\x0b":
                    self._delete_line()
                elif self.mode == "INSERT":
                    if key == b"\x1b":
                        self.mode = "NORMAL"
                        self.status = "NORMAL mode"
                    elif key == b"\r":
                        line = self.lines[self.cursor_row]
                        left = line[:self.cursor_col]
                        right = line[self.cursor_col:]
                        self.lines[self.cursor_row] = left
                        self.lines.insert(self.cursor_row + 1, right)
                        self.cursor_row += 1
                        self.cursor_col = 0
                        self.dirty = True
                    elif key == b"\x08":
                        if self.cursor_col > 0:
                            line = self.lines[self.cursor_row]
                            self.lines[self.cursor_row] = line[:self.cursor_col - 1] + line[self.cursor_col:]
                            self.cursor_col -= 1
                            self.dirty = True
                        elif self.cursor_row > 0:
                            prev_len = len(self.lines[self.cursor_row - 1])
                            self.lines[self.cursor_row - 1] += self.lines[self.cursor_row]
                            del self.lines[self.cursor_row]
                            self.cursor_row -= 1
                            self.cursor_col = prev_len
                            self.dirty = True
                    elif key == b"\t":
                        self._insert_text("    ")
                    else:
                        try:
                            ch = key.decode("utf-8")
                        except Exception:
                            ch = ""
                        if ch and ch >= " ":
                            self._insert_text(ch)
                else:
                    if key in (b"i", b"I"):
                        self.mode = "INSERT"
                        self.status = "INSERT mode"
                        self.pending_discard = False
                    elif key in (b"a", b"A"):
                        self._move_right()
                        self.mode = "INSERT"
                        self.status = "INSERT mode"
                        self.pending_discard = False
                    elif key in (b"h", b"H"):
                        self._move_left()
                    elif key in (b"l", b"L"):
                        self._move_right()
                    elif key in (b"j", b"J"):
                        self.cursor_row += 1
                        self._clamp()
                    elif key in (b"k", b"K"):
                        self.cursor_row -= 1
                        self._clamp()
                    elif key in (b"o", b"O"):
                        self.lines.insert(self.cursor_row + 1, "")
                        self.cursor_row += 1
                        self.cursor_col = 0
                        self.mode = "INSERT"
                        self.status = "INSERT mode"
                        self.dirty = True
                    elif key in (b"x", b"X"):
                        line = self.lines[self.cursor_row]
                        if self.cursor_col < len(line):
                            self.lines[self.cursor_row] = line[:self.cursor_col] + line[self.cursor_col + 1:]
                            self.dirty = True
                    elif key in (b"q", b"Q", b"\x1b"):
                        if not self.dirty:
                            return None
                        if self.pending_discard:
                            return None
                        self.status = "Unsaved changes. Press Esc/q again to discard, or Ctrl+S to save."
                        self.pending_discard = True

                if HAS_TUILKIT:
                    _safe_write(canvas.redraw(self._build_frame()))
                else:
                    print("\n".join(self._build_frame()))
        finally:
            if HAS_TUILKIT:
                _safe_write(Cursor.show())
            print()

    def _fallback(self, *, allow_empty: bool) -> Optional[str]:
        print("=== VILE (fallback mode) ===")
        print("Enter text. Type a single '.' line to save; Ctrl+C to cancel.")
        lines: List[str] = []
        try:
            while True:
                line = input()
                if line.strip() == ".":
                    break
                lines.append(line)
        except (KeyboardInterrupt, EOFError):
            return None

        text = "\n".join(lines).rstrip()
        if text or allow_empty:
            return text
        return None


def _run_vile_editor(
    *,
    prompt: str,
    initial_text: str,
    allow_empty: bool,
    mode: str,
    feature_flags: Optional[Dict[str, Any]],
    file_path: Optional[str] = None,
) -> Optional[str]:
    if prompt:
        print(prompt)
    return VILEditor(initial_text, mode=mode, feature_flags=feature_flags, file_path=file_path).edit(allow_empty=allow_empty)


def multiline_editor(
    prompt: str = "",
    initial_text: str = "",
    allow_empty: bool = False,
    *,
    mode: str = "vile",
    feature_flags: Optional[Dict[str, Any]] = None,
    file_path: Optional[str] = None,
) -> Optional[str]:
    """Compatibility helper used by apps expecting multiline_editor API.

    The default path remains the raw VILE editor behavior. `mode` is plumbed for
    the future VISE overlay stage and currently resolves to the same legacy flow.
    This helper intentionally does not delegate back into the compatibility shim;
    that creates a recursion loop and bypasses the documented fallback behavior.
    """
    return _run_vile_editor(
        prompt=prompt,
        initial_text=initial_text,
        allow_empty=allow_empty,
        mode=mode,
        feature_flags=feature_flags,
        file_path=file_path,
    )
