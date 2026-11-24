import * as fs from "fs";
import * as path from "path";

export interface MenuDefinition {
  id: string;
  type: "menu";
  title: string;
  header?: { type: string } | null;
  items: {
    key: string;
    label: string;
    capability: string | null;
    submenu_ref: string | null;
    ui_framework?: string;
    visibility_condition?: string;
  }[];
}

export type UiFramework =
  | "basic"
  | "menu"
  | "pane"
  | "multi_pane"
  | "structured_editor"
  | "toggle_table"
  | "diff_view"
  | "validation_panel"
  | "custom";

const ALLOWED_UI_FRAMEWORKS = new Set<UiFramework>([
  "basic",
  "menu",
  "pane",
  "multi_pane",
  "structured_editor",
  "toggle_table",
  "diff_view",
  "validation_panel",
  "custom",
]);

export interface SchemaDefinition {
  id: string;
  version: string;
  type: string;
  properties: Record<string, { type: string }>;
}

function parseScalar(value: string): string | null {
  const trimmed = value.trim();

  if (trimmed === "null") {
    return null;
  }

  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }

  return trimmed;
}

function normalizeLegacyMenuItem(item: Record<string, unknown>): MenuDefinition["items"][number] {
  const normalized = { ...item } as Record<string, unknown>;

  if (
    (typeof normalized.label !== "string" || (normalized.label as string).trim() === "") &&
    typeof normalized.name === "string"
  ) {
    normalized.label = normalized.name;
  }

  if (
    (typeof normalized.submenu_ref !== "string" || (normalized.submenu_ref as string).trim() === "") &&
    typeof normalized.navigateTarget === "string"
  ) {
    normalized.submenu_ref = normalized.navigateTarget;
  }

  if (
    (typeof normalized.visibility_condition !== "string" || (normalized.visibility_condition as string).trim() === "") &&
    typeof normalized.visibilityCondition === "string"
  ) {
    normalized.visibility_condition = normalized.visibilityCondition;
  }

  if (
    (typeof normalized.key !== "string" || (normalized.key as string).trim() === "") &&
    typeof normalized.udi === "string"
  ) {
    normalized.key = normalized.udi;
  }

  if (
    typeof normalized.id === "string" &&
    (typeof normalized.key !== "string" || (normalized.key as string).trim() === "")
  ) {
    normalized.key = normalized.id as string;
  }

  if (typeof normalized.header === "object" && normalized.header !== null && !("text" in (normalized.header as Record<string, unknown>))) {
    const headerValue = normalized.header as Record<string, unknown>;
    if (typeof headerValue.title === "string") {
      headerValue.text = headerValue.title;
    }
  }

  return normalized as MenuDefinition["items"][number];
}

export function loadMenuYaml(yaml: string): MenuDefinition {
  const menu: Partial<MenuDefinition> & { items: MenuDefinition["items"] } = {
    items: [],
  };

  let inHeader = false;
  let currentItem: MenuDefinition["items"][number] | null = null;

  for (const rawLine of yaml.split(/\r?\n/)) {
    const line = rawLine.trimEnd();

    if (!line.trim()) {
      continue;
    }

    if (line.trim() === "items:") {
      inHeader = false;
      continue;
    }

    if (line.trim() === "header:") {
      inHeader = true;
      continue;
    }

    if (line.startsWith("  - ")) {
      if (currentItem) {
        menu.items.push(normalizeLegacyMenuItem(currentItem as Record<string, unknown>));
      }

      currentItem = {
        key: "",
        label: "",
        capability: null,
        submenu_ref: null,
      };

      const entry = line.slice(4);
      const separatorIndex = entry.indexOf(":");

      if (separatorIndex !== -1) {
        const key = entry.slice(0, separatorIndex).trim();
        const value = entry.slice(separatorIndex + 1).trim();
        (currentItem as Record<string, unknown>)[key] = parseScalar(value);
      }

      continue;
    }

    const separatorIndex = line.indexOf(":");

    if (separatorIndex === -1) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim();

    if (currentItem) {
      (currentItem as Record<string, unknown>)[key] = parseScalar(value);
      continue;
    }

    if (inHeader) {
      (menu as any).header = (menu as any).header ?? {};
      (menu as any).header[key] = parseScalar(value);
    } else {
      (menu as Record<string, unknown>)[key] = parseScalar(value);
    }
  }

  if (currentItem) {
    menu.items.push(normalizeLegacyMenuItem(currentItem as Record<string, unknown>));
  }

  return menu as MenuDefinition;
}

export function loadSchemaYaml(yaml: string): SchemaDefinition {
  const schema: Partial<SchemaDefinition> & {
    properties: NonNullable<SchemaDefinition["properties"]>;
  } = {
    properties: {},
  };

  let inProperties = false;

  for (const rawLine of yaml.split(/\r?\n/)) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();

    if (!trimmed) {
      continue;
    }

    if (trimmed === "properties:") {
      inProperties = true;
      continue;
    }

    const separatorIndex = trimmed.indexOf(":");

    if (separatorIndex === -1) {
      continue;
    }

    if (inProperties && line.startsWith("  ")) {
      const key = trimmed.slice(0, separatorIndex).trim();
      const value = trimmed.slice(separatorIndex + 1).trim();
      const typeMatch = value.match(/type:\s*([a-zA-Z_][a-zA-Z0-9_-]*)/);

      schema.properties[key] = {
        type: typeMatch?.[1] ?? "unknown",
      };

      continue;
    }

    inProperties = false;

    const key = trimmed.slice(0, separatorIndex).trim();
    const value = trimmed.slice(separatorIndex + 1).trim();
    (schema as Record<string, unknown>)[key] = parseScalar(value);
  }

  return schema as SchemaDefinition;
}

export function normalizeViewName(id: string): string {
  const normalized = id
    .replace("prismata.universe.menu.", "")
    .replace("prismata.universe.menu-", "")
    .replace(/\./g, "-");

  return normalized;
}

export function normalizeMenuItemFrameworks(
  menu: MenuDefinition,
  sourcePath: string
): MenuDefinition {
  const normalized = menu.items.map(item => {
    const declared = typeof item.ui_framework === "string" ? item.ui_framework.trim() : "";
    const candidate = declared ? declared.toLowerCase() : "basic";
    const effective = ALLOWED_UI_FRAMEWORKS.has(candidate as UiFramework)
      ? (candidate as UiFramework)
      : "basic";

    if (!declared) {
      console.warn(
        `[Universe][menu] Missing ui_framework in ${sourcePath}; item key=${item.key}, label=${item.label}; defaulting to "basic".`
      );
    } else if (effective === "basic" && candidate !== "basic") {
      console.warn(
        `[Universe][menu] Unsupported ui_framework="${declared}" in ${sourcePath}; item key=${item.key}, label=${item.label}; defaulting to "basic".`
      );
    }

    return { ...item, ui_framework: effective };
  });

  return {
    ...menu,
    items: normalized,
  };
}

export function validateMenuItemFrameworks(
  menu: MenuDefinition,
  sourcePath: string
): MenuDefinition {
  return normalizeMenuItemFrameworks(menu, sourcePath);
}

export function injectFrameworkFromCapability(
  menu: MenuDefinition,
  capabilityMap: Record<string, UiFramework>
): MenuDefinition {
  const items = menu.items.map(item => {
    if (item.ui_framework) return item;
    if (!item.capability) return item;
    const mapped = capabilityMap[item.capability];
    if (mapped && ALLOWED_UI_FRAMEWORKS.has(mapped)) {
      return { ...item, ui_framework: mapped };
    }
    return item;
  });

  return { ...menu, items };
}

export function loadCapabilityFrameworkMapFromFile(filePath: string): Record<string, UiFramework> {
  if (!filePath || !fs.existsSync(filePath)) {
    return {};
  }

  const out: Record<string, UiFramework> = {};
  for (const rawLine of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const idx = line.indexOf(":");
    if (idx === -1) continue;
    const key = line.slice(0, idx).trim();
    const val = line.slice(idx + 1).trim();
    if (ALLOWED_UI_FRAMEWORKS.has(val as UiFramework)) {
      out[key] = val as UiFramework;
    }
  }
  return out;
}

export function loadMenuFromFile(menuFilePath: string): MenuDefinition {
  const yaml = fs.readFileSync(menuFilePath, "utf8");
  const loadedMenu = loadMenuYaml(yaml);
  return validateMenuItemFrameworks(loadedMenu, menuFilePath);
}

export function loadSchemaFromFile(schemaFilePath: string, schemaId?: string): SchemaDefinition {
  const yaml = fs.readFileSync(schemaFilePath, "utf8");
  const schema = loadSchemaYaml(yaml);

  if (!schema.id && schemaId) {
    schema.id = schemaId;
  }

  return schema;
}

export function loadCapabilityFrameworkMap(filePath: string): Record<string, UiFramework> {
  return loadCapabilityFrameworkMapFromFile(filePath);
}

export function loadMenu(id: string, basePath = process.cwd()): MenuDefinition {
  const fileName = `${normalizeViewName(id)}-menu.yaml`;
  const fullPath = path.join(basePath, "config", "project-menus", fileName);
  return loadMenuFromFile(fullPath);
}

export function loadSchema(id: string, basePath = process.cwd()): SchemaDefinition {
  const schemaId = id.replace("prismata.universe.menu.", "prismata.universe.schema.");
  const fileName = `${normalizeViewName(id)}.yaml`;
  const fullPath = path.join(basePath, "config", "schemas", fileName);
  return loadSchemaFromFile(fullPath, schemaId);
}

// ─── PCMS-2026 Menu Tree Support ─────────────────────────────────────────────

export interface Pcms2026MenuHeader {
  udi?: string;
  text?: string;
  style?: string;
  colourScheme?: string;
  borderScheme?: string;
  visibilityMode?: string;
}

export interface Pcms2026MenuItem {
  udi: string;
  key: string;
  name: string;
  label: string;
  type: string;
  order: number;
  selectionMethod: string;
  action: string;
  ui_framework: UiFramework;
  capability: string | null;
  executeTarget: string | null;
  navigateTarget: string | null;
  submenu_ref: string | null;
  icon?: string;
  colourScheme?: string;
  description?: string;
  visibilityMode?: string;
  visibilityCondition?: string | null;
  visibilityDependencies?: string[];
  enableMode?: string;
  enableCondition?: string | null;
  enableDependencies?: string[];
}

export interface Pcms2026Menu {
  id: string;
  key: string;
  udi: string;
  name: string;
  title?: string;
  label?: string;
  position?: string;
  order?: number;
  type?: string;
  icon?: string;
  colourScheme?: string;
  borderScheme?: string;
  description?: string;
  finalItemType?: string;
  header?: Pcms2026MenuHeader;
  footer?: Pcms2026MenuHeader;
  items: Pcms2026MenuItem[];
}

export interface Pcms2026MenuTree {
  menus: Pcms2026Menu[];
}

function parsePcms2026ScalarValue(v: string): string | number | boolean | null {
  const t = v.trim();
  if (t === "null" || t === "~") return null;
  if (t === "true") return true;
  if (t === "false") return false;
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    return t.slice(1, -1);
  }
  const n = Number(t);
  if (!Number.isNaN(n) && t !== "") return n;
  return t;
}

function normalizePcms2026Item(raw: Record<string, unknown>): Pcms2026MenuItem {
  const label = (raw.label as string) || (raw.name as string) || "";
  const name = (raw.name as string) || label;
  const framework = typeof raw.ui_framework === "string" ? raw.ui_framework.toLowerCase() : "basic";
  const effectiveFramework: UiFramework = ALLOWED_UI_FRAMEWORKS.has(framework as UiFramework)
    ? (framework as UiFramework)
    : "basic";
  return {
    udi: (raw.udi as string) || "",
    key: (raw.key as string) || "",
    name,
    label,
    type: (raw.type as string) || "action",
    order: typeof raw.order === "number" ? raw.order : Number(raw.order) || 0,
    selectionMethod: (raw.selectionMethod as string) || "number",
    action: (raw.action as string) || "execute",
    ui_framework: effectiveFramework,
    capability: (raw.capability as string) ?? null,
    executeTarget: (raw.executeTarget as string) ?? null,
    navigateTarget: (raw.navigateTarget as string) ?? null,
    submenu_ref: (raw.submenu_ref as string) ?? null,
    icon: raw.icon as string | undefined,
    colourScheme: raw.colourScheme as string | undefined,
    description: raw.description as string | undefined,
    visibilityMode: raw.visibilityMode as string | undefined,
    visibilityCondition: (raw.visibilityCondition as string | null) ?? null,
    visibilityDependencies: Array.isArray(raw.visibilityDependencies)
      ? (raw.visibilityDependencies as string[])
      : undefined,
    enableMode: raw.enableMode as string | undefined,
    enableCondition: (raw.enableCondition as string | null) ?? null,
    enableDependencies: Array.isArray(raw.enableDependencies)
      ? (raw.enableDependencies as string[])
      : undefined,
  };
}

function normalizePcms2026Menu(
  raw: Record<string, unknown>,
  rawItems: Record<string, unknown>[],
  rawHeader?: Record<string, string>,
  rawFooter?: Record<string, string>
): Pcms2026Menu {
  const toHeader = (obj?: Record<string, string>): Pcms2026MenuHeader | undefined => {
    if (!obj || Object.keys(obj).length === 0) return undefined;
    return {
      udi: obj.udi,
      text: obj.text,
      style: obj.style,
      colourScheme: obj.colourScheme,
      borderScheme: obj.borderScheme,
      visibilityMode: obj.visibilityMode,
    };
  };
  return {
    id: (raw.id as string) || "",
    key: (raw.key as string) || "",
    udi: (raw.udi as string) || "",
    name: (raw.name as string) || "",
    title: raw.title as string | undefined,
    label: raw.label as string | undefined,
    position: raw.position as string | undefined,
    order: typeof raw.order === "number" ? raw.order : Number(raw.order) || 0,
    type: raw.type as string | undefined,
    icon: raw.icon as string | undefined,
    colourScheme: raw.colourScheme as string | undefined,
    borderScheme: raw.borderScheme as string | undefined,
    description: raw.description as string | undefined,
    finalItemType: raw.finalItemType as string | undefined,
    header: toHeader(rawHeader),
    footer: toHeader(rawFooter),
    items: rawItems.map(normalizePcms2026Item),
  };
}

export function parsePcms2026MenuTreeFromYaml(content: string): Pcms2026MenuTree {
  type Block =
    | "root"
    | "in_menus"
    | "in_menu"
    | "in_header"
    | "in_footer"
    | "in_items"
    | "in_item"
    | "in_item_deps";

  const menus: Pcms2026Menu[] = [];

  let menuRaw: Record<string, unknown> = {};
  let menuItems: Record<string, unknown>[] = [];
  let menuHeader: Record<string, string> = {};
  let menuFooter: Record<string, string> = {};
  let itemRaw: Record<string, unknown> = {};
  let itemDepsKey = "";

  let block: Block = "root";

  const flushItem = () => {
    if (Object.keys(itemRaw).length > 0) {
      menuItems.push({ ...itemRaw });
      itemRaw = {};
      itemDepsKey = "";
    }
  };

  const flushMenu = () => {
    if (Object.keys(menuRaw).length > 0) {
      flushItem();
      menus.push(normalizePcms2026Menu(menuRaw, menuItems, menuHeader, menuFooter));
      menuRaw = {};
      menuItems = [];
      menuHeader = {};
      menuFooter = {};
    }
  };

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.replace(/\r$/, "");
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const indent = line.search(/\S|$/);

    if (trimmed === "menus:" && indent === 0) {
      block = "in_menus";
      continue;
    }

    if (block === "root") continue;

    // New menu entry at indent 2: "  - id: ..."
    if (indent === 2 && trimmed.startsWith("- ")) {
      flushMenu();
      block = "in_menu";
      const rest = trimmed.slice(2);
      const sep = rest.indexOf(":");
      if (sep !== -1) {
        const k = rest.slice(0, sep).trim();
        const v = rest.slice(sep + 1).trim();
        if (k && v !== "") menuRaw[k] = parsePcms2026ScalarValue(v);
      }
      continue;
    }

    if (block === "in_menus") continue;

    // Menu-level property at indent 4
    if (indent === 4) {
      if (block === "in_items" || block === "in_item" || block === "in_item_deps") {
        flushItem();
        block = "in_menu";
      }
      if (trimmed === "header:") { block = "in_header"; menuHeader = {}; continue; }
      if (trimmed === "footer:") { block = "in_footer"; menuFooter = {}; continue; }
      if (trimmed === "items:") { block = "in_items"; continue; }

      if (block === "in_header" || block === "in_footer") {
        block = "in_menu";
      }

      const sep = trimmed.indexOf(":");
      if (sep !== -1) {
        const k = trimmed.slice(0, sep).trim();
        const v = trimmed.slice(sep + 1).trim();
        menuRaw[k] = parsePcms2026ScalarValue(v);
      }
      continue;
    }

    // Header / footer sub-props at indent 6
    if (indent === 6 && (block === "in_header" || block === "in_footer")) {
      const sep = trimmed.indexOf(":");
      if (sep !== -1) {
        const k = trimmed.slice(0, sep).trim();
        const v = trimmed.slice(sep + 1).trim();
        const target = block === "in_header" ? menuHeader : menuFooter;
        target[k] = v.startsWith('"') || v.startsWith("'") ? v.slice(1, -1) : v;
      }
      continue;
    }

    // New item entry at indent 6: "      - udi: ..."
    if (indent === 6 && trimmed.startsWith("- ") && (block === "in_items" || block === "in_item" || block === "in_item_deps")) {
      flushItem();
      block = "in_item";
      const rest = trimmed.slice(2);
      const sep = rest.indexOf(":");
      if (sep !== -1) {
        const k = rest.slice(0, sep).trim();
        const v = rest.slice(sep + 1).trim();
        if (k && v !== "") itemRaw[k] = parsePcms2026ScalarValue(v);
      }
      continue;
    }

    // Item property at indent 8
    if (indent === 8 && (block === "in_item" || block === "in_item_deps")) {
      if (trimmed.endsWith(":") && !trimmed.includes(": ")) {
        const k = trimmed.slice(0, -1).trim();
        itemRaw[k] = [];
        itemDepsKey = k;
        block = "in_item_deps";
        continue;
      }
      block = "in_item";
      itemDepsKey = "";
      const sep = trimmed.indexOf(":");
      if (sep !== -1) {
        const k = trimmed.slice(0, sep).trim();
        const v = trimmed.slice(sep + 1).trim();
        itemRaw[k] = parsePcms2026ScalarValue(v);
      }
      continue;
    }

    // Dependency list item at indent 10
    if (indent === 10 && block === "in_item_deps" && itemDepsKey) {
      if (trimmed.startsWith("- ")) {
        const val = trimmed.slice(2).trim();
        const arr = itemRaw[itemDepsKey];
        if (Array.isArray(arr)) arr.push(val);
      }
      continue;
    }
  }

  flushMenu();
  return { menus };
}

export function loadPcms2026MenuTree(filePath: string): Pcms2026MenuTree {
  const content = fs.readFileSync(filePath, "utf8");
  return parsePcms2026MenuTreeFromYaml(content);
}

export function findPcms2026MenuById(
  tree: Pcms2026MenuTree,
  id: string
): Pcms2026Menu | undefined {
  return tree.menus.find(m => m.id === id || m.udi === id || m.key === id);
}