from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Any

import yaml

from capabilities.registry import Capability
from ui.frameworks import UIFramework, UIFrameworkLoader
from ui.menus import Menu, MenuLoader
from ui.panes import Pane, PaneLoader, PaneRuntime


@dataclass(slots=True)
class RuntimeContext:
    initiating_object: str
    related_objects: list[str] = field(default_factory=list)
    execution_path: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextGraphBuilder:
    """Build a bounded, ordered Hello UDI runtime context."""

    @staticmethod
    def build(
        initiating_object: str,
        menu_item_udi: str,
        menu_udi: str,
        pane_udi: str,
        framework_udi: str,
        capability_udi: str,
        max_related_objects: int = 10,
    ) -> RuntimeContext:
        ordered = [menu_item_udi, menu_udi, pane_udi, framework_udi, capability_udi]
        limit = max(0, min(max_related_objects, 10))
        related = ordered[:limit]
        return RuntimeContext(
            initiating_object=initiating_object,
            related_objects=related,
            execution_path=list(related),
            metadata={
                "menu_item_udi": menu_item_udi,
                "menu_udi": menu_udi,
                "pane_udi": pane_udi,
                "framework_udi": framework_udi,
                "capability_udi": capability_udi,
            },
        )


class HelloUDICapability:
    """The reference capability for the Hello UDI runtime slice."""

    UDI = "prismata.example.capability.hello_udi"

    @staticmethod
    def execute(context: RuntimeContext) -> str:
        greetings: list[str] = []
        for udi in context.related_objects:
            segments = udi.split(".")
            kind = segments[-2] if len(segments) >= 2 else "object"
            greetings.append(f"Hello to {kind} {udi} from {HelloUDICapability.UDI}")
        return "\n".join(greetings)


class PaneOutputInjector:
    """Route functional capability output to a target pane."""

    @staticmethod
    def inject(pane_states: dict[str, str], target_pane_udi: str, output: str) -> dict[str, str]:
        updated = dict(pane_states)
        updated[target_pane_udi] = output
        return updated


class HelloUDIRuntimeEngine:
    """Load and run the structural Hello UDI demonstration."""

    def __init__(self, sdk_root: str | Path | None = None) -> None:
        self.sdk_root = Path(sdk_root or Path(__file__).resolve().parents[1])
        self.framework: UIFramework
        self.panes: dict[str, Pane]
        self.menu: Menu
        self.capability: Capability
        self.pane_states: dict[str, str] = {}
        self._load()

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError(f"{path} must contain a YAML mapping")
        return payload

    def _load(self) -> None:
        framework_payload = self._load_yaml(
            self.sdk_root / "examples" / "registry" / "ui_frameworks" / "two_pane.yaml"
        )
        self.framework = UIFrameworkLoader.load(framework_payload)

        pane_paths = [
            self.sdk_root / "examples" / "registry" / "panes" / "lh_test_pane.yaml",
            self.sdk_root / "examples" / "registry" / "panes" / "rh_test_pane.yaml",
        ]
        self.panes = {}
        for pane_path in pane_paths:
            pane_payload = self._load_yaml(pane_path)
            pane = PaneLoader.load(pane_payload)
            if pane.udi:
                self.panes[pane.udi] = pane

        menu_payload = self._load_yaml(
            self.sdk_root / "examples" / "registry" / "menus" / "test_menu.yaml"
        )
        self.menu = MenuLoader.load(menu_payload)

        self.capability = Capability.load_from_file(
            self.sdk_root / "examples" / "capabilities" / "hello_udi" / "hello_udi.yaml"
        )
        self.pane_states = {pane_udi: "" for pane_udi in self.panes}

    def select(self, key: str) -> tuple[bool, str | None]:
        if key == "0":
            return False, None

        menu_item = next((item for item in self.menu.items if item.id == key), None)
        if menu_item is None:
            return True, f"Unknown menu selection: {key}"
        if menu_item.action == "quit":
            return False, None
        if menu_item.action != "execute_capability" or not menu_item.capability or not menu_item.target_pane:
            return True, f"Menu item {key} is not executable"

        context = ContextGraphBuilder.build(
            initiating_object=menu_item.udi or f"prismata.example.menu_item.test_{key}",
            menu_item_udi=menu_item.udi or f"prismata.example.menu_item.test_{key}",
            menu_udi=self.menu.id,
            pane_udi=menu_item.target_pane,
            framework_udi=self.framework.id,
            capability_udi=menu_item.capability,
        )
        output = HelloUDICapability.execute(context)
        self.pane_states = PaneOutputInjector.inject(
            self.pane_states,
            menu_item.target_pane,
            output,
        )
        return True, output

    def render(self) -> str:
        left_udi = "prismata.example.pane.lh_test"
        right_udi = "prismata.example.pane.rh_test"
        left_pane = PaneRuntime(self.panes[left_udi])
        right_pane = PaneRuntime(self.panes[right_udi])
        left_output = self.pane_states.get(left_udi, "")
        right_output = self.pane_states.get(right_udi, "")

        left_pane.pane.size = {"width": 48, "height": 14}
        right_pane.pane.size = {"width": 48, "height": 14}
        left_lines = left_pane.render_frame(width=48, height=14).splitlines()
        right_lines = right_pane.render_frame(width=48, height=14).splitlines()

        if left_output:
            left_lines[1] = "|" + " " + left_output.splitlines()[0][:46].ljust(46) + "|"
        if right_output:
            right_lines[1] = "|" + " " + right_output.splitlines()[0][:46].ljust(46) + "|"

        lines = [left + "  " + right for left, right in zip(left_lines, right_lines)]
        lines.append("")
        for item in self.menu.items:
            lines.append(f"{item.id}) {item.label}")
        return "\n".join(lines)

    def run(
        self,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> None:
        while True:
            output_fn(self.render())
            selection = input_fn("Selection: ").strip()
            continue_running, message = self.select(selection)
            if not continue_running:
                output_fn("Goodbye.")
                return
            if message:
                output_fn(message)
