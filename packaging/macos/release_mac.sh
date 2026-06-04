#!/usr/bin/env bash
# release_mac.sh — build, sign, and notarize both macOS .app bundles
# (arm64 + x86_64) for an E-Tipitaka release, in one shot.
#
# This encodes the proven release sequence:
#   1. build arm64  (.venv, native)              -> dist/E-Tipitaka-arm64.app
#   2. build x86_64 (.venv-x86 under Rosetta)    -> dist/E-Tipitaka-x86_64.app
#   3. Developer ID sign each (hardened runtime, inside-out)
#   4. notarize + staple each
#
# Flags:
#   --no-notarize   stop after signing (e.g. offline, or notary creds absent)
#   --no-sign       build only (implies --no-notarize)
#
# Overridable via env:
#   ARM_PYBIN   (default .venv/bin/python      — arm64 framework Python)
#   X86_PYBIN   (default .venv-x86/bin/python  — universal2 Python, run x86_64)
#   DEVID_APP_IDENTITY  (default "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)")
#   NOTARY_PROFILE      (default etipitaka-notary — notarytool keychain profile)
set -euo pipefail
cd "$(dirname "$0")/../.."

DEVID="${DEVID_APP_IDENTITY:-Developer ID Application: Sutee Sudprasert (A6DJDJ7527)}"
NPROFILE="${NOTARY_PROFILE:-etipitaka-notary}"
ARM_PY="${ARM_PYBIN:-.venv/bin/python}"
X86_PY="${X86_PYBIN:-.venv-x86/bin/python}"

DO_SIGN=1
DO_NOTARIZE=1
for a in "$@"; do
  case "$a" in
    --no-notarize) DO_NOTARIZE=0 ;;
    --no-sign)     DO_SIGN=0; DO_NOTARIZE=0 ;;
    *) echo "unknown flag: $a" >&2; exit 64 ;;
  esac
done

log() { printf '[release-mac] %s\n' "$*"; }

build() {  # $1 = arch label (arm64|x86_64)
  local arch="$1"
  log "build $arch"
  if [ "$arch" = "arm64" ]; then
    unset ETIPITAKA_MAC_ARCH 2>/dev/null || true
    "$ARM_PY" -m PyInstaller etipitaka.spec --noconfirm --clean
  else
    # x86_64 needs a universal2 Python run under Rosetta + x86_64 deps; the
    # spec reads ETIPITAKA_MAC_ARCH to set PyInstaller target_arch.
    ETIPITAKA_MAC_ARCH=x86_64 arch -x86_64 "$X86_PY" -m PyInstaller etipitaka.spec --noconfirm --clean
  fi
  rm -rf "dist/E-Tipitaka-$arch.app"
  mv "dist/E-Tipitaka.app" "dist/E-Tipitaka-$arch.app"
  local got; got="$(lipo -archs "dist/E-Tipitaka-$arch.app/Contents/MacOS/e-tipitaka")"
  log "  $arch built (archs: $got)"
  case " $got " in *" $arch "*) : ;; *) log "FATAL: $arch app has archs '$got'"; exit 1 ;; esac
}

build arm64
build x86_64

for arch in arm64 x86_64; do
  app="dist/E-Tipitaka-$arch.app"
  if [ "$DO_SIGN" -eq 1 ]; then
    log "sign $app"
    DEVID_APP_IDENTITY="$DEVID" ./packaging/macos/sign_devid.sh "$app"
  fi
  if [ "$DO_NOTARIZE" -eq 1 ]; then
    log "notarize $app"
    NOTARY_PROFILE="$NPROFILE" ./packaging/macos/notarize.sh "$app"
  fi
done

log "=== summary ==="
for arch in arm64 x86_64; do
  app="dist/E-Tipitaka-$arch.app"
  printf '[release-mac]   %s : archs=%s' "$app" "$(lipo -archs "$app/Contents/MacOS/e-tipitaka")"
  if [ "$DO_SIGN" -eq 1 ] && codesign --verify --deep --strict "$app" 2>/dev/null; then printf ' | signed'; fi
  if [ "$DO_NOTARIZE" -eq 1 ] && xcrun stapler validate "$app" >/dev/null 2>&1; then printf ' | stapled'; fi
  printf '\n'
done
log "done"
