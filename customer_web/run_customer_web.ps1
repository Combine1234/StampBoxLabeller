$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
.\.venv\Scripts\python.exe .\customer_web\server.py
