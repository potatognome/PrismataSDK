param(
    [Parameter(Mandatory=$true)]
    [string]$input,

    [Parameter(Mandatory=$true)]
    [string]$output,

    [string]$config = "",
    [string]$include = "",
    [string]$exclude = "",
    [string]$skipFolders = "",
    [switch]$relative
)

# -----------------------------------------
# Resolve script root
# -----------------------------------------
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# -----------------------------------------
# Load config if provided
# -----------------------------------------
function Load-Yaml($path) {
    if (Get-Command ConvertFrom-Yaml -ErrorAction SilentlyContinue) {
        return ConvertFrom-Yaml (Get-Content $path -Raw)
    }
    throw "YAML parser not available. Install powershell-yaml or use CLI args."
}

$configData = $null
if ($config -ne "") {
    $configPath = (Resolve-Path $config).Path
    $configData = Load-Yaml $configPath
}

# -----------------------------------------
# Defaults
# -----------------------------------------
$defaultInclude = @(".ts", ".json", ".yaml")
$defaultExclude = @(".log", ".tmp", ".cache")
$defaultSkip    = @("node_modules", ".git", "dist", "build", ".workspace")

# -----------------------------------------
# Merge config + CLI overrides
# -----------------------------------------
$includeList = if ($include -ne "") { $include.Split(",") } elseif ($configData) { $configData.extensionRules.include } else { $defaultInclude }
$excludeList = if ($exclude -ne "") { $exclude.Split(",") } elseif ($configData) { $configData.extensionRules.exclude } else { $defaultExclude }
$skipList    = if ($skipFolders -ne "") { $skipFolders.Split(",") } elseif ($configData) { $configData.folderSummaryRules } else { $defaultSkip }

# -----------------------------------------
# Resolve input/output paths
# -----------------------------------------
if ($relative) {
    $workspaceRoot = Split-Path -Parent $scriptRoot
    $inputRoot  = Join-Path $workspaceRoot $input
    $outputRoot = Join-Path $workspaceRoot $output
} else {
    $inputRoot  = (Resolve-Path $input).Path
    $outputRoot = (Resolve-Path $output).Path
}

New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

# -----------------------------------------
# Helper: extension filter
# -----------------------------------------
function ShouldIncludeExtension($filePath) {
    $ext = [System.IO.Path]::GetExtension($filePath)
    if ($includeList -contains $ext) { return $true }
    if ($excludeList -contains $ext) { return $false }
    return $true
}

# -----------------------------------------
# Helper: skip folder check
# -----------------------------------------
function ShouldSkipFolder($folderPath) {
    $folderName = Split-Path $folderPath -Leaf
    return $skipList -contains $folderName
}

# -----------------------------------------
# Helper: folder summary generator
# -----------------------------------------
function SummarizeFolder($folderPath) {
    $files = Get-ChildItem -Recurse $folderPath -File
    $summary = @{}

    foreach ($f in $files) {
        $ext = [System.IO.Path]::GetExtension($f.FullName)
        if (-not $summary.ContainsKey($ext)) { $summary[$ext] = 0 }
        $summary[$ext]++
    }

    $output = "SUMMARY FOR FOLDER: $folderPath`n"
    $output += "Total files: $($files.Count)`n"
    $output += "By extension:`n"

    foreach ($key in $summary.Keys) {
        $output += "  $key : $($summary[$key])`n"
    }

    return $output
}

# -----------------------------------------
# Annotation output file
# -----------------------------------------
$annotationFile = Join-Path $outputRoot "folder-annotation.txt"
"" | Out-File $annotationFile

"================ DIRECTORY TREE ================" | Out-File $annotationFile -Append
tree $inputRoot /f | Out-File $annotationFile -Append

"================ FILE CONTENTS ================" | Out-File $annotationFile -Append

# -----------------------------------------
# Annotation engine
# -----------------------------------------
Get-ChildItem -Recurse $inputRoot | ForEach-Object {

    if ($_.PSIsContainer) {
        if (ShouldSkipFolder $_.FullName) {
            SummarizeFolder $_.FullName | Out-File $annotationFile -Append
        }
        return
    }

    if (-not (ShouldIncludeExtension $_.FullName)) {
        return
    }

    "------------------------------------------------------------" | Out-File $annotationFile -Append
    "FILE: $($_.FullName)" | Out-File $annotationFile -Append
    "------------------------------------------------------------" | Out-File $annotationFile -Append

    Get-Content $_.FullName | Out-File $annotationFile -Append
    "`n" | Out-File $annotationFile -Append
}

Write-Host "Annotation complete."
Write-Host "Annotation file written to: $annotationFile"
