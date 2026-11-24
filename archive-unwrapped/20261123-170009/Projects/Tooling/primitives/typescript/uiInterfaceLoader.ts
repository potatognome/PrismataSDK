import * as fs from "fs";
import * as path from "path";
import { UiFramework } from "./menuLoaders";

export interface UiFrameworkOverridePaths {
  project?: string;
  tenant?: string;
}

export interface UiPaneCoordinates {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface UiPaneCarouselNavigation {
  wrap: boolean;
  jump: boolean;
  refresh: boolean;
}

export interface UiPaneCarousel {
  enabled: boolean;
  active_index?: number;
  navigation?: UiPaneCarouselNavigation;
}

export interface UiPaneDefinition {
  id: string;
  role: string;
  coordinates: UiPaneCoordinates;
  border_pattern?: string;
  // Optional per-pane override of the layout colour scheme
  colour_scheme_override?: string;
  carousel?: UiPaneCarousel;
}

export interface UniverseUiFrameworksConfig {
  ui_framework: UiFramework;
  sourcePath: string;
  overrides: UiFrameworkOverridePaths;
  hasProjectOverride: boolean;
  hasTenantOverride: boolean;
  panes: UiPaneDefinition[];
  layoutColourScheme?: string;
}

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

function parseScalar(value: string): string {
  const trimmed = value.trim();
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function parseBoolean(value: string): boolean | undefined {
  const normalized = value.trim().toLowerCase();
  if (normalized === "true") return true;
  if (normalized === "false") return false;
  return undefined;
}

function parseInteger(value: string): number | undefined {
  const parsed = Number.parseInt(value.trim(), 10);
  if (Number.isNaN(parsed)) return undefined;
  return parsed;
}

function parseUiFrameworksYaml(yaml: string): {
  uiFramework?: string;
  projectOverride?: string;
  tenantOverride?: string;
  panes: UiPaneDefinition[];
  layoutColourScheme?: string;
} {
  let uiFramework: string | undefined;
  let projectOverride: string | undefined;
  let tenantOverride: string | undefined;
  let inOverrides = false;
  let inPanes = false;
  let inCoordinates = false;
  let inCarousel = false;
  let inNavigation = false;

  const panes: UiPaneDefinition[] = [];
  let currentPane: {
    id: string;
    role: string;
    coordinates: Partial<UiPaneCoordinates>;
    border_pattern?: string;
    colour_scheme?: string;
    colour_scheme_override?: string;
    carousel?: {
      enabled?: boolean;
      active_index?: number;
      navigation?: Partial<UiPaneCarouselNavigation>;
    };
  } | null = null;

  const flushPane = () => {
    if (!currentPane || !currentPane.id) return;

    const normalizedPane: UiPaneDefinition = {
      id: currentPane.id,
      role: currentPane.role || "list",
      coordinates: {
        x: currentPane.coordinates.x ?? 0,
        y: currentPane.coordinates.y ?? 0,
        width: currentPane.coordinates.width ?? 100,
        height: currentPane.coordinates.height ?? 100,
      },
      border_pattern: (currentPane as any).border_pattern ?? "default",
        colour_scheme_override: (currentPane as any).colour_scheme_override ?? (currentPane as any).colour_scheme ?? undefined,
    };

    if (currentPane.carousel) {
      normalizedPane.carousel = {
        enabled: currentPane.carousel.enabled ?? false,
      };
      if (typeof currentPane.carousel.active_index === "number") {
        const ai = currentPane.carousel.active_index;
        normalizedPane.carousel.active_index = typeof ai === "number" && ai >= 0 ? Math.floor(ai) : 0;
      }
      if (currentPane.carousel.navigation) {
        normalizedPane.carousel.navigation = {
          wrap: currentPane.carousel.navigation.wrap ?? false,
          jump: currentPane.carousel.navigation.jump ?? true,
          refresh: currentPane.carousel.navigation.refresh ?? true,
        };
      }
    }

    panes.push(normalizedPane);
    currentPane = null;
  };

  for (const rawLine of yaml.split(/\r?\n/)) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();
    const indent = rawLine.search(/\S|$/);

    if (!trimmed || trimmed.startsWith("#")) continue;

    // No special top-level header required: accept keys anywhere in the file.

    if (trimmed === "panes:") {
      inPanes = true;
      inCoordinates = false;
      inCarousel = false;
      inNavigation = false;
      continue;
    }

    if (inPanes && indent <= 2 && trimmed !== "panes:" && !trimmed.startsWith("- id:")) {
      flushPane();
      inPanes = false;
      inCoordinates = false;
      inCarousel = false;
      inNavigation = false;
    }

    if (trimmed === "overrides:") {
      inOverrides = true;
      continue;
    }

    // accept top-level layout colour scheme key (handled later via regex fallback)

    if (inPanes) {
      if (trimmed.startsWith("- id:")) {
        flushPane();
        const paneId = parseScalar(trimmed.slice("- id:".length).trim());
        currentPane = {
          id: paneId,
          role: "list",
          coordinates: {},
        };
        inCoordinates = false;
        inCarousel = false;
        inNavigation = false;
        continue;
      }

      if (!currentPane) continue;

      if (trimmed === "coordinates:") {
        inCoordinates = true;
        inCarousel = false;
        inNavigation = false;
        continue;
      }

      if (trimmed === "carousel:") {
        inCoordinates = false;
        inCarousel = true;
        inNavigation = false;
        currentPane.carousel = currentPane.carousel ?? {};
        continue;
      }

      if (trimmed === "navigation:") {
        inNavigation = true;
        currentPane.carousel = currentPane.carousel ?? {};
        currentPane.carousel.navigation = currentPane.carousel.navigation ?? {};
        continue;
      }
    }

    if (trimmed.endsWith(":")) {
      if (trimmed !== "overrides:" && !line.startsWith("    ")) {
        inOverrides = false;
      }
      continue;
    }

    const separatorIndex = trimmed.indexOf(":");
    if (separatorIndex === -1) continue;

    const key = trimmed.slice(0, separatorIndex).trim();
    const value = parseScalar(trimmed.slice(separatorIndex + 1).trim());

    // Accept ui framework declaration and overrides regardless of top-level header
    if (!inPanes && !inOverrides && (key === "ui_framework" || key === "project" || key === "tenant" || key === "colour_scheme" || key === "colour-scheme")) {
      if (key === "ui_framework") uiFramework = value;
      if (inOverrides && key === "project") projectOverride = value;
      if (inOverrides && key === "tenant") tenantOverride = value;
      if ((key === "colour_scheme" || key === "colour-scheme") && !inOverrides) {
        // top-level layout colour scheme
        // record as layoutColourScheme by attaching to a variable via closure
        // we don't have a local variable declared here, so set below after parsing loop
      }
      continue;
    }

    if (inPanes && currentPane) {
      if (key === "role") {
        currentPane.role = value;
        continue;
      }
      if (key === "border_pattern") {
        currentPane.border_pattern = value;
        continue;
      }
      if (key === "colour_scheme" || key === "colour-scheme-override" || key === "colour_scheme_override") {
        // accept either legacy `colour_scheme` or explicit `colour-scheme-override`
        currentPane.colour_scheme_override = value;
        continue;
      }
      if (inCoordinates && (key === "x" || key === "y" || key === "width" || key === "height")) {
        const parsedValue = parseInteger(value);
        if (typeof parsedValue === "number") {
          currentPane.coordinates[key] = parsedValue;
        }
        continue;
      }
      if (inCarousel && key === "enabled") {
        currentPane.carousel = currentPane.carousel ?? {};
        currentPane.carousel.enabled = parseBoolean(value);
        continue;
      }
      if (inCarousel && key === "active_index") {
        currentPane.carousel = currentPane.carousel ?? {};
        const parsedIndex = parseInteger(value);
        if (typeof parsedIndex === "number") currentPane.carousel.active_index = parsedIndex;
        continue;
      }
      if (inNavigation && (key === "wrap" || key === "jump" || key === "refresh")) {
        currentPane.carousel = currentPane.carousel ?? {};
        currentPane.carousel.navigation = currentPane.carousel.navigation ?? {};
        const parsedValue = parseBoolean(value);
        if (typeof parsedValue === "boolean") {
          currentPane.carousel.navigation[key] = parsedValue;
        }
        continue;
      }
    }

    if (key === "ui_framework") {
      uiFramework = value;
      continue;
    }

    if ((key === "colour_scheme" || key === "colour-scheme") && !inPanes && !inOverrides) {
      // top-level colour scheme
      // set as a special token in the YAML by inserting into a synthetic variable
      // We'll attach to layoutColourScheme after the loop by re-parsing the YAML simply
      // using a minimal regex. (Handled after the loop.)
      continue;
    }

    if (inOverrides && key === "project") {
      projectOverride = value;
      continue;
    }

    if (inOverrides && key === "tenant") {
      tenantOverride = value;
      continue;
    }
  }

  flushPane();

  // attempt to extract top-level colour_scheme via regex fallback
  let layoutColourScheme: string | undefined;
  for (const l of yaml.split(/\r?\n/)) {
    const m = l.match(/^\s*(?:colour_scheme|colour-scheme)\s*:\s*([^#\n\r]+)/i);
    if (m) {
      layoutColourScheme = m[1].trim();
      break;
    }
  }

  return { uiFramework, projectOverride, tenantOverride, panes, layoutColourScheme };
}

function findFirstExisting(...candidatePaths: string[]): string | undefined {
  for (const candidate of candidatePaths) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return undefined;
}

function mergePanes(basePanes: UiPaneDefinition[], overlayPanes: UiPaneDefinition[]): UiPaneDefinition[] {
  const byId = new Map<string, UiPaneDefinition>();

  for (const pane of basePanes) {
    byId.set(pane.id, {
      ...pane,
      coordinates: { ...pane.coordinates },
      carousel: pane.carousel ? { ...pane.carousel, navigation: pane.carousel.navigation ? { ...pane.carousel.navigation } : undefined } : undefined,
    });
  }

  for (const overlay of overlayPanes) {
    const existing = byId.get(overlay.id);
    if (!existing) {
      byId.set(overlay.id, overlay);
      continue;
    }

    const mergedNavigation = existing.carousel || overlay.carousel ? {
      wrap: overlay.carousel?.navigation?.wrap ?? existing.carousel?.navigation?.wrap ?? false,
      jump: overlay.carousel?.navigation?.jump ?? existing.carousel?.navigation?.jump ?? true,
      refresh: overlay.carousel?.navigation?.refresh ?? existing.carousel?.navigation?.refresh ?? true,
    } : undefined;

    const mergedCarousel = overlay.carousel || existing.carousel ? {
      enabled: overlay.carousel?.enabled ?? existing.carousel?.enabled ?? false,
      active_index: overlay.carousel?.active_index ?? existing.carousel?.active_index,
      navigation: mergedNavigation,
    } : undefined;

    byId.set(overlay.id, {
      ...existing,
      ...overlay,
      coordinates: {
        ...existing.coordinates,
        ...overlay.coordinates,
      },
      carousel: mergedCarousel,
    });
  }

  return [...byId.values()];
}

function resolveUniverseAppRoot(prismataRoot: string): string {
  const normalizedRoot = path.normalize(prismataRoot);
  const looksLikeProjectsRoot =
    path.basename(normalizedRoot).toLowerCase() === "projects" &&
    fs.existsSync(path.join(normalizedRoot, "Applications", "Universe"));

  if (looksLikeProjectsRoot) {
    return path.join(normalizedRoot, "Applications", "Universe");
  }

  return path.join(normalizedRoot, "Projects", "Applications", "Universe");
}

export function loadUniverseUiFrameworksConfig(prismataRoot: string): UniverseUiFrameworksConfig {
  const appRoot = resolveUniverseAppRoot(prismataRoot);
  const sourcePath = path.join(appRoot, "config", "ui-framework", "universe.ui-framework.yaml");

  if (!fs.existsSync(sourcePath)) {
    console.warn(`[Universe][ui_framework] Missing ${sourcePath}; defaulting runtime framework to "basic".`);
    return {
      ui_framework: "basic",
      sourcePath,
      overrides: {},
      hasProjectOverride: false,
      hasTenantOverride: false,
      panes: [],
    };
  }

  const yaml = fs.readFileSync(sourcePath, "utf8");
  const parsed = parseUiFrameworksYaml(yaml);

  const declaredFramework = (parsed.uiFramework ?? "").trim();
  const effectiveFramework = ALLOWED_UI_FRAMEWORKS.has(declaredFramework as UiFramework)
    ? (declaredFramework as UiFramework)
    : "basic";

  if (!declaredFramework) {
    console.warn(`[Universe][ui_framework] Missing ui_framework in ${sourcePath}; defaulting to "basic".`);
  } else if (effectiveFramework === "basic" && declaredFramework !== "basic") {
    console.warn(`[Universe][ui_framework] Unsupported ui_framework="${declaredFramework}" in ${sourcePath}; defaulting to "basic".`);
  }

  const projectOverride = parsed.projectOverride;
  const tenantOverride = parsed.tenantOverride;
  const projectOverridePath = projectOverride ? path.join(appRoot, "config", projectOverride) : "";
  const tenantOverridePath = tenantOverride ? path.join(appRoot, "config", tenantOverride) : "";

  const hasProjectOverride = !!projectOverridePath && fs.existsSync(projectOverridePath);
  const hasTenantOverride = !!tenantOverridePath && fs.existsSync(tenantOverridePath);

  if (projectOverride && !hasProjectOverride) {
    console.warn(`[Universe][ui_framework] Project override file not found: ${projectOverridePath}`);
  }

  if (tenantOverride && !hasTenantOverride) {
    console.warn(`[Universe][ui_framework] Tenant override file not found: ${tenantOverridePath}`);
  }

  let effectivePanes = parsed.panes;
  if (hasProjectOverride && projectOverridePath) {
    const projectYaml = fs.readFileSync(projectOverridePath, "utf8");
    const projectParsed = parseUiFrameworksYaml(projectYaml);
    effectivePanes = mergePanes(effectivePanes, projectParsed.panes);
  }
  if (hasTenantOverride && tenantOverridePath) {
    const tenantYaml = fs.readFileSync(tenantOverridePath, "utf8");
    const tenantParsed = parseUiFrameworksYaml(tenantYaml);
    effectivePanes = mergePanes(effectivePanes, tenantParsed.panes);
  }

  try {
    // @ts-ignore
    const Ajv = require("ajv");
    // @ts-ignore
    const jsyaml = require("js-yaml");
    if (Ajv && jsyaml) {
      const ajv = new Ajv({ allErrors: true });
      const canonicalRoot = path.join(prismataRoot, "Meta", "canonical");

      const uiFrameworkSchemaPath = findFirstExisting(
        path.join(canonicalRoot, "object.schemas", "ui-framework.schema.yaml"),
        path.join(canonicalRoot, "ui.schemas", "ui-framework.schema.yaml")
      );
      if (uiFrameworkSchemaPath) {
        try {
          const uiSchema = jsyaml.load(fs.readFileSync(uiFrameworkSchemaPath, "utf8"));
          const validateUi = ajv.compile(uiSchema as object);
          const uiPayload = { ui_framework: effectiveFramework };
          if (!validateUi(uiPayload)) {
            const uiErrors = typeof ajv.errorsText === "function"
              ? ajv.errorsText(validateUi.errors)
              : JSON.stringify(validateUi.errors ?? []);
            console.warn(`[Universe][ui_framework] ui_framework validation failed: ${uiErrors}`);
          }
        } catch (e) {
          console.warn(`[Universe][ui_framework] ui_framework schema load/validate error: ${e}`);
        }
      }

      const paneSchemaPath = findFirstExisting(
        path.join(canonicalRoot, "object.schemas", "pane.schema.yaml"),
        path.join(canonicalRoot, "shared.schemas", "shared-pane-fields.schema.yaml"),
        path.join(canonicalRoot, "ui.schemas", "pane.schema.yaml")
      );
      if (paneSchemaPath) {
        try {
          const paneSchema = jsyaml.load(fs.readFileSync(paneSchemaPath, "utf8"));
          const validatePane = ajv.compile(paneSchema as object);
          for (const pane of effectivePanes) {
            if (!validatePane(pane)) {
              const paneErrors = typeof ajv.errorsText === "function"
                ? ajv.errorsText(validatePane.errors)
                : JSON.stringify(validatePane.errors ?? []);
              console.warn(`[Universe][ui_framework] Pane validation failed for ${pane.id}: ${paneErrors}`);
            }
          }
        } catch (e) {
          console.warn(`[Universe][ui_framework] pane schema load/validate error: ${e}`);
        }
      }
    }
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : String(e);
    console.warn(`[Universe][ui_framework] Schema validation skipped: ${errorMessage}`);
  }

  return {
    ui_framework: effectiveFramework,
    sourcePath,
    overrides: {
      project: projectOverride,
      tenant: tenantOverride,
    },
    hasProjectOverride,
    hasTenantOverride,
    panes: effectivePanes,
    layoutColourScheme: parsed.layoutColourScheme,
  };
}

/**
 * Generic version of loadUniverseUiFrameworksConfig.
 * Loads the UI interface config for any Prismata application given its root folder.
 *
 * The config file is resolved as:
 *   <appRoot>/config/ui-framework/<appName>.ui-framework.yaml  (first match)
 *   or the first *.ui-framework.yaml found in that folder.
 *
 * Project overrides are resolved relative to <appRoot>/config/.
 */
export function loadAppUiFrameworksConfig(appRoot: string): UniverseUiFrameworksConfig {
  const uiInterfaceDir = path.join(appRoot, "config", "ui-framework");

  // Find the first *.ui-framework.yaml in the ui-framework dir
  let sourcePath = "";
  if (fs.existsSync(uiInterfaceDir)) {
    const files = fs.readdirSync(uiInterfaceDir).filter((f: string) => f.endsWith(".ui-framework.yaml"));
    if (files.length > 0) {
      sourcePath = path.join(uiInterfaceDir, files[0]);
    }
  }

  if (!sourcePath || !fs.existsSync(sourcePath)) {
    console.warn(`[ui_framework] No *.ui-framework.yaml found in ${uiInterfaceDir}; defaulting to "basic".`);
    return {
      ui_framework: "basic",
      sourcePath: sourcePath || path.join(uiInterfaceDir, "(not found)"),
      overrides: {},
      hasProjectOverride: false,
      hasTenantOverride: false,
      panes: [],
    };
  }

  const yaml = fs.readFileSync(sourcePath, "utf8");
  const parsed = parseUiFrameworksYaml(yaml);

  const declaredFramework = (parsed.uiFramework ?? "").trim();
  const effectiveFramework = ALLOWED_UI_FRAMEWORKS.has(declaredFramework as UiFramework)
    ? (declaredFramework as UiFramework)
    : "basic";

  if (!declaredFramework) {
    console.warn(`[ui_framework] Missing ui_framework in ${sourcePath}; defaulting to "basic".`);
  } else if (effectiveFramework === "basic" && declaredFramework !== "basic") {
    console.warn(`[ui_framework] Unsupported ui_framework="${declaredFramework}" in ${sourcePath}; defaulting to "basic".`);
  }

  const projectOverride = parsed.projectOverride;
  const tenantOverride = parsed.tenantOverride;
  const projectOverridePath = projectOverride ? path.join(appRoot, "config", projectOverride) : "";
  const tenantOverridePath = tenantOverride ? path.join(appRoot, "config", tenantOverride) : "";

  const hasProjectOverride = !!projectOverridePath && fs.existsSync(projectOverridePath);
  const hasTenantOverride = !!tenantOverridePath && fs.existsSync(tenantOverridePath);

  let effectivePanes = parsed.panes;
  if (hasProjectOverride && projectOverridePath) {
    const projectYaml = fs.readFileSync(projectOverridePath, "utf8");
    const projectParsed = parseUiFrameworksYaml(projectYaml);
    effectivePanes = mergePanes(effectivePanes, projectParsed.panes);
  }
  if (hasTenantOverride && tenantOverridePath) {
    const tenantYaml = fs.readFileSync(tenantOverridePath, "utf8");
    const tenantParsed = parseUiFrameworksYaml(tenantYaml);
    effectivePanes = mergePanes(effectivePanes, tenantParsed.panes);
  }

  return {
    ui_framework: effectiveFramework,
    sourcePath,
    overrides: {
      project: projectOverride,
      tenant: tenantOverride,
    },
    hasProjectOverride,
    hasTenantOverride,
    panes: effectivePanes,
    layoutColourScheme: parsed.layoutColourScheme,
  };
}
