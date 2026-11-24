import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import { loadUniverseUiFrameworksConfig } from "../../../Tooling/primitives/typescript/uiInterfaceLoader";
import { resolvePrismataRoot } from "../src/utils/paths";

test("uiInterfaceLoader logs warnings when mocked validator fails", () => {
  const prismataRoot = resolvePrismataRoot();
  const nm = path.join(prismataRoot, "node_modules");
  const ajvDir = path.join(nm, "ajv");
  const jsyamlDir = path.join(nm, "js-yaml");

  try {
    fs.mkdirSync(ajvDir, { recursive: true });
    fs.mkdirSync(jsyamlDir, { recursive: true });

    // Minimal mocked Ajv that fails validation for ui_framework === 'multi_pane'
    const ajvIndex = `module.exports = function Ajv(opts) {
  return {
    compile: function(schema) {
      function validate(payload) {
        if (payload && payload.ui_framework === 'multi_pane') {
          validate.errors = [{ message: 'mocked invalid ui_framework' }];
          return false;
        }
        return true;
      }
      validate.errors = null;
      return validate;
    }
  };
};`;
    fs.writeFileSync(path.join(ajvDir, "index.js"), ajvIndex, "utf8");

    // Minimal mocked js-yaml that returns an empty object for schema loads
    const jsyamlIndex = `exports.load = function(text) { try { return JSON.parse(text); } catch(e) { return {}; } }`;
    fs.writeFileSync(path.join(jsyamlDir, "index.js"), jsyamlIndex, "utf8");

    const warnings: string[] = [];
    const origWarn = console.warn;
    console.warn = (msg?: any, ...args: any[]) => {
      warnings.push(String(msg) + (args.length ? ` ${args.join(' ')}` : ''));
    };

    try {
      // Run the loader which will attempt to require our mocked modules
      const cfg = loadUniverseUiFrameworksConfig(prismataRoot);

      // Our mock Ajv returns false for ui_framework === 'multi_pane', so we
      // expect at least one warning message to have been emitted.
      assert.ok(warnings.length > 0, 'Expected validation warnings to be emitted');
      const joined = warnings.join(' ');
      assert.ok(
        joined.includes('mocked invalid') || joined.toLowerCase().includes('ui_framework'),
        `Unexpected warning contents: ${joined}`
      );
    } finally {
      console.warn = origWarn;
    }
  } finally {
    // Clean up only the mocks we created
    try {
      fs.rmSync(ajvDir, { recursive: true, force: true });
    } catch (e) {
      // ignore
    }
    try {
      fs.rmSync(jsyamlDir, { recursive: true, force: true });
    } catch (e) {
      // ignore
    }
  }
});
