from pathlib import Path
import yaml
from Projects.Tooling.validators.casing_linter.core.rules import classify_yaml_key
from Projects.Tooling.validators.validator_suite.utils import should_ignore

REGISTRY_ROOT = Path('Meta/registry')
SCHEMA_ROOT = Path('Meta/canonical/object.schemas')

def scan_yaml_file(path):
    issues = []
    data = yaml.safe_load(path.read_text())

    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                casing = classify_yaml_key(key)
                if casing.startswith('invalid'):
                    issues.append((path, key, casing))
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return issues

def scan_all_yaml():
    issues = []
    root = Path("Meta")

    for file in root.rglob("*.yaml"):
        if should_ignore(file):
            continue

    for root in (REGISTRY_ROOT, SCHEMA_ROOT):
        for file in root.rglob('*.yaml'):
            issues.extend(scan_yaml_file(file))

    return issues