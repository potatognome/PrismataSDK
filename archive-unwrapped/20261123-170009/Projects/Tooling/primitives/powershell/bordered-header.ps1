function Show-BorderedHeader {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true, Position=0)]
        [string] $Message,

        [Parameter(Mandatory=$false)]
        [string] $BorderChar = '=',

        [Parameter(Mandatory=$false)]
        [string] $BorderColor = 'Cyan',

        [Parameter(Mandatory=$false)]
        [string] $MessageColor = 'White',

        [Parameter(Mandatory=$false)]
        [int] $Width = 0
    )

    # Determine terminal width if not provided
    if (-not $Width -or $Width -le 0) {
        try {
            $Width = $Host.UI.RawUI.WindowSize.Width
        } catch {
            $Width = 80
        }
    }

    if ($Width -lt 10) { $Width = 10 }

    # Ensure message fits
    if ($Message.Length -ge $Width) {
        $Message = $Message.Substring(0, $Width - 2)
    }

    # Build full border line by repeating the border char/pattern
    $repeat = [math]::Ceiling($Width / [Math]::Max(1, $BorderChar.Length))
    $full = ($BorderChar * $repeat).Substring(0, $Width)

    # Compute left/right fills for centered message
    $available = $Width - $Message.Length
    $leftCount = [math]::Floor($available/2)
    $rightCount = $available - $leftCount

    $left = ($BorderChar * [math]::Ceiling($leftCount / [Math]::Max(1, $BorderChar.Length))).Substring(0, $leftCount)
    $right = ($BorderChar * [math]::Ceiling($rightCount / [Math]::Max(1, $BorderChar.Length))).Substring(0, $rightCount)

    # Print top border
    Write-Host $full -ForegroundColor $BorderColor

    # Print centered message with colored border segments
    Write-Host -NoNewline $left -ForegroundColor $BorderColor
    Write-Host -NoNewline $Message -ForegroundColor $MessageColor
    Write-Host $right -ForegroundColor $BorderColor

    # Print bottom border
    Write-Host $full -ForegroundColor $BorderColor
}

# Example: Show-BorderedHeader -Message 'Starting Scrape' -BorderChar '=' -BorderColor Cyan -MessageColor Magenta
