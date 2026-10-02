# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    构建 dsh-pet 下载器单文件 exe。
.DESCRIPTION
    pip install -r requirements.txt 后运行本脚本，产物在 dist\dsh-pet-downloader.exe。
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build.ps1
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed: $LASTEXITCODE" }

python -m PyInstaller --noconfirm --clean downloader.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed: $LASTEXITCODE" }

Write-Host "Done: $root\dist\dsh-pet-downloader.exe" -ForegroundColor Green
