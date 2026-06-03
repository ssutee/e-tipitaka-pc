# macOS packaging

Two distribution paths for `E-Tipitaka.app` (built by `etipitaka.spec` via
PyInstaller, `BUNDLE` -> `dist/E-Tipitaka.app`):

1. **Developer ID notarized DMG** — direct download from your site, runs on any
   Mac. Practical, recommended.
2. **Mac App Store (MAS)** — sandboxed `.pkg` uploaded to App Store Connect.
   Higher effort, real rejection risk with PyInstaller/wxPython.

All scripts run on macOS with the Homebrew framework Python
(`/opt/homebrew/bin/python3.12`) — uv's standalone Python segfaults wxPython.

| File | Purpose |
|------|---------|
| `build_app.sh`          | PyInstaller build (`--mas`, `--universal2`, `--arm64`, `--x86_64`) |
| `verify_arch.sh`        | Check the built `.app` is universal2 (flags thin libs) |
| `entitlements-devid.plist` | Hardened-runtime entitlements (Developer ID) |
| `entitlements-mas.plist`   | App Sandbox entitlements (MAS) |
| `sign_devid.sh`         | Inside-out codesign for Developer ID |
| `notarize.sh`           | notarytool submit + staple (.app or .dmg) |
| `make_dmg.sh`           | Build + sign the DMG |
| `build_mas.sh`          | Sign (sandbox) + `productbuild` the MAS `.pkg` |

Bundle id: **`org.watnapahpong.etipitaka`** (set in `etipitaka.spec`). The MAS
App ID and provisioning profile must match it. (The legacy `pkg_osx.sh` /
`sign_app.sh` used `com.watnapp.etipitaka` — superseded by these scripts.)

Architecture: the default build is **arm64** (Apple Silicon), matching the
Homebrew Python + wxPython wheel. A **universal2** (arm64 + x86_64) build is
supported via `build_app.sh --universal2` — see "Universal2 build" below.

---

## Universal2 build (arm64 + x86_64)

PyInstaller builds a fat binary only when **every** input is fat: the Python
interpreter and every native wheel. The spec passes `target_arch=universal2`
when `ETIPITAKA_MAC_ARCH=universal2` is set (done for you by `--universal2`).

Prerequisites:

1. **A universal2 Python** — install the python.org macOS framework build of
   3.12 (universal2). The Homebrew Python is single-arch (arm64) and will NOT
   produce a fat app. `build_app.sh --universal2` defaults `PYBIN` to
   `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12`.
2. **Universal2 wheels** for the native deps. Install into the env used by that
   Python so pip/uv pick the `*_universal2.whl`:
   - `wxPython`, `Pillow`, `reportlab` ship universal2 wheels.
   - `pony`, `whoosh`, `xhtml2pdf`, `appdirs`, `packaging`, `requests` are pure
     Python (arch-agnostic).
   If any dep resolves to a thin (arm64-only) wheel, the build aborts naming the
   file — replace it with its universal2 wheel (or `pip install --platform
   macosx_11_0_universal2 --only-binary=:all:`).

Build + verify:

```bash
./packaging/macos/build_app.sh --universal2          # or: --mas --universal2
./packaging/macos/verify_arch.sh                     # confirms fat, lists thin libs
lipo -archs dist/E-Tipitaka.app/Contents/MacOS/e-tipitaka   # -> x86_64 arm64
```

Signing / notarizing / DMG / MAS steps below are identical for a universal2
`.app` — no changes needed.

---

## Path 1 — Developer ID notarized DMG

Certs needed (one-time, in your keychain): **Developer ID Application** and
(optional, for a `.pkg`) **Developer ID Installer**. Team ID `A6DJDJ7527`.

```bash
# 0. one-time: store notary credentials
xcrun notarytool store-credentials etipitaka-notary \
  --apple-id you@example.com --team-id A6DJDJ7527 --password <app-specific-pw>

# 1. build (updater stays ON for direct distribution)
./packaging/macos/build_app.sh

# 2. sign (hardened runtime + entitlements)
DEVID_APP_IDENTITY="Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" \
  ./packaging/macos/sign_devid.sh

# 3. DMG + notarize + staple
./packaging/macos/make_dmg.sh dist/E-Tipitaka.app 3.2.0
NOTARY_PROFILE=etipitaka-notary ./packaging/macos/notarize.sh dist/E-Tipitaka-3.2.0.dmg
```

Ship `dist/E-Tipitaka-3.2.0.dmg`. Gatekeeper passes (signed + notarized +
stapled).

---

## Path 2 — Mac App Store

Extra setup in the Apple Developer portal:

1. Register an **App ID** `org.watnapahpong.etipitaka`.
2. Create certs: **Apple Distribution** and **Mac Installer Distribution**
   (a.k.a. "3rd Party Mac Developer Installer").
3. Create a **Mac App Store provisioning profile** for that App ID; download it.
4. Create the app record in **App Store Connect**.

```bash
# 1. build with the Store toggle (disables the in-app exe/pkg self-updater,
#    which MAS forbids)
./packaging/macos/build_app.sh --mas

# 2. sign (sandbox) + package
MAS_PROVISION_PROFILE=path/to/etipitaka_mas.provisionprofile \
MAS_APP_IDENTITY="Apple Distribution: Sutee Sudprasert (A6DJDJ7527)" \
MAS_INSTALLER_IDENTITY="3rd Party Mac Developer Installer: Sutee Sudprasert (A6DJDJ7527)" \
  ./packaging/macos/build_mas.sh

# 3. upload dist/E-Tipitaka-mas.pkg via Transporter.app (or xcrun altool)
```

### Known risks / gotchas

- **App Sandbox** redirects the app's data dir into
  `~/Library/Containers/org.watnapahpong.etipitaka/Data/…`. The app stores user
  data via `appdirs` and copies the shipped SQLite DBs into the user dir on
  first run — this works inside the container, but existing non-sandboxed user
  data won't carry over.
- **Library validation stays ON for MAS** (the Developer ID exceptions are
  removed). Every bundled `.dylib`/`.so` must be signed with the Apple
  Distribution cert — `build_mas.sh` does this. If review still flags it, that
  is the classic PyInstaller + wxPython MAS friction.
- **wxPython review risk:** wx can reference deprecated/private APIs that App
  Review rejects. No guaranteed fix short of patching wx.
- **No self-update:** ensured by `--mas` (build.store.toml -> `store_build`).
- **Bump `CFBundleVersion`** in `etipitaka.spec` for every new upload — App
  Store Connect rejects a reused build number.
