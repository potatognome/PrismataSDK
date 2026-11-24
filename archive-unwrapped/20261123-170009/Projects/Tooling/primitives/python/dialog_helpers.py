"""
/Projects/Tooling/primitives/python/dialog_helpers.py
Reusable native file and folder selection helpers.
"""

from __future__ import annotations

import os
import platform
import subprocess
import shutil
from typing import Optional


def _pick_via_tk(kind: str) -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    try:
        root = tk.Tk()
        root.withdraw()
        root.update()
        if kind == "file":
            selected = filedialog.askopenfilename(title="Select file to scan")
        else:
            selected = filedialog.askdirectory(title="Select folder to scan")
        root.destroy()
        selected = (selected or "").strip()
        return selected or None
    except Exception:
        return None


def _pick_via_windows_dialog(kind: str) -> Optional[str]:
    if os.name != "nt":
        return None

    if kind == "file":
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$dlg = New-Object System.Windows.Forms.OpenFileDialog; "
            "$dlg.CheckFileExists = $true; "
            "if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $dlg.FileName }"
        )
    else:
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$dlg = New-Object System.Windows.Forms.FolderBrowserDialog; "
            "if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $dlg.SelectedPath }"
        )

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        out = (proc.stdout or "").strip()
        return out or None
    except Exception:
        return None


def _pick_via_macos_dialog(kind: str) -> Optional[str]:
    if platform.system().lower() != "darwin":
        return None

    if kind == "file":
        expr = 'POSIX path of (choose file with prompt "Select file to scan")'
    else:
        expr = 'POSIX path of (choose folder with prompt "Select folder to scan")'

    try:
        proc = subprocess.run(
            ["osascript", "-e", expr],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        out = (proc.stdout or "").strip()
        return out or None
    except Exception:
        return None


def _pick_via_linux_dialog(kind: str) -> Optional[str]:
    if platform.system().lower() != "linux":
        return None

    if kind == "file" and shutil.which("zenity"):
        cmd = ["zenity", "--file-selection"]
    elif kind == "folder" and shutil.which("zenity"):
        cmd = ["zenity", "--file-selection", "--directory"]
    elif kind == "file" and shutil.which("kdialog"):
        cmd = ["kdialog", "--getopenfilename"]
    elif kind == "folder" and shutil.which("kdialog"):
        cmd = ["kdialog", "--getexistingdirectory"]
    else:
        return None

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        out = (proc.stdout or "").strip()
        return out or None
    except Exception:
        return None


def pick_native_path(kind: str) -> Optional[str]:
    """Pick a file or folder using the best available native dialog."""
    if kind not in ("file", "folder"):
        raise ValueError("kind must be 'file' or 'folder'")

    for picker in (_pick_via_tk, _pick_via_windows_dialog, _pick_via_macos_dialog, _pick_via_linux_dialog):
        selected = picker(kind)
        if selected:
            return selected
    return None


def _save_via_tk(default_filename: str) -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    try:
        root = tk.Tk()
        root.withdraw()
        root.update()
        selected = filedialog.asksaveasfilename(
            title="Save output as",
            initialfile=default_filename,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        root.destroy()
        selected = (selected or "").strip()
        return selected or None
    except Exception:
        return None


def _save_via_windows_dialog(default_filename: str) -> Optional[str]:
    if os.name != "nt":
        return None

    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$dlg = New-Object System.Windows.Forms.SaveFileDialog; "
        f"$dlg.FileName = '{default_filename.replace("'", "''")}'; "
        "$dlg.Filter = 'JSON files (*.json)|*.json|All files (*.*)|*.*'; "
        "$dlg.DefaultExt = 'json'; "
        "if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $dlg.FileName }"
    )

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        out = (proc.stdout or "").strip()
        return out or None
    except Exception:
        return None


def _save_via_macos_dialog(default_filename: str) -> Optional[str]:
    if platform.system().lower() != "darwin":
        return None

    escaped = default_filename.replace('"', '\\"')
    expr = f'POSIX path of (choose file name default name "{escaped}" with prompt "Save output as")'

    try:
        proc = subprocess.run(
            ["osascript", "-e", expr],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        out = (proc.stdout or "").strip()
        return out or None
    except Exception:
        return None


def _save_via_linux_dialog(default_filename: str) -> Optional[str]:
    if platform.system().lower() != "linux":
        return None

    if shutil.which("zenity"):
        cmd = ["zenity", "--file-selection", "--save", "--confirm-overwrite", f"--filename={default_filename}"]
    elif shutil.which("kdialog"):
        cmd = ["kdialog", "--getsavefilename", ".", "JSON files (*.json)"]
    else:
        return None

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        out = (proc.stdout or "").strip()
        return out or None
    except Exception:
        return None


def pick_native_save_path(default_filename: str = "astalyzer-output.json") -> Optional[str]:
    """Pick a file path for saving output using the best available native dialog."""
    for picker in (_save_via_tk, _save_via_windows_dialog, _save_via_macos_dialog, _save_via_linux_dialog):
        selected = picker(default_filename)
        if selected:
            return selected
    return None


def select_scan_path(prompt_func) -> str:
    """Prompt for a scan target, using native dialogs when possible."""
    print("Scan target options:")
    print("1) Select folder (native picker)")
    print("2) Select file (native picker)")
    print("3) Enter path manually")
    print("4) Current directory (.)")

    choice = (prompt_func("Choose target option [1-4]") or "4").strip()
    if choice == "1":
        selected = pick_native_path("folder")
        if selected:
            return selected
        print("Native folder picker unavailable; falling back to manual input.")
        return (prompt_func("Folder path") or ".").strip() or "."
    if choice == "2":
        selected = pick_native_path("file")
        if selected:
            return selected
        print("Native file picker unavailable; falling back to manual input.")
        return (prompt_func("File path") or ".").strip() or "."
    if choice == "3":
        return (prompt_func("Scan path") or ".").strip() or "."
    return "."


def select_save_path(prompt_func, default_filename: str = "astalyzer-output.json") -> str:
    """Prompt for a save destination, using native dialogs when possible."""
    selected = pick_native_save_path(default_filename)
    if selected:
        return selected
    return (prompt_func("Destination path") or default_filename).strip() or default_filename