import * as path from "path";
import {
  UiFramework,
  MenuDefinition,
  SchemaDefinition,
  injectFrameworkFromCapability,
  loadCapabilityFrameworkMapFromFile,
  loadMenuFromFile,
  loadSchemaFromFile,
  normalizeMenuItemFrameworks,
  normalizeViewName,
  validateMenuItemFrameworks,
} from "../../../../Tooling/primitives/typescript/menuLoaders";

export { UiFramework, MenuDefinition, SchemaDefinition };
export {
  injectFrameworkFromCapability,
  loadCapabilityFrameworkMapFromFile,
  normalizeMenuItemFrameworks,
  normalizeViewName,
  validateMenuItemFrameworks,
};

export function loadCapabilityFrameworkMap(prismataRoot: string): Record<string, UiFramework> {
  const file = path.join(prismataRoot, "config", "capability-framework.map.yaml");
  return loadCapabilityFrameworkMapFromFile(file);
}

export function loadMenu(id: string): MenuDefinition {
  const fileName = `${normalizeViewName(id)}-menu.yaml`;
  const fullPath = path.join(__dirname, "../../config/project-menus", fileName);
  return loadMenuFromFile(fullPath);
}

export function loadSchema(id: string): SchemaDefinition {
  const schemaId = id.replace("prismata.universe.menu.", "prismata.universe.schema.");
  const fileName = `${normalizeViewName(id)}.yaml`;
  const fullPath = path.join(__dirname, "../../config/schemas", fileName);
  return loadSchemaFromFile(fullPath, schemaId);
}
