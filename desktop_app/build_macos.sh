#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
APP_VERSION="${STAMPBOX_VERSION:-1.0.2}"
EXPECTED_ARCH="${STAMPBOX_TARGET_ARCH:-$(uname -m)}"
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

APP_EXECUTABLE="dist/StampBOX.app/Contents/MacOS/StampBOX"
ACTUAL_ARCH="$(lipo -archs "$APP_EXECUTABLE")"
if [[ "$ACTUAL_ARCH" != "$EXPECTED_ARCH" ]]; then
  echo "Expected app architecture '$EXPECTED_ARCH', got '$ACTUAL_ARCH'." >&2
  exit 1
fi

# PyInstaller signs every collected binary and the final bundle. Re-signing an
# ad-hoc build with hardened runtime breaks Python framework library validation.
codesign --verify --deep --strict --verbose=2 dist/StampBOX.app
STAMPBOX_SMOKE_TEST=1 STAMPBOX_MAPPING_OFFLINE=1 "$APP_EXECUTABLE"

DMG_STAGE="$(mktemp -d "${TMPDIR:-/tmp}/stampbox-dmg.XXXXXX")"
VERIFY_MOUNT="$(mktemp -d "${TMPDIR:-/tmp}/stampbox-verify.XXXXXX")"
DMG_PATH="dist/StampBOX-macOS-${APP_VERSION}.dmg"
DMG_ATTACHED=0

cleanup() {
  if [[ "$DMG_ATTACHED" -eq 1 ]]; then
    hdiutil detach "$VERIFY_MOUNT" >/dev/null || true
  fi
  rm -rf "$DMG_STAGE" "$VERIFY_MOUNT"
}
trap cleanup EXIT

ditto dist/StampBOX.app "$DMG_STAGE/StampBOX.app"
ln -s /Applications "$DMG_STAGE/Applications"
hdiutil create \
  -volname "StampBOX" \
  -srcfolder "$DMG_STAGE" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

hdiutil attach -nobrowse -readonly -mountpoint "$VERIFY_MOUNT" "$DMG_PATH" >/dev/null
DMG_ATTACHED=1
codesign --verify --deep --strict --verbose=2 "$VERIFY_MOUNT/StampBOX.app"
STAMPBOX_SMOKE_TEST=1 STAMPBOX_MAPPING_OFFLINE=1 \
  "$VERIFY_MOUNT/StampBOX.app/Contents/MacOS/StampBOX"
hdiutil detach "$VERIFY_MOUNT" >/dev/null
DMG_ATTACHED=0

echo "macOS app: $PROJECT_ROOT/dist/StampBOX.app"
echo "macOS architecture: $ACTUAL_ARCH"
echo "macOS installer: $PROJECT_ROOT/$DMG_PATH"
