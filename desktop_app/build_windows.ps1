$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$AppVersion = if ($env:STAMPBOX_VERSION) { $env:STAMPBOX_VERSION } else { "1.0.5" }

function Assert-LastCommand {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$BuildRoot = if (Test-Path "D:\") {
    "D:\StampBOXDesktopBuild"
} else {
    Join-Path $ProjectRoot ".desktop-build"
}
$DistRoot = Join-Path $BuildRoot "dist"
$WorkRoot = Join-Path $BuildRoot "work"
$TempRoot = Join-Path $BuildRoot "temp"
$CacheRoot = Join-Path $BuildRoot "pyinstaller-cache"
New-Item -ItemType Directory -Force -Path $DistRoot, $WorkRoot, $TempRoot, $CacheRoot | Out-Null

# Keep large packaging intermediates off the system drive.
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:PYINSTALLER_CONFIG_DIR = $CacheRoot

& $Python -m pip install -r .\desktop_app\requirements-desktop.txt
Assert-LastCommand "Installing desktop dependencies"
& $Python .\desktop_app\create_icons.py
Assert-LastCommand "Creating application icons"
& $Python -m PyInstaller --noconfirm --clean `
    --distpath $DistRoot `
    --workpath $WorkRoot `
    .\desktop_app\StampBOX.spec
Assert-LastCommand "Building StampBOX"

$IsccCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
)
$Iscc = $IsccCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if ($Iscc) {
    & $Iscc "/DBuildRoot=$DistRoot" .\desktop_app\installer_windows.iss
    Assert-LastCommand "Building Windows installer"
    Write-Host "Installer: $DistRoot\installer\StampBOX-Setup-$AppVersion.exe"
} else {
    $ZipPath = Join-Path $DistRoot "StampBOX-Windows-Portable-$AppVersion.zip"
    Compress-Archive -Path (Join-Path $DistRoot "StampBOX\*") -DestinationPath $ZipPath -Force
    Write-Warning "Inno Setup was not found. A portable ZIP was created instead."
    Write-Host "Portable app: $ZipPath"
}
