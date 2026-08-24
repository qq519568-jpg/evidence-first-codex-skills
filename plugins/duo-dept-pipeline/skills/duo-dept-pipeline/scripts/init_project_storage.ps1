param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectName,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$CollectionRoot,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$BlenderRoot
)

$invalidChars = [System.IO.Path]::GetInvalidFileNameChars()
if ($ProjectName.IndexOfAny($invalidChars) -ge 0) {
    throw "项目名包含 Windows 文件名禁用字符：$ProjectName"
}
if ($ProjectName -in @('.', '..') -or $ProjectName.Trim() -ne $ProjectName) {
    throw "项目名不能是点路径，也不能带首尾空格：$ProjectName"
}

$collectionResolved = [System.IO.Path]::GetFullPath($CollectionRoot).TrimEnd('\')
$blenderResolved = [System.IO.Path]::GetFullPath($BlenderRoot).TrimEnd('\')
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $collectionResolved $ProjectName))
if (-not $projectRoot.StartsWith($collectionResolved + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "项目路径必须位于正式项目根内：$projectRoot"
}
$paths = @(
    (Join-Path $projectRoot '00_交付物_当前'),
    (Join-Path $projectRoot '01_项目总档案\00_上下文'),
    (Join-Path $projectRoot '01_项目总档案\01_立项与交接'),
    (Join-Path $projectRoot '01_项目总档案\02_视觉真值与参考'),
    (Join-Path $projectRoot '01_项目总档案\03_下游投喂记录'),
    (Join-Path $projectRoot '01_项目总档案\04_下游回传与成片'),
    (Join-Path $projectRoot '01_项目总档案\05_验收与报告'),
    (Join-Path $projectRoot '01_项目总档案\90_历史交付物'),
    (Join-Path $projectRoot '01_项目总档案\99_其他'),
    (Join-Path $blenderResolved $ProjectName)
)

foreach ($path in $paths) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}

$contextRoot = Join-Path $projectRoot '01_项目总档案\00_上下文'
$gatePath = Join-Path $contextRoot '混元3D_资产闸门.json'
if (-not (Test-Path -LiteralPath $gatePath)) {
    $templatePath = Join-Path (Split-Path -Parent $PSScriptRoot) 'templates\hunyuan3d_asset_gate_template.json'
    if (-not (Test-Path -LiteralPath $templatePath -PathType Leaf)) {
        throw "缺少混元3D资产闸门模板：$templatePath"
    }
    $gate = Get-Content -LiteralPath $templatePath -Raw | ConvertFrom-Json
    $gate.project = $ProjectName
    $gate.updated_at = (Get-Date).ToString('yyyy-MM-dd')
    $gate | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $gatePath -Encoding utf8
}

[PSCustomObject]@{
    ProjectName = $ProjectName
    ProjectRoot = $projectRoot
    CurrentDelivery = Join-Path $projectRoot '00_交付物_当前'
    ProjectArchive = Join-Path $projectRoot '01_项目总档案'
    BlenderProduction = Join-Path $blenderResolved $ProjectName
    Hunyuan3DAssetGate = $gatePath
}
