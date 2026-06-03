#!/usr/bin/env bash
# Notarize a Developer ID .app or .dmg and staple the ticket.
#
# One-time credential setup (stores an App Store Connect API key or an
# app-specific password in the keychain under a named profile):
#   xcrun notarytool store-credentials etipitaka-notary \
#     --apple-id you@example.com --team-id A6DJDJ7527 --password <app-specific-pw>
#
# Then:
#   NOTARY_PROFILE=etipitaka-notary ./packaging/macos/notarize.sh dist/E-Tipitaka.app
#   NOTARY_PROFILE=etipitaka-notary ./packaging/macos/notarize.sh dist/E-Tipitaka-3.2.0.dmg
set -euo pipefail
cd "$(dirname "$0")/../.."

TARGET="${1:-dist/E-Tipitaka.app}"
PROFILE="${NOTARY_PROFILE:-etipitaka-notary}"

[[ -e "$TARGET" ]] || { echo "not found: $TARGET" >&2; exit 1; }

case "$TARGET" in
  *.dmg)
    SUBMIT="$TARGET"
    ;;
  *.app)
    SUBMIT="dist/$(basename "${TARGET%.app}")-notarize.zip"
    echo "[notarize] zipping app -> $SUBMIT"
    /usr/bin/ditto -c -k --keepParent "$TARGET" "$SUBMIT"
    ;;
  *)
    echo "unsupported target (need .app or .dmg): $TARGET" >&2; exit 1 ;;
esac

echo "[notarize] submitting $SUBMIT (profile: $PROFILE) ..."
xcrun notarytool submit "$SUBMIT" --keychain-profile "$PROFILE" --wait

echo "[notarize] stapling ticket to $TARGET"
xcrun stapler staple "$TARGET"
xcrun stapler validate "$TARGET"
echo "[notarize] done"
