import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

import {
  getUniversePaths,
  loadUniverseSettings,
  saveUniverseSettings,
  getRuntimeState,
  getSharedUiConfigFiles,
} from "../src/bootstrap/state";
import { runBootstrapIngestion } from "../src/ingestion/pipeline";

function writeTextFile(filePath: string, content: string): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
}

function createFixturePrismataRoot(): { baseDir: string; prismataRoot: string } {
  const baseDir = fs.mkdtempSync(path.join(os.tmpdir(), "universe-suite-"));
  const prismataRoot = path.join(baseDir, "Prismata");

  fs.mkdirSync(prismataRoot, { recursive: true });

  const toolingManifestPath = path.join(
    prismataRoot,
    ".workspace",
    "projects.manifests",
    "tooling.manifest.yaml"
  );
  writeTextFile(
    toolingManifestPath,
    [
      "primitives:",
      "  - udi: tooling.vile",
      "    name: Vile",
      "    version: 0.0.1",
      "    module: Vile",
      "",
    ].join("\n")
  );

  const vaultGuardDocPath = path.join(
    prismataRoot,
    "Meta",
    "governance",
    "vaultguard-prismcommand-onboarding.md"
  );
  writeTextFile(vaultGuardDocPath, "# VaultGuard onboarding\n\nScaffolded service metadata.\n");

  fs.mkdirSync(path.join(prismataRoot, "Projects", "Tooling", "Vile"), { recursive: true });
  writeTextFile(path.join(prismataRoot, "Projects", "Tooling", "Vile", "README.md"), "vile\n");

  const tuilkitPath = path.join(baseDir, "tUilKit");
  fs.mkdirSync(tuilkitPath, { recursive: true });
  writeTextFile(path.join(tuilkitPath, "README.md"), "tUilKit\n");

  return { baseDir, prismataRoot };
}

function sanitizePathSegment(value: string): string {
  return value.replace(/[^a-zA-Z0-9._-]+/g, "-");
}

test("bootstrap ingestion produces deterministic item ordering and valid registry entries", () => {
  const fixture = createFixturePrismataRoot();

  try {
    const paths = getUniversePaths(fixture.prismataRoot);

    const first = runBootstrapIngestion(paths);
    const firstIngestion = JSON.parse(fs.readFileSync(first.ingestionFilePath, "utf8")) as {
      items: Array<{ udi: string }>;
    };

    const second = runBootstrapIngestion(paths);
    const secondIngestion = JSON.parse(fs.readFileSync(second.ingestionFilePath, "utf8")) as {
      items: Array<{ udi: string }>;
    };

    assert.deepEqual(
      firstIngestion.items.map(item => item.udi),
      secondIngestion.items.map(item => item.udi)
    );

    const registryLines = fs
      .readFileSync(second.registryFilePath, "utf8")
      .split(/\r?\n/)
      .filter(Boolean);

    assert.ok(registryLines.length >= secondIngestion.items.length);

    const parsedRegistry = registryLines.map(line => JSON.parse(line) as Record<string, string>);

    for (const entry of parsedRegistry) {
      assert.match(entry.version ?? "", /^\d+\.\d+\.\d+$/);
      assert.equal(entry.validation_status, "validated");
      assert.equal(entry.canonicalization_status, "canonicalized");
      assert.ok(entry.udi);
      assert.ok(entry.package_name);
      assert.ok(entry.timestamp_utc);
    }

    const vaultGuardEntry = parsedRegistry.find(entry => entry.udi === "module.vaultguard");
    assert.ok(vaultGuardEntry);
    assert.equal(vaultGuardEntry?.install_status, "missing");

    const vileEntry = parsedRegistry.find(entry => entry.udi === "tooling.vile");
    assert.ok(vileEntry);
    assert.equal(vileEntry?.install_status, "installed");
  } finally {
    fs.rmSync(fixture.baseDir, { recursive: true, force: true });
  }
});

test("archive artifacts are written for every ingested item", () => {
  const fixture = createFixturePrismataRoot();

  try {
    const paths = getUniversePaths(fixture.prismataRoot);
    const summary = runBootstrapIngestion(paths);
    const ingestion = JSON.parse(fs.readFileSync(summary.ingestionFilePath, "utf8")) as {
      items: Array<{ udi: string }>;
    };

    for (const item of ingestion.items) {
      const itemRoot = path.join(paths.archiveDir, sanitizePathSegment(item.udi), "0.0.1");
      assert.ok(fs.existsSync(path.join(itemRoot, "metadata.json")));
      assert.ok(fs.existsSync(path.join(itemRoot, "manifest.fragment.yaml")));
      assert.ok(fs.existsSync(path.join(itemRoot, "udi.assignment.json")));
      assert.ok(fs.existsSync(path.join(itemRoot, "validation.log")));
      assert.ok(fs.existsSync(path.join(itemRoot, "module.files.json")));
    }
  } finally {
    fs.rmSync(fixture.baseDir, { recursive: true, force: true });
  }
});

test("universe settings persist and restore on startup", () => {
  const fixture = createFixturePrismataRoot();

  try {
    const paths = getUniversePaths(fixture.prismataRoot);
    const settings = {
      paths: { workspaceRoot: paths.workspaceRoot, defaultRoot: "/tmp/example" },
      naming: { fileCase: "snake_case" },
      export: { format: "yaml" },
      registry: { strict: true },
    };

    saveUniverseSettings(paths, settings);

    const reloaded = loadUniverseSettings(paths);
    const runtime = getRuntimeState(paths);

    assert.deepEqual(reloaded, settings);
    assert.deepEqual(runtime.settings, settings);
    assert.equal(fs.existsSync(path.join(paths.stateDir, "settings.json")), true);
  } finally {
    fs.rmSync(fixture.baseDir, { recursive: true, force: true });
  }
});

test("shared tUilKit border and colour config files are available to Universe", () => {
  const fixture = createFixturePrismataRoot();

  try {
    const prismataRoot = fixture.prismataRoot;
    const tuilkitRoot = path.resolve(prismataRoot, "..", "tUilKit");
    fs.mkdirSync(path.join(tuilkitRoot, ".workspace", ".projects_config", "GLOBAL_SHARED.d"), {
      recursive: true,
    });
    fs.writeFileSync(
      path.join(tuilkitRoot, ".workspace", ".projects_config", "GLOBAL_SHARED.d", "COLOURS.json"),
      JSON.stringify({ COLOUR_KEY: { "!data": "BLUE|BLACK" } }, null, 2),
      "utf8"
    );
    fs.writeFileSync(
      path.join(tuilkitRoot, ".workspace", ".projects_config", "GLOBAL_SHARED.d", "BORDER_PATTERNS.json"),
      JSON.stringify({ BORDER_PATTERNS: { SINGLE_LINE: { TOP: ["─"], BOTTOM: ["─"], LEFT: ["│"], RIGHT: ["│"] } } }, null, 2),
      "utf8"
    );

    const resolved = getSharedUiConfigFiles(prismataRoot);
    assert.ok(resolved.coloursJson);
    assert.ok(resolved.borderPatternsJson);

    const colours = JSON.parse(fs.readFileSync(resolved.coloursJson!, "utf8"));
    const borders = JSON.parse(fs.readFileSync(resolved.borderPatternsJson!, "utf8"));

    assert.ok(colours.COLOUR_KEY && colours.COLOUR_KEY["!data"]);
    assert.ok(borders.BORDER_PATTERNS && borders.BORDER_PATTERNS.SINGLE_LINE);
  } finally {
    fs.rmSync(fixture.baseDir, { recursive: true, force: true });
  }
});
