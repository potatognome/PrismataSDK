import { CapabilityContext } from "./dispatcher";
import * as fs from "fs";
import * as path from "path";
import { pickNativePath } from "../../../../Tooling/primitives/typescript/dialogHelpers";
import { getUniversePaths, loadUniverseSettings, saveUniverseSettings, SearchParams } from "../bootstrap/state";
import { remapVersion } from "../versioning/versionUtil";

export type CapabilityHandler = (
  context: CapabilityContext
) => Promise<any>;

export interface CapabilityHandlerMap {
  [capabilityId: string]: CapabilityHandler;
}

function assertEditUnlocked(context: CapabilityContext): void {
  const runtimeMode = String(context.runtimeState?.tuilkitRuntimeMode ?? "");
  const hasRuntimeMode = runtimeMode.length > 0;
  const tuilkitIngested =
    typeof context.runtimeState?.tuilkitIngested === "boolean"
      ? context.runtimeState.tuilkitIngested
      : !!context.runtimeState?.vileIngested;
  const tuilkitReady = hasRuntimeMode
    ? runtimeMode === "tuilkit" && tuilkitIngested
    : !!context.runtimeState?.vileIngested;

  if (!tuilkitReady) {
    throw new Error("Create/Edit is locked until VILE has been ingested.");
  }
}

function buildSimpleDiff(before: string, after: string): string {
  if (before === after) {
    return "";
  }

  const beforeLines = before.split(/\r?\n/);
  const afterLines = after.split(/\r?\n/);
  const max = Math.max(beforeLines.length, afterLines.length);
  const out: string[] = [];

  for (let i = 0; i < max; i += 1) {
    const a = beforeLines[i];
    const b = afterLines[i];
    if (a === b) {
      continue;
    }
    if (typeof a === "string") {
      out.push(`- ${a}`);
    }
    if (typeof b === "string") {
      out.push(`+ ${b}`);
    }
  }

  return out.join("\n");
}

function archiveFile(filePath: string, archiveDir: string): void {
  if (!fs.existsSync(filePath)) return;
  fs.mkdirSync(archiveDir, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const base = path.basename(filePath);
  const archivePath = path.join(archiveDir, `${base}.${timestamp}.archive`);
  fs.copyFileSync(filePath, archivePath);
}

function writeFileEnsured(filePath: string, content: string): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
}

function defaultManifestContent(name: string): string {
  return [
    "id: prismata.universe.test.manifest",
    `name: ${name}`,
    "version: 0.0.1",
    "kind: module",
    "metadata:",
    "  generated_by: universe-create",
    "",
  ].join("\n");
}

export const handlers: CapabilityHandlerMap = {
  "prismata.universe.capability.fs-search": async ctx => {
    // Manage runtime-only search parameters. Supports actions: add, remove, toggle, list
    const action = String(ctx.args?.action ?? "list");
    const ptype = String(ctx.args?.type ?? "");
    const value = ctx.args?.value;

    // Ensure a mutable search params container on runtimeState
    if (!ctx.runtimeState) {
      throw new Error("Runtime state is required for fs-search capability.");
    }

    if (!ctx.runtimeState.searchParams) {
      ctx.runtimeState.searchParams = {
        folders: [],
        projects: [],
        fileTypes: [],
        queries: [],
        tags: [],
        canonicalOnly: false,
        recursive: true,
      };
    }

    const params = ctx.runtimeState.searchParams as SearchParams & Record<string, any>;

    if (action === "list") {
      return { params };
    }

    if (action === "add") {
      if (!ptype) throw new Error("type required for add action");
      if (value == null) throw new Error("value required for add action");
      if (!Array.isArray(params[ptype])) {
        throw new Error(`type ${ptype} is not a multi-value type`);
      }
      if (!params[ptype].includes(value)) params[ptype].push(value);
      return { params };
    }

    if (action === "remove") {
      if (!ptype) throw new Error("type required for remove action");
      if (value == null) throw new Error("value required for remove action");
      if (!Array.isArray(params[ptype])) {
        throw new Error(`type ${ptype} is not a multi-value type`);
      }
      params[ptype] = params[ptype].filter((v: any) => v !== value);
      return { params };
    }

    if (action === "toggle") {
      if (!ptype) throw new Error("type required for toggle action");
      if (typeof params[ptype] !== "boolean") {
        throw new Error(`type ${ptype} is not a boolean toggle`);
      }
      params[ptype] = !params[ptype];
      return { params };
    }

    throw new Error(`Unknown action for fs-search: ${action}`);
  },
  "prismata.universe.capability.fs-search-location": async ctx => {
    const mode = String(ctx.args?.mode ?? "folder");
    const picked = pickNativePath(mode === "file" ? "file" : "folder");
    const resolved = picked || String(ctx.args?.path ?? ctx.args?.folderPath ?? process.cwd() ?? ".");

    return {
      location: {
        mode,
        path: resolved,
        pickedFromNativeDialog: !!picked,
      },
    };
  },
  "prismata.universe.capability.fs-search-execute": async ctx => {
    // Execute a search using runtime searchParams (runtime-only) or args override
    const runtimeParams = ctx.runtimeState?.searchParams;
    const argsParams = ctx.args ?? {};

    const effective = {
      folders: Array.isArray(argsParams.folders) ? argsParams.folders : (runtimeParams?.folders ?? (argsParams.rootPath ? [argsParams.rootPath] : [])),
      projects: Array.isArray(argsParams.projects) ? argsParams.projects : (runtimeParams?.projects ?? []),
      fileTypes: Array.isArray(argsParams.fileTypes) ? argsParams.fileTypes : (runtimeParams?.fileTypes ?? []),
      queries: Array.isArray(argsParams.queries) ? argsParams.queries : (runtimeParams?.queries ?? []),
      tags: Array.isArray(argsParams.tags) ? argsParams.tags : (runtimeParams?.tags ?? []),
      canonicalOnly: typeof argsParams.canonicalOnly === "boolean" ? argsParams.canonicalOnly : (runtimeParams?.canonicalOnly ?? false),
      recursive: typeof argsParams.recursive === "boolean" ? argsParams.recursive : (runtimeParams?.recursive ?? true),
      maxDepth: typeof argsParams.maxDepth === "number" ? argsParams.maxDepth : undefined,
    };

    // Lazy import to avoid cycles
    const { runSearch } = await import("../search/searchEngine");

    const aggregatedResults: any[] = [];

    // Build roots from folders + projects; fallback to cwd
    const rootsSet = new Set<string>();
    if (Array.isArray(effective.folders) && effective.folders.length) {
      for (const f of effective.folders) rootsSet.add(String(f));
    }
    if (Array.isArray(effective.projects) && effective.projects.length) {
      for (const p of effective.projects) rootsSet.add(String(p));
    }

    // Always include configured project_scope paths from settings (supports string or array)
    const configuredProjectScope = ctx.runtimeState?.settings?.paths?.project_scope;
    if (configuredProjectScope) {
      if (Array.isArray(configuredProjectScope) && configuredProjectScope.length) {
        for (const p of configuredProjectScope) rootsSet.add(String(p));
      } else if (typeof configuredProjectScope === "string" && configuredProjectScope.trim()) {
        rootsSet.add(String(configuredProjectScope));
      }
    }

    // If canonicalOnly is requested, include the configured canonical_folder from settings (if present)
    const configuredCanonical = String(ctx.runtimeState?.settings?.paths?.canonical_folder ?? "").trim();
    if (effective.canonicalOnly && configuredCanonical) {
      rootsSet.add(configuredCanonical);
    }

    // If no explicit roots are selected, default to the Universe workspace root
    // (not the current working directory) so the UI message about "searching
    // workspace by default" is accurate.
    const roots =
      rootsSet.size > 0
        ? Array.from(rootsSet)
        : [getUniversePaths(path.resolve(__dirname, "../../../../")).workspaceRoot];

    // Ensure effective.folders represents the exact set of roots we will search
    effective.folders = roots;

    // Persist the chosen search folders into runtimeState.searchParams so UI reflects actual search roots
    if (ctx.runtimeState) {
      if (!ctx.runtimeState.searchParams) ctx.runtimeState.searchParams = { folders: [], projects: [], fileTypes: [], queries: [], tags: [], canonicalOnly: false, recursive: true };
      ctx.runtimeState.searchParams.folders = roots;
    }

    for (const root of roots) {
      try {
        const res = runSearch({
          rootPath: root,
          fileTypes: effective.fileTypes,
          queries: effective.queries,
          tags: effective.tags,
          canonicalOnly: effective.canonicalOnly,
          recursive: effective.recursive,
          maxDepth: effective.maxDepth,
        });

        aggregatedResults.push(...res.results.map((r: any) => ({ ...r, rootPath: res.rootPath })));
      } catch (err) {
        // ignore individual root failures but continue
      }
    }

    // Attach version-grouping metadata
    const { groupResultsByBasename } = await import("../search/searchEngine");
    const versions = groupResultsByBasename(aggregatedResults as any);

    return { results: aggregatedResults, parameters: effective, versions };
  },
  "prismata.universe.capability.fs-search-results": async ctx => ({ panes: [] }),

  "prismata.universe.capability.fs-select-multi": async ctx => ({ selected: ctx.selectedObjects }),
  "prismata.universe.capability.fs-select-single": async ctx => ({ reference: ctx.referenceObject }),
  "prismata.universe.capability.fs-exemplar-preview": async ctx => ({ registry: [] }),

  "prismata.universe.capability.fs-create-from-object": async ctx => {
    assertEditUnlocked(ctx);

    const requestedPath = String(ctx.args?.filePath ?? "").trim();
    if (!requestedPath) {
      return { created: true, mode: "no-op" };
    }

    const content = String(
      ctx.args?.content ?? defaultManifestContent(String(ctx.args?.name ?? "Universe Test Panel"))
    );

    const autoArchive = ctx.runtimeState?.settings?.features?.autoArchive ?? false;
    if (autoArchive) {
      const runtimePaths = getUniversePaths(path.resolve(__dirname, "../../../../"));
      archiveFile(requestedPath, runtimePaths.archiveDir);
    }

    writeFileEnsured(requestedPath, content);
    return { created: true, filePath: requestedPath, archived: autoArchive };
  },
  "prismata.universe.capability.fs-edit-multi": async ctx => {
    assertEditUnlocked(ctx);
    return { edited: ctx.selectedObjects };
  },
  "prismata.universe.capability.fs-update-fields": async ctx => {
    assertEditUnlocked(ctx);
    return { updated: true };
  },
  "prismata.universe.capability.fs-update-version": async ctx => {
    assertEditUnlocked(ctx);

    const autoVersioning = ctx.runtimeState?.settings?.features?.autoVersioning ?? false;
    if (!autoVersioning || ctx.selectedObjects.length === 0) {
      return { versioned: false, autoVersioning, note: autoVersioning ? "no objects selected" : "auto-versioning disabled" };
    }

    const versioned: string[] = [];
    for (const obj of ctx.selectedObjects) {
      const filePath = String(obj.id ?? "").trim();
      if (!filePath || !fs.existsSync(filePath)) continue;

      const runtimePaths = getUniversePaths(path.resolve(__dirname, "../../../../"));
      const autoArchive = ctx.runtimeState?.settings?.features?.autoArchive ?? false;
      if (autoArchive) {
        archiveFile(filePath, runtimePaths.archiveDir);
      }

      const content = fs.readFileSync(filePath, "utf8");
      const direction = String(ctx.args?.direction ?? "forward") as "forward" | "backward";

      // Find and replace the version field in YAML/JSON content
      const updated = content.replace(
        /^(\s*version:\s*)["']?([^\s"'\n#]+)["']?(\s*(?:#[^\n]*)?)$/m,
        (_match: string, prefix: string, rawVer: string, suffix: string) => {
          const next = remapVersion(rawVer, direction);
          return `${prefix}${next}${suffix}`;
        }
      );

      if (updated !== content) {
        writeFileEnsured(filePath, updated);
        versioned.push(filePath);
      }
    }

    return { versioned: true, autoVersioning, files: versioned };
  },
  "prismata.universe.capability.fs-edit-vile": async ctx => {
    assertEditUnlocked(ctx);

    const requestedPath = String(ctx.args?.filePath ?? "").trim();
    const mode = String(ctx.args?.mode ?? ctx.args?.editorMode ?? "vile").trim().toLowerCase();
    const selectedFile = requestedPath || String(ctx.selectedObjects?.[0]?.id ?? "").trim();

    if (!selectedFile) {
      return { opened: ctx.selectedObjects[0], mode: "no-op" };
    }

    const before = fs.existsSync(selectedFile)
      ? fs.readFileSync(selectedFile, "utf8")
      : "";
    const newContent = String(ctx.args?.newContent ?? ctx.args?.content ?? `${before}\n# edited-by-vile\n`);
    const allowedModes = new Set(["vile", "vise"]);
    const normalizedMode = allowedModes.has(mode) ? mode : "vile";

    const autoArchive = ctx.runtimeState?.settings?.features?.autoArchive ?? false;
    if (autoArchive) {
      const runtimePaths = getUniversePaths(path.resolve(__dirname, "../../../../"));
      archiveFile(selectedFile, runtimePaths.archiveDir);
    }

    writeFileEnsured(selectedFile, newContent);

    const diff = buildSimpleDiff(before, newContent);
    return {
      opened: ctx.selectedObjects[0],
      edited: true,
      filePath: selectedFile,
      mode: normalizedMode,
      diff,
      archived: autoArchive,
    };
  },
  "prismata.universe.capability.fs-edit-registry-insert": async ctx => {
    assertEditUnlocked(ctx);
    return { inserted: true };
  },
  "prismata.universe.capability.fs-export-custom": async ctx => {
    assertEditUnlocked(ctx);
    return { exported: true };
  },
  // Internal stub: retained for future structured conform flows.
  // Intentionally not exposed by any current menu.
  "prismata.universe.capability.fs-edit-conform": async ctx => {
    assertEditUnlocked(ctx);
    return { conformed: true };
  },

  "prismata.universe.capability.fs-verify-reference": async ctx => ({ verified: true }),
  "prismata.universe.capability.fs-verify-multi": async ctx => ({ summary: {} }),
  "prismata.universe.capability.fs-verify-sequence": async ctx => ({ mode: "sequence" }),
  "prismata.universe.capability.fs-verify-collective": async ctx => ({ mode: "collective" }),
  "prismata.universe.capability.fs-version-apply": async ctx => ({ remapped: true }),
  "prismata.universe.capability.fs-diff-compatible": async ctx => ({ diff: {} }),

  // Internal stub: reserved for semantic value normalization pipelines.
  // Intentionally not exposed by any current menu.
  "prismata.universe.capability.value-match": async ctx => ({ normalized: true }),

  "prismata.universe.capability.semantic-primitive-extract": async ctx => {
    const primitive = String(ctx.args?.primitive ?? "tooling.primitive");
    const result = {
      primitive,
      detected: true,
      metadata: {
        family: String(ctx.args?.family ?? "tooling"),
        source: "universe.semantic.stub",
      },
    };
    return result;
  },

  "prismata.universe.capability.semantic-dependency-graph": async ctx => {
    const graph = {
      nodes: Array.isArray(ctx.args?.nodes) ? ctx.args?.nodes : ["tooling.vile", "module.vaultguard"],
      edges: Array.isArray(ctx.args?.edges)
        ? ctx.args?.edges
        : [["tooling.vile", "module.vaultguard"]],
    };
    return graph;
  },

  "prismata.universe.capability.semantic-bundle": async ctx => {
    const outputDir = String(ctx.args?.outputDir ?? "").trim();
    const bundleName = String(ctx.args?.bundleName ?? "semantic-bundle.json");
    const payload = {
      created_at_utc: new Date().toISOString(),
      primitives: ctx.args?.primitives ?? ["tooling.vile"],
      graph: ctx.args?.graph ?? { nodes: ["tooling.vile"], edges: [] },
    };

    if (!outputDir) {
      return { bundled: true, payload };
    }

    const bundlePath = path.join(outputDir, bundleName);
    const archivePath = path.join(outputDir, `${bundleName}.archive.json`);

    writeFileEnsured(bundlePath, `${JSON.stringify(payload, null, 2)}\n`);
    writeFileEnsured(archivePath, `${JSON.stringify(payload, null, 2)}\n`);

    return {
      bundled: true,
      bundlePath,
      archivePath,
    };
  },

  "prismata.universe.capability.app-settings-paths": async ctx => {
    const runtimePaths = getUniversePaths(path.resolve(__dirname, "../../../../"));
    const settings = loadUniverseSettings(runtimePaths);
    const nextSettings = saveUniverseSettings(runtimePaths, {
      ...settings,
      paths: { ...(settings.paths ?? {}), ...(ctx.args ?? {}) },
    });

    return { paths: nextSettings.paths };
  },

  "prismata.universe.capability.app-settings-ignore": async ctx => {
    const runtimePaths = getUniversePaths(path.resolve(__dirname, "../../../../"));
    const settings = loadUniverseSettings(runtimePaths);

    const current = Array.isArray(settings.ignore_extensions)
      ? settings.ignore_extensions.map((s: any) => String(s).trim()).filter(Boolean)
      : [];

    const action = String(ctx.args?.action ?? "list").toLowerCase();
    const value = typeof ctx.args?.value === "string" ? String(ctx.args.value).trim() : (typeof ctx.args?.extension === "string" ? String(ctx.args.extension).trim() : "");

    // Normalize existing entries to lowercase with leading dot
    let nextArr = current
      .map((s: string) => (s.startsWith(".") ? s.toLowerCase() : `.${s.toLowerCase()}`))
      .filter(Boolean);

    if (action === "add" && value) {
      const normalized = value.startsWith(".") ? value.toLowerCase() : `.${value.toLowerCase()}`;
      if (!nextArr.includes(normalized)) nextArr.push(normalized);
    } else if (action === "remove") {
      if (value) {
        const normalized = value.startsWith(".") ? value.toLowerCase() : `.${value.toLowerCase()}`;
        nextArr = nextArr.filter(x => x !== normalized);
      } else {
        // if no explicit value, allow removal by index via ctx.args.index
        const idx = typeof ctx.args?.index === "number" ? ctx.args.index : (typeof ctx.args?.index === "string" ? Number.parseInt(ctx.args.index, 10) : NaN);
        if (!Number.isNaN(idx) && idx >= 0 && idx < nextArr.length) {
          nextArr.splice(idx, 1);
        }
      }
    }

    const nextSettings = saveUniverseSettings(runtimePaths, {
      ...settings,
      ignore_extensions: nextArr,
    });

    return { ignore_extensions: nextSettings.ignore_extensions };
  },
  "prismata.universe.capability.app-settings-export": async ctx => {
    const runtimePaths = getUniversePaths(path.resolve(__dirname, "../../../../"));
    const settings = loadUniverseSettings(runtimePaths);
    const nextSettings = saveUniverseSettings(runtimePaths, {
      ...settings,
      export: { ...(settings.export ?? {}), ...(ctx.args ?? {}) },
    });

    return { export: nextSettings.export };
  },
  "prismata.universe.capability.app-settings-registry": async ctx => {
    const runtimePaths = getUniversePaths(path.resolve(__dirname, "../../../../"));
    const settings = loadUniverseSettings(runtimePaths);
    const nextSettings = saveUniverseSettings(runtimePaths, {
      ...settings,
      registry: { ...(settings.registry ?? {}), ...(ctx.args ?? {}) },
    });

    return { registry: nextSettings.registry };
  },

  "prismata.universe.capability.app-settings-auto-archive": async ctx => {
    const runtimePaths = getUniversePaths(path.resolve(__dirname, "../../../../"));
    const settings = loadUniverseSettings(runtimePaths);
    const current = settings.features?.autoArchive ?? false;
    // Support explicit value override or toggle
    const next = typeof ctx.args?.value === "boolean" ? ctx.args.value : !current;
    const nextSettings = saveUniverseSettings(runtimePaths, {
      ...settings,
      features: { ...(settings.features ?? {}), autoArchive: next },
    });
    return { features: nextSettings.features };
  },
  "prismata.universe.capability.app-settings-auto-versioning": async ctx => {
    const runtimePaths = getUniversePaths(path.resolve(__dirname, "../../../../"));
    const settings = loadUniverseSettings(runtimePaths);
    const current = settings.features?.autoVersioning ?? false;
    // Support explicit value override or toggle
    const next = typeof ctx.args?.value === "boolean" ? ctx.args.value : !current;
    const nextSettings = saveUniverseSettings(runtimePaths, {
      ...settings,
      features: { ...(settings.features ?? {}), autoVersioning: next },
    });
    return { features: nextSettings.features };
  },

  "prismata.universe.capability.app-bootstrap-run": async ctx => {
    if (!ctx.services?.runBootstrapSequence) {
      throw new Error("Bootstrap service is not available.");
    }
    return ctx.services.runBootstrapSequence();
  },

  "prismata.universe.capability.app-quit": async () => ({ exit: true }),
};
