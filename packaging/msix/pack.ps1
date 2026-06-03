<#
.SYNOPSIS
  Assemble and pack the E-Tipitaka MSIX from an existing one-dir PyInstaller
  build (dist\e-tipitaka\). Produces an UNSIGNED dist\e-tipitaka.msix —
  Partner Center re-signs on upload.

.DESCRIPTION
  Used by the GitLab `package:msix` job and runnable locally on Windows after
  `pyinstaller etipitaka.spec` with build.store.toml in place. Identity values
  come from parameters or the matching MSIX_* environment variables.
#>
param(
  [string]$IdentityName        = $env:MSIX_IDENTITY_NAME,
  [string]$Publisher           = $env:MSIX_PUBLISHER,
  [string]$PublisherDisplayName = $env:MSIX_PUBLISHER_DISPLAY_NAME,
  [string]$Version             = $(if ($env:MSIX_VERSION) { $env:MSIX_VERSION } else { "3.2.0.0" })
)

$ErrorActionPreference = "Stop"
$root  = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent  # project root
$stage = Join-Path $root "build\msix"
$payload = Join-Path $root "dist\e-tipitaka"

if (-not (Test-Path $payload)) {
  throw "payload not found: $payload (run pyinstaller etipitaka.spec with build.store.toml first)"
}
foreach ($v in @($IdentityName, $Publisher, $PublisherDisplayName)) {
  if ([string]::IsNullOrWhiteSpace($v)) {
    throw "missing identity value — set MSIX_IDENTITY_NAME, MSIX_PUBLISHER, MSIX_PUBLISHER_DISPLAY_NAME"
  }
}

# 1. Layout: app payload + assets + manifest.
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory "$stage\app" | Out-Null
Copy-Item "$payload\*" "$stage\app" -Recurse
Copy-Item (Join-Path $PSScriptRoot "Assets") "$stage\Assets" -Recurse

# 2. Fill manifest tokens.
$manifest = Get-Content (Join-Path $PSScriptRoot "AppxManifest.xml")
$manifest = $manifest -replace '__IDENTITY_NAME__', $IdentityName
$manifest = $manifest -replace '__PUBLISHER__', $Publisher
$manifest = $manifest -replace '__PUBLISHER_DISPLAY_NAME__', $PublisherDisplayName
$manifest = $manifest -replace '__VERSION__', $Version
$manifest | Set-Content "$stage\AppxManifest.xml" -Encoding UTF8

# 3. Pack with the newest makeappx from the Windows SDK (unsigned).
$makeappx = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\makeappx.exe" |
  Sort-Object FullName | Select-Object -Last 1
if (-not $makeappx) { throw "makeappx.exe not found — install the Windows SDK" }

$out = Join-Path $root "dist\e-tipitaka.msix"
New-Item -ItemType Directory (Join-Path $root "dist") -Force | Out-Null
& $makeappx.FullName pack /d $stage /p $out /o
Write-Host "packed: $out"
