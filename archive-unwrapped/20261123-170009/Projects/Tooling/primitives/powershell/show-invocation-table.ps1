<#
.SYNOPSIS
  Render a command invocation as a human-friendly table or machine-friendly JSON.

.DESCRIPTION
  `Show-InvocationTable` accepts a hashtable, PSCustomObject, or array of name/value entries
  and prints a formatted table showing parameter names, values, and types. It also supports
  a `-Format json` mode that emits a JSON array for automation.

.PARAMETER Args
  The arguments to display. Accepts a hashtable (`[ordered]@{}` recommended), PSCustomObject,
  or an array of objects with `Name`/`Value` properties.

.PARAMETER Title
  Title text printed above the table.

.PARAMETER Width
  Maximum total width used for layout. Defaults to 80.

.PARAMETER ShowMode
  Which parameters to show: `Provided` (default), `Eligible`, or `Both`.

.PARAMETER EligibleParams
  Optional array of param descriptors (Name, Default, Type, Help) used when showing eligible set.

.PARAMETER Format
  `table` (default) or `json` or `compact`.

.EXAMPLE
  . .\show-invocation-table.ps1
  Show-InvocationTable -Args $PSBoundParameters -Title 'Invocation' -Format table
#>
function Show-InvocationTable {
    param(
        [Parameter(Mandatory=$true)][object]$InvocationArgs,
        [string]$Title = 'Command Invocation',
        [string]$InvocationLine = $null,
        [int]$Width = 80,
        [ValidateSet('Provided','Eligible','Both')][string]$ShowMode = 'Provided',
        [object[]]$EligibleParams,
        [switch]$AutoDiscoverEligible,
        [ValidateSet('table','json','compact')][string]$Format = 'table',
        [switch]$ShowMeta,
        [int]$MaxValueWidth = 60,
        [switch]$Wrap,
        [switch]$ShowTypes,
        [switch]$ShowEmpty
    )

    # Helper: convert inputs to normalized entries
    function Convert-ToEntriesInner {
        param($Input)
        $entries = @()
        if ($null -eq $Input) { return $entries }

        if ($Input -is [System.Collections.IDictionary]) {
            foreach ($k in $Input.Keys) {
                $v = $Input[$k]
                 if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { $disp = ($v | ForEach-Object { $_ }) -join ',' } else { $disp = $v }
                $type = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
                 $entries += [PSCustomObject]@{ Name = [string]$k; Value = $disp; Type = $type; Provided = $true; Default = $null }
            }
            return $entries
        }

        if ($Input -is [System.Management.Automation.PSCustomObject]) {
            $props = $Input | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name
            foreach ($p in $props) {
                $v = $Input.$p
                 if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { $disp = ($v | ForEach-Object { $_ }) -join ',' } else { $disp = $v }
                $type = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
                 $entries += [PSCustomObject]@{ Name = [string]$p; Value = $disp; Type = $type; Provided = $true; Default = $null }
            }
            return $entries
        }

        if ($Input -is [System.Array]) {
            foreach ($item in $Input) {
                if ($item -is [System.Management.Automation.PSCustomObject] -and $item.PSObject.Properties.Name -contains 'Name') {
                    $name = $item.Name
                    $val = $item.Value
                        if ($val -is [System.Collections.IEnumerable] -and -not ($val -is [string])) { $dispVal = ($val | ForEach-Object { $_ }) -join ',' } else { $dispVal = $val }
                    $type = if ($null -ne $item.Type) { $item.Type } elseif ($null -ne $val) { $val.GetType().Name } else { 'Null' }
                    $providedFlag = if ($item.PSObject.Properties.Name -contains 'Provided') { $item.Provided } else { $true }
                    $defaultVal = if ($item.PSObject.Properties.Name -contains 'Default') { $item.Default } else { $null }
                        $entries += [PSCustomObject]@{ Name = [string]$name; Value = $dispVal; Type = $type; Provided = $providedFlag; Default = $defaultVal }
                }
            }
            return $entries
        }

        # Handle IEnumerable enumerators (OrderedDictionary, Hashtable enumerator, etc.)
        if ($Input -is [System.Collections.IEnumerable] -and -not ($Input -is [string])) {
            foreach ($it in $Input) {
                if ($it -is [System.Collections.DictionaryEntry]) {
                    $k = $it.Key; $v = $it.Value
                        if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { $disp = ($v | ForEach-Object { $_ }) -join ',' } else { $disp = $v }
                    $t = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
                        $entries += [PSCustomObject]@{ Name = [string]$k; Value = $disp; Type = $t; Provided = $true; Default = $null }
                } elseif ($it.PSObject -and $it.PSObject.Properties.Name -contains 'Key' -and $it.PSObject.Properties.Name -contains 'Value') {
                    $k = $it.Key; $v = $it.Value
                        if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { $disp = ($v | ForEach-Object { $_ }) -join ',' } else { $disp = $v }
                    $t = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
                        $entries += [PSCustomObject]@{ Name = [string]$k; Value = $disp; Type = $t; Provided = $true; Default = $null }
                }
            }
            if ($entries.Count -gt 0) { return $entries }
        }

        # Fallback: return a single-entry with default name
        return ,([PSCustomObject]@{ Name = 'Args'; Value = $Input; Type = if ($null -ne $Input) { $Input.GetType().Name } else { 'Null' }; Provided = $true; Default = $null })
    }

    function Get-ParamsFromScript {
        param([string]$ScriptPath)
        $out = @()
        if (-not $ScriptPath) { return $out }
        if (-not (Test-Path $ScriptPath)) { return $out }
        $content = Get-Content -Raw -Path $ScriptPath -ErrorAction SilentlyContinue
        if (-not $content) { return $out }
        $m = [System.Text.RegularExpressions.Regex]::Match($content, 'param\s*\((.*?)\)', [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if (-not $m.Success) { return $out }
        $paramText = $m.Groups[1].Value
        # normalize and split by commas
        $paramText = $paramText -replace "`r?`n", ' '
        $tokens = $paramText -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
        foreach ($t in $tokens) {
            # remove attribute blocks with parentheses like [Parameter(...)] but keep simple type annotations like [string]
            $s = $t -replace '\[[^\]]*\([^\]]*\)\]', ''
            $s = $s.Trim()
            # match [type]$name = default OR $name = default OR [type]$name
            $rx = '^(?:\s*\[(?<type>[^\]]+)\]\s*)?\$?(?<name>[A-Za-z0-9_]+)(?:\s*=\s*(?<default>.*))?$'
            $mm = [System.Text.RegularExpressions.Regex]::Match($s, $rx)
            if ($mm.Success) {
                $name = $mm.Groups['name'].Value
                $type = $mm.Groups['type'].Value
                if (-not $type) { $type = 'Unknown' }
                $default = $mm.Groups['default'].Value
                if ($default) {
                    $default = $default.Trim()
                    # strip trailing parentheses or trailing tokens
                    $default = $default.TrimEnd(')')
                    $default = $default.Trim()
                    $default = $default.Trim('"','''')
                } else { $default = $null }
                $out += [PSCustomObject]@{ Name = $name; Type = $type; Default = $default }
            }
        }
        return $out
    }

    function Show-TableInner {
        param($entries, $ShowTypesFlag, $WidthVal, $WrapFlag, $TitleVal, $InvocationLineVal)

        # compute widths
        $nameWidth = ([int](($entries | Select-Object -ExpandProperty Name | ForEach-Object { $_.Length } | Measure-Object -Maximum).Maximum))
        if ($nameWidth -lt 8) { $nameWidth = 8 }
        if ($nameWidth -gt 30) { $nameWidth = 30 }
        $typeWidth = if ($ShowTypesFlag) { 12 } else { 0 }
        $providedWidth = if ($ShowMeta) { 9 } else { 0 }
        $defaultWidth = if ($ShowMeta) { 20 } else { 0 }
        $metaWidth = $providedWidth + $defaultWidth
        if ($ShowMeta) { $metaWidth += 2 }
        $padding = 6
        $valueWidth = $WidthVal - $nameWidth - $typeWidth - $metaWidth - $padding
        if ($valueWidth -lt 20) { $valueWidth = 20 }

        # Raw invocation line (if provided)
        if ($InvocationLineVal) { Write-Host "Invocation: $InvocationLineVal" -ForegroundColor DarkGray }

        # Header
        Write-Host $TitleVal -ForegroundColor Cyan
        # Columns: Param-Arg, Type, Provided, Default, Value
        $hdr = ('{0,-' + $nameWidth + '}  {1,-' + $typeWidth + '}  {2,-' + $providedWidth + '}  {3,-' + $defaultWidth + '}  {4,-' + $valueWidth + '}')
        $colLabels = @('Param-Arg','Type','Provided','Default','Value')
        Write-Host ($hdr -f $colLabels) -ForegroundColor Yellow
        Write-Host ('-' * ($WidthVal)) -ForegroundColor DarkGray

        foreach ($e in $entries) {
            $name = $e.Name
            $val = if ($null -eq $e.Value) { '<null>' } else { $e.Value.ToString() }
            # Sanitize display strings if helper is available
            $sanitizer = Join-Path $PSScriptRoot 'sanitize-output.ps1'
            if (Test-Path $sanitizer) { . $sanitizer }
            try { $val = Sanitize-DisplayString $val } catch {}
            $type = if ($ShowTypesFlag) { $e.Type } else { '' }
            if (-not $WrapFlag -and $val.Length -gt $valueWidth) {
                $val = $val.Substring(0, $valueWidth - 1) + '...'
            }
            # multiline values: split on newlines and print subsequent lines indented under Value column
            $lines = $val -split "`n"
            $first = $lines[0]
            $prov = if ($e.PSObject.Properties.Name -contains 'Provided') { $e.Provided } else { $true }
            $def = if ($e.PSObject.Properties.Name -contains 'Default') { $e.Default } else { '' }
            $typeVal = if ($ShowTypesFlag) { $e.Type } else { '' }
            # Print in order: Name, Type, Provided, Default, Value
            Write-Host ($hdr -f $name, $typeVal, $prov, $def, $first) -ForegroundColor Gray
            if ($lines.Count -gt 1) {
                for ($i = 1; $i -lt $lines.Count; $i++) {
                    $ln = $lines[$i]
                    $padLength = $nameWidth + 2 + $typeWidth + 2 + $providedWidth + 2 + $defaultWidth + 2
                    $pad = ' ' * $padLength
                    try { $ln = Sanitize-DisplayString $ln } catch {}
                    if (-not $WrapFlag -and $ln.Length -gt $valueWidth) { $ln = $ln.Substring(0, $valueWidth - 1) + '...' }
                    Write-Host ($pad + $ln) -ForegroundColor DarkGray
                }
            }
        }
    }

    # Normalize provided args (handle OrderedDictionary and related types directly)
    $provided = @()
    if ($InvocationArgs -ne $null -and ($InvocationArgs -is [System.Collections.IDictionary] -or $InvocationArgs.GetType().FullName -eq 'System.Collections.Specialized.OrderedDictionary')) {
        foreach ($k in $InvocationArgs.Keys) {
            $v = $InvocationArgs[$k]
              if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { $disp = ($v | ForEach-Object { $_ }) -join ',' } else { $disp = $v }
            $t = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
              $provided += [PSCustomObject]@{ Name = [string]$k; Value = $disp; Type = $t; Provided = $true; Default = $null }
        }
    } elseif ($InvocationArgs -is [System.Management.Automation.PSCustomObject]) {
        $props = $InvocationArgs | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name
        foreach ($p in $props) {
            $v = $InvocationArgs.$p
              if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { $disp = ($v | ForEach-Object { $_ }) -join ',' } else { $disp = $v }
            $t = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
              $provided += [PSCustomObject]@{ Name = [string]$p; Value = $disp; Type = $t; Provided = $true; Default = $null }
        }
    } elseif ($InvocationArgs -is [System.Array]) {
        foreach ($item in $InvocationArgs) {
                if ($item -is [System.Management.Automation.PSCustomObject] -and $item.PSObject.Properties.Name -contains 'Name') {
                $name = $item.Name; $val = $item.Value
                $t = if ($null -ne $item.Type) { $item.Type } elseif ($null -ne $val) { $val.GetType().Name } else { 'Null' }
                if ($item.PSObject.Properties.Name -contains 'Provided') { $pf = $item.Provided } else { $pf = $true }
                if ($item.PSObject.Properties.Name -contains 'Default') { $df = $item.Default } else { $df = $null }
                $provided += [PSCustomObject]@{ Name = [string]$name; Value = $val; Type = $t; Provided = $pf; Default = $df }
            }
        }
    } elseif ($InvocationArgs -is [System.Collections.IEnumerable] -and -not ($InvocationArgs -is [string])) {
        foreach ($it in $InvocationArgs) {
            if ($it -is [System.Collections.DictionaryEntry]) {
                $k = $it.Key; $v = $it.Value
                    if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { $disp = ($v | ForEach-Object { $_ }) -join ',' } else { $disp = $v }
                $t = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
                    $provided += [PSCustomObject]@{ Name = [string]$k; Value = $disp; Type = $t; Provided = $true; Default = $null }
            } elseif ($it.PSObject -and $it.PSObject.Properties.Name -contains 'Key' -and $it.PSObject.Properties.Name -contains 'Value') {
                $k = $it.Key; $v = $it.Value
                    if ($v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) { $disp = ($v | ForEach-Object { $_ }) -join ',' } else { $disp = $v }
                $t = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
                    $provided += [PSCustomObject]@{ Name = [string]$k; Value = $disp; Type = $t; Provided = $true; Default = $null }
            }
        }
    } else {
        $provided = ,([PSCustomObject]@{ Name = 'Args'; Value = $InvocationArgs; Type = if ($null -ne $InvocationArgs) { $InvocationArgs.GetType().Name } else { 'Null' }; Provided = $true; Default = $null })
    }

    # Auto-discover eligible params from the invocation line when requested
    if ($AutoDiscoverEligible -and -not $EligibleParams -and $InvocationLine) {
        # extract script path from invocation line: & "path" or & path
        $scriptPath = $null
        $m = [System.Text.RegularExpressions.Regex]::Match($InvocationLine, '&\s*(?:"(?<q>[^"]+)"|(?<p>[^\s]+))')
        if ($m.Success) {
            if ($m.Groups['q'].Value) { $scriptPath = $m.Groups['q'].Value }
            else { $scriptPath = $m.Groups['p'].Value }
        }
        if ($scriptPath) {
            try { $found = Get-ParamsFromScript -ScriptPath $scriptPath } catch { $found = @() }
            if ($found -and $found.Count -gt 0) { $EligibleParams = $found }
        }
    }

    # If eligible mode requested and EligibleParams provided, merge
    if ($ShowMode -ne 'Provided' -and $EligibleParams) {
        $eligible = @()
        foreach ($p in $EligibleParams) {
            $n = $p.Name
            $hasDefaultProp = $p.PSObject.Properties.Name -contains 'Default'
            $defaultVal = if ($hasDefaultProp) { $p.Default } else { $null }
            $existing = $provided | Where-Object { $_.Name -eq $n }
            if ($existing) {
                foreach ($row in $existing) {
                    if (($null -eq $row.Default -or [string]::IsNullOrWhiteSpace([string]$row.Default)) -and $hasDefaultProp) {
                        $row.Default = $defaultVal
                    }
                    if (($null -eq $row.Type -or $row.Type -eq 'Unknown' -or $row.Type -eq 'Null') -and $p.Type) {
                        $row.Type = $p.Type
                    }
                }
                continue
            }
            $eligible += [PSCustomObject]@{ Name = $n; Value = if ($hasDefaultProp) { $defaultVal } else { $null }; Type = if ($p.Type) { $p.Type } else { 'Unknown' }; Provided = $false; Default = $defaultVal }
        }
        $entries = $provided + $eligible
    } else {
        $entries = $provided
    }

    if ($Format -eq 'json') {
        $out = $entries | Select-Object Name,@{Name='Value';Expression={[string]($_.Value)}},Type,Provided,Default
        # ConvertTo-Json can throw on complex objects; use Depth 5
        $json = $out | ConvertTo-Json -Depth 5
        Write-Output $json
        return
    }

    Show-TableInner -entries $entries -ShowTypesFlag:$ShowTypes -WidthVal $Width -WrapFlag:$Wrap -TitleVal $Title -InvocationLineVal $InvocationLine
}


function Convert-ToEntries {
    param($Input)
    $entries = @()
    if ($null -eq $Input) { return $entries }

    if ($Input -is [System.Collections.IDictionary]) {
        foreach ($k in $Input.Keys) {
            $v = $Input[$k]
            $type = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
            $entries += [PSCustomObject]@{ Name = [string]$k; Value = $v; Type = $type; Provided = $true; Default = $null }
        }
        return $entries
    }

    # OrderedDictionary can sometimes not match IDictionary checks in some hosts; handle explicitly
    if ($Input -ne $null -and $Input.GetType().FullName -eq 'System.Collections.Specialized.OrderedDictionary') {
        foreach ($k in $Input.Keys) {
            $v = $Input[$k]
            $type = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
            $entries += [PSCustomObject]@{ Name = [string]$k; Value = $v; Type = $type; Provided = $true; Default = $null }
        }
        return $entries
    }

    if ($Input -is [System.Management.Automation.PSCustomObject]) {
        $props = $Input | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name
        foreach ($p in $props) {
            $v = $Input.$p
            $type = if ($null -ne $v) { $v.GetType().Name } else { 'Null' }
            $entries += [PSCustomObject]@{ Name = [string]$p; Value = $v; Type = $type; Provided = $true; Default = $null }
        }
        return $entries
    }

    if ($Input -is [System.Array]) {
        foreach ($item in $Input) {
            if ($item -is [System.Management.Automation.PSCustomObject] -and $item.PSObject.Properties.Name -contains 'Name') {
                $name = $item.Name
                $val = $item.Value
                $type = if ($null -ne $item.Type) { $item.Type } elseif ($null -ne $val) { $val.GetType().Name } else { 'Null' }
                $providedFlag = if ($item.PSObject.Properties.Name -contains 'Provided') { $item.Provided } else { $true }
                $defaultVal = if ($item.PSObject.Properties.Name -contains 'Default') { $item.Default } else { $null }
                $entries += [PSCustomObject]@{ Name = [string]$name; Value = $val; Type = $type; Provided = $providedFlag; Default = $defaultVal }
            }
        }
        return $entries
    }

    # Fallback: return a single-entry with default name
    return ,([PSCustomObject]@{ Name = 'Args'; Value = $Input; Type = if ($null -ne $Input) { $Input.GetType().Name } else { 'Null' }; Provided = $true; Default = $null })
}

function Show-Table {
    param($entries)

    # compute widths
    $nameWidth = ([int](($entries | Select-Object -ExpandProperty Name | ForEach-Object { $_.Length } | Measure-Object -Maximum).Maximum))
    if ($nameWidth -lt 8) { $nameWidth = 8 }
    if ($nameWidth -gt 30) { $nameWidth = 30 }
    $typeWidth = if ($ShowTypes) { 12 } else { 0 }
    $padding = 6
    $valueWidth = $Width - $nameWidth - $typeWidth - $padding
    if ($valueWidth -lt 20) { $valueWidth = 20 }

    # Header
    Write-Host $Title -ForegroundColor Cyan
    $hdr = ('{0,-' + $nameWidth + '}  {1,-' + $valueWidth + '}')
    if ($ShowTypes) { $hdr += ('  {2,-' + $typeWidth + '}') }
    if ($ShowTypes) { $typeLabel = 'Type' } else { $typeLabel = '' }
    Write-Host ($hdr -f 'Name','Value',$typeLabel) -ForegroundColor Yellow
    Write-Host ('-' * ($Width)) -ForegroundColor DarkGray

    foreach ($e in $entries) {
        $name = $e.Name
        $val = if ($null -eq $e.Value) { '<null>' } else { $e.Value.ToString() }
        # sanitize
        $sanitizer = Join-Path $PSScriptRoot 'sanitize-output.ps1'
        if (Test-Path $sanitizer) { . $sanitizer }
        try { $val = Sanitize-DisplayString $val } catch {}
        $type = if ($ShowTypes) { $e.Type } else { '' }
            if (-not $Wrap -and $val.Length -gt $valueWidth) {
            $val = $val.Substring(0, $valueWidth - 1) + '...'
        }
        # multiline values: split on newlines and print subsequent lines indented under Value column
        $lines = $val -split "`n"
        $first = $lines[0]
        if ($ShowTypes) {
            Write-Host ($hdr -f $name, $first, $type) -ForegroundColor Gray
        } else {
            Write-Host ($hdr -f $name, $first) -ForegroundColor Gray
        }
        if ($lines.Count -gt 1) {
            for ($i = 1; $i -lt $lines.Count; $i++) {
                $ln = $lines[$i]
                $pad = ' ' * ($nameWidth + 2)
                try { $ln = Sanitize-DisplayString $ln } catch {}
                if (-not $Wrap -and $ln.Length -gt $valueWidth) { $ln = $ln.Substring(0, $valueWidth - 1) + '...' }
                Write-Host ($pad + $ln) -ForegroundColor DarkGray
            }
        }
    }
}

return
