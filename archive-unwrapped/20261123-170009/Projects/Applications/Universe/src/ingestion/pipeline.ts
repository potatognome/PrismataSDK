import * as fs from "fs";
import * as path from "path";
import { bootstrapLog } from "../bootstrap/logger";
import { UniversePaths, ensureUniverseDirs, markInitialized } from "../bootstrap/state";

interface IngestionItem {
  packageName: string;
  udi: string;
  sourcePath?: string;
  sourceKind: "module" | "manifest" | "placeholder";
  manifestFragment?: string;
  metadata?: Record<string, unknown>;
}

interface ValidationResult {
  status: "validated";
  details: string;
}

interface CanonicalizationResult {
  status: "canonicalized";
  details: string;
}

interface RegistryEntry {
  package_name: string;
  udi: string;
  version: string;
  install_status: "installed" | "missing";
  validation_status: "validated";
  canonicalization_status: "canonicalized";
  timestamp_utc: string;
}

interface BootstrapSummary {
  initializedFlagPath: string;
  ingestionFilePath: string;
  registryFilePath: string;
  archiveRoot: string;
  ingestedCount: number;
}

function nowIsoUtc(): string {
  return new Date().toISOString();
}

function sanitizePathSegment(value: string): string {
  return value.replace(/[^a-zA-Z0-9._-]+/g, "-");
}

function readSafe(pathValue: string): string {
  try {
    return fs.readFileSync(pathValue, "utf8");
  } catch {
    return "";
  }
}

function parseSimpleScalar(value: string): string {
  const trimmed = value.trim();
  if (
    (trimmed.startsWith("\"") && trimmed.endsWith("\"")) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function parseToolingManifest(toolingManifestPath: string): IngestionItem[] {
  const raw = readSafe(toolingManifestPath);
  if (!raw) {
    return [];
  }

  const lines = raw.split(/\r?\n/);
  const items: IngestionItem[] = [];
  let inPrimitives = false;
  let current: {
    udi?: string;
    name?: string;
    version?: string;
    module?: string;
  } | null = null;

  const flushCurrent = (): void => {
    if (!current || !current.udi) {
      return;
    }

    const manifestFragment = [
      `udi: ${current.udi}`,
      `name: ${current.name ?? current.udi}`,
      `version: ${current.version ?? "0.0.1"}`,
      `module: ${current.module ?? ""}`,
    ].join("\n");

    items.push({
      packageName: current.name ?? current.udi,
      udi: current.udi,
      sourceKind: "module",
      sourcePath: current.module,
      manifestFragment,
      metadata: {
        origin: "tooling.manifest.yaml",
      },
    });
  };

  for (const line of lines) {
    if (!inPrimitives) {
      if (line.trim() === "primitives:") {
        inPrimitives = true;
      }
      continue;
    }

    const itemStart = line.match(/^\s{2}-\s+udi:\s*(.+)\s*$/);
    if (itemStart) {
      flushCurrent();
      current = { udi: parseSimpleScalar(itemStart[1]) };
      continue;
    }

    if (!current) {
      continue;
    }

    const nameMatch = line.match(/^\s{4}name:\s*(.+)\s*$/);
    if (nameMatch) {
      current.name = parseSimpleScalar(nameMatch[1]);
      continue;
    }

    const versionMatch = line.match(/^\s{4}version:\s*(.+)\s*$/);
    if (versionMatch) {
      current.version = parseSimpleScalar(versionMatch[1]);
      continue;
    }

    const moduleMatch = line.match(/^\s{4}module:\s*(.+)\s*$/);
    if (moduleMatch) {
      current.module = parseSimpleScalar(moduleMatch[1]);
      continue;
    }
  }

  flushCurrent();
  return items;
}

function validateStub(item: IngestionItem): ValidationResult {
  return {
    status: "validated",
    details: `validated ${item.udi}`,
  };
}

function canonicalizeStub(item: IngestionItem): CanonicalizationResult {
  return {
    status: "canonicalized",
    details: `canonicalized ${item.udi}`,
  };
}

function resolveSourcePath(item: IngestionItem, prismataRoot: string): string | undefined {
  if (!item.sourcePath) {
    return undefined;
  }

  const normalized = item.sourcePath.replace(/\\/g, "/");
  const asProvided = path.resolve(prismataRoot, normalized);
  if (fs.existsSync(asProvided)) {
    return asProvided;
  }

  const toolingRoot = path.join(prismataRoot, "Projects", "Tooling");
  const underTooling = path.resolve(toolingRoot, normalized);
  if (fs.existsSync(underTooling)) {
    return underTooling;
  }

  return undefined;
}

function snapshotModuleFiles(sourcePath: string): string[] {
  const files: string[] = [];

  const walk = (currentPath: string): void => {
    const stat = fs.statSync(currentPath);
    if (stat.isFile()) {
      files.push(currentPath);
      return;
    }

    for (const child of fs.readdirSync(currentPath)) {
      walk(path.join(currentPath, child));
      if (files.length >= 250) {
        return;
      }
    }
  };

  walk(sourcePath);
  return files;
}

function writeArchive(
  paths: UniversePaths,
  item: IngestionItem,
  version: string,
  validation: ValidationResult,
  canonicalization: CanonicalizationResult,
  resolvedSourcePath?: string
): void {
  const itemRoot = path.join(
    paths.archiveDir,
    sanitizePathSegment(item.udi),
    sanitizePathSegment(version)
  );
  fs.mkdirSync(itemRoot, { recursive: true });

  const metadata = {
    package_name: item.packageName,
    udi: item.udi,
    version,
    source_kind: item.sourceKind,
    source_path: resolvedSourcePath ?? item.sourcePath ?? null,
    ingested_at_utc: nowIsoUtc(),
    metadata: item.metadata ?? {},
  };

  fs.writeFileSync(
    path.join(itemRoot, "metadata.json"),
    `${JSON.stringify(metadata, null, 2)}\n`,
    "utf8"
  );

  fs.writeFileSync(
    path.join(itemRoot, "manifest.fragment.yaml"),
    `${item.manifestFragment ?? `udi: ${item.udi}\nname: ${item.packageName}`}\n`,
    "utf8"
  );

  fs.writeFileSync(
    path.join(itemRoot, "udi.assignment.json"),
    `${JSON.stringify({ udi: item.udi, package_name: item.packageName }, null, 2)}\n`,
    "utf8"
  );

  fs.writeFileSync(
    path.join(itemRoot, "validation.log"),
    [validation.details, canonicalization.details].join("\n") + "\n",
    "utf8"
  );

  if (resolvedSourcePath && fs.existsSync(resolvedSourcePath)) {
    const stat = fs.statSync(resolvedSourcePath);
    const moduleFiles = stat.isDirectory()
      ? snapshotModuleFiles(resolvedSourcePath)
      : [resolvedSourcePath];
    const normalized = moduleFiles.map(filePath =>
      path.relative(paths.prismataRoot, filePath).replace(/\\/g, "/")
    );
    fs.writeFileSync(
      path.join(itemRoot, "module.files.json"),
      `${JSON.stringify({ count: normalized.length, files: normalized }, null, 2)}\n`,
      "utf8"
    );
  } else {
    fs.writeFileSync(
      path.join(itemRoot, "module.files.json"),
      `${JSON.stringify({ count: 0, files: [], missing_source: true }, null, 2)}\n`,
      "utf8"
    );
  }
}

function writeRegistryEntry(paths: UniversePaths, entry: RegistryEntry): void {
  fs.mkdirSync(paths.registryDir, { recursive: true });
  const registryPath = path.join(paths.registryDir, "registry.jsonl");
  fs.appendFileSync(registryPath, `${JSON.stringify(entry)}\n`, "utf8");
}

function defaultBootstrapItems(
  prismataRoot: string,
  toolingManifestPath: string,
  vaultGuardMetaPath: string
): IngestionItem[] {
  const toolingItems = parseToolingManifest(toolingManifestPath);

  const tuilkitPath = path.resolve(prismataRoot, "..", "tUilKit");

  const seeds: IngestionItem[] = [
    {
      packageName: "tUilKit",
      udi: "module.tuilkit",
      sourceKind: "module",
      sourcePath: tuilkitPath,
      metadata: {
        reused_primitives: [
          "scraper",
          "foldertree",
          "configmerge",
          "config-helpers",
          "path-helpers",
          "colour-path-helpers",
          "menu-helpers",
          "vile",
          "ASTalyzer",
        ],
      },
    },
    {
      packageName: "VaultGuard",
      udi: "module.vaultguard",
      sourceKind: "placeholder",
      sourcePath: undefined,
      manifestFragment: readSafe(vaultGuardMetaPath).slice(0, 1200),
      metadata: {
        placeholder: true,
        provenance: vaultGuardMetaPath,
      },
    },
  ];

  return [...seeds, ...toolingItems];
}

export function runBootstrapIngestion(paths: UniversePaths): BootstrapSummary {
  ensureUniverseDirs(paths);

  const toolingManifestPath = path.join(
    paths.prismataRoot,
    ".workspace",
    "projects.manifests",
    "tooling.manifest.yaml"
  );
  const vaultGuardMetaPath = path.join(
    paths.prismataRoot,
    "Meta",
    "governance",
    "vaultguard-prismcommand-onboarding.md"
  );

  const items = defaultBootstrapItems(
    paths.prismataRoot,
    toolingManifestPath,
    vaultGuardMetaPath
  );

  const ingestionFilePath = path.join(paths.ingestionDir, "first-ingestion.json");
  fs.writeFileSync(
    ingestionFilePath,
    `${JSON.stringify({ created_at_utc: nowIsoUtc(), items }, null, 2)}\n`,
    "utf8"
  );
  bootstrapLog(`bootstrap ingestion file created: ${ingestionFilePath}`);

  const version = "0.0.1";

  for (const item of items) {
    bootstrapLog(`ingest ${item.udi}`);

    const validation = validateStub(item);
    const canonicalization = canonicalizeStub(item);

    // Every item is versioned immediately after validation/canonicalization.
    const assignedVersion = version;
    const resolvedSourcePath = resolveSourcePath(item, paths.prismataRoot);

    writeArchive(
      paths,
      item,
      assignedVersion,
      validation,
      canonicalization,
      resolvedSourcePath
    );

    const installStatus = resolvedSourcePath ? "installed" : "missing";

    writeRegistryEntry(paths, {
      package_name: item.packageName,
      udi: item.udi,
      version: assignedVersion,
      install_status: installStatus,
      validation_status: validation.status,
      canonicalization_status: canonicalization.status,
      timestamp_utc: nowIsoUtc(),
    });
  }

  markInitialized(paths);
  bootstrapLog(`initialized flag created: ${paths.initializedFlagPath}`);

  return {
    initializedFlagPath: paths.initializedFlagPath,
    ingestionFilePath,
    registryFilePath: path.join(paths.registryDir, "registry.jsonl"),
    archiveRoot: paths.archiveDir,
    ingestedCount: items.length,
  };
}
