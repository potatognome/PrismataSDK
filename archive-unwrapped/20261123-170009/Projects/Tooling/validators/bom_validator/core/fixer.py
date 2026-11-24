import shutil
from pathlib import Path

ARCHIVE_ROOT = Path('Projects/Tooling/validators/bom_validator/archive')

def bump_version(path: Path) -> Path:
    stem = path.stem
    if '.v' in stem:
        base, v = stem.rsplit('.v', 1)
        new_stem = f'{base}.v{int(v)+1}'
    else:
        new_stem = f'{stem}.v2'
    return path.with_name(new_stem + path.suffix)

def remove_bom(path: Path) -> Path:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, ARCHIVE_ROOT / path.name)

    with open(path, 'rb') as f:
        raw = f.read()

    if raw.startswith(b'\xEF\xBB\xBF'):
        raw = raw[3:]

    new_path = bump_version(path)

    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(raw.decode('utf-8'))

    return new_path
