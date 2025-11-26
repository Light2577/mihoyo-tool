Param(
    [ValidateSet("install", "run", "build")]
    [string]$Mode = "run",
    [string]$Version
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $Root "..")
Set-Location $RepoRoot

function Get-Python {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { throw "未找到 python，可在 PATH 配置后重试。" }
    return $python.Source
}

function Install-Dependencies {
    $python = Get-Python
    Write-Host ">> 安装依赖 (requirements.txt)" -ForegroundColor Cyan
    & $python -m pip install -r requirements.txt
}

function Run-App {
    $python = Get-Python
    Write-Host ">> 以管理员权限运行应用" -ForegroundColor Cyan
    & $python main.py
}

function Build-App {
    $python = Get-Python
    Write-Host ">> Nuitka 打包" -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path dist | Out-Null
    $outputName = "miHoYo Tool.exe"
    if ($Version) {
        $safe = $Version -replace '[^0-9A-Za-z_.-]', ''
        if ($safe) { $outputName = "miHoYo Tool_$safe.exe" }
    }
    & $python -m nuitka `
        --standalone `
        --onefile `
        --enable-plugin=pyside6 `
        --windows-console-mode=disable `
        --windows-uac-admin `
        --windows-icon-from-ico=icon.ico `
        --output-filename=$outputName `
        --output-dir=dist `
        main.py
}

switch ($Mode) {
    "install" { Install-Dependencies }
    "run"     { Install-Dependencies; Run-App }
    "build"   { Install-Dependencies; Build-App }
}
