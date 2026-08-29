$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python -c "import webview" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $Python -m pip install -r .\desktop_app\requirements-desktop.txt
}

& $Python .\desktop_app\launcher.py
