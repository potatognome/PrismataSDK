import { renderMenu } from "../../../../Tooling/primitives/typescript/menuRenderer";
import { UdiDispatcher } from "../capabilities/dispatcher";
import { handlers } from "../capabilities/handlers";
import { SelectedObject, computeSelectionLogic } from "../selection/selectionLogic";
import { runSearch } from "../search/searchEngine";
import { bootstrapLog } from "../bootstrap/logger";
import {
  getRuntimeState,
  getUniversePaths,
  saveUniverseSettings,
  updateRuntimeSettings,
} from "../bootstrap/state";
import { runBootstrapIngestion } from "../ingestion/pipeline";

import * as fs from "fs";
import * as path from "path";
import * as readline from "readline";
import { CliMenuPrimitives } from "../../../../Tooling/primitives/typescript/menuPrimitives";
import { convertConfigToText } from "../../../../Tooling/primitives/typescript/configHelpers";
import { loadMenu, loadSchema } from "../../../../Tooling/primitives/typescript/menuLoaders";
import { resolvePrismataRoot, capabilityArgsFor } from "../utils/paths";
import { renderResultsList, renderPreview, renderVersionCarousel } from "../renderer/resultRenderer";
import { loadUniverseUiFrameworksConfig } from "../../../../Tooling/primitives/typescript/uiInterfaceLoader";
import { pythonExecute as universePythonExecute } from "../../ts/python-bridge/python_bridge";

// Entry: start the CLI loop and build runtime state + UI primitives
export async function runCli() {
  const prismataRoot = resolvePrismataRoot();
  const universePaths = getUniversePaths(prismataRoot);
  // runtimeState holds current settings, flags (bootstrapMode, vileIngested), and runtime searchParams
  let runtimeState = getRuntimeState(universePaths);
  // UI config and available panes for result/preview/version UI
  const uiFrameworksConfig = loadUniverseUiFrameworksConfig(prismataRoot);
  const availablePaneIds = uiFrameworksConfig.panes.map(pane => pane.id);
  const ui = new CliMenuPrimitives({ basePath: prismataRoot });
  const dispatcher = new UdiDispatcher(handlers);
  // services provided to capabilities (e.g. bootstrap)
  const services = { runBootstrapSequence: async () => { /*...*/ } };

  ui.colourLog(
    "!help",
    `[ui_frameworks] framework=${uiFrameworksConfig.ui_framework} project_override=${uiFrameworksConfig.hasProjectOverride} tenant_override=${uiFrameworksConfig.hasTenantOverride}`
  );

  let currentMenuId = "prismata.universe.menu.main";
  const menuHistory: string[] = [];
  let selectedObjects: SelectedObject[] = [];
  let referenceObject: SelectedObject | undefined;

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  async function refreshTuilkitRuntimeState(): Promise<void> {
    try {
      const status = await universePythonExecute("tuilkit_status", {
        runtimeState: {
          vileIngested: runtimeState.vileIngested,
          tuilkitIngested: runtimeState.tuilkitIngested,
        },
      });

      runtimeState = {
        ...runtimeState,
        tuilkitRuntimeMode: String(status?.mode ?? runtimeState.tuilkitRuntimeMode ?? ""),
        tuilkitIngested:
          typeof status?.ingested === "boolean"
            ? status.ingested
            : runtimeState.tuilkitIngested,
        tuilkitFallback:
          typeof status?.fallback === "boolean"
            ? status.fallback
            : runtimeState.tuilkitFallback,
      };
    } catch {
      // Preserve existing runtimeState when Python bridge is unavailable.
    }
  }

  async function loop() {
    await refreshTuilkitRuntimeState();
    const view = loadView(currentMenuId);
    console.clear();

    if (view.kind === "schema") {
      ui.colourLog("!warn", `No menu definition found for '${currentMenuId}'.`);
      ui.colourLog("!help", convertConfigToText(view.schema as unknown as Record<string, unknown>));
      await ui.promptInput(rl, "Press Enter to return", true);

      if (menuHistory.length > 0) {
        currentMenuId = menuHistory.pop() as string;
      } else {
        currentMenuId = "prismata.universe.menu.main";
      }

      await loop();
      return;
    }

    // Render menu (visibility computed by selection logic) -> RenderedMenu
    const rendered = renderMenu(
      view.menu,
      selectedObjects,
      referenceObject,
      runtimeState,
      availablePaneIds,
      universePaths,
      prismataRoot
    );

    let pythonVisibleItems = rendered.visibleItems;
    let pythonVisiblePanes = rendered.visiblePanes;
    let pythonActiveCapabilities = rendered.activeCapabilities;
    let pythonHeader: string | undefined;
    try {
      const selectionLogic = computeSelectionLogic(selectedObjects, referenceObject);
      const pyVisibility = await universePythonExecute("render_menu_visibility", {
        menu: view.menu,
        runtimeState,
        selectedObjects,
        selectionState: {
          selectionType: selectionLogic.state.selectionType,
          referenceObjectSelected: selectionLogic.state.referenceObjectSelected,
        },
        compatibility: {
          semantic_compatible: selectionLogic.compatibility.semantic_compatible,
          version_compatible: selectionLogic.compatibility.version_compatible,
          type_compatible: selectionLogic.compatibility.type_compatible,
        },
        availablePaneIds,
        prismataRoot,
        paths: universePaths,
      });

      if (Array.isArray(pyVisibility?.visibleItems)) {
        const allowedKeys = new Set(
          pyVisibility.visibleItems
            .filter((item: any) => item && typeof item === "object")
            .map((item: any) => String(item.key ?? ""))
        );

        if (allowedKeys.size > 0) {
          pythonVisibleItems = rendered.visibleItems.filter(item => allowedKeys.has(String(item.key)));
        }
      }

      if (Array.isArray(pyVisibility?.visiblePanes)) {
        pythonVisiblePanes = pyVisibility.visiblePanes
          .map((pane: any) => String(pane))
          .filter((pane: string) => availablePaneIds.includes(pane));
      }

      if (Array.isArray(pyVisibility?.activeCapabilities)) {
        pythonActiveCapabilities = pyVisibility.activeCapabilities
          .map((cap: any) => String(cap))
          .filter((cap: string) => cap.length > 0);
      }

      if (typeof pyVisibility?.header === "string") {
        pythonHeader = pyVisibility.header;
      }
    } catch {
      // Keep TypeScript visibility results when Python visibility service is unavailable.
    }

    rendered.activeCapabilities = pythonActiveCapabilities;
    const headerForDisplay = pythonHeader ?? rendered.header;

    // Display header lines (rendered.header may show status/settings)
    if (headerForDisplay) {
      for (const line of String(headerForDisplay).split(/\r?\n/)) {
        ui.colourLog("!help", line);
      }
    }

    const menuOptions = pythonVisibleItems.map(item => ({
      key: item.key,
      label: item.label,
    }));

    if (menuHistory.length > 0) {
      menuOptions.push({ key: "0", label: "Back" });
    }
    // Print options + prompt for user selection
    ui.printOptions(menuOptions);
    const answer = await ui.promptInput(rl, "Select option", true);
    const selectedKey = (answer ?? "").trim();

    if (selectedKey === "0" && menuHistory.length > 0) {
      currentMenuId = menuHistory.pop() as string;
      await loop();
      return;
    }

    // Map typed answer to a MenuItem (returns undefined if invalid)
    const item = pythonVisibleItems.find(i => i.key === selectedKey);
    if (!item) { await loop(); return; }

    // Quit: persist settings and exit loop
    if (item.capability === "prismata.universe.capability.app-quit") {
      const persisted = saveUniverseSettings(universePaths, runtimeState.settings);
      runtimeState = updateRuntimeSettings(runtimeState, persisted);
      rl.close();
      return;
    }

    // Submenu: push history and switch to submenu id
    if (item.submenu_ref) {
      menuHistory.push(currentMenuId);
      currentMenuId = item.submenu_ref;
      await loop();
      return;
    }

    if (item.capability) {
      // Special-case fs-search items to collect action/type/value from the user
      let args = capabilityArgsFor(item.capability, universePaths);

      // Special-case: selecting Workspace Root uses native folder picker capability
      // - Calls capability 'fs-search-location' which returns a location.path
      // - Persists into settings.paths.workspace_root via saveUniverseSettings
      // - Optionally runs runBootstrapIngestion() if not initialized at that path
      if (
        item.capability === "prismata.universe.capability.app-settings-paths" &&
        String((item as any).key_value ?? "") === "workspace_root"
      ) {
        const locResult = await dispatcher.execute("prismata.universe.capability.fs-search-location", {
          selectedObjects,
          referenceObject,
          args: { mode: "folder" },
          runtimeState,
          services,
        });

        const location = (((locResult as any)?.location) ?? (((locResult as any)?.data as any)?.location)) as any;
        if (!location || !location.path) {
          await loop();
          return;
        }

        const pathVal = String(location.path);

        const nextSettings = {
          ...runtimeState.settings,
          paths: { ...(runtimeState.settings?.paths ?? {}), workspace_root: pathVal },
        };

        const persisted = saveUniverseSettings(universePaths, nextSettings);
        runtimeState = updateRuntimeSettings(runtimeState, persisted);

        // Build a UniversePaths-like object for the selected workspace root so we can bootstrap into it
        const customPaths = {
          prismataRoot: prismataRoot,
          workspaceRoot: pathVal,
          stateDir: path.join(pathVal, "state"),
          initializedFlagPath: path.join(pathVal, "state", "initialized.flag"),
          ingestionDir: path.join(pathVal, "ingestion"),
          registryDir: path.join(pathVal, "registry"),
          archiveDir: path.join(pathVal, "archive"),
        };

        if (!fs.existsSync(customPaths.initializedFlagPath)) {
          const createAnswer = await ui.promptInput(rl, "No tenant-universe initialized at this path. Create and bootstrap now? (y/N)", true);
          if (createAnswer && /^[yY]/.test(createAnswer.trim())) {
            const summary = runBootstrapIngestion(customPaths as any);
            ui.colourLog("!done", `Bootstrap complete; ingested=${summary.ingestedCount}`);
            // Reload runtime settings and state
            runtimeState = updateRuntimeSettings(runtimeState, persisted);
          } else {
            ui.colourLog("!help", "Skipped bootstrap.");
          }
        } else {
          // Already initialized: reload registries/settings
          runtimeState = updateRuntimeSettings(runtimeState, persisted);
          ui.colourLog("!done", `Workspace root set to ${pathVal}`);
        }

        await loop();
        return;
      }

      // Generic folder/path setting updates for non-workspace keys
      if (item.capability === "prismata.universe.capability.app-settings-paths") {
        const keyValue = String((item as any).key_value ?? "").trim();
        const pickMode = String((item as any).pick_mode ?? "").trim().toLowerCase();

        if (keyValue) {
          let nextValue: string | undefined;

          if (pickMode === "folder") {
            const locResult = await dispatcher.execute("prismata.universe.capability.fs-search-location", {
              selectedObjects,
              referenceObject,
              args: { mode: "folder" },
              runtimeState,
              services,
            });

            const location = (((locResult as any)?.location) ?? (((locResult as any)?.data as any)?.location)) as any;
            if (!location || !location.path) {
              ui.colourLog("!help", "Path selection cancelled.");
              await loop();
              return;
            }

            nextValue = String(location.path);
          } else {
            const entered = await ui.promptInput(rl, `Enter value for ${keyValue} or press Enter to cancel`, true);
            if (!entered || !entered.trim()) {
              ui.colourLog("!help", "Update cancelled.");
              await loop();
              return;
            }
            nextValue = entered.trim();
          }

          const nextSettings = {
            ...runtimeState.settings,
            paths: { ...(runtimeState.settings?.paths ?? {}), [keyValue]: nextValue },
          };
          const persisted = saveUniverseSettings(universePaths, nextSettings);
          runtimeState = updateRuntimeSettings(runtimeState, persisted);
          ui.colourLog("!done", `Updated paths.${keyValue} = ${nextValue}`);
          await loop();
          return;
        }
      }

      // Special-case Ignore File Types settings menu: prompt user for add/remove/list
      if (item.capability === "prismata.universe.capability.app-settings-ignore") {
        const menuAction = String(((item as any).action) ?? (args && (args as any).action) ?? "list").toLowerCase();

        if (menuAction === "add") {
          const ext = await ui.promptInput(rl, "Enter extension to ignore (e.g. .mid or mid) or press Enter to cancel", true);
          if (!ext || !ext.trim()) {
            await loop();
            return;
          }

          const added = await dispatcher.execute("prismata.universe.capability.app-settings-ignore", {
            selectedObjects,
            referenceObject,
            args: { action: "add", value: ext.trim() },
            runtimeState,
            services,
          });

          const list = (added.data as any)?.ignore_extensions ?? [];
          ui.colourLog("!done", `Ignore extensions updated. Count=${list.length}`);
          await loop();
          return;
        }

        if (menuAction === "remove") {
          // fetch current list
          const listResp = await dispatcher.execute("prismata.universe.capability.app-settings-ignore", {
            selectedObjects,
            referenceObject,
            args: { action: "list" },
            runtimeState,
            services,
          });

          const current = (listResp.data as any)?.ignore_extensions ?? [];
          if (!Array.isArray(current) || current.length === 0) {
            ui.colourLog("!warn", "No ignore extensions configured.");
            await loop();
            return;
          }

          const rows = current.map((v: any, i: number) => ({ key: String(i + 1), label: String(v) }));
          ui.renderSelectionTable("Ignore Extensions", rows, { width: 80 });
          const choice = await ui.promptInput(rl, `Select extension to remove (1-${rows.length}) or type extension to remove, or press Enter to cancel`, true);
          if (!choice || !choice.trim()) {
            ui.colourLog("!help", "Remove cancelled.");
            await loop();
            return;
          }

          let execArgs: any = { action: "remove" };
          const raw = choice.trim();
          if (/^[0-9]+$/.test(raw)) {
            const num = Number.parseInt(raw, 10);
            if (Number.isNaN(num) || num < 1 || num > rows.length) {
              ui.colourLog("!warn", "Invalid selection; cancelling.");
              await loop();
              return;
            }
            execArgs.index = num - 1;
          } else {
            execArgs.value = raw;
          }

          const removed = await dispatcher.execute("prismata.universe.capability.app-settings-ignore", {
            selectedObjects,
            referenceObject,
            args: execArgs,
            runtimeState,
            services,
          });

          const list = (removed.data as any)?.ignore_extensions ?? [];
          ui.colourLog("!done", `Ignore extensions updated. Count=${list.length}`);
          await loop();
          return;
        }

        // default: list
        const resp = await dispatcher.execute("prismata.universe.capability.app-settings-ignore", {
          selectedObjects,
          referenceObject,
          args: { action: "list" },
          runtimeState,
          services,
        });

        const cur = (resp.data as any)?.ignore_extensions ?? [];
        if (!cur || (Array.isArray(cur) && cur.length === 0)) {
          ui.colourLog("!help", "No ignore extensions configured.");
        } else {
          ui.renderSelectionTable("Ignore Extensions", cur.map((v: any, i: number) => ({ key: String(i + 1), label: String(v) })), { width: 80 });
          await ui.promptInput(rl, "Press Enter to continue", true);
        }

        await loop();
        return;
      }

      if (item.capability === "prismata.universe.capability.fs-search") {
        // Map visible labels/keys to search param types
        const labelToType: Record<string, string> = {
          "File Type": "fileTypes",
          "Text Query": "queries",
          Tags: "tags",
          "Search Canonical Folders Only (Y/N)": "canonicalOnly",
          "Search Folders Recursively (Y/N)": "recursive",
        };
        // Active parameters are shown in the menu header when available.

        const ptype = labelToType[item.label] ?? "queries";

        if (ptype === "canonicalOnly" || ptype === "recursive") {
          // Toggle the boolean flag
          args = { action: "toggle", type: ptype };
        } else {
          const actionOptions = [
            { label: "Add", value: "add" },
            { label: "Remove", value: "remove" },
            { label: "Back", value: "back" },
          ];

          const actionAnswer = await ui.promptInput(
            rl,
            `Choose action (1) Add, (2) Remove, (3) Back [1]`,
            true
          );

          const raw = (actionAnswer && actionAnswer.trim()) || "";

          // If the user typed a non-numeric value (e.g. 'yaml') treat that as a direct Add
          if (raw && !/^[0-9]+$/.test(raw)) {
            const values = [raw];

            for (const v of values) {
              await dispatcher.execute("prismata.universe.capability.fs-search", {
                selectedObjects,
                referenceObject,
                args: { action: "add", type: ptype, value: v },
                runtimeState,
                services,
              });
            }

            ui.colourLog("!done", `Added ${values.length} value(s) to ${item.label}`);
            await loop();
            return;
          }

          const chosen = raw || "1";
          const action = actionOptions[Number(chosen) - 1]?.value;

          if (!action || action === "back") {
            await loop();
            return;
          }

          if (action === "add") {
            const values = await ui.promptMultiInput(rl, `Add value for ${item.label}`);
            if (!values || values.length === 0) {
              await loop();
              return;
            }

            // Add each value via the fs-search capability
            for (const v of values) {
              await dispatcher.execute("prismata.universe.capability.fs-search", {
                selectedObjects,
                referenceObject,
                args: { action: "add", type: ptype, value: v },
                runtimeState,
                services,
              });
            }

            ui.colourLog("!done", `Added ${values.length} value(s) to ${item.label}`);
            await loop();
            return;
          } else if (action === "remove") {
            // Fetch current params to offer choices
            const listResult = await dispatcher.execute("prismata.universe.capability.fs-search", {
              selectedObjects,
              referenceObject,
              args: { action: "list" },
              runtimeState,
              services,
            });

            const current = (listResult.data as any)?.params?.[ptype] ?? [];
            if (!Array.isArray(current) || current.length === 0) {
              ui.colourLog("!warn", `No values set for ${item.label}`);
              await loop();
              return;
            }

            const rows = current.map((v: any, i: number) => ({ key: String(i + 1), label: String(v) }));
            ui.renderSelectionTable(`Values for ${item.label}`, rows, { width: 80 });

            const choice = await ui.promptInput(rl, `Select value to remove (1-${rows.length}) or press Enter to cancel`, true);
            if (!choice || !choice.trim()) {
              ui.colourLog("!help", "Remove cancelled.");
              await loop();
              return;
            }

            const num = Number.parseInt(choice.trim(), 10);
            if (Number.isNaN(num) || num < 1 || num > rows.length) {
              ui.colourLog("!warn", "Invalid selection; cancelling.");
              await loop();
              return;
            }

            const value = current[num - 1];
            args = { action: "remove", type: ptype, value };
          }
        }
      }
      if (item.capability === "prismata.universe.capability.fs-search-results") {
        if (!pythonVisiblePanes.includes("results_list")) {
          ui.colourLog("!warn", "[ui_interface] results_list pane is disabled; cannot render search results.");
          await ui.promptInput(rl, "Press Enter to continue", true);
          await loop();
          return;
        }

        // Run the canonical search execute to get fresh results
        const exec = await dispatcher.execute("prismata.universe.capability.fs-search-execute", {
          selectedObjects,
          referenceObject,
          args: {},
          runtimeState,
          services,
        });

        const results = ((exec as any).results as any) ?? (exec.data as any)?.results ?? [];
        const versionsMap = (exec as any)?.versions ?? {};

        const selected = await renderResultsList(ui, rl, results as any, {
          searchParams: runtimeState.searchParams,
          paths: runtimeState.settings?.paths as Record<string, string> | undefined,
        });
        if (selected) {
          if (pythonVisiblePanes.includes("preview")) {
            renderPreview(ui, selected);
          }

          const basename = (selected.relativePath || selected.fullPath).split("/").pop() ?? selected.relativePath ?? selected.fullPath;
          const versions = versionsMap[(basename || "").toLowerCase()] ?? [];
          if (
            pythonVisiblePanes.includes("version_carousel") &&
            Array.isArray(versions) &&
            versions.length > 1
          ) {
            ui.colourLog("!help", `Found ${versions.length} versions; entering carousel.`);
            await renderVersionCarousel(ui, rl, versions as any);
          }
        }

        await ui.promptInput(rl, "Press Enter to return to results menu", true);
        await loop();
        return;
      }

      // Special-case Add/Remove Search Paths: prompt action first, then run folder picker only for Add
      if (
        item.capability === "prismata.universe.capability.fs-search-location" &&
        /search path/i.test(item.label)
      ) {
        const actionAnswer = await ui.promptInput(
          rl,
          `Choose action: (1) Add path, (2) Remove path, (3) Back [1]`,
          true
        );

        const rawAction = (actionAnswer && actionAnswer.trim()) || "1";
        if (rawAction === "3" || rawAction.toLowerCase() === "back") {
          await loop();
          return;
        }

        if (rawAction === "1") {
          // Add path via native picker
          const res = await dispatcher.execute("prismata.universe.capability.fs-search-location", {
            selectedObjects,
            referenceObject,
            args: { mode: "folder" },
            runtimeState,
            services,
          });
          const location = (((res as any)?.location) ?? (((res as any)?.data as any)?.location)) as any;
          if (!location || !location.path) {
            ui.colourLog("!help", "Add cancelled.");
            await loop();
            return;
          }

          const pathVal = String(location.path);
          if (!runtimeState.searchParams) runtimeState.searchParams = { folders: [], projects: [], fileTypes: [], queries: [], tags: [], canonicalOnly: false, recursive: true };

          const existingSettings = (runtimeState.settings?.paths?.project_scope ?? []) as any;
          const settingsArr = Array.isArray(existingSettings) ? existingSettings.map(String) : (typeof existingSettings === "string" ? [String(existingSettings)] : []);
          if (!settingsArr.includes(pathVal)) settingsArr.push(pathVal);

          runtimeState.searchParams.projects = settingsArr.slice();
          const nextSettings = {
            ...runtimeState.settings,
            paths: { ...(runtimeState.settings?.paths ?? {}), project_scope: settingsArr },
          };
          const persisted = saveUniverseSettings(universePaths, nextSettings);
          runtimeState = updateRuntimeSettings(runtimeState, persisted);
          ui.colourLog("!done", `Added project scope path: ${pathVal}`);
          await loop();
          return;
        }

        if (rawAction === "2") {
          // Remove path: present current project_scope entries for selection
          const currentSettings = (runtimeState.settings?.paths?.project_scope ?? []) as any;
          const currentArr = Array.isArray(currentSettings)
            ? currentSettings.map(String)
            : (typeof currentSettings === "string" && currentSettings.trim() ? [String(currentSettings)] : []);

          if (currentArr.length === 0) {
            ui.colourLog("!warn", "No project scope paths configured.");
            await loop();
            return;
          }

          const rows = currentArr.map((v: string, i: number) => ({ key: String(i + 1), label: v }));
          ui.renderSelectionTable("Remove entry from Search path(s)", rows, { width: 100 });
          const choice = await ui.promptInput(rl, `Remove entry from Search path(s) (1-${rows.length}) or press Enter to cancel`, true);
          if (!choice || !choice.trim()) {
            ui.colourLog("!help", "Remove cancelled.");
            await loop();
            return;
          }

          const num = Number.parseInt(choice.trim(), 10);
          if (Number.isNaN(num) || num < 1 || num > rows.length) {
            ui.colourLog("!warn", "Invalid selection; cancelling.");
            await loop();
            return;
          }

          const removed = currentArr.splice(num - 1, 1);
          const nextSettings = {
            ...runtimeState.settings,
            paths: { ...(runtimeState.settings?.paths ?? {}), project_scope: currentArr },
          };
          const persisted = saveUniverseSettings(universePaths, nextSettings);
          runtimeState = updateRuntimeSettings(runtimeState, persisted);
          if (!runtimeState.searchParams) runtimeState.searchParams = { folders: [], projects: [], fileTypes: [], queries: [], tags: [], canonicalOnly: false, recursive: true };
          runtimeState.searchParams.projects = currentArr.slice();
          ui.colourLog("!done", `Removed project scope path: ${removed[0]}`);
          await loop();
          return;
        }
      }

      // Prompt + set value for naming/export/registry settings capabilities.
      if (
        item.capability === "prismata.universe.capability.app-settings-naming" ||
        item.capability === "prismata.universe.capability.app-settings-export" ||
        item.capability === "prismata.universe.capability.app-settings-registry"
      ) {
        const settingKey = String((item as any).setting_key ?? "").trim();
        const valueType = String((item as any).value_type ?? "string").toLowerCase();

        if (settingKey) {
          if (valueType === "boolean") {
            const raw = await ui.promptInput(rl, `Set ${settingKey} (y/n)`, true);
            if (!raw || !raw.trim()) {
              ui.colourLog("!help", "Update cancelled.");
              await loop();
              return;
            }
            const normalized = raw.trim().toLowerCase();
            if (!["y", "yes", "n", "no", "true", "false"].includes(normalized)) {
              ui.colourLog("!warn", "Expected y/n (or true/false). Update cancelled.");
              await loop();
              return;
            }
            args = { [settingKey]: ["y", "yes", "true"].includes(normalized) };
          } else if (valueType === "string_array") {
            const values = await ui.promptMultiInput(rl, `Add one or more values for ${settingKey}`);
            if (!values || values.length === 0) {
              ui.colourLog("!help", "Update cancelled.");
              await loop();
              return;
            }
            args = { [settingKey]: values.map(v => String(v).trim()).filter(Boolean) };
          } else if (valueType === "object_json") {
            const raw = await ui.promptInput(rl, `Enter JSON object for ${settingKey}`, true);
            if (!raw || !raw.trim()) {
              ui.colourLog("!help", "Update cancelled.");
              await loop();
              return;
            }

            try {
              const parsed = JSON.parse(raw.trim());
              if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
                ui.colourLog("!warn", "Expected a JSON object. Update cancelled.");
                await loop();
                return;
              }
              args = { [settingKey]: parsed };
            } catch {
              ui.colourLog("!warn", "Invalid JSON object. Update cancelled.");
              await loop();
              return;
            }
          } else {
            const raw = await ui.promptInput(rl, `Enter value for ${settingKey}`, true);
            if (!raw || !raw.trim()) {
              ui.colourLog("!help", "Update cancelled.");
              await loop();
              return;
            }
            args = { [settingKey]: raw.trim() };
          }
        }
      }

      // Generic dispatch:
      const result = await dispatcher.execute(item.capability, { selectedObjects, referenceObject, args, runtimeState, services });
      // Show capability message and raw data (if any)
      ui.colourLog("!help", result.message);
      if (result.data !== undefined) console.log(JSON.stringify(result.data, null, 2));
      const data = result.data as Record<string, unknown> | undefined;
      // If capability returned settings-like data (paths/naming/export/registry/features),
      // merge into runtimeState using updateRuntimeSettings()
      if (data && typeof data === "object") {
        runtimeState = updateRuntimeSettings(runtimeState, {
          paths: data.paths as Record<string, unknown> | undefined,
          naming: data.naming as Record<string, unknown> | undefined,
          export: data.export as Record<string, unknown> | undefined,
          registry: data.registry as Record<string, unknown> | undefined,
          features: data.features as Record<string, unknown> | undefined,
          ignore_extensions: Array.isArray(data.ignore_extensions)
            ? data.ignore_extensions.map(v => String(v))
            : undefined,
        });
      }

      // NOTE: Removed interactive confirmation prompt for toggles. The
      // capabilities for auto-archive and auto-versioning toggle their state
      // when executed. We surface the current state in the menu header instead
      // of prompting here.

      if (item.capability === "prismata.universe.capability.app-bootstrap-run") {
        runtimeState = getRuntimeState(universePaths);
        currentMenuId = "prismata.universe.menu.main";
      }

      if (item.capability === "prismata.universe.capability.fs-search-execute") {
        const searchResult = runSearch({
          rootPath: ".",
          fileTypes: [".yaml", ".yml", ".json"],
        });
        selectedObjects = searchResult.results.map(r => ({
          id: r.id,
          udi: r.udi,
          type: r.extension.replace(".", ""),
          version: undefined,
          registryKey: undefined,
          semanticKeys: ["path"],
        }));

        ui.colourLog("!done", "Search completed:", searchResult.results.length, "results.");
      }
    }

    await loop();
  }

  function loadView(id: string) {
    try {
      return { kind: "menu", menu: loadMenu(id) } as const;
    } catch (error: any) {
      if (error?.code !== "ENOENT") {
        throw error;
      }

      return { kind: "schema", schema: loadSchema(id) } as const;
    }
  }

  await loop();
}
