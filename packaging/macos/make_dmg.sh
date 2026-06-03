#!/usr/bin/env bash
# Build a compressed DMG containing the (already signed) E-Tipitaka.app with a
# drag-to-/Applications shortcut, and sign the DMG. Notarize separately:
#   ./packaging/macos/notarize.sh dist/E-Tipitaka-<ver>.dmg
#
#   ./packaging/macos/make_dmg.sh [dist/E-Tipitaka.app] [version]
set -euo pipefail
cd "$(dirname "$0")/../.."

APP="${1:-dist/E-Tipitaka.app}"
VER="${2:-3.2.0}"
DMG="dist/E-Tipitaka-${VER}.dmg"
IDENTITY="${DEVID_APP_IDENTITY:-Developer ID Application: Sutee Sudprasert (A6DJDJ7527)}"

[[ -d "$APP" ]] || { echo "not found: $APP" >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

rm -f "$DMG"
hdiutil create -volname "E-Tipitaka" -srcfolder "$STAGE" -ov -format UDZO "$DMG"

codesign --force --timestamp --sign "$IDENTITY" "$DMG"
echo "[make_dmg] built + signed: $DMG"
echo "[make_dmg] next: ./packaging/macos/notarize.sh $DMG"
