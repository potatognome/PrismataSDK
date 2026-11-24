# Prismata UDI Tooling

Small toolkit for scanning, validating, and proposing deterministic UDIs for Prismata artifacts.

Usage (development):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
python -m uditool.cli scan --help
```

All generated tooling lives under `Projects/Tooling/udi`.
