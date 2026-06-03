#!/usr/bin/env bash
# Code-sign E-Tipitaka.app for Developer ID distribution (hardened runtime).
# Signs nested mach-O inside-out, then the .app with entitlements.
#
#   DEVID_APP_IDENTITY="Developer ID Application: NAME (TEAMID)" \
#     ./packaging/macos/sign_devid.sh [dist/E-Tipitaka.app]
set -euo pipefail
cd "$(dirname "$0")/../.."

APP="${1:-dist/E-Tipitaka.app}"
IDENTITY="${DEVID_APP_IDENTITY:-Developer ID Application: Sutee Sudprasert (A6DJDJ7527)}"
ENT="packaging/macos/entitlements-devid.plist"

[[ -d "$APP" ]] || { echo "not found: $APP (run build_app.sh first)" >&2; exit 1; }
echo "[sign_devid] identity: $IDENTITY"

# 1. Sign every nested dylib / .so first (inside-out).
find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 |
  while IFS= read -r -d '' lib; do
    codesign --force --timestamp --options runtime --sign "$IDENTITY" "$lib"
  done

# 2. Sign any nested frameworks and helper executables.
find "$APP/Contents/Frameworks" -type d -name "*.framework" -print0 2>/dev/null |
  while IFS= read -r -d '' fw; do
    codesign --force --timestamp --options runtime --sign "$IDENTITY" "$fw"
  done

# 3. Sign the app bundle last, with entitlements.
codesign --force --timestamp --options runtime \
  --entitlements "$ENT" --sign "$IDENTITY" "$APP"

# 4. Verify.
codesign --verify --deep --strict --verbose=2 "$APP"
echo "[sign_devid] signed + verified: $APP"
