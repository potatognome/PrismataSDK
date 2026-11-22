from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class UIFramework:
    """Framework descriptor for pane layout and menu routing."""

    id: str
    kind: str = "ui-framework"
    panes: list[str] = field(default_factory=list)
    menu_routes: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UIFrameworkRuntime:
    """Runtime representation of a composed UI framework."""

    framework: UIFramework
    panes: list[str] = field(default_factory=list)
    menu_routes: dict[str, str] = field(default_factory=dict)

    def _pane_slots(self) -> dict[str, str]:
        metadata = self.framework.metadata or {}
        pane_slots = metadata.get("pane_slots")
        if isinstance(pane_slots, dict):
            return {str(slot): str(target) for slot, target in pane_slots.items()}
        return {}

    def _resolve_slot_target(self, route: str | None) -> str | None:
        if route is None:
            return None
        if not route.startswith("slot:"):
            return route

        slot_name = route.split(":", 1)[1]
        target = self._pane_slots().get(slot_name)
        if target is None:
            return None

        pane_ids = set(self.panes or self.framework.panes)
        if pane_ids and target not in pane_ids:
            return None
        return target

    def resolve_menu_target(self, menu_id: str) -> str | None:
        route = self.menu_routes.get(menu_id)
        resolved = self._resolve_slot_target(route)
        if resolved is not None:
            return resolved

        if self.framework.menu_routes:
            framework_route = self.framework.menu_routes.get(menu_id)
            return self._resolve_slot_target(framework_route)
        return None

    def compose(self) -> dict[str, Any]:
        layout = self.framework.metadata.get("layout", "default") if self.framework.metadata else "default"
        return {
            "id": self.framework.id,
            "kind": self.framework.kind,
            "panes": self.panes or self.framework.panes,
            "menu_routes": self.menu_routes or self.framework.menu_routes,
            "metadata": self.framework.metadata,
            "layout": layout,
        }


def resolve_menu_target(framework: UIFramework, menu_id: str) -> str | None:
    runtime = UIFrameworkRuntime(framework=framework)
    return runtime.resolve_menu_target(menu_id)


class UIFrameworkLoader:
    """Loads a UI framework from a CMF-like registry payload."""

    @staticmethod
    def load(payload: dict[str, Any]) -> UIFramework:
        required = {"id", "udi", "kind", "version"}
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"UI framework payload missing required fields: {', '.join(missing)}")

        content = payload.get("content")
        if not isinstance(content, dict):
            content = {}

        panes = content.get("panes", [])
        if isinstance(panes, dict):
            pane_ids = list(panes.values())
        else:
            pane_ids = list(panes)

        metadata = dict(payload.get("metadata", content))
        menu_routes = dict(content.get("menu_routes", {}))
        if not menu_routes and isinstance(content.get("menu"), str):
            menu_routes = {content["menu"]: "slot:left"}

        return UIFramework(
            id=str(payload["id"]),
            kind=str(payload["kind"]),
            panes=[str(pane) for pane in pane_ids],
            menu_routes=menu_routes,
            metadata=metadata,
        )
