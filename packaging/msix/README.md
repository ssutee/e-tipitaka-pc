# Microsoft Store (MSIX) packaging

Turns the Windows PyInstaller build into an `.msix` for the Microsoft Store.

## What this directory holds

| File | Purpose |
|------|---------|
| `AppxManifest.xml` | Package manifest with `__TOKENS__` filled at pack time |
| `pack.ps1`         | Assembles the layout, fills tokens, runs `makeappx` |
| `make_assets.py`   | Generates tile/logo PNGs from `resources/e-tipitaka.icns` |
| `Assets/`          | Generated logos (regenerate with `make_assets.py`) |

The Store build is driven by `../../build.store.toml` (`store_build = true`),
which makes:

- `etipitaka.spec` emit a **one-dir** payload (`dist/e-tipitaka/`) instead of
  the one-file `.exe` (MSIX wants a folder; one-file's temp extraction fights
  the Store container), and
- `constants.py` suppress the in-app exe self-update prompt (Store policy
  forbids an app updating its own code). The online **database** patcher keeps
  working — it downloads data, not code.

## One-time setup

1. **Partner Center account** — register at <https://partner.microsoft.com>
   (~US$19 one-time individual fee). Create the app, reserve the name. Note:
   - `Package/Identity/Name`
   - `Package/Identity/Publisher` (e.g. `CN=ABCD1234-...`)
   - `Publisher display name`

2. These become the `__IDENTITY_NAME__`, `__PUBLISHER__`,
   `__PUBLISHER_DISPLAY_NAME__` tokens in `AppxManifest.xml`.

## Build + pack locally (on Windows)

```powershell
# 1. Build the one-dir Store payload
Copy-Item build.store.toml build.toml
uv sync --python 3.12
uv run pyinstaller etipitaka.spec --noconfirm --clean   # -> dist\e-tipitaka\

# 2. Assemble + pack (fills the manifest tokens, runs makeappx). Identity
#    values can be passed as params or via MSIX_* env vars.
packaging\msix\pack.ps1 `
  -IdentityName        "<your Identity Name>" `
  -Publisher           "CN=<your Publisher>" `
  -PublisherDisplayName "<your display name>" `
  -Version             "3.2.0.0"
# -> dist\e-tipitaka.msix  (unsigned)
```

### Test the package on your own machine

Store re-signs on submission, but to *install locally* you must sign with a
cert your machine trusts:

```powershell
# self-signed cert whose subject MATCHES the manifest Publisher exactly
New-SelfSignedCertificate -Type Custom -Subject "CN=<your Publisher>" `
  -KeyUsage DigitalSignature -CertStoreLocation "Cert:\CurrentUser\My" `
  -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3")
# export to test.pfx, trust it under LocalMachine\TrustedPeople, then:
$sign = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" |
        Sort-Object FullName | Select-Object -Last 1
& $sign.FullName sign /fd SHA256 /a /f test.pfx /p <pwd> dist\e-tipitaka.msix
Add-AppxPackage dist\e-tipitaka.msix
```

## Submit to the Store

Upload the **unsigned** `.msix` (from step 4) in Partner Center > your app >
**Packages**. The Store signs it with the trusted Store certificate. Then fill
the listing (Thai description, screenshots, age rating, privacy policy URL) and
submit for certification. The Identity in the manifest must match the values
Partner Center assigned, or the upload is rejected.

## Regenerate logos

```bash
python packaging/msix/make_assets.py            # uses resources/e-tipitaka.icns
python packaging/msix/make_assets.py path/to/source.png
```
