import * as fs from "fs";
import * as path from "path";
import { getUniversePaths, loadUniverseSettings } from "../bootstrap/state";

export interface SearchParameters {
  // Accept multiple roots for convenience (runSearch will use rootPath or folders)
  rootPath?: string;
  folders?: string[];
  projects?: string[];
  fileTypes?: string[]; // extensions with leading dot preferred
  queries?: string[]; // match against filename or file content
  tags?: string[]; // simple key or value match in file content (CONFIG only: .json, .jsonl, .yaml, .ini, .toml, etc.)
  canonicalOnly?: boolean;
  recursive?: boolean;
  maxDepth?: number;
}

export interface SearchResultItem {
  id: string;
  udi: string;
  fullPath: string;
  relativePath: string;
  extension: string;
  sizeBytes: number;
  modifiedAt: Date;
}

export interface SearchResult {
  results: SearchResultItem[];
  rootPath: string;
  parameters: SearchParameters;
}

function walkDir(
  root: string,
  current: string,
  maxDepth: number,
  depth: number,
  recursive: boolean,
  cb: (fullPath: string) => void
): void {
  if (depth > maxDepth) return;

  const entries = fs.readdirSync(current, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(current, entry.name);

    if (entry.isDirectory()) {
      if (recursive) {
        walkDir(root, fullPath, maxDepth, depth + 1, recursive, cb);
      }
      // if not recursive, skip subdirectories
    } else if (entry.isFile()) {
      cb(fullPath);
    }
  }
}

function isUtf8Capable(fullPath: string): boolean {
  try {
    const fd = fs.openSync(fullPath, "r");
    const buf = Buffer.allocUnsafe(4096);
    const bytes = fs.readSync(fd, buf, 0, buf.length, 0);
    fs.closeSync(fd);

    // If file is empty, treat as text
    if (bytes === 0) return true;

    for (let i = 0; i < bytes; i++) {
      if (buf[i] === 0) return false; // NUL byte -> likely binary
    }

    // Heuristic: if the buffer contains a high percentage of non-printable characters, treat as binary
    let nonPrintable = 0;
    for (let i = 0; i < bytes; i++) {
      const b = buf[i];
      // allow common whitespace and printable ASCII (9,10,13,32-126)
      if (b === 9 || b === 10 || b === 13) continue;
      if (b >= 32 && b <= 126) continue;
      nonPrintable++;
    }

    const ratio = nonPrintable / bytes;
    return ratio < 0.3; // if less than 30% non-printable, consider UTF-capable
  } catch {
    return false;
  }
}

function fileMatches(fullPath: string, params: SearchParameters, ignoreExtensions: string[] = []): boolean {
  const ext = path.extname(fullPath);
  const base = path.basename(fullPath);

  // Within-type matching: OR semantics
  if (params.fileTypes && params.fileTypes.length > 0) {
    const normalized = params.fileTypes.map(f => (f.startsWith(".") ? f : `.${f}`));
    if (!normalized.includes(ext)) return false;
  }

  // Deterministic ignore list from settings: always skip these extensions
  if (Array.isArray(ignoreExtensions) && ignoreExtensions.length > 0) {
    const norm = ignoreExtensions.map(s => (s.startsWith(".") ? s.toLowerCase() : `.${s.toLowerCase()}`));
    if (norm.includes(ext.toLowerCase())) return false;
  }

  // If no explicit fileTypes selected, filter out obvious non-text/binary files
  if (!params.fileTypes || params.fileTypes.length === 0) {
    if (!isUtf8Capable(fullPath)) return false;
  }

  if (params.queries && params.queries.length > 0) {
    // match any query in filename or file content
    const fileContent = (() => {
      try {
        return fs.readFileSync(fullPath, "utf8");
      } catch {
        return "";
      }
    })();

    const anyQueryMatches = params.queries.some(q => {
      if (!q) return false;
      if (base.includes(q)) return true;
      if (fileContent.includes(q)) return true;
      return false;
    });

    if (!anyQueryMatches) return false;
  }

  if (params.tags && params.tags.length > 0) {
    // Only search tags against keys/values inside config files.
    const isConfigFile = (() => {
      const cfgExts = [".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"];
      const lower = fullPath.toLowerCase();
      if (cfgExts.includes(ext.toLowerCase())) return true;
      if (lower.includes(`${path.sep}config${path.sep}`) || lower.endsWith(`${path.sep}config`)) return true;
      return false;
    })();

    if (!isConfigFile) return false;

    const fileContent = (() => {
      try {
        return fs.readFileSync(fullPath, "utf8");
      } catch {
        return "";
      }
    })();

    const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

    const jsonDeepContains = (obj: any, tag: string): boolean => {
      if (obj == null) return false;
      if (typeof obj === "string") return obj.includes(tag);
      if (typeof obj === "number" || typeof obj === "boolean") return String(obj).includes(tag);
      if (Array.isArray(obj)) {
        return obj.some(i => jsonDeepContains(i, tag));
      }
      if (typeof obj === "object") {
        return Object.keys(obj).some(k => k.includes(tag) || jsonDeepContains(obj[k], tag));
      }
      return false;
    };

    const anyTagMatches = params.tags.some(t => {
      if (!t) return false;
      const tag = String(t);

      // For JSON files, try to parse and search keys/values structurally.
      if (ext.toLowerCase() === ".json") {
        try {
          const parsed = JSON.parse(fileContent);
          return jsonDeepContains(parsed, tag);
        } catch {
          // fall back to textual search if parsing fails
        }
      }

      // For other config formats, use a token-aware substring search to approximate key/value matching.
      const re = new RegExp("\\b" + escapeRegExp(tag) + "\\b", "i");
      return re.test(fileContent);
    });

    if (!anyTagMatches) return false;
  }

  // canonicalOnly currently not implemented as a concrete filter
  // If canonicalOnly is requested, enforce that the file appears to be a
  // canonical artifact: it must contain a UDI, a version, and an active flag.
  if (params.canonicalOnly) {
    const content = (() => {
      try {
        return fs.readFileSync(fullPath, "utf8");
      } catch {
        return "";
      }
    })();

    const hasUdi = /\budi\b\s*[:=]/i.test(content) || /\budi\b/i.test(path.basename(fullPath));
    const hasVersion = /\bversion\b\s*[:=]/i.test(content);
    const hasActiveTrue = /\bactive\b\s*[:=]\s*(?:true|1)\b/i.test(content);

    if (!hasUdi || !hasVersion || !hasActiveTrue) return false;
  }

  return true;
}

function deriveUdi(relativePath: string): string {
  const slug = relativePath
    .toLowerCase()
    .replace(/\\/g, "/")
    .replace(/[^a-z0-9/]/g, "-")
    .replace(/\/+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 64);
  return `prismata.universe.search-result.${slug}`;
}

function buildResultItem(
  rootPath: string,
  fullPath: string
): SearchResultItem {
  const stats = fs.statSync(fullPath);
  const relativePath = path.relative(rootPath, fullPath);
  const extension = path.extname(fullPath);

  return {
    id: fullPath,
    udi: deriveUdi(relativePath),
    fullPath,
    relativePath,
    extension,
    sizeBytes: stats.size,
    modifiedAt: stats.mtime,
  };
}

export function runSearch(params: SearchParameters): SearchResult {
  const roots: string[] = [];
  if (Array.isArray(params.folders) && params.folders.length > 0) {
    roots.push(...params.folders.map(p => path.resolve(p)));
  } else if (params.rootPath) {
    roots.push(path.resolve(params.rootPath));
  } else {
    roots.push(path.resolve(process.cwd()));
  }

  const maxDepth = params.maxDepth ?? 10;

  const results: SearchResultItem[] = [];

  const recursive = params.recursive !== undefined ? Boolean(params.recursive) : true;

  // Load persisted ignore extensions from settings (if present)
  const runtimePaths = getUniversePaths(path.resolve(__dirname, "../../../../"));
  const settings = loadUniverseSettings(runtimePaths);
  const ignoreExtensions = Array.isArray((settings as any).ignore_extensions) ? (settings as any).ignore_extensions.map((s: any) => String(s).trim()).filter(Boolean) : [];

  for (const root of roots) {
    try {
      walkDir(root, root, maxDepth, 0, recursive, fullPath => {
        if (fileMatches(fullPath, params, ignoreExtensions)) {
          results.push(buildResultItem(root, fullPath));
        }
      });
    } catch {
      // ignore failures for individual roots
    }
  }

  return {
    results,
    rootPath: roots[0] ?? path.resolve(process.cwd()),
    parameters: params,
  };
}

export function groupResultsByBasename(results: SearchResultItem[]): Record<string, SearchResultItem[]> {
  const map: Record<string, SearchResultItem[]> = {};
  for (const r of results) {
    const base = (r.relativePath || r.fullPath).split(/[\\/]/).pop() || r.relativePath || r.fullPath;
    const key = base.toLowerCase();
    if (!map[key]) map[key] = [];
    map[key].push(r);
  }
  // Optionally sort versions by modified date descending
  for (const k of Object.keys(map)) {
    map[k].sort((a, b) => b.modifiedAt.getTime() - a.modifiedAt.getTime());
  }
  return map;
}
