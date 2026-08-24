param(
    [string]$SourceRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$ValidateRetired
)

$root = (Resolve-Path -LiteralPath $SourceRoot).Path
$skillPath = Join-Path $root 'SKILL.md'
$manifestPath = Join-Path $root 'references\manifest.json'
$errors = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

if (-not (Test-Path -LiteralPath $skillPath -PathType Leaf)) {
    throw "缺少根入口：$skillPath"
}
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "缺少 reference 清单：$manifestPath"
}

$skillText = Get-Content -LiteralPath $skillPath -Raw -Encoding UTF8
$skillBytes = (Get-Item -LiteralPath $skillPath).Length
$skillLines = (Get-Content -LiteralPath $skillPath -Encoding UTF8).Count
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ($skillBytes -gt [int]$manifest.skill_budget.hard_max_bytes) {
    $errors.Add("SKILL.md 超过硬上限：$skillBytes > $($manifest.skill_budget.hard_max_bytes) bytes")
} elseif ($skillBytes -gt [int]$manifest.skill_budget.warning_bytes) {
    $warnings.Add("SKILL.md 超过软预算：$skillBytes > $($manifest.skill_budget.warning_bytes) bytes")
}
if ($skillLines -gt [int]$manifest.skill_budget.hard_max_lines) {
    $errors.Add("SKILL.md 超过行数硬上限：$skillLines > $($manifest.skill_budget.hard_max_lines)")
}

$activeSkillFiles = @(
    Get-ChildItem -LiteralPath $root -Recurse -File -Filter 'SKILL.md' |
        Where-Object {
            $_.FullName -notmatch '[\\/]90_实验资料_可归档[\\/]' -and
            $_.FullName -notmatch '[\\/]91_历史会话记录[\\/]' -and
            $_.FullName -notmatch '[\\/]92_原始参考[\\/]'
        }
)
if ($activeSkillFiles.Count -ne 1 -or $activeSkillFiles[0].FullName -ne $skillPath) {
    $errors.Add("活跃区必须只有根目录一个 SKILL.md，当前数量：$($activeSkillFiles.Count)")
}

$referenceEntries = @($manifest.references)
$manifestPaths = @($referenceEntries | ForEach-Object { [string]$_.path })
$duplicates = @($manifestPaths | Group-Object | Where-Object Count -gt 1)
foreach ($duplicate in $duplicates) {
    $errors.Add("reference 清单重复：$($duplicate.Name)")
}

$diskReferences = @(
    Get-ChildItem -LiteralPath (Join-Path $root 'references') -File -Filter '*.md' |
        ForEach-Object { 'references/' + $_.Name }
)
foreach ($diskPath in $diskReferences) {
    if ($manifestPaths -notcontains $diskPath) {
        $errors.Add("未分类 reference：$diskPath")
    }
}
foreach ($manifestRef in $manifestPaths) {
    if ($diskReferences -notcontains $manifestRef) {
        $errors.Add("清单中的 reference 不存在：$manifestRef")
    }
}

foreach ($entry in $referenceEntries) {
    $path = [string]$entry.path
    $status = [string]$entry.status
    $deploy = [bool]$entry.deploy
    if (@('runtime', 'research', 'deprecated') -notcontains $status) {
        $errors.Add("非法 reference 状态：$path => $status")
        continue
    }
    if ($status -eq 'runtime') {
        if (-not $deploy) {
            $errors.Add("runtime reference 必须 deploy=true：$path")
        }
        if (-not $skillText.Contains($path)) {
            $errors.Add("runtime reference 未从 SKILL.md 直接路由：$path")
        }
    } else {
        if ($deploy) {
            $errors.Add("$status reference 不得部署：$path")
        }
        if ($status -eq 'deprecated' -and [string]::IsNullOrWhiteSpace([string]$entry.superseded_by)) {
            $errors.Add("deprecated reference 缺 superseded_by：$path")
        }
    }
}

$linkedReferences = @(
    [regex]::Matches($skillText, 'references/[^`\r\n]+?\.md') |
        ForEach-Object Value |
        Sort-Object -Unique
)
foreach ($linked in $linkedReferences) {
    $localPath = Join-Path $root ($linked -replace '/', '\')
    if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
        $errors.Add("SKILL.md 链接不存在：$linked")
    }
}

if ($ValidateRetired) {
    foreach ($entry in @($manifest.retired)) {
        $retiredPath = [string]$entry.path
        $retiredStatus = [string]$entry.status
        if (@('research', 'deprecated') -notcontains $retiredStatus) {
            $errors.Add("retired 状态必须是 research/deprecated：$retiredPath")
        }
        if ([string]::IsNullOrWhiteSpace([string]$entry.superseded_by)) {
            $errors.Add("retired 记录缺 superseded_by：$retiredPath")
        }
        $localRetired = Join-Path $root ($retiredPath -replace '/', '\')
        if (-not (Test-Path -LiteralPath $localRetired -PathType Leaf)) {
            $errors.Add("retired 文件不存在：$retiredPath")
        }
    }
}

foreach ($warning in $warnings) {
    Write-Warning $warning
}
if ($errors.Count -gt 0) {
    throw "技能结构校验失败：`n- $($errors -join "`n- ")"
}

[PSCustomObject]@{
    SourceRoot = $root
    SkillBytes = $skillBytes
    SkillLines = $skillLines
    RuntimeReferences = @($referenceEntries | Where-Object status -eq 'runtime').Count
    ResearchReferences = @($referenceEntries | Where-Object status -eq 'research').Count
    DeprecatedReferences = @($referenceEntries | Where-Object status -eq 'deprecated').Count
    LinkedReferences = $linkedReferences.Count
    Warnings = $warnings.Count
    Errors = 0
}
