import ast
import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any


# ---------- Data models ----------

@dataclass
class ArgumentInfo:
    name: str
    type: Optional[str]


@dataclass
class FunctionInfo:
    name: str
    inputs: List[ArgumentInfo]
    outputs: Optional[str]
    is_method: bool = False
    is_exported: bool = False


@dataclass
class ClassInfo:
    name: str
    bases: List[str]
    methods: List[FunctionInfo] = field(default_factory=list)
    is_exported: bool = False


@dataclass
class ModuleInfo:
    file_path: str
    module_name: str
    imports_internal: List[str] = field(default_factory=list)
    imports_external: List[str] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)


# ---------- Helpers ----------

def parse_signature(node: ast.FunctionDef) -> FunctionInfo:
    """Extract function/method arguments and return annotation."""
    args: List[ArgumentInfo] = []

    # Positional args
    for arg in node.args.args:
        annotation = ast.unparse(arg.annotation) if arg.annotation else None
        args.append(ArgumentInfo(name=arg.arg, type=annotation))

    # *args
    if node.args.vararg:
        annotation = ast.unparse(node.args.vararg.annotation) if node.args.vararg.annotation else None
        args.append(ArgumentInfo(name="*" + node.args.vararg.arg, type=annotation))

    # **kwargs
    if node.args.kwarg:
        annotation = ast.unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else None
        args.append(ArgumentInfo(name="**" + node.args.kwarg.arg, type=annotation))

    returns = ast.unparse(node.returns) if node.returns else None

    return FunctionInfo(
        name=node.name,
        inputs=args,
        outputs=returns,
    )


def is_public_name(name: str) -> bool:
    return not name.startswith("_")


def guess_module_name(root: str, file_path: str) -> str:
    rel = os.path.relpath(file_path, root)
    rel_no_ext = os.path.splitext(rel)[0]
    parts = []
    for part in rel_no_ext.split(os.sep):
        if part == "__init__":
            continue
        parts.append(part)
    return ".".join(parts) if parts else os.path.basename(root)


def classify_import(module: Optional[str], level: int, project_root_name: str) -> str:
    """
    Very simple heuristic:
    - Relative imports (level > 0) => internal
    - Absolute imports starting with project root name => internal
    - Everything else => external
    """
    if level and level > 0:
        return "internal"
    if module and module.split(".")[0] == project_root_name:
        return "internal"
    return "external"


# ---------- AST Analyzer ----------

class ModuleAnalyzer(ast.NodeVisitor):
    def __init__(self, module_info: ModuleInfo, project_root_name: str):
        self.module_info = module_info
        self.project_root_name = project_root_name
        self.current_class: Optional[ClassInfo] = None
        self.explicit_exports: Optional[List[str]] = None

    # Imports

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            module = alias.name
            kind = classify_import(module, level=0, project_root_name=self.project_root_name)
            if kind == "internal":
                self.module_info.imports_internal.append(module)
            else:
                self.module_info.imports_external.append(module)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        kind = classify_import(module, level=node.level, project_root_name=self.project_root_name)
        target_list = self.module_info.imports_internal if kind == "internal" else self.module_info.imports_external
        full_name = ("." * node.level) + module if module else "." * node.level
        target_list.append(full_name)

    # Exports via __all__

    def visit_Assign(self, node: ast.Assign) -> None:
        # Look for __all__ = [...]
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    names = []
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            names.append(elt.value)
                    self.explicit_exports = names
        self.generic_visit(node)

    # Classes

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = []
        for base in node.bases:
            try:
                bases.append(ast.unparse(base))
            except Exception:
                bases.append(type(base).__name__)

        cls = ClassInfo(name=node.name, bases=bases)
        prev_class = self.current_class
        self.current_class = cls

        # Visit body to collect methods
        for body_item in node.body:
            self.visit(body_item)

        self.module_info.classes.append(cls)
        self.current_class = prev_class

    # Functions (both top-level and methods)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        fn = parse_signature(node)
        if self.current_class is not None:
            fn.is_method = True
            self.current_class.methods.append(fn)
        else:
            self.module_info.functions.append(fn)
        # Still walk into body if needed later
        self.generic_visit(node)

    # Finalization

    def finalize_exports(self) -> None:
        if self.explicit_exports is not None:
            self.module_info.exports = sorted(set(self.explicit_exports))
        else:
            # Fallback: public names from classes + functions
            names = [c.name for c in self.module_info.classes if is_public_name(c.name)]
            names += [f.name for f in self.module_info.functions if is_public_name(f.name)]
            self.module_info.exports = sorted(set(names))

        # Mark exported flags
        export_set = set(self.module_info.exports)
        for c in self.module_info.classes:
            c.is_exported = c.name in export_set
        for f in self.module_info.functions:
            f.is_exported = f.name in export_set


# ---------- Project scanning ----------

def analyze_file(root: str, file_path: str, project_root_name: str) -> ModuleInfo:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=file_path)
    module_name = guess_module_name(root, file_path)

    module_info = ModuleInfo(
        file_path=file_path,
        module_name=module_name,
    )

    analyzer = ModuleAnalyzer(module_info, project_root_name)
    analyzer.visit(tree)
    analyzer.finalize_exports()

    # Deduplicate imports
    module_info.imports_internal = sorted(set(module_info.imports_internal))
    module_info.imports_external = sorted(set(module_info.imports_external))

    return module_info


def scan_project(root: str) -> List[ModuleInfo]:
    root = os.path.abspath(root)

    # Allow scanning a single file (useful for file-picker based flows).
    if os.path.isfile(root):
        if not root.endswith(".py"):
            return []
        file_root = os.path.dirname(root) or os.getcwd()
        project_root_name = os.path.basename(file_root.rstrip(os.sep))
        return [analyze_file(file_root, root, project_root_name)]

    project_root_name = os.path.basename(root.rstrip(os.sep))
    results: List[ModuleInfo] = []

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            full_path = os.path.join(dirpath, filename)
            results.append(analyze_file(root, full_path, project_root_name))

    return results


# ---------- Entry point ----------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Powerful Python code analyzer (AST-based).")
    parser.add_argument("root", nargs="?", default=".", help="Project root directory")
    args = parser.parse_args()

    modules = scan_project(args.root)
    data = [asdict(m) for m in modules]
    print(json.dumps(data, indent=2))
