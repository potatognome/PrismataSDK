from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MenuItem:
    id: str
    label: str
    udi: str | None = None
    target: str | None = None
    action: str | None = None
    capability: str | None = None
    target_pane: str | None = None
    enabled: bool = True


@dataclass(slots=True)
class Menu:
    id: str
    title: str
    items: list[MenuItem] = field(default_factory=list)

    def route_item(self, item_id: str) -> str | None:
        for item in self.items:
            if item.id == item_id:
                return item.target or item.action or None
        return None


def route_menu(menu: Menu, item_id: str) -> dict[str, Any]:
    target = menu.route_item(item_id)
    return {
        "menu_id": menu.id,
        "item_id": item_id,
        "target": target,
    }


class MenuLoader:
    """Loads menus and menu items from CMF-like registry payloads."""

    @staticmethod
    def load(payload: dict[str, Any]) -> Menu:
        required = {"id", "udi", "kind", "version"}
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"Menu payload missing required fields: {', '.join(missing)}")

        content = payload.get("content")
        if not isinstance(content, dict):
            content = {}

        items: list[MenuItem] = []
        for raw_item in content.get("items", []):
            if not isinstance(raw_item, dict):
                raise TypeError("Menu items must be dictionaries")
            key = str(raw_item.get("key") or raw_item.get("id") or len(items))
            items.append(
                MenuItem(
                    id=key,
                    udi=raw_item.get("udi"),
                    label=str(raw_item.get("name") or raw_item.get("label") or key),
                    target=raw_item.get("target"),
                    action=raw_item.get("action"),
                    capability=raw_item.get("capability"),
                    target_pane=raw_item.get("target_pane"),
                    enabled=bool(raw_item.get("enabled", True)),
                )
            )

        title = str(payload.get("metadata", {}).get("name") or payload.get("id") or "Menu")
        return Menu(id=str(payload["id"]), title=title, items=items)
