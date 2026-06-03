#!/usr/bin/env bash
# Verify a built .app is universal2 (fat). Reports the main executable's archs
# and flags any nested Mach-O lib that is missing x86_64 (i.e. still thin) —
# those are what break a universal2 build / leave it arm64-only.
#
#   ./packaging/macos/verify_arch.sh [dist/E-Tipitaka.app]
set -euo pipefail
cd "$(dirname "$0")/../.."

APP="${1:-dist/E-Tipitaka.app}"
MAIN="$APP/Contents/MacOS/e-tipitaka"
[[ -d "$APP" ]] || { echo "not found: $APP" >&2; exit 1; }

echo "main executable: $(lipo -archs "$MAIN" 2>/dev/null || echo '??')"

thin=0
total=0
while IFS= read -r -d '' f; do
  file "$f" | grep -q 'Mach-O' || continue
  total=$((total + 1))
  archs="$(lipo -archs "$f" 2>/dev/null || echo '')"
  if ! grep -q 'x86_64' <<<"$archs" || ! grep -q 'arm64' <<<"$archs"; then
    echo "  THIN: ${f#"$APP"/}  [$archs]"
    thin=$((thin + 1))
  fi
done < <(find "$APP/Contents" -type f \( -name '*.so' -o -name '*.dylib' \) -print0)

echo "checked $total nested Mach-O libs; thin (non-universal): $thin"
if [[ "$thin" -eq 0 ]]; then
  echo "OK: bundle is universal2"
else
  echo "NOT universal2 — replace the thin deps with universal2 wheels (README)"
  exit 1
fi
