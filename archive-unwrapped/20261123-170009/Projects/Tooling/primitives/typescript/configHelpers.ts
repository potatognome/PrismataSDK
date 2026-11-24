export interface FlattenedEntry {
  key: string;
  value: any;
  type: string;
}

function getTypeFullName(value: any): string {
  if (value === null || value === undefined) return "Null";
  if (Array.isArray(value)) return "Array";
  if (typeof value === "object") return value.constructor?.name ?? "Object";
  return typeof value;
}

export function flattenConfigObject(input: any, prefix = ""): FlattenedEntry[] {
  const out: FlattenedEntry[] = [];

  if (input === null || input === undefined) {
    if (prefix) out.push({ key: prefix, value: input, type: getTypeFullName(input) });
    return out;
  }

  if (Array.isArray(input)) {
    for (let i = 0; i < input.length; i++) {
      const item = input[i];
      const key = prefix ? `${prefix}[${i}]` : `[${i}]`;
      if (item !== null && typeof item === "object") {
        out.push(...flattenConfigObject(item, key));
      } else {
        out.push({ key, value: item, type: getTypeFullName(item) });
      }
    }
    return out;
  }

  if (typeof input === "object") {
    for (const k of Object.keys(input)) {
      const v = input[k];
      const key = prefix ? `${prefix}.${k}` : k;
      if (v !== null && typeof v === "object") {
        out.push(...flattenConfigObject(v, key));
      } else {
        out.push({ key, value: v, type: getTypeFullName(v) });
      }
    }
    return out;
  }

  // scalar
  out.push({ key: prefix, value: input, type: getTypeFullName(input) });
  return out;
}

function isAllowedChar(ch: string): boolean {
  const code = ch.charCodeAt(0);
  // alphanumeric
  if ((code >= 48 && code <= 57) || (code >= 65 && code <= 90) || (code >= 97 && code <= 122)) return true;
  // space, dot, dash, underscore
  if (ch === ' ' || ch === '.' || ch === '-' || ch === '_') return true;
  return false;
}

export function convertConfigToText(obj: any, options?: { removePunctuation?: boolean; includeTypeNames?: boolean }): string {
  const opts = { removePunctuation: true, includeTypeNames: true, ...(options ?? {}) };
  const flat = flattenConfigObject(obj, "");

  const sanitize = (val: string) => {
    if (!opts.removePunctuation) return val;
    let out = "";
    for (const ch of String(val)) {
      if (isAllowedChar(ch)) out += ch;
    }
    return out;
  };

  const lines = flat.map(item => {
    let val = "";
    if (item.value === null || item.value === undefined) {
      val = "";
    } else if (Array.isArray(item.value)) {
      val = item.value.join(", ");
    } else {
      val = String(item.value);
    }

    val = sanitize(val);
    if (opts.includeTypeNames) {
      return `${item.key} : ${val} (Type: ${item.type})`;
    }
    return `${item.key} : ${val}`;
  });

  return lines.join("\n");
}

export default { flattenConfigObject, convertConfigToText };
