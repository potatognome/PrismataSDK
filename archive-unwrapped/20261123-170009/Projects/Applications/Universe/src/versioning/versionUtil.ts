// src/versioning/versionUtils.ts

export type VersionModel = "semantic" | "integer" | "date" | "unknown";

export interface NormalizedVersion {
  model: VersionModel;
  major?: number;
  minor?: number;
  patch?: number;
  int?: number;
  date?: Date;
  raw: string;
}

/**
 * Detect version model from raw string.
 */
export function detectVersionModel(raw: string): VersionModel {
  if (/^\d+\.\d+\.\d+$/.test(raw)) return "semantic";
  if (/^\d+$/.test(raw)) return "integer";
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return "date";
  return "unknown";
}

/**
 * Normalize any version string into a structured NormalizedVersion object.
 */
export function normalizeVersion(raw: string): NormalizedVersion {
  const model = detectVersionModel(raw);

  switch (model) {
    case "semantic": {
      const [major, minor, patch] = raw.split(".").map(n => parseInt(n, 10));
      return { model, major, minor, patch, raw };
    }

    case "integer": {
      return { model, int: parseInt(raw, 10), raw };
    }

    case "date": {
      return { model, date: new Date(raw), raw };
    }

    default:
      return { model: "unknown", raw };
  }
}

/**
 * Compare two normalized versions.
 * Returns:
 *   -1 if a < b
 *    0 if a == b
 *    1 if a > b
 */
export function compareVersions(a: NormalizedVersion, b: NormalizedVersion): number {
  if (a.model === "semantic" && b.model === "semantic") {
    if (a.major! !== b.major!) return a.major! < b.major! ? -1 : 1;
    if (a.minor! !== b.minor!) return a.minor! < b.minor! ? -1 : 1;
    if (a.patch! !== b.patch!) return a.patch! < b.patch! ? -1 : 1;
    return 0;
  }

  if (a.model === "integer" && b.model === "integer") {
    return a.int! < b.int! ? -1 : a.int! > b.int! ? 1 : 0;
  }

  if (a.model === "date" && b.model === "date") {
    return a.date!.getTime() < b.date!.getTime()
      ? -1
      : a.date!.getTime() > b.date!.getTime()
      ? 1
      : 0;
  }

  return a.raw < b.raw ? -1 : a.raw > b.raw ? 1 : 0;
}

/**
 * Check if two versions are compatible (same model or normalizable).
 */
export function versionsCompatible(a: string, b: string): boolean {
  const na = normalizeVersion(a);
  const nb = normalizeVersion(b);

  if (na.model === "unknown" || nb.model === "unknown") return false;
  if (na.model === nb.model) return true;

  if (na.model === "semantic" && nb.model === "integer") return true;
  if (na.model === "integer" && nb.model === "semantic") return true;

  if (na.model === "date" || nb.model === "date") return false;

  return false;
}

/**
 * Apply forward or backward version remapping.
 */
export function remapVersion(
  raw: string,
  direction: "forward" | "backward"
): string {
  const n = normalizeVersion(raw);

  switch (n.model) {
    case "semantic": {
      const major = n.major!;
      const minor = n.minor!;
      const patch = n.patch!;
      return direction === "forward"
        ? `${major}.${minor}.${patch + 1}`
        : `${major}.${minor}.${Math.max(0, patch - 1)}`;
    }

    case "integer": {
      const next = direction === "forward" ? n.int! + 1 : Math.max(0, n.int! - 1);
      return `${next}`;
    }

    case "date": {
      const d = new Date(n.date!);
      const delta = direction === "forward" ? 1 : -1;
      d.setDate(d.getDate() + delta);
      return d.toISOString().split("T")[0];
    }

    default:
      return raw;
  }
}

/**
 * Build a version lineage map for a list of version strings.
 */
export function buildVersionLineage(versions: string[]): string[] {
  const normalized = versions.map(v => normalizeVersion(v));
  normalized.sort(compareVersions);
  return normalized.map(v => v.raw);
}
