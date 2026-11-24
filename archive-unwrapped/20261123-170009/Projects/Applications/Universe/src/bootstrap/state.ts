import * as fs from "fs";
import * as path from "path";

export interface UniversePaths {
  prismataRoot: string;
  workspaceRoot: string;
  stateDir: string;
  initializedFlagPath: string;
  ingestionDir: string;
  registryDir: string;
  archiveDir: string;
}

export interface UniverseFeatures {
  autoArchive?: boolean;
  autoVersioning?: boolean;
}

export interface UniverseSettings {
  paths?: Record<string, unknown>;
  naming?: Record<string, unknown>;
  export?: Record<string, unknown>;
  registry?: Record<string, unknown>;
  features?: UniverseFeatures;
  ignore_extensions?: string[];
}

export interface SearchParams {
  folders: string[];
  projects: string[];
  fileTypes: string[];
  queries: string[];
  tags: string[];
  canonicalOnly: boolean;
  recursive: boolean;
}

export interface RuntimeState {
  bootstrapMode: boolean;
  initialized: boolean;
  vileIngested: boolean;
  tuilkitIngested?: boolean;
  tuilkitRuntimeMode?: string;
  tuilkitFallback?: boolean;
  initializedFlagPath: string;
  settings: UniverseSettings;
  /** Runtime-only: search parameters accumulated during the session. */
  searchParams?: SearchParams;
}

export interface SharedUiConfigFiles {
  coloursJson?: string;
  borderPatternsJson?: string;
}

/**
 * Get paths to shared UI configuration files when present.
 *
 * Purpose: Locate GLOBAL_SHARED configuration directory and return
 * the paths to COLOURS.json and BORDER_PATTERNS.json if they exist.
 *
 * @param prismataRoot - Path to the Prismata repository root.
 * @returns An object with optional `coloursJson` and `borderPatternsJson` paths.
 * @external Available: exported from this module.
 */
export function getSharedUiConfigFiles(prismataRoot: string): SharedUiConfigFiles {
  const candidates = [
    path.join(prismataRoot, ".workspace", ".projects_config", "GLOBAL_SHARED.d"),
    path.join(path.resolve(prismataRoot, ".."), "tUilKit", ".workspace", ".projects_config", "GLOBAL_SHARED.d"),
  ];

  const configDir = candidates.find(candidate => fs.existsSync(candidate));
  if (!configDir) {
    return {};
  }

  const coloursJson = path.join(configDir, "COLOURS.json");
  const borderPatternsJson = path.join(configDir, "BORDER_PATTERNS.json");

  return {
    coloursJson: fs.existsSync(coloursJson) ? coloursJson : undefined,
    borderPatternsJson: fs.existsSync(borderPatternsJson) ? borderPatternsJson : undefined,
  };
}

/**
 * Build canonical universe-related directory paths.
 *
 * Purpose: Given the `prismataRoot`, return a `UniversePaths` object
 * describing locations used by the Universe application (workspace, state,
 * ingestion, registry, archive, and initialized flag path).
 *
 * @param prismataRoot - Path to the Prismata repository root.
 * @returns A fully populated `UniversePaths` object.
 * @external Available: exported from this module.
 */
export function getUniversePaths(prismataRoot: string): UniversePaths {
  const workspaceRoot = path.join(prismataRoot, ".workspace", "universe");

  return {
    prismataRoot,
    workspaceRoot,
    stateDir: path.join(workspaceRoot, "state"),
    initializedFlagPath: path.join(
      workspaceRoot,
      "state",
      "initialized.flag"
    ),
    ingestionDir: path.join(workspaceRoot, "ingestion"),
    registryDir: path.join(workspaceRoot, "registry"),
    archiveDir: path.join(workspaceRoot, "archive"),
  };
}

/**
 * Ensure required Universe directories exist on disk.
 *
 * Purpose: Create the workspace, state, ingestion, registry and archive
 * directories if they do not already exist.
 *
 * @param paths - `UniversePaths` describing target directories.
 * @returns `void`.
 * @external Available: exported from this module.
 */
export function ensureUniverseDirs(paths: UniversePaths): void {
  for (const dir of [
    paths.workspaceRoot,
    paths.stateDir,
    paths.ingestionDir,
    paths.registryDir,
    paths.archiveDir,
  ]) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }
}

/**
 * Mark the Universe as initialized by writing an initialized flag file.
 *
 * Purpose: Ensure directories exist and create the `initialized.flag`
 * file under the state directory to record initialization.
 *
 * @param paths - `UniversePaths` describing the target initialized flag path.
 * @returns `void`.
 * @external Available: exported from this module.
 */
export function markInitialized(paths: UniversePaths): void {
  ensureUniverseDirs(paths);
  fs.writeFileSync(paths.initializedFlagPath, "initialized=true\n", "utf8");
}

/**
 * Load JSON-lines registry entries from a file.
 *
 * Purpose: Read a JSONL registry file, parse each non-empty line as JSON,
 * and return an array of entries. Malformed lines are ignored to keep
 * startup resilient.
 *
 * @param registryPath - Filesystem path to the registry JSONL file.
 * @returns An array of parsed registry entry objects. Empty array if file missing.
 * @external Available: NOT exported (module-private).
 */
function loadRegistryEntries(registryPath: string): Array<Record<string, unknown>> {
  if (!fs.existsSync(registryPath)) {
    return [];
  }

  const lines = fs
    .readFileSync(registryPath, "utf8")
    .split(/\r?\n/)
    .map((line: string) => line.trim())
    .filter(Boolean);

  const entries: Array<Record<string, unknown>> = [];
  for (const line of lines) {
    try {
      const parsed = JSON.parse(line);
      if (parsed && typeof parsed === "object") {
        entries.push(parsed as Record<string, unknown>);
      }
    } catch {
      // Ignore malformed lines to keep startup resilient.
    }
  }

  return entries;
}

/**
 * Compute the path to the Universe settings file.
 *
 * Purpose: Return the full filesystem path for `settings.json` inside the
 * Universe `state` directory.
 *
 * @param paths - `UniversePaths` describing the state directory.
 * @returns The filesystem path to `settings.json` as a string.
 * @external Available: exported from this module.
 */
export function getUniverseSettingsPath(paths: UniversePaths): string {
  return path.join(paths.stateDir, "settings.json");
}

/**
 * Load persisted Universe settings from disk.
 *
 * Purpose: Read and parse `settings.json` from the Universe state directory.
 * If the file does not exist or is malformed, return an empty settings object.
 *
 * @param paths - `UniversePaths` describing where settings are stored.
 * @returns A `UniverseSettings` object (possibly empty on error/missing file).
 * @external Available: exported from this module.
 */
export function loadUniverseSettings(paths: UniversePaths): UniverseSettings {
  const settingsPath = getUniverseSettingsPath(paths);
  if (!fs.existsSync(settingsPath)) {
    return {};
  }

  try {
    const raw = fs.readFileSync(settingsPath, "utf8");
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      const settings = parsed as UniverseSettings;
      if (!Array.isArray(settings.ignore_extensions)) {
        return settings;
      }

      return {
        ...settings,
        ignore_extensions: settings.ignore_extensions
          .map(value => String(value).trim())
          .filter(Boolean),
      };
    }
  } catch {
    // Ignore malformed settings and fall back to defaults.
  }

  return {};
}

/**
 * Persist Universe settings to disk, normalizing missing keys.
 *
 * Purpose: Ensure target directories exist, normalize provided settings to
 * include the expected top-level keys, write them to `settings.json`, and
 * return the normalized settings.
 *
 * @param paths - `UniversePaths` describing where to save settings.
 * @param settings - Partial or full `UniverseSettings` to persist.
 * @returns The normalized `UniverseSettings` object that was written.
 * @external Available: exported from this module.
 */
export function saveUniverseSettings(
  paths: UniversePaths,
  settings: UniverseSettings
): UniverseSettings {
  ensureUniverseDirs(paths);

  const normalized: UniverseSettings = {
    ...(settings.paths !== undefined ? { paths: settings.paths } : {}),
    ...(settings.naming !== undefined ? { naming: settings.naming } : {}),
    ...(settings.export !== undefined ? { export: settings.export } : {}),
    ...(settings.registry !== undefined ? { registry: settings.registry } : {}),
    ...(settings.features !== undefined ? { features: settings.features } : {}),
    ...(settings.ignore_extensions !== undefined
      ? {
          ignore_extensions: Array.isArray(settings.ignore_extensions)
            ? settings.ignore_extensions.map(value => String(value).trim()).filter(Boolean)
            : [],
        }
      : {}),
  };

  // Normalize known path keys: ensure project_scope is stored as an array
  if (normalized.paths) {
    const ps = normalized.paths as Record<string, any>;
    if (ps.project_scope != null) {
      if (Array.isArray(ps.project_scope)) {
        ps.project_scope = ps.project_scope.map((p: any) => String(p));
      } else if (typeof ps.project_scope === "string") {
        ps.project_scope = [ps.project_scope];
      } else {
        // Unexpected type -> remove
        delete ps.project_scope;
      }
    }
  }

  fs.writeFileSync(
    getUniverseSettingsPath(paths),
    `${JSON.stringify(normalized, null, 2)}\n`,
    "utf8"
  );

  return normalized;
}

/**
 * Create an updated `RuntimeState` with merged settings.
 *
 * Purpose: Merge `nextSettings` into the existing `state.settings` while
 * preserving other runtime fields and return a new `RuntimeState` object.
 *
 * @param state - Current `RuntimeState` to base updates on.
 * @param nextSettings - Partial settings to merge into the runtime state.
 * @returns A new `RuntimeState` with merged settings.
 * @external Available: exported from this module.
 */
export function updateRuntimeSettings(
  state: RuntimeState,
  nextSettings: Partial<UniverseSettings>
): RuntimeState {
  const ignoreExtensions = Array.isArray(nextSettings.ignore_extensions)
    ? nextSettings.ignore_extensions.map(value => String(value).trim()).filter(Boolean)
    : Array.isArray(state.settings?.ignore_extensions)
      ? state.settings.ignore_extensions
      : [];

  return {
    ...state,
    settings: {
      paths: { ...(state.settings?.paths ?? {}), ...(nextSettings.paths ?? {}) },
      naming: { ...(state.settings?.naming ?? {}), ...(nextSettings.naming ?? {}) },
      export: { ...(state.settings?.export ?? {}), ...(nextSettings.export ?? {}) },
      registry: { ...(state.settings?.registry ?? {}), ...(nextSettings.registry ?? {}) },
      features: { ...(state.settings?.features ?? {}), ...(nextSettings.features ?? {}) },
      ignore_extensions: ignoreExtensions,
    },
  };
}

/**
 * Build the current runtime state for the Universe application.
 *
 * Purpose: Inspect the filesystem for the initialized flag, load registry
 * entries and settings, compute whether `tooling.vile` is installed, and
 * return a `RuntimeState` describing bootstrap mode and other flags.
 *
 * @param paths - `UniversePaths` used to locate state, registry and settings.
 * @returns A populated `RuntimeState` object.
 * @external Available: exported from this module.
 */
export function getRuntimeState(paths: UniversePaths): RuntimeState {
  const initialized = fs.existsSync(paths.initializedFlagPath);
  const registryPath = path.join(paths.registryDir, "registry.jsonl");
  const entries = loadRegistryEntries(registryPath);
  const settings = loadUniverseSettings(paths);

  const vileIngested = entries.some(entry => {
    const udi = String(entry.udi ?? "");
    const installStatus = String(entry.install_status ?? "");
    return udi === "tooling.vile" && installStatus === "installed";
  });

  const tuilkitIngested = entries.some(entry => {
    const udi = String(entry.udi ?? "");
    const installStatus = String(entry.install_status ?? "");
    return udi === "module.tuilkit" && installStatus !== "missing";
  });

  return {
    bootstrapMode: !initialized,
    initialized,
    vileIngested,
    tuilkitIngested,
    tuilkitRuntimeMode: tuilkitIngested ? "tuilkit" : "fallback-not-ingested",
    tuilkitFallback: !tuilkitIngested,
    initializedFlagPath: paths.initializedFlagPath,
    settings,
  };
}
