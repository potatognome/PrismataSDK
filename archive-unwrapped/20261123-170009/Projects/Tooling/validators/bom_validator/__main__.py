import sys
from pathlib import Path
# Add Prismata root to sys.path
ROOT = Path(__file__).resolve().parents[4]   # goes up to your repo root
print("")
print (f"Root Folder: {ROOT}")
print("")

sys.path.insert(0, str(ROOT))

from Projects.Tooling.validators.bom_validator.cli import run_cli

if __name__ == '__main__':
    run_cli()
