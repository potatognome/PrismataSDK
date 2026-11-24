import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Projects.Tooling.primitives.python import (
    enable_windows_vt,
    find_prismata_root,
    load_registry,
    render_panes_to_terminal_frame,
    resolve_registry_entry,
    terminal_space,
)

ROOT = find_prismata_root(ROOT)


def _object_name(obj: dict | None) -> str:
    if not isinstance(obj, dict):
        return "unnamed"
    return obj.get("name") or obj.get("id") or "unnamed"


def _effective_value(obj: dict | None, fallback: str | None, *keys: str) -> str | None:
    if not isinstance(obj, dict):
        return fallback
    for key in keys:
        value = obj.get(key)
        if value not in (None, ""):
            return str(value)
    return fallback


def _informational_header(obj_type: str, object_name: str | None, colour_role: str | None, border_pattern: str | None) -> str:
    return f"{obj_type}: {object_name or 'unnamed'} | colour_role={colour_role or 'default'} | border_pattern={border_pattern or 'single-line'}"


def _menu_items_for(menu: dict | None) -> list[dict]:
    if not isinstance(menu, dict):
        return []

    menu_body = menu.get("menu") if isinstance(menu.get("menu"), dict) else menu
    items = menu_body.get("items") or []
    resolved: list[dict] = []
    item_registry = load_registry("menu-item", ROOT)

    for item in items:
        if isinstance(item, str):
            entry = resolve_registry_entry(item_registry, item)
            if entry is not None:
                resolved.append(entry)
        elif isinstance(item, dict):
            resolved.append(item)

    return resolved


def _override_trace(framework: dict) -> list[str]:
    lines: list[str] = []
    lines.append(
        f"ui-framework: {_object_name(framework)} | colour_role={_effective_value(framework, 'default', 'colour_role')} | border_pattern={_effective_value(framework, 'single-line', 'border_pattern')}"
    )

    for pane in framework.get("panes", []):
        pane_name = _object_name(pane)
        pane_role = _effective_value(pane, "default", "colour_role")
        pane_pattern = _effective_value(pane, "single-line", "border_pattern")
        lines.append(
            f"pane: {pane_name} | colour_role={pane_role} | border_pattern={pane_pattern} | content_role={_effective_value(pane, pane_role, 'content_role')}"
        )

        menu = pane.get("menu")
        if not isinstance(menu, dict):
            continue

        menu_body = menu.get("menu") if isinstance(menu.get("menu"), dict) else menu
        menu_role = _effective_value(menu_body, pane_role, "colour_role")
        menu_pattern = _effective_value(menu_body, pane_pattern, "border_pattern")
        lines.append(f"menu: {_object_name(menu_body)} | colour_role={menu_role} | border_pattern={menu_pattern}")

        for item in _menu_items_for(menu_body):
            item_name = _object_name(item)
            item_role = _effective_value(item, menu_role, "colour_role")
            item_pattern = _effective_value(item, menu_pattern, "border_pattern")
            lines.append(f"menu-item: {item_name} | colour_role={item_role} | border_pattern={item_pattern}")

    return lines


def build_exemplar_multi_pane_menu_framework() -> dict:
    ui_frameworks = load_registry("ui-framework", ROOT)
    framework = resolve_registry_entry(ui_frameworks, "exemplar-multi-pane-menus")
    if framework is None:
        raise ValueError("The 'exemplar-multi-pane-menus' ui-framework entry is not present in the registry.")

    pane_registry = load_registry("pane", ROOT)
    menu_registry = load_registry("menu", ROOT)
    pane_specs: list[dict] = []

    for pane_ref in framework.get("panes") or []:
        pane = resolve_registry_entry(pane_registry, pane_ref)
        if pane is None:
            raise ValueError(f"The pane reference '{pane_ref}' does not resolve to a manifest-backed pane entry.")

        pane_copy = dict(pane)
        pane_copy["title"] = pane_copy.get("title") or pane_copy.get("label") or pane_copy.get("id")
        pane_copy["label"] = pane_copy.get("label") or pane_copy.get("title") or pane_copy.get("id")

        menu_ref = None
        for binding in framework.get("pane_bindings", []):
            if binding.get("pane") == pane_ref:
                menu_ref = binding.get("menu")
                break

        if menu_ref:
            menu = resolve_registry_entry(menu_registry, menu_ref)
            if menu is None:
                raise ValueError(f"The menu reference '{menu_ref}' does not resolve to a manifest-backed menu entry.")
            menu_copy = dict(menu)
            menu_copy["title"] = menu_copy.get("title") or menu_copy.get("label") or menu_copy.get("id")
            menu_copy["label"] = menu_copy.get("label") or menu_copy.get("title") or menu_copy.get("id")
            pane_copy["menu"] = menu_copy

        pane_specs.append(pane_copy)

    framework_copy = dict(framework)
    framework_copy["panes"] = pane_specs
    return framework_copy


def render_exemplar_multi_pane_menus(verbose: bool = False) -> list[str]:
    framework = build_exemplar_multi_pane_menu_framework()
    lines: list[str] = []
    if verbose:
        lines.extend(_override_trace(framework))

    pane_list: list[dict] = []
    for pane in framework["panes"]:
        pane_copy = dict(pane)
        menu = pane_copy.pop("menu", None)
        if isinstance(menu, dict):
            menu_payload = menu.get("menu") if isinstance(menu.get("menu"), dict) else menu
            menu_copy = dict(menu_payload)
            menu_copy["items"] = _menu_items_for(menu_payload)
            menu_copy["colour_role"] = _effective_value(menu_payload, pane_copy.get("colour_role", "default"), "colour_role")
            menu_copy["border_pattern"] = _effective_value(menu_payload, pane_copy.get("border_pattern", "single-line"), "border_pattern")
            pane_copy["menu"] = menu_copy
        pane_list.append(pane_copy)

    rendered = render_panes_to_terminal_frame(
        pane_list,
        meta_root=ROOT / "Meta",
        colour_scheme=framework.get("colour_scheme", "default"),
        size=terminal_space((120, 38)),
    )
    if verbose:
        return lines + [""] + rendered
    return rendered


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    enable_windows_vt()

    for line in render_exemplar_multi_pane_menus(verbose=False):
        print(line)


if __name__ == "__main__":
    main()
