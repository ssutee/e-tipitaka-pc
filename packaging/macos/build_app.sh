#!/usr/bin/env bash
# Build dist/E-Tipitaka.app with PyInstaller.
#
#   ./packaging/macos/build_app.sh          # normal build (DMG path; updater on)
#   ./packaging/macos/build_app.sh --mas    # Store build (updater disabled via
#                                           # build.store.toml -> store_build)
#
# Must run on macOS with the Homebrew framework Python (uv's standalone Python
# segfaults wxPython on macOS — see CLAUDE.md).
set -euo pipefail
cd "$(dirname "$0")/../.."

PY="${PYBIN:-/opt/homebrew/bin/python3.12}"

if [[ "${1:-}" == "--mas" ]]; then
  echo "[build_app] Store build: copying build.store.toml -> build.toml"
  cp build.store.toml build.toml
else
  echo "[build_app] normal build (in-app updater enabled)"
fi

uv run --python "$PY" pyinstaller etipitaka.spec --noconfirm --clean
echo "[build_app] done -> dist/E-Tipitaka.app"
