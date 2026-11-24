import yaml
from .utils import find_field

def extract_dependencies_from_schema(schema):
    deps = []
    for field in schema.get("fields", []):
        f_type = field.get("type")
        f_name = field.get("name")
        required = field.get("required", False)

        if f_type == "string":
            deps.append({"field": f_name, "type": "single", "required": required})
        elif f_type == "array":
            deps.append({"field": f_name, "type": "list", "required": required})
    return deps

def analyze_manifest(manifest_file, deps, registry):
    data = yaml.safe_load(manifest_file.read_text())
    out = []
    out.append(f"Dependency Graph for {manifest_file.name}")
    out.append("------------------------------------------------------------")

    for dep in deps:
        field = dep["field"]
        dtype = dep["type"]
        required = dep["required"]

        value = find_field(data, field)

        if value is None:
            fallback = "(fallback applies)" if not required else "(missing required dependency)"
            out.append(f"  ├─ {field}: ✘ missing {fallback}")
            continue

        if dtype == "single":
            if value in registry:
                out.append(f"  ├─ {field}: ✔ {value} loaded")
            else:
                out.append(f"  ├─ {field}: ✘ {value} missing (fallback applies)")
        elif dtype == "list":
            out.append(f"  ├─ {field}:")
            for ref in value:
                if ref in registry:
                    out.append(f"  │   ├─ {ref}: ✔ loaded")
                else:
                    out.append(f"  │   ├─ {ref}: ✘ missing (fallback applies)")

    return "\n".join(out)
