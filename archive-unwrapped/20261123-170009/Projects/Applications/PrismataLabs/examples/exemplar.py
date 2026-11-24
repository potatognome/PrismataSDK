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


def _load_pane_specs(pane_ids: list[str]) -> list[dict]:
    pane_registry = load_registry("pane", ROOT)
    panes: list[dict] = []
    for pane_ref in pane_ids:
        pane = resolve_registry_entry(pane_registry, pane_ref)
        if pane is None:
            raise ValueError(f"Pane reference '{pane_ref}' not found in pane registry.")
        panes.append({
            "id": pane.get("id", pane_ref),
            "label": pane.get("label") or pane.get("title") or pane_ref,
            "title": pane.get("title") or pane.get("label") or pane_ref,
            "colour_role": pane.get("colour_role") or "primary-surface",
            "border_role": pane.get("border_role") or "border",
            "content_role": pane.get("content_role") or "primary-surface",
            "border_pattern": pane.get("border_pattern") or "single-line",
            "x": pane.get("x", 5),
            "y": pane.get("y", 5),
            "width": pane.get("width", 40),
            "height": pane.get("height", 20),
        })
    return panes


def _terminal_space() -> tuple[int, int]:
    return terminal_space((120, 38))


def _override_trace(framework: dict) -> list[str]:
    lines: list[str] = []
    lines.append(
        f"ui-framework: {framework.get('id', 'unknown')} | colour_role={framework.get('colour_role', 'default')} | border_pattern={framework.get('border_pattern', 'single-line')}"
    )
    for pane in framework.get("panes", []):
        pane_name = pane.get("label") or pane.get("title") or pane.get("id") or "unnamed"
        lines.append(
            f"pane: {pane_name} | colour_role={pane.get('colour_role', 'default')} | border_pattern={pane.get('border_pattern', 'single-line')} | content_role={pane.get('content_role', pane.get('colour_role', 'default'))}"
        )
    return lines


def build_exemplar_ui_framework() -> dict:
    ui_frameworks = load_registry("ui-framework", ROOT)
    framework = resolve_registry_entry(ui_frameworks, "exemplar") or resolve_registry_entry(ui_frameworks, "prismata.meta.ui-framework.exemplar")
    if framework is None:
        raise ValueError("UI framework 'exemplar' not found in ui-framework registry.")
    pane_refs = framework.get("panes") or []
    if not pane_refs:
        raise ValueError("Exemplar ui-framework does not declare panes.")
    pane_specs = _load_pane_specs(pane_refs)
    framework["panes"] = pane_specs
    framework["active_pane"] = framework.get("active_pane") or pane_specs[0]["id"]
    return framework


def render_exemplar_framework() -> list[str]:
    framework = build_exemplar_ui_framework()
    rendered = render_panes_to_terminal_frame(
        framework["panes"],
        meta_root=ROOT / "Meta",
        colour_scheme=framework.get("colour_scheme", "default"),
        size=_terminal_space(),
    )
    if rendered and rendered[0].startswith("\x1b[2J"):
        return rendered[1:]
    return rendered


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    enable_windows_vt()

    for line in render_exemplar_framework():
        print(line)


if __name__ == "__main__":
    main()
