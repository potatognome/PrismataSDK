import argparse
from .core.schema_loader import load_schema, load_all_schemas
from .core.registry_loader import load_registry
from .core.dependency_extractor import extract_dependencies_from_schema, analyze_manifest

def run_cli():
    parser = argparse.ArgumentParser(description="Prismata Dependency Inspector")
    parser.add_argument("--schema", type=str, help="Schema name")
    parser.add_argument("--all", action="store_true", help="Scan all schemas")
    parser.add_argument("--report", type=str, help="Write output to a report file")

    args = parser.parse_args()

    registry = load_registry()
    results = []

    if args.schema:
        schema = load_schema(args.schema)
        if not schema:
            print(f"Schema '{args.schema}' not found.")
            return

        deps = extract_dependencies_from_schema(schema)
        folder = registry.get(args.schema, {})
        entry_id = registry.get("id", "")

        for entry_id, info in folder.items():
            results.append(analyze_manifest(info["file"], deps, registry))

    elif args.all:
        schemas = load_all_schemas()
        for schema_name, schema in schemas.items():
            deps = extract_dependencies_from_schema(schema)
            folder = registry.get(schema_name, {})
            for entry_id, info in folder.items():
                results.append(analyze_manifest(info["file"], deps, registry))

    else:
        print("Specify --schema <name> or --all")
        return

    output = "\n".join(results)
    print(output)

    if args.report:
        with open(args.report, "w") as f:
            f.write(output)
        print(f"Report written to {args.report}")
