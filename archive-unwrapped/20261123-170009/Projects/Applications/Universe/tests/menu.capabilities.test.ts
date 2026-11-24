import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "fs";
import * as path from "path";

import { renderMenu, MenuDefinition } from "../../../Tooling/primitives/typescript/menuRenderer";
import { RuntimeState } from "../src/bootstrap/state";
import { UdiDispatcher } from "../src/capabilities/dispatcher";
import { handlers } from "../src/capabilities/handlers";

const mainMenu: MenuDefinition = {
  id: "prismata.universe.menu.main",
  type: "menu",
  title: "Main Menu",
  items: [
    {
      key: "1",
      label: "Run Bootstrap Sequence",
      capability: "prismata.universe.capability.app-bootstrap-run",
      submenu_ref: null,
      udi: "prismata.universe.menu-main.run-bootstrap-sequence",
      visibility_condition: "bootstrap_mode",
    },
    {
      key: "1",
      label: "Find",
      capability: "prismata.universe.capability.fs-search-results",
      submenu_ref: "prismata.universe.menu-find",
      udi: "prismata.universe.menu-main.find",
      visibility_condition: "initialized",
    },
    {
      key: "2",
      label: "Select",
      capability: "prismata.universe.capability.fs-select-multi",
      submenu_ref: "prismata.universe.menu-select",
      udi: "prismata.universe.menu-main.select",
      visibility_condition: "initialized",
    },
    {
      key: "3",
      label: "Edit",
      capability: "prismata.universe.capability.fs-edit-multi",
      submenu_ref: "prismata.universe.menu-edit",
      udi: "prismata.universe.menu-main.edit",
      visibility_condition: "initialized_and_vile_ingested",
    },
    {
      key: "3",
      label: "Edit (Locked until Vile ingestion)",
      capability: "prismata.universe.capability.fs-edit-multi",
      submenu_ref: null,
      udi: "prismata.universe.menu-main.edit-locked-until-vile-ingestion",
      visibility_condition: "initialized_and_vile_not_ingested",
    },
    {
      key: "4",
      label: "Verify",
      capability: "prismata.universe.capability.fs-verify-multi",
      submenu_ref: "prismata.universe.menu-verify",
      udi: "prismata.universe.menu-main.verify",
      visibility_condition: "initialized",
    },
    {
      key: "5",
      label: "Settings",
      capability: "prismata.universe.capability.app-settings-paths",
      submenu_ref: "prismata.universe.menu-settings",
      udi: "prismata.universe.menu-main.settings",
      visibility_condition: "initialized",
    },
  ],
};

function labelsFor(state: RuntimeState): string[] {
  return renderMenu(mainMenu, [], undefined, state).visibleItems.map(item => item.label);
}

test("bootstrap mode shows only bootstrap-path menu options", () => {
  const labels = labelsFor({
    bootstrapMode: true,
    initialized: false,
    vileIngested: false,
    initializedFlagPath: "",
  });

  assert.ok(labels.includes("Run Bootstrap Sequence"));
  assert.ok(!labels.includes("Find"));
  assert.ok(!labels.includes("Select"));
  assert.ok(!labels.includes("Edit"));
  assert.ok(!labels.includes("Verify"));
});

test("initialized mode exposes create/edit gating according to vile ingestion", () => {
  const noVile = labelsFor({
    bootstrapMode: false,
    initialized: true,
    vileIngested: false,
    initializedFlagPath: "",
  });
  assert.ok(noVile.includes("Find"));
  assert.ok(noVile.includes("Select"));
  assert.ok(noVile.includes("Verify"));
  assert.ok(noVile.includes("Settings"));
  assert.ok(noVile.includes("Edit (Locked until Vile ingestion)"));
  assert.ok(!noVile.includes("Edit"));

  const withVile = labelsFor({
    bootstrapMode: false,
    initialized: true,
    vileIngested: true,
    initializedFlagPath: "",
  });
  assert.ok(withVile.includes("Edit"));
  assert.ok(!withVile.includes("Edit (Locked until Vile ingestion)"));
});

test("dispatcher enforces create/edit lock before vile ingestion", async () => {
  const dispatcher = new UdiDispatcher(handlers);

  const locked = await dispatcher.execute(
    "prismata.universe.capability.fs-create-from-object",
    {
      selectedObjects: [],
      runtimeState: {
        bootstrapMode: false,
        initialized: true,
        vileIngested: false,
        initializedFlagPath: "",
      },
    }
  );

  assert.equal(locked.success, false);
  assert.match(locked.message, /locked until VILE has been ingested/i);

  const unlocked = await dispatcher.execute(
    "prismata.universe.capability.fs-create-from-object",
    {
      selectedObjects: [],
      runtimeState: {
        bootstrapMode: false,
        initialized: true,
        vileIngested: true,
        initializedFlagPath: "",
      },
    }
  );

  assert.equal(unlocked.success, true);
});

test("Find branch keeps collapsed search-path and results flows inside the live menus", () => {
  const menuDir = path.resolve(__dirname, "../config/project-menus");
  const expectedFiles = [
    "find-parameters-menu.yaml",
    "find-results-menu.yaml",
  ];

  for (const fileName of expectedFiles) {
    const filePath = path.join(menuDir, fileName);
    assert.ok(fs.existsSync(filePath), `Expected ${fileName} to exist`);

    const content = fs.readFileSync(filePath, "utf8");
    assert.match(content, /id:\s*"prismata\.universe\.menu\.find\./i);
    assert.match(content, /udi:\s*"prismata\.universe\.menu-/i);
    assert.match(content, /items:/i);
  }

  const parametersContent = fs.readFileSync(
    path.join(menuDir, "find-parameters-menu.yaml"),
    "utf8"
  );
  assert.match(parametersContent, /Add\/Remove Search Path\(s\)/i);
  assert.match(parametersContent, /fs-search-location/i);

  const resultsContent = fs.readFileSync(
    path.join(menuDir, "find-results-menu.yaml"),
    "utf8"
  );
  assert.match(resultsContent, /Results List/i);
  assert.match(resultsContent, /Preview Pane/i);
  assert.match(resultsContent, /Version Carousel/i);
  assert.match(resultsContent, /Diff Finder/i);
});
