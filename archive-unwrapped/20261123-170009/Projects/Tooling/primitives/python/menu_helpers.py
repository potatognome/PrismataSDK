"""Reusable menu and bordered-text helpers with safe fallbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, TypeVar

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency
    yaml = None

from Prismata.Projects.Tooling.primitives.python.border_patterns import get_border_pattern


T = TypeVar("T")


def colour_log_safe(
    logger: Any,
    colour: str,
    *parts: object,
    log_files: Optional[Iterable[str]] = None,
    **kwargs: Any,
) -> None:
    """Use logger.colour_log when available, otherwise fallback to plain print."""
    if logger and hasattr(logger, "colour_log"):
        logger.colour_log(
            colour,
            *parts,
            log_files=list(log_files or []),
            **kwargs,
        )
        return
    print(" ".join(str(part) for part in parts))


def apply_bordered_header(
    logger: Any,
    text: str,
    *,
    pattern: Optional[Dict[str, str]] = None,
    pattern_name: str = "standard",
    total_length: int = 70,
    border_rainbow: bool = True,
    log_files: Optional[Iterable[str]] = None,
) -> None:
    """Draw a bordered header using logger.apply_border or fallback ASCII output."""
    resolved_pattern = pattern or get_border_pattern(pattern_name)
    if logger and hasattr(logger, "apply_border"):
        logger.apply_border(
            text=text,
            pattern=resolved_pattern,
            total_length=total_length,
            border_rainbow=border_rainbow,
            log_files=list(log_files or []),
        )
        return

    print(resolved_pattern.get("TOP", "=") * total_length)
    print(f"  {text}")
    print(resolved_pattern.get("BOTTOM", "=") * total_length)


def prompt_input(message: str, allow_empty: bool = False) -> Optional[str]:
    """Prompt for input and return None for empty values when not allowed."""
    try:
        value = input(f"\n{message}: ").strip()
    except (KeyboardInterrupt, EOFError):
        return None
    return value if value or allow_empty else None


def confirm_action(message: str, default: bool = False) -> bool:
    """Prompt for yes/no confirmation and return the selected boolean value."""
    default_str = "Y/n" if default else "y/N"
    try:
        choice = input(f"\n{message} ({default_str}): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return False

    if not choice:
        return default
    return choice in ("y", "yes")


def as_dict(value: Any) -> Dict[str, Any]:
    """Return a dict for mapping-like values, otherwise an empty dict."""
    return value if isinstance(value, dict) else {}


def load_yaml_menu_registry(menus_path: Path) -> Tuple[Dict[str, Dict[str, Any]], Optional[str]]:
    """Load YAML menu definitions keyed by id and return (registry, default_id)."""
    registry: Dict[str, Dict[str, Any]] = {}
    if not menus_path or not menus_path.is_dir() or yaml is None:
        return registry, None

    for yaml_file in sorted(menus_path.glob("*.yaml")):
        try:
            with open(yaml_file, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            menu_id = data.get("id")
            if menu_id:
                registry[str(menu_id)] = data
        except Exception:
            continue

    default_id = "menu_main" if "menu_main" in registry else next(iter(registry), None)
    return registry, default_id


def select_with_arrows(
    items: Sequence[T],
    *,
    render_line: Callable[[int, T], str],
    title: str,
    has_msvcrt: bool,
    clog: Callable[..., None],
    border: Callable[[str], None],
    prompt: Callable[[str], Optional[str]],
    msvcrt_module: Any = None,
) -> Optional[T]:
    """Select an item by arrow keys when available, else fallback to numeric input."""
    if not items:
        return None

    if not has_msvcrt or len(items) == 1 or msvcrt_module is None:
        print()
        for i, item in enumerate(items, 1):
            clog("!list", str(i), "!info", ". " + render_line(i, item))

        idx_raw = prompt(f"Select entry (1-{len(items)})")
        try:
            idx = int(idx_raw or "0") - 1
            if 0 <= idx < len(items):
                return items[idx]
        except (ValueError, TypeError):
            pass
        return None

    cursor = 0
    while True:
        print("\n" * 2)
        border(title)
        print()

        for i, item in enumerate(items):
            if i == cursor:
                clog("!selection", ">", "!info", " " + render_line(i + 1, item))
            else:
                clog("!list", str(i + 1), "!info", ". " + render_line(i + 1, item))

        print()
        clog("!help", "↑/↓=navigate  Enter=select  Esc/Q=cancel")

        try:
            key = msvcrt_module.getch()

            if key in (b"\xe0", b"\x00"):
                key2 = msvcrt_module.getch()
                if key2 == b"H":
                    cursor = max(0, cursor - 1)
                elif key2 == b"P":
                    cursor = min(len(items) - 1, cursor + 1)
            elif key == b"\r":
                return items[cursor]
            elif key == b"\x1b":
                return None
            elif key in (b"q", b"Q"):
                return None
            elif key == b" ":
                return items[cursor]
        except KeyboardInterrupt:
            return None


def render_external_menu(
    menu_id: Optional[str],
    menus: Dict[str, Dict[str, Any]],
    *,
    border: Callable[[str], None],
    clog: Callable[..., None],
    prompt: Callable[[str], Optional[str]],
) -> Optional[str]:
    """Render an external YAML menu and return selected action."""
    if not menu_id or menu_id not in menus:
        return None

    menu = menus[menu_id]
    metadata = as_dict(menu.get("metadata", {}))
    title = metadata.get("name", menu_id)
    border(str(title))
    items = menu.get("items", [])
    if not isinstance(items, list):
        return None

    def _is_reserved(item: Dict[str, Any]) -> bool:
        item_id = str(item.get("id", "")).lower()
        action = str(item.get("action", "")).lower()
        return item_id in ("back", "cancel") or action == "quit"

    reserved_item: Optional[Dict[str, Any]] = None
    non_reserved: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if reserved_item is None and _is_reserved(item):
            reserved_item = item
        else:
            non_reserved.append(item)

    if reserved_item:
        label = str(reserved_item.get("label", reserved_item.get("id", "0")))
        clog("!list", "0", "!info", ". " + label)

    for i, item in enumerate(non_reserved, 1):
        label = str(item.get("label", item.get("id", str(i))))
        clog("!list", str(i), "!info", ". " + label)

    max_choice = len(non_reserved)
    prompt_range = f"0-{max_choice}" if reserved_item else f"1-{max_choice}"

    sel = prompt(f"Select option ({prompt_range})")
    try:
        if sel is None:
            return None
        idx = int(sel)
        if reserved_item and idx == 0:
            return str(reserved_item.get("action", ""))
        idx0 = idx - 1
        if 0 <= idx0 < len(non_reserved):
            return str(non_reserved[idx0].get("action", ""))
    except Exception:
        return None
    return None


def render_action_menu(
    *,
    title: str,
    actions: Sequence[str],
    border: Callable[[str], None],
    clog: Callable[..., None],
    prompt: Callable[[str], Optional[str]],
    action_labels: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Render a numeric action menu and return a selected action id or quit."""
    if not actions:
        return None

    border(title)
    print()

    for i, action in enumerate(actions, 1):
        label = (action_labels or {}).get(
            action,
            action.replace("_", " ").title(),
        )
        clog("!list", str(i), "!info", ". " + label)

    clog("!list", "0", "!info", ". Exit")

    sel = prompt(f"Select option (0-{len(actions)})")
    try:
        if sel is None:
            return "quit"
        idx = int(sel)
        if idx == 0:
            return "quit"
        idx0 = idx - 1
        if 0 <= idx0 < len(actions):
            return actions[idx0]
    except Exception:
        return None
    return None
