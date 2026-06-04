#!/usr/bin/env bash
# make_release_zips.sh VERSION WEB_DIR WIN_JOB_ID LIN_JOB_ID
#
# Build the 4 distributable zips into $WEB_DIR/versions/$VERSION/ to match the
# layout scripts/release.sh expects:
#   E-Tipitaka-$VER-arm64.zip          <- dist/E-Tipitaka-arm64.app  (E-Tipitaka.app/ inside)
#   E-Tipitaka-$VER-x86_64.zip         <- dist/E-Tipitaka-x86_64.app
#   E-Tipitaka-$VER-windows-x86_64.zip <- CI windows job artifact (e-tipitaka.exe)
#   E-Tipitaka-$VER-linux-x86_64.zip   <- CI linux job artifact (e-tipitaka)
#
# The two mac .app must already be signed + notarized (release_mac.sh). ditto is
# used so the bundle's signature + stapled notarization ticket survive zipping.
#
# Env: RELEASE_GLAB_REPO (default sutee-s%2Fe-tipitaka-pc, URL-encoded path).
set -euo pipefail
cd "$(dirname "$0")/../.."   # desktop repo root

VER="${1:?usage: make_release_zips.sh VERSION WEB_DIR WIN_JOB_ID LIN_JOB_ID}"
WEB="${2:?web repo dir}"
WIN_JOB="${3:?windows CI job id}"
LIN_JOB="${4:?linux CI job id}"
REPO_API="${RELEASE_GLAB_REPO:-sutee-s%2Fe-tipitaka-pc}"

OUT="$WEB/versions/$VER"
mkdir -p "$OUT"

zip_mac() {  # $1 = arch label (arm64|x86_64)
  local arch="$1" app="dist/E-Tipitaka-$1.app" tmp
  [ -d "$app" ] || { echo "FATAL: missing $app (run packaging/macos/release_mac.sh)"; exit 1; }
  codesign --verify --deep --strict "$app" 2>/dev/null \
    || { echo "FATAL: $app is not validly signed"; exit 1; }
  xcrun stapler validate "$app" >/dev/null 2>&1 \
    || echo "WARN: $app has no stapled notarization ticket"
  tmp="$(mktemp -d)"
  ditto "$app" "$tmp/E-Tipitaka.app"                       # bundle must be named E-Tipitaka.app
  ditto -c -k --keepParent "$tmp/E-Tipitaka.app" "$OUT/E-Tipitaka-$VER-$arch.zip"
  rm -rf "$tmp"
  echo "  mac $arch  -> E-Tipitaka-$VER-$arch.zip"
}

zip_ci() {  # $1 job id, $2 zip basename, $3 inner filename, $4 path inside artifact
  local job="$1" base="$2" inner="$3" src="$4" tmp
  tmp="$(mktemp -d)"
  glab api "projects/$REPO_API/jobs/$job/artifacts" > "$tmp/a.zip"
  unzip -o -q "$tmp/a.zip" -d "$tmp"
  [ -f "$tmp/$src" ] || { echo "FATAL: $src not in job $job artifact"; exit 1; }
  cp "$tmp/$src" "$tmp/$inner"
  ( cd "$tmp" && zip -q "$OUT/$base.zip" "$inner" )
  rm -rf "$tmp"
  echo "  ci $base.zip"
}

zip_mac arm64
zip_mac x86_64
zip_ci "$WIN_JOB" "E-Tipitaka-$VER-windows-x86_64" "E-Tipitaka-$VER-windows-x86_64.exe" "dist/e-tipitaka.exe"
zip_ci "$LIN_JOB" "E-Tipitaka-$VER-linux-x86_64"   "E-Tipitaka-$VER-linux-x86_64"       "dist/e-tipitaka"

echo "=== $OUT ==="
ls -la "$OUT"
[ -f "$OUT/changelog.md" ] || echo "NOTE: changelog.md missing — create it before release.sh"
