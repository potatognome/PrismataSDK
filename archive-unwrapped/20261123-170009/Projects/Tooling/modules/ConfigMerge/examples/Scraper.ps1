Import-Module "$PSScriptRoot/../ConfigMerge.psm1" -Force

function Invoke-Scraper {
    param(
        [hashtable] $Defaults,
        [hashtable] $ModeConfig,
        [hashtable] $UserConfig,
        [hashtable] $StyleConfig,
        [hashtable] $CliConfig
    )

    $settings = Merge-Config -Defaults $Defaults `
                             -Mode     $ModeConfig `
                             -Config   $UserConfig `
                             -Style    $StyleConfig `
                             -Cli      $CliConfig

    # Use $settings.includeTypes, $settings.excludeTypes, etc.
    return $settings
}