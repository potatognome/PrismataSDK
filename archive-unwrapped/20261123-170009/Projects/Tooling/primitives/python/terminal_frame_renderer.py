"""
Terminal frame compositor for pane rendering.

This module renders panes to a shared terminal-space canvas so pane coordinates
can overlap while preserving ANSI colour/style sequences emitted by pane renderer.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

from .pane_renderer import (
    load_border_pattern_registry,
    load_colour_role_registry,
    load_colour_scheme_registry,
    render_pane,
)


def _scale_percentage(value: Any, *, axis_size: int) -> int:
    """Convert a 1-100 screen percentage into a terminal cell coordinate."""
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            return int(value)

    if isinstance(value, (int, float)):
        if 0 <= float(value) <= 100:
            if axis_size <= 0:
                return 0
            return max(0, min(axis_size, int(round((float(value) / 100.0) * axis_size))))
        return int(value)

    return int(value)


def enable_windows_vt() -> None:
    """Enable ANSI virtual terminal processing in Windows consoles when available."""
    if os.name != "nt" or not sys.stdout.isatty():
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def terminal_space(default_size: tuple[int, int] = (120, 38)) -> tuple[int, int]:
    width, height = shutil.get_terminal_size(default_size)
    return max(80, width), max(24, height)


def _paint_pane_to_frame(
    frame: list[list[tuple[str, str]]],
    pane_lines: list[str],
    origin_x: int,
    origin_y: int,
    pane_width: int | None = None,
) -> None:
    max_width = len(frame[0]) if pane_width is None else min(pane_width, len(frame[0]))
    clip_right = origin_x + max_width

    for row_offset, line in enumerate(pane_lines):
        y = origin_y + row_offset
        if y < 0 or y >= len(frame):
            continue

        active_style = ""
        x = origin_x
        i = 0

        while i < len(line):
            if line.startswith("\x1b[", i):
                end = line.find("m", i)
                if end != -1:
                    sequence = line[i : end + 1]
                    if sequence in {"\x1b[0m", "\x1b[39m", "\x1b[49m"}:
                        active_style = ""
                    else:
                        active_style += sequence
                    i = end + 1
                    continue

            char = line[i]
            if char in {"\n", "\r"}:
                i += 1
                continue

            if x < 0 or x >= len(frame[0]) or x >= clip_right:
                i += 1
                x += 1
                continue

            frame[y][x] = (char, active_style)
            x += 1
            i += 1


def _finalize_frame(frame: list[list[tuple[str, str]]]) -> list[str]:
    rendered: list[str] = []
    for row in frame:
        row_text: list[str] = []
        active_style = ""
        for char, cell_style in row:
            if cell_style != active_style:
                if active_style:
                    row_text.append("\x1b[0m")
                active_style = cell_style
                if active_style:
                    row_text.append(active_style)
            row_text.append(char)
        if active_style:
            row_text.append("\x1b[0m")
        rendered.append("".join(row_text))
    return rendered


def render_panes_to_terminal_frame(
    panes: list[dict[str, Any]],
    *,
    meta_root: Path,
    colour_scheme: str = "default",
    size: tuple[int, int] | None = None,
) -> list[str]:
    """Render panes on a shared frame so positioned panes can overlap correctly."""
    width, height = size if size else terminal_space()
    frame = [[(" ", "") for _ in range(width)] for _ in range(height)]

    border_registry = load_border_pattern_registry(meta_root / "registry" / "border-pattern.d")
    colour_roles = load_colour_role_registry(meta_root / "registry" / "colour-role.d")
    colour_schemes = load_colour_scheme_registry(meta_root / "registry" / "colour-scheme.d")

    for pane in panes:
        pane_layout = dict(pane)
        x = _scale_percentage(pane_layout.get("x", 0), axis_size=width)
        y = _scale_percentage(pane_layout.get("y", 0), axis_size=height)
        pane_width = _scale_percentage(pane_layout.get("width", 100), axis_size=width)
        pane_height = _scale_percentage(pane_layout.get("height", 100), axis_size=height)

        pane_width = min(pane_width, max(1, width - x))
        pane_height = min(pane_height, max(1, height - y))

        pane_layout["x"] = x
        pane_layout["y"] = y
        pane_layout["width"] = pane_width
        pane_layout["height"] = pane_height

        pane_lines = render_pane(
            pane_layout,
            border_registry,
            colour_roles,
            colour_schemes,
            {"colour_scheme": colour_scheme},
            {},
        )
        _paint_pane_to_frame(frame, pane_lines, x, y, pane_width)

    rendered = _finalize_frame(frame)
    if rendered:
        return ["\x1b[2J\x1b[H"] + rendered
    return ["\x1b[2J\x1b[H"]
