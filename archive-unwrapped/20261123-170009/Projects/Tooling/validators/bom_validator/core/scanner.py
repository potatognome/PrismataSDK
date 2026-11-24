from pathlib import Path
from Projects.Tooling.validators.validator_suite.utils import should_ignore

BOM = b"\xEF\xBB\xBF"

def file_has_bom(path: Path) -> bool:
    with open(path, "rb") as f:
        return f.read(3) == BOM

def scan_yaml_for_bom(root: Path):
    issues = []
    for file in root.rglob("*.yaml"):
        if should_ignore(file):
            continue
        if file_has_bom(file):
            issues.append(file)
    return issues
