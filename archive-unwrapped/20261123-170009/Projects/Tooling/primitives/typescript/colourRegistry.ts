import * as fs from "fs";
import * as path from "path";

export interface ColourRoleLayers {
  fg?: string;
  bg?: string;
}

export interface ColourSchemeEntry {
  id: string;
  label?: string;
  description?: string;
  chroma_source?: string;
  roles: Record<string, ColourRoleLayers>;
}

function registryDir(prismataRoot: string) {
  return path.join(prismataRoot, "Meta", "registry", "colour-schemes.d");
}

export function loadColourRegistry(prismataRoot: string): ColourSchemeEntry[] {
  const dir = registryDir(prismataRoot);
  if (!fs.existsSync(dir)) return [];

  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.yaml') || f.endsWith('.yml'));
  const entries: ColourSchemeEntry[] = [];

  let jsyaml: any = null;
  try {
    // @ts-ignore
    jsyaml = require('js-yaml');
  } catch (_) {
    jsyaml = null;
  }

  for (const f of files) {
    try {
      const raw = fs.readFileSync(path.join(dir, f), 'utf8');
      const obj = jsyaml ? jsyaml.load(raw) : JSON.parse(raw);
      let entry = obj;
      if (entry && typeof entry === 'object' && Object.keys(entry).length === 1) {
        const onlyKey = Object.keys(entry)[0];
        if (entry[onlyKey] && typeof entry[onlyKey] === 'object') entry = entry[onlyKey];
      }
      if (entry && entry.id && entry.roles) {
        entries.push(entry as ColourSchemeEntry);
      }
    } catch (_) {
      continue;
    }
  }

  return entries;
}

export function mergeScheme(base: ColourSchemeEntry, overlay: Partial<ColourSchemeEntry>): ColourSchemeEntry {
  const merged: ColourSchemeEntry = {
    id: base.id,
    label: overlay.label ?? base.label,
    description: overlay.description ?? base.description,
    chroma_source: overlay.chroma_source ?? base.chroma_source,
    roles: { ...(base.roles ?? {}) },
  };

  if (overlay.roles) {
    for (const r of Object.keys(overlay.roles)) {
      merged.roles[r] = { ...(merged.roles[r] ?? {}), ...(overlay.roles as any)[r] };
    }
  }

  return merged;
}

export function findColourSchemeById(prismataRoot: string, id: string, appRoot?: string): ColourSchemeEntry | null {
  const all = loadColourRegistry(prismataRoot);
  const base = all.find((e) => e.id === id) ?? null;
  if (!base) return null;

  // if no appRoot provided, return base
  if (!appRoot) return base;

  // check project and tenant override files
  const projectPath = path.join(appRoot, 'config', 'project', 'ui', 'colour-scheme.override.yaml');
  const tenantPath = path.join(appRoot, 'config', 'tenant', 'ui', 'colour-scheme.override.yaml');

  let overlay: Partial<ColourSchemeEntry> | null = null;
  let jsyaml: any = null;
  try { jsyaml = require('js-yaml'); } catch (_) { jsyaml = null; }

  function tryLoadOverride(p: string): Partial<ColourSchemeEntry> | null {
    if (!fs.existsSync(p)) return null;
    try {
      const raw = fs.readFileSync(p, 'utf8');
      const obj = jsyaml ? jsyaml.load(raw) : JSON.parse(raw);
      // file may be a mapping of id->entry or a single entry
      if (!obj) return null;
      if (obj.id && obj.id === id) return obj as Partial<ColourSchemeEntry>;
      if (typeof obj === 'object') {
        if (obj[id]) return obj[id] as Partial<ColourSchemeEntry>;
        // try to find in nested mapping
        for (const k of Object.keys(obj)) {
          const v = (obj as any)[k];
          if (v && v.id === id) return v as Partial<ColourSchemeEntry>;
        }
      }
    } catch (_) { return null; }
    return null;
  }

  // project override preferred over tenant (per Option A)
  overlay = tryLoadOverride(projectPath) ?? tryLoadOverride(tenantPath) ?? null;

  if (overlay) return mergeScheme(base, overlay);
  return base;
}

export default { loadColourRegistry, findColourSchemeById };
