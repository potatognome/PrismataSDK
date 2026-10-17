from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MenuItem:
    id: str
    label: str
    target: str | None = None
    action: str | None = None
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
