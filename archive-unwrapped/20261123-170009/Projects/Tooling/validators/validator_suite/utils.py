# Reserved for future shared utilities
# utils.py

IGNORE_FOLDERS = {
    "Projects/Tooling/validators/validator_suite",
    "Projects/Tooling/validators/casing_linter/archive",
    "Projects/Tooling/validators/bom_validator/archive",
    "Meta/deprecated",
    "archive",
    "backup"
}

def should_ignore(path):
    p = str(path).replace("\\", "/")
    return any(p.startswith(folder) for folder in IGNORE_FOLDERS)
