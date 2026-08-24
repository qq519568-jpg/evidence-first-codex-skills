[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path -Parent $PSScriptRoot
$requirementsPath = Join-Path $skillRoot 'requirements.txt'
$vendorPath = Join-Path $PSScriptRoot 'vendor'

$python = $null
foreach ($commandName in @('python.exe', 'python3.exe')) {
    $command = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($command) {
        $python = $command.Source
        break
    }
}
if (-not $python) {
    $profilePath = [Environment]::GetEnvironmentVariable('USERPROFILE')
    $candidate = Join-Path $profilePath '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        $python = $candidate
    }
}
if (-not $python) {
    throw 'Python 3 was not found.'
}

$npm = Get-Command 'npm.cmd' -ErrorAction SilentlyContinue
if (-not $npm) {
    $npm = Get-Command 'npm' -ErrorAction SilentlyContinue
}
if (-not $npm) {
    throw 'npm was not found. Install Node.js with npm before setting up the Ziwei dependency.'
}

New-Item -ItemType Directory -Force -Path $vendorPath | Out-Null
& $python -m pip install --disable-pip-version-check --no-input --target $vendorPath --requirement $requirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "Python dependency installation failed with exit code $LASTEXITCODE."
}

Push-Location $PSScriptRoot
try {
    & $npm.Source ci --ignore-scripts --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) {
        throw "npm ci failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

[PSCustomObject]@{
    Python = $python
    PythonVendor = $vendorPath
    NodeModules = Join-Path $PSScriptRoot 'node_modules'
    Status = 'READY'
}
