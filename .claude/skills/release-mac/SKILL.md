---
name: release-mac
description: Build, code-sign, and notarize the two macOS .app bundles (Apple Silicon arm64 + Intel x86_64) for an E-Tipitaka release. Use this whenever the user wants to produce, sign, or notarize a macOS build of E-Tipitaka — phrasings like "release the mac version", "build the mac apps", "sign and notarize the .app", "make the macOS dmg build", or "/release-mac". Trigger even if the user only says "build the mac app" without mentioning signing/notarization, since a real release needs both architectures signed and notarized.
---

# Release macOS build

Produce both macOS `.app` bundles for E-Tipitaka, Developer ID signed and
notarized, ready to package into a DMG or release zips.

The whole flow is encoded in `packaging/macos/release_mac.sh`. Prefer running
that one script over re-deriving the steps — it bakes in the arch-specific
interpreters, the rename-to-avoid-clobber dance, hardened-runtime signing, and
notarization, and it self-verifies each stage.

## Run it

```bash
./packaging/macos/release_mac.sh
```

That does, in order:

1. **Build arm64** with `.venv` (native Apple Silicon) → `dist/E-Tipitaka-arm64.app`
2. **Build x86_64** with `.venv-x86` under `arch -x86_64` (Rosetta) and
   `ETIPITAKA_MAC_ARCH=x86_64` → `dist/E-Tipitaka-x86_64.app`
3. **Sign** each with Developer ID + hardened runtime (`sign_devid.sh`)
4. **Notarize + staple** each (`notarize.sh`)

`dist/` is reused for both builds, so the script renames each `.app`
immediately after building (PyInstaller always emits `dist/E-Tipitaka.app`).

Useful flags:
- `--no-notarize` — stop after signing (offline, or to inspect before submitting)
- `--no-sign` — build only (implies `--no-notarize`)

Run it in the **background** — a full run builds two ~1.4 GB bundles and waits
on Apple's notarization service, so it takes ~20–40 min. Stream progress from
the log rather than blocking a foreground shell.

## Prerequisites (one-time)

These are already set up on the maintainer's machine; check them if a run fails.

- **Two venvs with deps** (wxPython, Pillow, reportlab, pyinstaller):
  - `.venv` — arm64 framework Python (Homebrew `python3.12`)
  - `.venv-x86` — universal2 Python (python.org); run x86_64 via `arch -x86_64`
- **Developer ID Application cert** in the keychain. Verify:
  `security find-identity -v -p codesigning` → expect
  `Developer ID Application: Sutee Sudprasert (A6DJDJ7527)`.
- **notarytool keychain profile** `etipitaka-notary`. Verify:
  `xcrun notarytool history --keychain-profile etipitaka-notary`.
  If missing, create it once:
  `xcrun notarytool store-credentials etipitaka-notary --apple-id <id> --team-id A6DJDJ7527 --password <app-specific-pw>`

Override any default via env: `ARM_PYBIN`, `X86_PYBIN`, `DEVID_APP_IDENTITY`,
`NOTARY_PROFILE`.

## Build config

The build honours `build.toml` (feature toggles). For a normal direct-download
release keep the in-app updater ON — do **not** use the store toggle. The slim
release omits the 162 MB thaiwn book (`include_thaiwn = false`). The version
comes from `settings.py` / `etipitaka.spec`; bump it before releasing.

## Verifying success

The script prints a summary and self-checks. To confirm independently:

```bash
for a in arm64 x86_64; do
  app="dist/E-Tipitaka-$a.app"
  lipo -archs "$app/Contents/MacOS/e-tipitaka"        # expect: $a
  codesign --verify --deep --strict "$app"            # silent = OK
  xcrun stapler validate "$app"                        # "validated"
  spctl -a -vv -t exec "$app"                          # "accepted"  (after notarize)
done
```

A correctly released bundle is single-arch (matching its name), signed by the
Developer ID Application authority with the `runtime` (hardened) flag, and has a
stapled notarization ticket that Gatekeeper accepts.

## After this skill

The signed/notarized `.app`s are inputs to packaging. Next steps (not part of
this skill): build a DMG (`packaging/macos/make_dmg.sh`) or zip them as
`E-Tipitaka-<ver>-{arm64,x86_64}.zip` for the website `release.sh` flow.

## Troubleshooting

- **`makeappx`/signing identity not found** → cert missing from keychain; see prerequisites.
- **x86_64 build is actually arm64 / "not a fat binary"** → wrong interpreter; `.venv-x86` must be a universal2 Python and the step must run under `arch -x86_64`.
- **Notarization "Invalid"** → fetch the log with
  `xcrun notarytool log <submission-id> --keychain-profile etipitaka-notary`;
  the usual cause is an unsigned nested binary (re-run signing) or a missing
  hardened-runtime flag.
- **Notarization slow/stuck** → Apple-side queue; the script waits. Check
  `xcrun notarytool history --keychain-profile etipitaka-notary`.
