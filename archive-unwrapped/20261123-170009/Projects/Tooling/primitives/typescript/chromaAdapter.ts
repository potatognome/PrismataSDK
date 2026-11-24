import * as fs from "fs";
import * as path from "path";

export interface Rgb { r: number; g: number; b: number }

export function rgbToAnsi24(rgb: Rgb): string {
  return `\u001b[38;2;${rgb.r};${rgb.g};${rgb.b}m`;
}

export function bgRgbToAnsi24(rgb: Rgb): string {
  return `\u001b[48;2;${rgb.r};${rgb.g};${rgb.b}m`;
}

export function resetAnsi(): string { return '\u001b[0m'; }

/**
 * Parse a simple exemplar chroma YAML file that contains `colourSet` mapping
 * like { c0: [r,g,b], c1: [r,g,b], ... } and return a token->rgb map.
 */
export function parseChromaColourSet(filePath: string): Record<string, Rgb> {
  let jsyaml: any = null;
  try { jsyaml = require('js-yaml'); } catch (_) { jsyaml = null; }
  const raw = fs.readFileSync(filePath, 'utf8');
  const obj = jsyaml ? jsyaml.load(raw) : JSON.parse(raw);
  const out: Record<string, Rgb> = {};
  const cs = obj?.colourSet ?? obj?.colour_set ?? obj?.colourSet;
  if (!cs || typeof cs !== 'object') return out;
  for (const k of Object.keys(cs)) {
    const arr = cs[k];
    if (Array.isArray(arr) && arr.length >= 3) {
      out[k] = { r: Number(arr[0]) || 0, g: Number(arr[1]) || 0, b: Number(arr[2]) || 0 };
    }
  }
  return out;
}

/**
 * Given a `roles` mapping where the values are { fg: "ansi:rgb(...)" } or colourRef tokens (e.g., 'c0'),
 * and a token->rgb map, produce role->ANSI mapping for fg/bg.
 */
export function buildRoleAnsiMap(roles: Record<string, any>, tokenMap: Record<string, Rgb>): Record<string, { fg?: string; bg?: string }> {
  const out: Record<string, { fg?: string; bg?: string }> = {};
  for (const r of Object.keys(roles)) {
    const layers = roles[r] || {};
    const entry: { fg?: string; bg?: string } = {};
    if (layers.fg) {
      const m = String(layers.fg).match(/ansi:rgb\((\d+),(\d+),(\d+)\)/);
      if (m) entry.fg = rgbToAnsi24({ r: Number(m[1]), g: Number(m[2]), b: Number(m[3]) });
      else if (tokenMap[layers.fg]) entry.fg = rgbToAnsi24(tokenMap[layers.fg]);
    }
    if (layers.bg) {
      const m = String(layers.bg).match(/ansi:rgb\((\d+),(\d+),(\d+)\)/);
      if (m) entry.bg = bgRgbToAnsi24({ r: Number(m[1]), g: Number(m[2]), b: Number(m[3]) });
      else if (tokenMap[layers.bg]) entry.bg = bgRgbToAnsi24(tokenMap[layers.bg]);
    }
    out[r] = entry;
  }
  return out;
}

export default { rgbToAnsi24, bgRgbToAnsi24, resetAnsi, parseChromaColourSet, buildRoleAnsiMap };
