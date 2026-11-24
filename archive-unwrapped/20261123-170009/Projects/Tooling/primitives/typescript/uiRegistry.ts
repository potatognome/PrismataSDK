import * as fs from "fs";
import * as path from "path";

export interface UiFrameworkRegistryEntry {
  id: string;
  label?: string;
  framework_id: string;
  presentation?: {
    default_layer?: string;
    supported_layers?: string[];
    hints?: Record<string, string>;
  };
}

function resolveSchemaDir(prismataRoot: string) {
  return path.join(prismataRoot, "Meta", "canonical", "ui.schemas");
}

function registryDir(prismataRoot: string) {
  return path.join(prismataRoot, "Meta", "canonical", "ui-frameworks");
}

export function loadUiFrameworkRegistry(prismataRoot: string): UiFrameworkRegistryEntry[] {
  const dir = registryDir(prismataRoot);
  if (!fs.existsSync(dir)) return [];

  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".yaml") || f.endsWith(".yml"));
  const entries: UiFrameworkRegistryEntry[] = [];

  let Ajv: any = null;
  let jsyaml: any = null;
  try {
    // @ts-ignore
    Ajv = require("ajv");
    // @ts-ignore
    jsyaml = require("js-yaml");
  } catch (_) {
    Ajv = null;
    jsyaml = null;
  }

  let validate: ((obj: any) => boolean) | null = null;
  if (Ajv && jsyaml) {
    try {
      const ajv = new Ajv({ allErrors: true });
      const schemaPath = path.join(resolveSchemaDir(prismataRoot), "ui-framework-registry.schema.yaml");
      if (fs.existsSync(schemaPath)) {
        const schema = jsyaml.load(fs.readFileSync(schemaPath, "utf8"));
        validate = ajv.compile(schema as object);
      }
    } catch (_) {
      validate = null;
    }
  }

  for (const f of files) {
    try {
      const raw = fs.readFileSync(path.join(dir, f), "utf8");
      const parsed = jsyaml ? jsyaml.load(raw) : (() => { try { return JSON.parse(raw); } catch { return null; } })();
      const obj = parsed as any;

      // If file wraps the object under a top-level key, unwrap
      let entry = obj;
      if (entry && typeof entry === "object" && Object.keys(entry).length === 1) {
        const onlyKey = Object.keys(entry)[0];
        if (entry[onlyKey] && typeof entry[onlyKey] === "object") entry = entry[onlyKey];
      }

      if (validate && !validate(entry)) {
        // validation failed: skip but continue
        continue;
      }

      entries.push(entry as UiFrameworkRegistryEntry);
    } catch (_) {
      continue;
    }
  }

  return entries;
}

export function listRegistryFrameworkIds(prismataRoot: string): string[] {
  return loadUiFrameworkRegistry(prismataRoot).map((e) => e.id);
}

export function getRegistryEntry(prismataRoot: string, id: string): UiFrameworkRegistryEntry | null {
  const all = loadUiFrameworkRegistry(prismataRoot);
  return all.find((e) => e.id === id) ?? null;
}
