// Recursive API scanner 
import * as fs from "fs";
import * as path from "path";

export interface APIScanResult {
  udi: string;
  root_path: string;
  files_scanned: string[];
  external_apis: any[];
  functions: any[];
}

function deriveScanUdi(rootPath: string): string {
  const slug = rootPath
    .toLowerCase()
    .replace(/\\/g, "/")
    .replace(/[^a-z0-9/]/g, "-")
    .replace(/\/+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 64);
  return `prismata.astalyzer.scan-result.${slug}`;
}

export function scanAPIsRecursive(root: string): APIScanResult {
  const files: string[] = [];

  function walk(p: string) {
    const stat = fs.statSync(p);
    if (stat.isDirectory()) {
      for (const entry of fs.readdirSync(p)) {
        walk(path.join(p, entry));
      }
    } else {
      files.push(p);
    }
  }

  walk(root);

  return {
    udi: deriveScanUdi(path.resolve(root)),
    root_path: root,
    files_scanned: files,
    external_apis: [],
    functions: [],
  };
}
