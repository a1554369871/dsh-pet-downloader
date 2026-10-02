# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Build the offline self-contained downloader: onedir app + payload (two setup.exe) + manifest -> zip.
.DESCRIPTION
    Output: dist-offline\dsh-pet-downloader-offline.zip
    Unzip and run dsh-pet-downloader.exe for a fully offline dsh-pet install.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build_offline.ps1
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

# 1) onedir build
if (-not $SkipBuild) {
    Write-Host "[1/4] PyInstaller onedir ..." -ForegroundColor Cyan
    python -m PyInstaller --noconfirm --clean `
        --distpath dist-onedir --workpath build-onedir downloader-onedir.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed: $LASTEXITCODE" }
}

$appDir = Join-Path $root 'dist-onedir\dsh-pet-downloader'
if (-not (Test-Path $appDir)) { throw "onedir output missing: $appDir" }

# 2) assemble payload
Write-Host "[2/4] Assembling payload ..." -ForegroundColor Cyan
$payloadOut = Join-Path $appDir 'payload'
if (Test-Path $payloadOut) { Remove-Item -Recurse -Force $payloadOut }
New-Item -ItemType Directory -Force -Path $payloadOut | Out-Null

$chatName = 'dsh-pet-standalone-webm-chat-setup.exe'
$plainName = 'dsh-pet-standalone-webm-setup.exe'
$chatSrc = Join-Path $PayloadDir $chatName
$plainSrc = Join-Path $PayloadDir $plainName
foreach ($src in @($chatSrc, $plainSrc)) {
    if (-not (Test-Path $src)) { throw "setup missing: $src (use -PayloadDir)" }
    Copy-Item $src $payloadOut -Force
}

# 3) version + manifest (UTF-8 no BOM)
$version = (Get-Item $chatSrc).VersionInfo.ProductVersion
if ($null -ne $version) { $version = ("$version").Trim() }
if ([string]::IsNullOrWhiteSpace($version)) {
    $initPy = Join-Path $root '..\dsh-pet\pet\__init__.py'
    if (Test-Path $initPy) {
        foreach ($line in Get-Content $initPy) {
            if ($line -match "__version__\s*=\s*'([^']+)'") { $version = $Matches[1]; break }
        }
    }
}
if ([string]::IsNullOrWhiteSpace($version)) { $version = '0.0.0' }

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

# 4) pack zip (tar/bsdtar preferred, fallback Compress-Archive)
Write-Host "[4/4] Packing offline zip ..." -ForegroundColor Cyan
$outDir = Join-Path $root 'dist-offline'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$zip = Join-Path $outDir 'dsh-pet-downloader-offline.zip'
if (Test-Path $zip) { Remove-Item $zip -Force }

$tar = Get-Command tar.exe -ErrorAction SilentlyContinue
if ($tar) {
    $items = Get-ChildItem $appDir -Force | ForEach-Object { $_.Name }
    & $tar.Source -a -c -f $zip -C $appDir $items
} else {
    Compress-Archive -Path "$appDir\*" -DestinationPath $zip -CompressionLevel Optimal
}
if ($LASTEXITCODE -ne 0) { throw "pack failed: $LASTEXITCODE" }

$mb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "Done: $zip ($mb MB)" -ForegroundColor Green
