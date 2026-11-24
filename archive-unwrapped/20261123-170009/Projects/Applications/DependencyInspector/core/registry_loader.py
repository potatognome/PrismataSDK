from pathlib import Path
import yaml

REGISTRY_ROOT = Path("Meta/registry")

def load_registry():
    registry = {}
    for folder in REGISTRY_ROOT.glob("*"):
        if folder.is_dir() and folder.name.endswith(".d"):
            kind = folder.name.replace(".d", "")
            registry[kind] = {}
            for file in folder.glob("*.yaml"):
                try:
                    data = yaml.safe_load(file.read_text())
                    entry_id = data.get("id")
                    if entry_id:
                        registry[kind][entry_id] = {
                            "file": file,
                            "data": data
                        }
                except Exception:
                    pass
    return registry
