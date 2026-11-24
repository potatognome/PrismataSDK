import { execSync } from "child_process";

export type DialogKind = "file" | "folder";

function runPowerShell(command: string): string | null {
  try {
    const output = execSync(`powershell -NoProfile -Command "${command.replace(/"/g, '\\"')}"`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    }).trim();
    return output || null;
  } catch {
    return null;
  }
}

export function pickNativePath(kind: DialogKind): string | null {
  if (process.platform !== "win32") {
    return null;
  }

  if (kind === "file") {
    const command = [
      "Add-Type -AssemblyName System.Windows.Forms;",
      "$dlg = New-Object System.Windows.Forms.OpenFileDialog;",
      "$dlg.CheckFileExists = $true;",
      "if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $dlg.FileName }",
    ].join(" ");
    return runPowerShell(command);
  }

  const command = [
    "Add-Type -AssemblyName System.Windows.Forms;",
    "$dlg = New-Object System.Windows.Forms.FolderBrowserDialog;",
    "if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $dlg.SelectedPath }",
  ].join(" ");

  return runPowerShell(command);
}

export function pickNativeSavePath(defaultFilename: string = "universe-output.json"): string | null {
  if (process.platform !== "win32") {
    return null;
  }

  const safeName = defaultFilename.replace(/'/g, "''");
  const command = [
    "Add-Type -AssemblyName System.Windows.Forms;",
    "$dlg = New-Object System.Windows.Forms.SaveFileDialog;",
    `$dlg.FileName = '${safeName}';`,
    "$dlg.Filter = 'JSON files (*.json)|*.json|All files (*.*)|*.*';",
    "$dlg.DefaultExt = 'json';",
    "if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $dlg.FileName }",
  ].join(" ");

  return runPowerShell(command);
}
