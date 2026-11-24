def simulate_renderer(kind, entry_id, registry):
    entry = registry.get(kind, {}).get(entry_id)
    if not entry:
        return f"{kind} '{entry_id}' not found."

    data = entry["data"]
    out = []
    out.append(f"Renderer Simulation for {kind} '{entry_id}'")
    out.append("------------------------------------------------------------")

    if kind == "pane":
        bp = data.get("pane", {}).get("border_pattern")
        cs = data.get("pane", {}).get("colour_scheme")
        cr = data.get("pane", {}).get("colour_role")

        border = registry.get("border-pattern", {}).get(bp)
        scheme = registry.get("colour-scheme", {}).get(cs)
        role = registry.get("colour-role", {}).get(cr)

        out.append(f"✔ colour_scheme: {cs}" if scheme else f"✘ colour_scheme: {cs} → fallback: black/white")
        out.append(f"✔ border_pattern: {bp}" if border else f"✘ border_pattern: {bp} → fallback: invisible border")
        out.append(f"✔ colour_role: {cr}" if role else f"✘ colour_role: {cr} → fallback: neutral_fg")

    return "\n".join(out)
