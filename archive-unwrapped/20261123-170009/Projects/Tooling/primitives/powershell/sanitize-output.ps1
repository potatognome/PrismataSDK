function Sanitize-DisplayString {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true, ValueFromPipeline=$true)]
        [string]$InputString
    )

    begin {
        if ($null -eq $InputString) { return $null }
    }
    process {
        $s = [string]$InputString
        # Normalize to NFC
        try { $s = [string][System.Text.Normalization]::Normalize($s, [System.Text.NormalizationForm]::FormC) } catch {}
        # Replace Unicode ellipsis with ASCII ellipsis (use char literal to avoid embedding non-ASCII bytes)
        $ellipsis = [char]0x2026
        $s = $s -replace $ellipsis, '...'
        return $s
    }
}

Set-StrictMode -Version Latest

return
