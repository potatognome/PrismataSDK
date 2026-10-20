from pathlib import Path

base = Path(__file__).resolve().parents[1] / "examples" / "registry"
print('base:', base)
print('exists:', base.exists())
files = list(base.rglob('*.yaml'))
print('count:', len(files))
for f in files[:20]:
    print(f)
