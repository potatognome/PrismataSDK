# ConfigMerge Module

Deterministic configuration merge engine with conflictMode precedence.

## Features
- Merge order: Defaults â†’ Mode â†’ Config â†’ Style â†’ CLI
- Array union merging
- Scalar overwrite
- No null erasure
- Deterministic output
- ConflictMode: removeWins, includeWins, unionWins

## Files
- ConfigMerge.psm1
- ConfigMerge.Tests.ps1
- ConfigMerge.schema.yaml
- examples/


## Usage
```powershell
Import-Module ConfigMerge

$settings = Merge-Config -Defaults $d -Mode $m -Config $c -Style $s -Cli $cli
