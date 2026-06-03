#!/usr/bin/env bash
# Build universal2 wheels for the native deps that ship ONLY thin (single-arch)
# wheels on PyPI -- wxPython and Pillow -- by fusing their arm64 + x86_64 wheels
# with delocate-fuse. Output: ./wheels-universal2/*.whl
#
# (reportlab is pure-Python; pony/whoosh/xhtml2pdf/appdirs/packaging/requests
#  are arch-agnostic -- none need fusing.)
#
# Usage:
#   PYBIN=/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 \
#     ./packaging/macos/fuse_wheels.sh
#   "$PYBIN" -m pip install wheels-universal2/*.whl
#   ./packaging/macos/build_app.sh --universal2
set -euo pipefail
cd "$(dirname "$0")/../.."

PY="${PYBIN:-/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12}"
[[ -x "$PY" ]] || { echo "Python not found: $PY (set PYBIN=)" >&2; exit 1; }

OUT="wheels-universal2"
PKGS=("wxPython==4.2.5" "Pillow")

# Multiple platform tags so pip can match whatever macOS minor the wheel targets
# (e.g. wx x86_64 is macosx_14_0, Pillow x86_64 is macosx_10_13).
ARM_TAGS=(--platform macosx_11_0_arm64 --platform macosx_12_0_arm64
          --platform macosx_13_0_arm64 --platform macosx_14_0_arm64)
X86_TAGS=(--platform macosx_10_13_x86_64 --platform macosx_11_0_x86_64
          --platform macosx_12_0_x86_64 --platform macosx_13_0_x86_64
          --platform macosx_14_0_x86_64)
COMMON=(--only-binary=:all: --python-version 3.12 --implementation cp
        --abi cp312 --no-deps)

"$PY" -m pip install -q --upgrade delocate
mkdir -p "$OUT"

for p in "${PKGS[@]}"; do
  a="$(mktemp -d)"; b="$(mktemp -d)"
  echo "[fuse] download $p (arm64)";  "$PY" -m pip download "${COMMON[@]}" "${ARM_TAGS[@]}" -d "$a" "$p"
  echo "[fuse] download $p (x86_64)"; "$PY" -m pip download "${COMMON[@]}" "${X86_TAGS[@]}" -d "$b" "$p"
  echo "[fuse] fuse $p -> $OUT/"
  # delocate-fuse: base wheel first, overlay second; emits a universal2 wheel.
  "$PY" -m delocate.cmd.delocate_fuse "$a"/*.whl "$b"/*.whl -w "$OUT"
  rm -rf "$a" "$b"
done

echo "[fuse] done -> $OUT/:"
ls -1 "$OUT"
echo "[fuse] install: \"$PY\" -m pip install $OUT/*.whl"
