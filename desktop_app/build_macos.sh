#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ ! -d ".venv-desktop" ]]; then
  "$PYTHON_BIN" -m venv .venv-desktop
fi

. .venv-desktop/bin/activate
python -m pip install --upgrade pip
python -m pip install -r desktop_app/requirements-desktop.txt
python desktop_app/create_icons.py
python -m PyInstaller --noconfirm --clean \
  --distpath dist \
  --workpath build/desktop \
  desktop_app/StampBOX.spec

SIGNING_IDENTITY="${APPLE_SIGNING_IDENTITY:--}"
codesign --deep --force --options runtime --sign "$SIGNING_IDENTITY" dist/StampBOX.app

DMG_STAGE="$(mktemp -d "${TMPDIR:-/tmp}/stampbox-dmg.XXXXXX")"
trap 'rm -rf "$DMG_STAGE"' EXIT
ditto dist/StampBOX.app "$DMG_STAGE/StampBOX.app"
ln -s /Applications "$DMG_STAGE/Applications"
hdiutil create \
  -volname "StampBOX" \
  -srcfolder "$DMG_STAGE" \
  -ov \
  -format UDZO \
  dist/StampBOX-macOS-1.0.0.dmg

echo "macOS app: $PROJECT_ROOT/dist/StampBOX.app"
echo "macOS installer: $PROJECT_ROOT/dist/StampBOX-macOS-1.0.0.dmg"
