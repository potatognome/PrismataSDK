export type SelectionType =
  | "none"
  | "single"
  | "multi"
  | "heterogeneous"
  | "homogeneous";

export interface SelectedObject {
  id: string;
  udi?: string;
  type: string;
  version?: string;
  registryKey?: string;
  semanticKeys?: string[];
}

export interface SelectionState {
  selectionType: SelectionType;
  selectionCount: number;
  referenceObjectSelected: boolean;
  referenceObject?: SelectedObject;
  selectedObjects: SelectedObject[];
}

export interface CompatibilityMatrix {
  type_compatible: boolean;
  semantic_compatible: boolean;
  version_compatible: boolean;
  registry_compatible: boolean;
}

export interface SelectionLogicResult {
  state: SelectionState;
  compatibility: CompatibilityMatrix;
  visibleOperations: string[];
}

function classifySelection(selected: SelectedObject[]): SelectionType {
  if (selected.length === 0) return "none";
  if (selected.length === 1) return "single";

  const types = new Set(selected.map(o => o.type));
  return types.size === 1 ? "homogeneous" : "heterogeneous";
}

function buildCompatibilityMatrix(
  selected: SelectedObject[],
  reference?: SelectedObject
): CompatibilityMatrix {
  if (selected.length === 0) {
    return {
      type_compatible: false,
      semantic_compatible: false,
      version_compatible: false,
      registry_compatible: false,
    };
  }

  const types = new Set(selected.map(o => o.type));
  const typeCompatible =
    !reference || types.has(reference.type) || types.size === 1;

  const semanticCompatible = (() => {
    if (selected.length < 2) return false;
    const [first, ...rest] = selected;
    const baseKeys = new Set(first.semanticKeys ?? []);
    if (baseKeys.size === 0) return false;
    return rest.some(obj =>
      (obj.semanticKeys ?? []).some(k => baseKeys.has(k))
    );
  })();

  const versionCompatible = selected.some(o => !!o.version);
  const registryCompatible = selected.some(o => !!o.registryKey);

  return {
    type_compatible: typeCompatible,
    semantic_compatible: semanticCompatible,
    version_compatible: versionCompatible,
    registry_compatible: registryCompatible,
  };
}

function deriveVisibleOperations(
  selectionType: SelectionType,
  compatibility: CompatibilityMatrix,
  referenceSelected: boolean
): string[] {
  const ops: string[] = [];

  if (selectionType !== "none") {
    ops.push("prismata.universe.capability.fs-verify-multi");
    ops.push("prismata.universe.capability.fs-update-fields");
  }

  if (selectionType === "single") {
    ops.push("prismata.universe.capability.fs-create-from-object");
    ops.push("prismata.universe.capability.fs-edit-vile");
    if (compatibility.version_compatible) {
      ops.push("prismata.universe.capability.fs-update-version");
      ops.push("prismata.universe.capability.fs-version-apply");
    }
  }

  if (selectionType === "multi" || selectionType === "homogeneous" || selectionType === "heterogeneous") {
    ops.push("prismata.universe.capability.fs-edit-multi");
    if (compatibility.registry_compatible) {
      ops.push("prismata.universe.capability.fs-edit-registry-insert");
    }
    if (compatibility.version_compatible) {
      ops.push("prismata.universe.capability.fs-update-version");
      ops.push("prismata.universe.capability.fs-version-apply");
    }
  }

  if (selectionType === "heterogeneous") {
    ops.push("prismata.universe.capability.fs-verify-sequence");
  }

  if (selectionType === "homogeneous") {
    ops.push("prismata.universe.capability.fs-verify-collective");
  }

  if (referenceSelected && compatibility.type_compatible) {
    ops.push("prismata.universe.capability.fs-edit-conform");
    ops.push("prismata.universe.capability.fs-verify-reference");
  }

  if (compatibility.semantic_compatible) {
    ops.push("prismata.universe.capability.fs-diff-compatible");
  }

  return ops;
}

export function computeSelectionLogic(
  selectedObjects: SelectedObject[],
  referenceObject?: SelectedObject
): SelectionLogicResult {
  const selectionType = classifySelection(selectedObjects);

  const state: SelectionState = {
    selectionType,
    selectionCount: selectedObjects.length,
    referenceObjectSelected: !!referenceObject,
    referenceObject,
    selectedObjects,
  };

  const compatibility = buildCompatibilityMatrix(selectedObjects, referenceObject);

  const visibleOperations = deriveVisibleOperations(
    selectionType,
    compatibility,
    state.referenceObjectSelected
  );

  return {
    state,
    compatibility,
    visibleOperations,
  };
}
