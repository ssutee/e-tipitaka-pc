#!/usr/bin/env python3
"""Generate MSIX tile/logo PNGs for the Microsoft Store build.

Resizes a single high-resolution square source (default the 1024px
resources/e-tipitaka.icns) down to every logo size the AppxManifest
references. Square tiles are a straight high-quality resize; the wide
tile centres the square logo on a transparent canvas.

Usage:
    python packaging/msix/make_assets.py [source_image]

Output: packaging/msix/Assets/*.png
"""

import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
ASSETS_DIR = os.path.join(HERE, 'Assets')

DEFAULT_SOURCE = os.path.join(PROJECT_ROOT, 'resources', 'e-tipitaka.icns')

# filename -> (width, height). Square entries resize the source directly;
# non-square entries centre the resized square logo on a transparent canvas.
TARGETS = {
    'Square44x44Logo.png': (44, 44),
    'Square71x71Logo.png': (71, 71),
    'Square150x150Logo.png': (150, 150),
    'Square310x310Logo.png': (310, 310),
    'StoreLogo.png': (50, 50),
    'Wide310x150Logo.png': (310, 150),
}


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE
    if not os.path.exists(source):
        sys.exit('source image not found: %s' % source)

    src = Image.open(source).convert('RGBA')
    if src.width != src.height:
        print('warning: source is not square (%dx%d); tiles may look off'
              % src.size)

    os.makedirs(ASSETS_DIR, exist_ok=True)
    for name, (w, h) in sorted(TARGETS.items()):
        if w == h:
            out = src.resize((w, h), Image.LANCZOS)
        else:
            side = min(w, h)
            logo = src.resize((side, side), Image.LANCZOS)
            out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            out.paste(logo, ((w - side) // 2, (h - side) // 2), logo)
        path = os.path.join(ASSETS_DIR, name)
        out.save(path, 'PNG')
        print('wrote %s (%dx%d)' % (os.path.relpath(path, PROJECT_ROOT), w, h))


if __name__ == '__main__':
    main()
