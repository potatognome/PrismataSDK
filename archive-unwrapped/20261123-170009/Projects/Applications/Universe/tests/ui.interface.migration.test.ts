import { test } from "node:test";
import assert from "node:assert/strict";

import {
  loadMenu,
  loadMenuYaml,
  normalizeMenuItemFrameworks,
} from "../../../Tooling/primitives/typescript/menuLoaders";
import { loadUniverseUiFrameworksConfig } from "../../../Tooling/primitives/typescript/uiInterfaceLoader";
import { resolvePrismataRoot } from "../src/utils/paths";
import { renderMenu, MenuDefinition } from "../../../Tooling/primitives/typescript/menuRenderer";

test("menu loader normalizes missing ui_framework to basic", () => {
  const menu = loadMenuYaml(`
id: "prismata.universe.menu.test"
type: "menu"
title: "Test"
items:
  - key: "1"
    label: "Test Item"
    capability: "prismata.universe.capability.fs-search"
    submenu_ref: null
`);

  const normalized = normalizeMenuItemFrameworks(menu, "test-menu.yaml");
  assert.equal(normalized.items[0]?.ui_framework, "basic");
});

test("menu loader accepts canonical menu item fields and keeps runtime compatibility", () => {
  const menu = loadMenuYaml(`
id: "prismata.universe.menu.canonical"
type: "menu"
title: "Canonical Test"
items:
  - key: "find"
    name: "Find"
    order: 1
    type: "navigate"
    selectionMethod: "number"
    action: "navigate"
    navigateTarget: "prismata.universe.menu-find"
    capability: "prismata.universe.capability.fs-search-results"
    ui_framework: "menu"
`);

  assert.equal(menu.items[0]?.label, "Find");
  assert.equal(menu.items[0]?.submenu_ref, "prismata.universe.menu-find");
  assert.equal(menu.items[0]?.ui_framework, "menu");
});

test("main menu items include a resolved ui_framework", () => {
  const menu = loadMenu("prismata.universe.menu.main");
  assert.ok(menu.items.length > 0);
  for (const item of menu.items) {
    assert.ok(item.ui_framework, `Expected ui_framework for item ${item.label}`);
  }
});

test("flattened UDI menu ids resolve to the existing project menu files", () => {
  const menu = loadMenu("prismata.universe.menu-settings");

  assert.equal(menu.id, "prismata.universe.menu.settings");
  assert.equal(menu.title, "Settings");
  assert.equal(menu.items[1]?.submenu_ref, "prismata.universe.menu.settings.paths");
  assert.equal(menu.items[2]?.submenu_ref, "prismata.universe.menu.settings.ignore");
});

test("ui_frameworks config loader resolves framework and override files", () => {
  const prismataRoot = resolvePrismataRoot();
  const config = loadUniverseUiFrameworksConfig(prismataRoot);

  assert.equal(config.ui_framework, "multi_pane");
  assert.equal(config.hasProjectOverride, true);
  assert.equal(config.hasTenantOverride, true);

  const resultsPane = config.panes.find(p => p.id === "results_list");
  assert.ok(resultsPane);
  assert.equal(resultsPane?.coordinates.width, 42);

  const previewPane = config.panes.find(p => p.id === "preview");
  assert.ok(previewPane);
  assert.equal(previewPane?.coordinates.x, 42);
});

test("renderMenu filters visible panes by available ui_interface pane IDs", () => {
  const menu: MenuDefinition = {
    id: "prismata.universe.menu.test",
    type: "menu",
    title: "Test",
    items: [
      {
        key: "1",
        label: "Find",
        capability: "prismata.universe.capability.fs-search-results",
        submenu_ref: null,
      },
    ],
  };

  const rendered = renderMenu(
    menu,
    [],
    undefined,
    {
      bootstrapMode: false,
      initialized: true,
      vileIngested: true,
      initializedFlagPath: "",
      settings: {},
    },
    ["results_list"]
  );

  assert.deepEqual(rendered.visiblePanes, ["results_list"]);
});
