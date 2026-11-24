import sys
from pathlib import Path

# Add Prismata root to sys.path
ROOT = Path(__file__).resolve().parents[3]   # goes up to your repo root
print("")
print (f"Root Folder: {ROOT}")
print("")

sys.path.insert(0, str(ROOT))


from Projects.Applications.DependencyInspector.cli import run_cli
from Projects.Applications.DependencyInspector.gui import run_gui

if __name__ == "__main__":
    if "--gui" in sys.argv:
        run_gui()
    else:
        run_cli()
