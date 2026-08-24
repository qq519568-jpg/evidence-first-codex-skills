[CmdletBinding()]
param(
    [string]$Root
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = Split-Path -Parent $PSScriptRoot
}
$rootResolved = (Resolve-Path -LiteralPath $Root).Path
$marketplacePath = Join-Path $rootResolved '.agents\plugins\marketplace.json'
$marketplace = Get-Content -LiteralPath $marketplacePath -Raw -Encoding UTF8 | ConvertFrom-Json
$errors = [System.Collections.Generic.List[string]]::new()

if ($marketplace.name -ne 'evidence-first-skills') {
    $errors.Add("Unexpected marketplace name: $($marketplace.name)")
}

foreach ($entry in @($marketplace.plugins)) {
    $pluginRoot = Join-Path $rootResolved (($entry.source.path -replace '/', '\').TrimStart('.', '\'))
    $manifestPath = Join-Path $pluginRoot '.codex-plugin\plugin.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        $errors.Add("Missing plugin manifest: $manifestPath")
        continue
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.name -ne $entry.name) {
        $errors.Add("Plugin name mismatch: $($entry.name) != $($manifest.name)")
    }
    $skillFiles = @(Get-ChildItem -LiteralPath (Join-Path $pluginRoot 'skills') -File -Recurse -Filter 'SKILL.md')
    if ($skillFiles.Count -ne 1) {
        $errors.Add("Plugin $($entry.name) must contain exactly one SKILL.md; found $($skillFiles.Count)")
        continue
    }
    $skillText = Get-Content -LiteralPath $skillFiles[0].FullName -Raw -Encoding UTF8
    if ($skillText -notmatch '(?ms)\A---\s*\r?\n.*?^name:\s*\S+\s*$.*?^description:\s*\S.+?^---\s*$') {
        $errors.Add("Invalid skill frontmatter: $($skillFiles[0].FullName)")
    }
}

if ($errors.Count -gt 0) {
    throw "Repository structure validation failed:`n- $($errors -join "`n- ")"
}

& (Join-Path $PSScriptRoot 'privacy_scan.ps1') -Root $rootResolved | Out-Null

$duoRoot = Join-Path $rootResolved 'plugins\duo-dept-pipeline\skills\duo-dept-pipeline'
& (Join-Path $duoRoot 'scripts\validate_skill_structure.ps1') -SourceRoot $duoRoot | Out-Null

[PSCustomObject]@{
    Root = $rootResolved
    Plugins = @($marketplace.plugins).Count
    Errors = 0
}
