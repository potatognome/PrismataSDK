Import-Module "$PSScriptRoot/../ConfigMerge.psm1" -Force

function Invoke-FolderTree {
    param(
        [hashtable] $Defaults,
        [hashtable] $ModeConfig,
        [hashtable] $UserConfig,
        [hashtable] $StyleConfig,
        [hashtable] $CliConfig
    )

    if (-not $Defaults.ContainsKey('conflictMode')) {
        $Defaults.conflictMode = 'includeWins'
    }

    $settings = Merge-Config -Defaults $Defaults `
                             -Mode     $ModeConfig `
                             -Config   $UserConfig `
                             -Style    $StyleConfig `
                             -Cli      $CliConfig

    return $settings
}
