from pathlib import Path
import os
import sys


ROOT = Path(SPECPATH).parent
DESKTOP_DIR = ROOT / "desktop_app"
WINDOWS_ICON = DESKTOP_DIR / "assets" / "StampBOX.ico"
MACOS_ICON = DESKTOP_DIR / "assets" / "StampBOX.icns"
APP_VERSION = os.environ.get("STAMPBOX_VERSION", "1.0.4")
MACOS_TARGET_ARCH = os.environ.get("STAMPBOX_TARGET_ARCH") or None
MACOS_SIGNING_IDENTITY = os.environ.get("APPLE_SIGNING_IDENTITY") or None

platform_hidden_imports = []
if sys.platform == "win32":
    platform_hidden_imports = ["webview.platforms.edgechromium"]
elif sys.platform == "darwin":
    platform_hidden_imports = ["webview.platforms.cocoa"]

a = Analysis(
    [str(DESKTOP_DIR / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(DESKTOP_DIR / "static"), "desktop_app/static"),
        (str(ROOT / "assets"), "assets"),
        (str(ROOT / "config"), "config"),
    ],
    hiddenimports=["customer_web.server", *platform_hidden_imports],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["streamlit", "flask", "pytest", "pandas", "numpy", "pyarrow"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StampBOX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=MACOS_TARGET_ARCH,
    codesign_identity=MACOS_SIGNING_IDENTITY,
    entitlements_file=None,
    icon=str(MACOS_ICON if sys.platform == "darwin" else WINDOWS_ICON),
    version=str(DESKTOP_DIR / "version_info.txt") if sys.platform == "win32" else None,
)

collect = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="StampBOX",
)

if sys.platform == "darwin":
    app = BUNDLE(
        collect,
        name="StampBOX.app",
        icon=str(MACOS_ICON),
        bundle_identifier="com.stampbox.desktop",
        info_plist={
            "CFBundleDisplayName": "StampBOX",
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
        },
    )
