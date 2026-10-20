from core.border import BorderLoader
from core.chroma import ChromaLoader
from ui.panes import Pane, PaneRuntime, apply_role_palette


def test_apply_role_palette_resolves_all_declared_roles():
    pane = Pane(id="pane.main", colour_roles=["fg", "bg", "accent"])
    palette = {"fg": "#ffffff", "bg": "#101010", "accent": "#00ffaa"}

    resolved = apply_role_palette(pane, palette)

    assert resolved == {"fg": "#ffffff", "bg": "#101010", "accent": "#00ffaa"}


def test_apply_role_palette_uses_default_for_missing_roles():
    pane = Pane(id="pane.main", colour_roles=["fg", "bg", "accent"])
    palette = {"fg": "#ffffff"}

    resolved = apply_role_palette(pane, palette, default_colour="#222222")

    assert resolved == {"fg": "#ffffff", "bg": "#222222", "accent": "#222222"}


def test_pane_runtime_render_includes_multi_colour_segments():
    pane = Pane(id="pane.main", colour_roles=["fg", "bg", "accent"])
    runtime = PaneRuntime(pane=pane)

    rendered = runtime.render({"fg": "#eeeeee", "bg": "#111111", "accent": "#ff9900"})

    assert rendered["resolved_role_colours"]["fg"] == "#eeeeee"
    assert rendered["resolved_role_colours"]["bg"] == "#111111"
    assert rendered["resolved_role_colours"]["accent"] == "#ff9900"
    assert rendered["colour_segments"] == [
        {"role": "fg", "colour": "#eeeeee"},
        {"role": "bg", "colour": "#111111"},
        {"role": "accent", "colour": "#ff9900"},
    ]


def test_pane_runtime_render_uses_existing_resolution_without_palette():
    pane = Pane(id="pane.main", colour_roles=["fg", "bg"])
    runtime = PaneRuntime(pane=pane, resolved_role_colours={"fg": "#fafafa", "bg": "#0f0f0f"})

    rendered = runtime.render()

    assert rendered["resolved_role_colours"] == {"fg": "#fafafa", "bg": "#0f0f0f"}
    assert rendered["colour_segments"] == [
        {"role": "fg", "colour": "#fafafa"},
        {"role": "bg", "colour": "#0f0f0f"},
    ]


def test_pane_runtime_render_frame_draws_visible_text_border():
    pane = Pane(id="pane.main", title="Demo Pane", size={"width": 18, "height": 6}, border_pattern="single-line")
    runtime = PaneRuntime(pane=pane)

    frame = runtime.render_frame()

    assert "Demo Pane" in frame
    assert "+" in frame
    assert "|" in frame


def test_pane_runtime_applies_chroma_and_border_from_registry_payloads():
    pane = Pane(id="pane.main", colour_roles=["primary-surface", "border-fg"], border_role="default")
    chroma = ChromaLoader.load({
        "id": "default",
        "palette": {"primary-surface": "#112233", "border-fg": "#334455"},
    })
    border = BorderLoader.load({"id": "single-line", "style": "single-line"})

    runtime = PaneRuntime(pane=pane)
    rendered = runtime.render(chroma.palette)
    rendered = runtime.apply_chroma(chroma)
    rendered = runtime.apply_border(border)

    assert rendered["resolved_role_colours"]["primary-surface"] == "#112233"
    assert rendered["resolved_role_colours"]["border-fg"] == "#334455"
    assert rendered["border_pattern"] == "single-line"
    assert rendered["applied_chroma"] == {"default": {"primary-surface": "#112233", "border-fg": "#334455"}}
    assert rendered["applied_border"] == {"single-line": "single-line"}
