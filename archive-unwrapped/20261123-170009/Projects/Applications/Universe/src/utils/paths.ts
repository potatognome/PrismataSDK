import * as path from "path";

export function resolvePrismataRoot(): string {
  // Climb to the repository root (Prismata) so callers can resolve
  // top-level sibling directories like `.workspace` correctly.
  return path.resolve(__dirname, "../../../../../");
}

export function capabilityArgsFor(capabilityId: string, universePaths: any): Record<string, unknown> {
  const runtimeCreateDir = path.join(universePaths.workspaceRoot, "create-tests");
  const runtimeSemanticDir = path.join(universePaths.workspaceRoot, "semantic");
  const runtimeManifestPath = path.join(runtimeCreateDir, "dummy.manifest.yaml");

  switch (capabilityId) {
    case "prismata.universe.capability.fs-create-from-object":
      return {
        filePath: runtimeManifestPath,
        name: "Universe Test Panel",
      };

    case "prismata.universe.capability.fs-edit-vile":
      return {
        filePath: runtimeManifestPath,
        content: [
          "id: prismata.universe.test.manifest",
          "name: Universe Test Panel",
          "version: 0.0.2",
          "kind: module",
          "",
        ].join("\n"),
        newContent: [
          "id: prismata.universe.test.manifest",
          "name: Universe Test Panel",
          "version: 0.0.2",
          "kind: module",
          "",
        ].join("\n"),
        mode: "vile",
      };

    case "prismata.universe.capability.semantic-primitive-extract":
      return {
        primitive: "tooling.vile",
        family: "tooling",
      };

    case "prismata.universe.capability.semantic-dependency-graph":
      return {
        nodes: ["tooling.vile", "module.vaultguard"],
        edges: [["tooling.vile", "module.vaultguard"]],
      };

    case "prismata.universe.capability.semantic-bundle":
      return {
        outputDir: runtimeSemanticDir,
        bundleName: "semantic-bundle.json",
      };

    default:
      return {};
  }
}
