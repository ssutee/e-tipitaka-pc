# -*- mode: python ; coding: utf-8 -*-
# Cross-platform PyInstaller spec (onedir). Bundles the full resources/ and
# fonts/ directories. Builds a .app on macOS, a folder elsewhere.
import os
import sys

# ---------------------------------------------------------------------------
# Build-time feature toggles (build.toml, gitignored; see build.toml.example).
# Same file is also read by constants.py at runtime so the UI hides whatever
# this section excludes from the bundle.
# ---------------------------------------------------------------------------
try:
    import tomllib
except ImportError:
    import tomli as tomllib

_build_cfg = {}
if os.path.exists('build.toml'):
    with open('build.toml', 'rb') as _f:
        _build_cfg = tomllib.load(_f)
_features = _build_cfg.get('features', {}) or {}

# Microsoft Store (MSIX) build. On Windows this forces a one-dir payload
# (folder of files) instead of the one-file .exe — MSIX expects a directory
# layout and the one-file bootloader's per-launch temp extraction fights the
# Store container. macOS/Linux are unaffected. See packaging/msix/.
_store_build = bool(_features.get('store_build', False))

# Per-feature exclusion lists. Add new toggles by extending these.
_excluded_resource_files = set()
if not _features.get('include_thaiwn', True):
    _excluded_resource_files.add('thaiwn.sqlite')

# Build the `datas` list. Normally we just bundle the whole `resources/`
# directory in one tuple; when something needs to be omitted we expand the
# top-level files into individual entries so the excluded ones can be
# skipped. Subdirectories under `resources/` are always bundled whole.
if not _excluded_resource_files:
    datas = [('resources', 'resources'), ('fonts', 'fonts')]
else:
    datas = [('fonts', 'fonts')]
    for entry in sorted(os.listdir('resources')):
        full = os.path.join('resources', entry)
        if os.path.isfile(full):
            if entry in _excluded_resource_files:
                continue
            datas.append((full, 'resources'))
        elif os.path.isdir(full):
            datas.append((full, os.path.join('resources', entry)))

# Ship the build.toml itself when present so constants.py at runtime applies
# the same gates (UI must hide what the bundle omits).
if os.path.exists('build.toml'):
    datas.append(('build.toml', '.'))

print('[etipitaka.spec] features=%r excluded=%r' % (_features, _excluded_resource_files))

hiddenimports = [
    'wx.adv', 'wx.html', 'wx.xml', 'wx.richtext', 'wx.grid',
    'wx.lib.agw.aui', 'wx.lib.buttons', 'wx.lib.splitter',
    'wx.lib.embeddedimage',
    'pony.orm.dbproviders.sqlite',
    'reportlab.graphics.barcode.common',
    'reportlab.graphics.barcode.code128',
    'reportlab.graphics.barcode.code93',
    'reportlab.graphics.barcode.code39',
    'reportlab.graphics.barcode.usps',
    'reportlab.graphics.barcode.usps4s',
    'reportlab.graphics.barcode.eanbc',
    'reportlab.graphics.barcode.fourstate',
    'reportlab.graphics.barcode.ecc200datamatrix',
]

a = Analysis(
    ['run.py'],
    pathex=[SPECPATH],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

# Windows MSIX builds take the one-dir path (COLLECT) below alongside macOS.
_win_msix = sys.platform == 'win32' and _store_build

if sys.platform in ('win32', 'linux') and not _win_msix:
    # Windows + Linux: single-file executable (resources bundled inside,
    # extracted to a tmpdir on each launch). macOS sticks with the one-dir
    # `.app` bundle below — codesigning + notarization expect the dir layout.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='e-tipitaka',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,
        console=False,
        icon='resources/e-tri_64_icon.ico',
    )
else:
    # macOS: one-dir bundle wrapped in BUNDLE -> .app.
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='e-tipitaka',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon='resources/e-tri_64_icon.ico',
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name='e-tipitaka',
    )

    if sys.platform == 'darwin':
        app = BUNDLE(
            coll,
            name='E-Tipitaka.app',
            icon='resources/e-tipitaka.icns',
            bundle_identifier='org.watnapahpong.etipitaka',
            info_plist={
                'NSRequiresAquaSystemAppearance': True,
                'NSHighResolutionCapable': True,
                'CFBundleShortVersionString': '3.2.0',
            },
        )
