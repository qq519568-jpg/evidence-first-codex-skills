[CmdletBinding()]
param(
    [string]$Root
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = Split-Path -Parent $PSScriptRoot
}
$resolvedRoot = (Resolve-Path -LiteralPath $Root).Path
$errors = [System.Collections.Generic.List[string]]::new()

$blockedNames = @(
    '.env', 'chart.json', 'analysis.json', 'report.html',
    'user-strategy-context.md', 'local-profile.md'
)
$blockedSegments = @(
    '\node_modules\', '\__pycache__\', '\results\', '\generated\',
    '\private\'
)
$textExtensions = @(
    '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.py', '.js',
    '.ts', '.ps1', '.html', '.css', '.xml', '.ini', '.cfg'
)
$patterns = [ordered]@{
    'Windows user profile path' = '(?i)C:\\Users\\[^\\\s`"'']+'
    'Windows absolute path' = '(?i)(?<![A-Za-z0-9_])[A-Z]:\\[^\r\n`"<>]+'
    'GitHub token' = '(?i)\b(?:github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9]{20,})\b'
    'OpenAI-style secret key' = '\bsk-[A-Za-z0-9_-]{20,}\b'
    'AWS access key' = '\bAKIA[0-9A-Z]{16}\b'
    'Tencent Cloud Secret ID' = '\bAKID[A-Za-z0-9]{32}\b'
    'Slack token' = '\bxox[baprs]-[A-Za-z0-9-]{10,}\b'
    'Private key block' = '-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'
    'Likely email address' = '(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
    'Likely mainland China mobile number' = '(?<!\d)1[3-9]\d{9}(?!\d)'
}

$files = Get-ChildItem -LiteralPath $resolvedRoot -File -Recurse -Force
foreach ($file in $files) {
    $relative = $file.FullName.Substring($resolvedRoot.Length).TrimStart('\')
    if ($relative.StartsWith('.git\', [System.StringComparison]::OrdinalIgnoreCase)) {
        continue
    }
    if ($relative -eq 'scripts\privacy_scan.ps1') {
        continue
    }
    if ($blockedNames -contains $file.Name) {
        $errors.Add("Blocked file name: $relative")
        continue
    }
    if ($blockedSegments | Where-Object { $file.FullName.IndexOf($_, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 }) {
        $errors.Add("Blocked directory content: $relative")
        continue
    }
    if ($textExtensions -notcontains $file.Extension.ToLowerInvariant()) {
        continue
    }
    $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 -ErrorAction Stop
    foreach ($entry in $patterns.GetEnumerator()) {
        if ($content -match $entry.Value) {
            $errors.Add("$($entry.Key): $relative")
        }
    }
}

if ($errors.Count -gt 0) {
    throw "Privacy scan failed:`n- $($errors -join "`n- ")"
}

[PSCustomObject]@{
    Root = $resolvedRoot
    FilesScanned = $files.Count
    Errors = 0
}
