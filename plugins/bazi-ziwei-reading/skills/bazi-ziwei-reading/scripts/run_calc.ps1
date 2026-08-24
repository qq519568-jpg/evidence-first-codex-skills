[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BirthDate,

    [string]$BirthTime,
    [Nullable[int]]$Hour,
    [Nullable[int]]$TimeIndex,

    [Parameter(Mandatory = $true)]
    [string]$Sex,

    [string]$Place = 'UNKNOWN',
    [string]$Timezone = 'UNKNOWN',
    [int[]]$FlowYear = @()
)

$ErrorActionPreference = 'Stop'

$hasBirthTime = $PSBoundParameters.ContainsKey('BirthTime')
$hasHour = $PSBoundParameters.ContainsKey('Hour')
$hasTimeIndex = $PSBoundParameters.ContainsKey('TimeIndex')
$timeInputCount = [int]$hasBirthTime + [int]$hasHour + [int]$hasTimeIndex
if ($timeInputCount -ne 1) {
    throw 'Provide exactly one of BirthTime, Hour, or TimeIndex.'
}

$male = [string][char]0x7537
$female = [string][char]0x5973
if ($Sex -notin @($male, $female)) {
    throw 'Sex must be the traditional engine parameter male or female in Chinese.'
}

$python = $null
$pythonPrefix = @()
foreach ($commandName in @('python.exe', 'python3.exe')) {
    $command = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($command) {
        $python = $command.Source
        break
    }
}

if (-not $python) {
    $userProfilePath = [Environment]::GetEnvironmentVariable('USERPROFILE')
    $codexPython = Join-Path $userProfilePath '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $codexPython) {
        $python = $codexPython
    }
}

if (-not $python) {
    $launcher = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    if ($launcher) {
        $python = $launcher.Source
        $pythonPrefix = @('-3')
    }
}

if (-not $python) {
    throw 'Python 3 was not found. Install Python 3.8+ or run from Codex desktop.'
}

$calcScript = Join-Path $PSScriptRoot 'calc_chart.py'
$calcArgs = @('-X', 'utf8', $calcScript, '--date', $BirthDate, '--sex', $Sex, '--place', $Place, '--timezone', $Timezone)
if ($hasBirthTime) {
    $calcArgs += @('--time', $BirthTime)
} elseif ($hasHour) {
    $calcArgs += @('--hour', [string]$Hour)
} else {
    $calcArgs += @('--time-index', [string]$TimeIndex)
}
foreach ($year in $FlowYear) {
    $calcArgs += @('--flow-year', [string]$year)
}

& $python @pythonPrefix @calcArgs
exit $LASTEXITCODE
