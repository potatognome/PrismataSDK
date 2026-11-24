from pathlib import Path
import yaml

SCHEMA_ROOT = Path("Meta/canonical/object.schemas")

def load_schema(name: str):
    file = SCHEMA_ROOT / f"{name}.schema.yaml"
    if file.exists():
        return yaml.safe_load(file.read_text())
    return None

def load_all_schemas():
    schemas = {}
    for file in SCHEMA_ROOT.glob("*.schema.yaml"):
        name = file.name.split(".")[0]
        schemas[name] = yaml.safe_load(file.read_text())
    return schemas
