$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
.\.venv\Scripts\python.exe -m streamlit run .\customer_app\app.py --server.port 8502
