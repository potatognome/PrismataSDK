import {
  computeSelectionLogic,
  SelectionLogicResult,
  SelectedObject,
} from "../selection/selectionLogic";
import { RuntimeState, UniversePaths, getSharedUiConfigFiles, getUniverseSettingsPath } from "../bootstrap/state";
import * as fs from "fs";

export interface MenuItem {
  key: string;
  label: string;
  capability: string | null;
  submenu_ref: string | null;
  ui_framework?: string;
  visibility_condition?: string;
}

export interface MenuDefinition {
  id: string;
  type: "menu";
  title: string;
  header?: { type: string } | null;
  items: MenuItem[];
}

export interface RenderedMenu {
  id: string;
  title: string;
  visibleItems: MenuItem[];
  activeCapabilities: string[];
  visiblePanes: string[];
  header?: string;
}

function renderSearchParamsHeader(runtimeState: RuntimeState | undefined): string | undefined {
  if (!runtimeState) return undefined;
  const p = runtimeState.searchParams;
  if (!p) {
    return "Search Parameters: (none configured)";
  }

  const lines: string[] = [];
  lines.push("Search parameters are provided by the Python runtime service.");
  lines.push(`projects: ${p.projects.length > 0 ? p.projects.join(", ") : "(none)"}`);
  lines.push(`file types: ${p.fileTypes.length > 0 ? p.fileTypes.join(", ") : "(all)"}`);
  lines.push(`queries: ${p.queries.length > 0 ? p.queries.join(", ") : "(none)"}`);
  lines.push(`tags: ${p.tags.length > 0 ? p.tags.join(", ") : "(none)"}`);
  return lines.join("\n");
}

function renderSearchLocationHeader(runtimeState: RuntimeState | undefined, paths?: UniversePaths): string | undefined {
  const workspace = String(
    (runtimeState?.settings?.paths as Record<string, unknown> | undefined)?.workspace_root ??
    paths?.workspaceRoot ??
    ""
  );
  return [
    "Search location details are provided by the Python runtime service.",
    `Workspace Root: ${workspace || "(not set)"}`,
  ].join("\n");
}

function renderSettingsFeaturesHeader(runtimeState: RuntimeState | undefined): string | undefined {
  const features = (runtimeState?.settings?.features as Record<string, unknown> | undefined) ?? {};
  return [
    "Settings feature details are provided by the Python runtime service.",
    `Auto-Archive: ${features.autoArchive ? "ON" : "OFF"}`,
    `Auto-Versioning: ${features.autoVersioning ? "ON" : "OFF"}`,
  ].join("\n");
}

function renderRuntimeStateHeader(
  runtimeState: RuntimeState | undefined,
  paths?: UniversePaths,
  prismataRoot?: string
): string | undefined {
  if (!runtimeState || !paths || !prismataRoot) return undefined;

  // Determine presence of runtime files
  const settingsPath = getUniverseSettingsPath(paths);
  const initializedFlag = paths.initializedFlagPath;

  const shared = getSharedUiConfigFiles(prismataRoot);
  const colours = shared.coloursJson;
  const border = shared.borderPatternsJson;

  const lines: string[] = [];

  const settingsExists = fs.existsSync(settingsPath);
  lines.push(
    `settings.json: ${settingsExists ? "✓" : "✗"}${settingsExists ? "" : `  (${settingsPath})`}`
  );

  const initializedExists = fs.existsSync(initializedFlag);
  lines.push(
    `initialized.flag: ${initializedExists ? "✓" : "✗"}${initializedExists ? "" : `  (${initializedFlag})`}`
  );

  const coloursExists = !!colours && fs.existsSync(colours);
  lines.push(
    `COLOURS.json: ${coloursExists ? "✓" : "✗"}${coloursExists ? "" : colours ? `  (${colours})` : ""}`
  );

  const borderExists = !!border && fs.existsSync(border);
  lines.push(
    `BORDER_PATTERNS.json: ${borderExists ? "✓" : "✗"}${borderExists ? "" : border ? `  (${border})` : ""}`
  );

  // Return a multi-line header (one file per line)
  return lines.join("\n");
}

function evaluateCondition(
  condition: string | undefined,
  logic: SelectionLogicResult,
  runtimeState?: RuntimeState
): boolean {
  if (!condition) return true;

  const { state, compatibility } = logic;
  const runtimeMode = String(runtimeState?.tuilkitRuntimeMode ?? "");
  const hasRuntimeMode = runtimeMode.length > 0;
  const tuilkitIngested =
    typeof runtimeState?.tuilkitIngested === "boolean"
      ? runtimeState.tuilkitIngested
      : !!runtimeState?.vileIngested;
  const tuilkitReady = hasRuntimeMode
    ? runtimeMode === "tuilkit" && tuilkitIngested
    : !!runtimeState?.vileIngested;

  switch (condition) {
    case "single_file_selected":
      return state.selectionType === "single";
    case "reference_object_selected":
      return state.referenceObjectSelected;
    case "heterogeneous_selection":
      return state.selectionType === "heterogeneous";
    case "homogeneous_selection":
      return state.selectionType === "homogeneous";
    case "semantic_compatible":
      return compatibility.semantic_compatible;
    case "version_compatible":
      return compatibility.version_compatible;
    case "type_compatible":
      return compatibility.type_compatible;
    case "bootstrap_mode":
      return !!runtimeState?.bootstrapMode;
    case "initialized":
      return !runtimeState?.bootstrapMode;
    case "vile_ingested":
      return tuilkitReady;
    case "vile_not_ingested":
      return !tuilkitReady;
    case "initialized_and_vile_ingested":
      return !runtimeState?.bootstrapMode && tuilkitReady;
    case "initialized_and_vile_not_ingested":
      return !runtimeState?.bootstrapMode && !tuilkitReady;
    default:
      return true;
  }
}

function computeVisiblePanes(
  logic: SelectionLogicResult,
  availablePaneIds?: Iterable<string>
): string[] {
  const panes: string[] = [];
  const { state, compatibility } = logic;
  const available = availablePaneIds ? new Set(availablePaneIds) : undefined;
  const includePane = (paneId: string) => {
    if (!available || available.has(paneId)) {
      panes.push(paneId);
    }
  };

  includePane("results_list");
  includePane("preview");

  if (state.selectionCount >= 1 && compatibility.version_compatible) {
    includePane("version_carousel");
  }

  if (state.selectionCount >= 2 && compatibility.semantic_compatible) {
    includePane("diff_panel");
  }

  return panes;
}

export function renderMenu(
  menu: MenuDefinition,
  selectedObjects: SelectedObject[],
  referenceObject?: SelectedObject,
  runtimeState?: RuntimeState,
  availablePaneIds?: Iterable<string>,
  paths?: UniversePaths,
  prismataRoot?: string
): RenderedMenu {
  const logic = computeSelectionLogic(selectedObjects, referenceObject);

  const visibleItems = menu.items.filter(item =>
    evaluateCondition(item.visibility_condition, logic, runtimeState)
  );

  const activeCapabilities = logic.visibleOperations;
  const visiblePanes = computeVisiblePanes(logic, availablePaneIds);

  const rendered: RenderedMenu = {
    id: menu.id,
    title: menu.title,
    visibleItems,
    activeCapabilities,
    visiblePanes,
  };

  // Optionally render a runtime-state header if the menu opts in
  if (menu.header && menu.header.type === "runtime_state") {
    rendered.header = renderRuntimeStateHeader(runtimeState, paths, prismataRoot);
  }

  if (menu.header && menu.header.type === "search_params") {
    rendered.header = renderSearchParamsHeader(runtimeState);
  }

  if (menu.header && menu.header.type === "search_location_state") {
    rendered.header = renderSearchLocationHeader(runtimeState, paths);
  }

  if (menu.header && menu.header.type === "settings_features") {
    rendered.header = renderSettingsFeaturesHeader(runtimeState);
  }

  return rendered;
}
