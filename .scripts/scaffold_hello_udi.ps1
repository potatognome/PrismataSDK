<#
    PrismataSDK Example Scaffolding Script
    Creates the hello_udi example module, capability, panes, menu,
    and two-pane UI framework using CMF envelopes.

    Safe:
    - Creates only missing folders
    - Does not overwrite existing files
    - Idempotent
#>

param(
    [string]$Root = "."
)

function Ensure-Folder {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
        Write-Host "Created: $Path"
    } else {
        Write-Host "Exists : $Path"
    }
}

function Ensure-File {
    param([string]$Path, [string]$Content)
    if (-not (Test-Path $Path)) {
        $Content | Out-File -FilePath $Path -Encoding utf8 -NoClobber
        Write-Host "Created: $Path"
    } else {
        Write-Host "Exists : $Path"
    }
}

Write-Host "=== Scaffolding hello_udi Example Module ==="

# Base example folders
$folders = @(
    "$Root/examples",
    "$Root/examples/manifests",
    "$Root/examples/manifests/hello_udi",
    "$Root/examples/capabilities",
    "$Root/examples/capabilities/hello_udi",
    "$Root/examples/registry",
    "$Root/examples/registry/panes",
    "$Root/examples/registry/menus",
    "$Root/examples/registry/ui_frameworks"
)

foreach ($folder in $folders) {
    Ensure-Folder -Path $folder
}

# 1. Module manifest
$manifestPath = "$Root/examples/manifests/hello_udi/manifest.yaml"
$manifestContent = @"
udi: prismata.example.module.hello_udi
kind: module
version: 1.0.0

capabilities:
  - udi: prismata.example.capability.hello_udi
    description: "Say hello to all related UDIs"
"@
Ensure-File -Path $manifestPath -Content $manifestContent

# 2. Capability CMF object
$capPath = "$Root/examples/capabilities/hello_udi/hello_udi.yaml"
$capContent = @"
udi: prismata.example.capability.hello_udi
kind: capability
version: 1.0.0

content:
  action: hello_udi
  max_depth: 10
"@
Ensure-File -Path $capPath -Content $capContent

# 3. Left-hand pane
$lhPanePath = "$Root/examples/registry/panes/lh_test_pane.yaml"
$lhPaneContent = @"
udi: prismata.example.pane.lh_test
kind: pane
version: 1.0.0

content:
  title: "Left Test Pane"
"@
Ensure-File -Path $lhPanePath -Content $lhPaneContent

# 4. Right-hand pane
$rhPanePath = "$Root/examples/registry/panes/rh_test_pane.yaml"
$rhPaneContent = @"
udi: prismata.example.pane.rh_test
kind: pane
version: 1.0.0

content:
  title: "Right Test Pane"
"@
Ensure-File -Path $rhPanePath -Content $rhPaneContent

# 5. Menu
$menuPath = "$Root/examples/registry/menus/test_menu.yaml"
$menuContent = @"
udi: prismata.example.menu.test_menu
kind: menu
version: 1.0.0

content:
  items:
    - key: "1"
      name: "Test LH Pane"
      action: execute
      capability: prismata.example.capability.hello_udi
      target_pane: prismata.example.pane.lh_test

    - key: "2"
      name: "Test RH Pane"
      action: execute
      capability: prismata.example.capability.hello_udi
      target_pane: prismata.example.pane.rh_test

    - key: "0"
      name: "Quit"
      action: exit
"@
Ensure-File -Path $menuPath -Content $menuContent

# 6. Two-pane UI framework
$frameworkPath = "$Root/examples/registry/ui_frameworks/two_pane.yaml"
$frameworkContent = @"
udi: prismata.example.ui_framework.two_pane
kind: ui_framework
version: 1.0.0

content:
  layout: two_pane
  panes:
    left: prismata.example.pane.lh_test
    right: prismata.example.pane.rh_test
  menu: prismata.example.menu.test_menu
"@
Ensure-File -Path $frameworkPath -Content $frameworkContent

Write-Host "=== hello_udi Example Module Scaffold Complete ==="
