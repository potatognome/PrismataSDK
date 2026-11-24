import shutil
from pathlib import Path
import yaml

ARCHIVE_ROOT = Path("Projects/Tooling/validators/bom_validator/archive")

def bump_version(path: Path) -> Path:
    stem = path.stem
    if ".v" in stem:
        base, v = stem.rsplit(".v", 1)
        new_stem = f"{base}.v{int(v)+1}"
    else:
        new_stem = f"{stem}.v2"
    return path.with_name(new_stem + path.suffix)

def remove_bom(path: Path) -> Path:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, ARCHIVE_ROOT / path.name)

    with open(path, "rb") as f:
        raw = f.read()

    # Strip BOM if present
    if raw.startswith(b"\xEF\xBB\xBF"):
        raw = raw[3:]

    new_path = bump_version(path)

    # Write clean UTF-8 (no BOM)
    with open(new_path, "w", encoding="utf-8") as f:
        f.write(raw.decode("utf-8"))

    return new_path

def fix_key(key):
    if '-' in key:
        return key.lower().replace('_', '-')
    if '_' in key:
        return key.lower().replace('-', '_')
    return key.lower()

def fix_yaml_file(path):
    data = yaml.safe_load(path.read_text())

    def fix(obj):
        if isinstance(obj, dict):
            new = {}
            for key, value in obj.items():
                new_key = fix_key(key)
                new[new_key] = fix(value)
            return new
        elif isinstance(obj, list):
            return [fix(item) for item in obj]
        return obj

    fixed = fix(data)

    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, ARCHIVE_ROOT / path.name)

    new_path = bump_version(path)
    new_path.write_text(yaml.dump(fixed, sort_keys=False))

    return new_path
