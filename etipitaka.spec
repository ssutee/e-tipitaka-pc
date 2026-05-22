# -*- mode: python ; coding: utf-8 -*-
# Cross-platform PyInstaller spec (onedir). Bundles the full resources/ and
# fonts/ directories. Builds a .app on macOS, a folder elsewhere.
import sys

datas = [('resources', 'resources'), ('fonts', 'fonts')]

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
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

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
        bundle_identifier='org.watnapahpong.etipitaka',
        info_plist={
            'NSRequiresAquaSystemAppearance': True,
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '3.2.0',
        },
    )
