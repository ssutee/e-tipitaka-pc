#!/usr/bin/env bash
# Build dist/E-Tipitaka.app with PyInstaller.
#
# Flags (combinable):
#   --mas          Store build: copies build.store.toml -> build.toml so the
#                  in-app self-updater is disabled (MAS forbids it).
#   --universal2   Fat arm64+x86_64 build. Requires a universal2 Python
#                  (python.org framework build) and universal2 wheels for every
#                  native dep. Defaults PYBIN to the python.org 3.12.
#   --arm64        Force arm64 only (default on Apple Silicon).
#   --x86_64       Force x86_64 only.
#
# Examples:
#   ./packaging/macos/build_app.sh                       # native arm64, updater on
#   ./packaging/macos/build_app.sh --universal2          # fat, updater on
#   ./packaging/macos/build_app.sh --mas --universal2    # fat, Store build
#
# uv's standalone Python segfaults wxPython on macOS — use a framework Python
# (Homebrew for native arm64; python.org for universal2). See CLAUDE.md.
set -euo pipefail
cd "$(dirname "$0")/../.."

MAS=0
ARCH=""
for a in "$@"; do
  case "$a" in
    --mas)        MAS=1 ;;
    --universal2) ARCH="universal2" ;;
    --arm64)      ARCH="arm64" ;;
    --x86_64)     ARCH="x86_64" ;;
    *) echo "unknown flag: $a" >&2; exit 1 ;;
  esac
done

# Pick the interpreter. universal2 needs the python.org universal2 framework
# build; native arm64 uses Homebrew. Override either with PYBIN=...
if [[ "$ARCH" == "universal2" ]]; then
  PY="${PYBIN:-/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12}"
else
  PY="${PYBIN:-/opt/homebrew/bin/python3.12}"
fi
[[ -x "$PY" ]] || { echo "Python not found/executable: $PY (set PYBIN=)" >&2; exit 1; }

if [[ -n "$ARCH" ]]; then
  export ETIPITAKA_MAC_ARCH="$ARCH"
  echo "[build_app] target arch: $ARCH  (python: $PY)"
else
  echo "[build_app] target arch: native  (python: $PY)"
fi

if [[ "$MAS" -eq 1 ]]; then
  echo "[build_app] Store build: build.store.toml -> build.toml (updater off)"
  cp build.store.toml build.toml
else
  echo "[build_app] normal build (in-app updater enabled)"
fi

uv run --python "$PY" pyinstaller etipitaka.spec --noconfirm --clean
echo "[build_app] done -> dist/E-Tipitaka.app"

if [[ "$ARCH" == "universal2" ]]; then
  echo "[build_app] verify archs: ./packaging/macos/verify_arch.sh"
fi
