# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    构建「离线自包含」下载器：onedir 程序 + payload（两个 setup.exe）+ manifest，打包成 zip。
.DESCRIPTION
    产物：dist-offline\dsh-pet-downloader-offline.zip
    用户解压后直接运行 dsh-pet-downloader.exe，即可完全离线安装 dsh-pet。
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build_offline.ps1
    # 指定其它 dsh-pet 产物目录（例如从 CI 下载）：
    powershell -ExecutionPolicy Bypass -File build_offline.ps1 -PayloadDir D:\dsh-pet-dist
#>
param(
    [string]$PayloadDir = "",
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

if (-not $PayloadDir) {
    $PayloadDir = Join-Path $root '..\dsh-pet\dist-onedir'
}

# 1) onedir 构建
if (-not $SkipBuild) {
    Write-Host "[1/4] PyInstaller onedir ..." -ForegroundColor Cyan
    python -m PyInstaller --noconfirm --clean --onedir `
        --distpath dist-onedir --workpath build-onedir downloader-onedir.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed: $LASTEXITCODE" }
}

$appDir = Join-Path $root 'dist-onedir\dsh-pet-downloader'
if (-not (Test-Path $appDir)) { throw "缺少 onedir 产物：$appDir" }

# 2) 复制 payload
Write-Host "[2/4] 组装 payload ..." -ForegroundColor Cyan
$payloadOut = Join-Path $appDir 'payload'
if (Test-Path $payloadOut) { Remove-Item -Recurse -Force $payloadOut }
New-Item -ItemType Directory -Force -Path $payloadOut | Out-Null

$chatName = 'dsh-pet-standalone-webm-chat-setup.exe'
$plainName = 'dsh-pet-standalone-webm-setup.exe'
$chatSrc = Join-Path $PayloadDir $chatName
$plainSrc = Join-Path $PayloadDir $plainName
foreach ($src in @($chatSrc, $plainSrc)) {
    if (-not (Test-Path $src)) { throw "缺少安装包：$src（用 -PayloadDir 指定目录）" }
    Copy-Item $src $payloadOut -Force
}

# 3) 版本 + manifest（无 BOM UTF-8）
$version = (Get-Item $chatSrc).VersionInfo.ProductVersion
if (-not $version) {
    $initPy = Join-Path $root '..\dsh-pet\pet\__init__.py'
    if (Test-Path $initPy) {
        $m = Select-String -Path $initPy -Pattern "__version__\s*=\s*'([^']+)'" | Select-Object -First 1
        if ($m) { $version = $m.Matches[0].Groups[1].Value }
    }
}
if (-not $version) { $version = '0.0.0' }

function New-Entry([string]$name) {
    $p = Join-Path $payloadOut $name
    return [ordered]@{
        file   = $name
        size   = (Get-Item $p).Length
        sha256 = (Get-FileHash $p -Algorithm SHA256).Hash.ToLower()
    }
}

$manifest = [ordered]@{
    version      = $version
    generated_at = (Get-Date).ToString('s')
    assets       = [ordered]@{
        winChatSetup = (New-Entry $chatName)
        winSetup     = (New-Entry $plainName)
    }
}
$json = $manifest | ConvertTo-Json -Depth 5
$manifestPath = Join-Path $payloadOut 'manifest.json'
[System.IO.File]::WriteAllText($manifestPath, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "      manifest: v$version" -ForegroundColor Green

# 4) 打包 zip（优先 tar/bsdtar，回退 Compress-Archive）
Write-Host "[4/4] 打包离线 zip ..." -ForegroundColor Cyan
$outDir = Join-Path $root 'dist-offline'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$zip = Join-Path $outDir 'dsh-pet-downloader-offline.zip'
if (Test-Path $zip) { Remove-Item $zip -Force }

$tar = Get-Command tar.exe -ErrorAction SilentlyContinue
if ($tar) {
    & $tar.Source -a -c -f $zip -C $appDir .
} else {
    Compress-Archive -Path "$appDir\*" -DestinationPath $zip -CompressionLevel Optimal
}
if ($LASTEXITCODE -ne 0) { throw "打包失败: $LASTEXITCODE" }

$mb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "Done: $zip ($mb MB)" -ForegroundColor Green
