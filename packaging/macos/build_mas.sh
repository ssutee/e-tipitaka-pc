#!/usr/bin/env bash
# Sign + package E-Tipitaka.app for the Mac App Store.
#
# Prereqs:
#   - Build with the Store toggle so the in-app updater is disabled:
#       ./packaging/macos/build_app.sh --mas
#   - Certificates in the keychain:
#       "Apple Distribution: NAME (TEAMID)"
#       "3rd Party Mac Developer Installer: NAME (TEAMID)"
#   - A Mac App Store provisioning profile for the app's bundle id
#     (org.watnapahpong.etipitaka), downloaded from the Apple Developer portal.
#
#   MAS_PROVISION_PROFILE=path/to/etipitaka_mas.provisionprofile \
#     ./packaging/macos/build_mas.sh [dist/E-Tipitaka.app]
set -euo pipefail
cd "$(dirname "$0")/../.."

APP="${1:-dist/E-Tipitaka.app}"
APP_IDENTITY="${MAS_APP_IDENTITY:-Apple Distribution: Sutee Sudprasert (A6DJDJ7527)}"
INSTALLER_IDENTITY="${MAS_INSTALLER_IDENTITY:-3rd Party Mac Developer Installer: Sutee Sudprasert (A6DJDJ7527)}"
PROFILE="${MAS_PROVISION_PROFILE:-packaging/macos/etipitaka_mas.provisionprofile}"
ENT="packaging/macos/entitlements-mas.plist"
PKG="dist/E-Tipitaka-mas.pkg"

[[ -d "$APP" ]]      || { echo "not found: $APP (run build_app.sh --mas first)" >&2; exit 1; }
[[ -f "$PROFILE" ]]  || { echo "provisioning profile not found: $PROFILE" >&2; exit 1; }

# 1. Embed the provisioning profile.
cp "$PROFILE" "$APP/Contents/embedded.provisionprofile"

# 2. Sign every nested dylib / .so with the Apple Distribution cert (inside-out).
#    MAS keeps library validation ON, so all of these must be signed by us.
find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 |
  while IFS= read -r -d '' lib; do
    codesign --force --timestamp --sign "$APP_IDENTITY" "$lib"
  done

# 3. Sign the app bundle with the sandbox entitlements.
codesign --force --timestamp --entitlements "$ENT" --sign "$APP_IDENTITY" "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"

# 4. Build the signed installer package for App Store Connect.
productbuild --component "$APP" /Applications --sign "$INSTALLER_IDENTITY" "$PKG"
echo "[build_mas] built: $PKG"
echo "[build_mas] upload via Transporter.app, or:"
echo "  xcrun altool --upload-package $PKG --type macos \\"
echo "    --apple-id <id> --bundle-id org.watnapahpong.etipitaka \\"
echo "    --bundle-version 3.2.0 --bundle-short-version-string 3.2.0 \\"
echo "    --username <appleid> --password <app-specific-pw>"
