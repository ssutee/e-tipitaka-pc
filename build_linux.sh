#!/bin/sh

pyinstaller \
    --hidden-import wx.adv \
    --hidden-import wx.html \
    --hidden-import wx.xml \
    --hidden-import pony.orm.dbproviders.sqlite \
    --hidden-import reportlab.graphics.barcode.common \
    --hidden-import reportlab.graphics.barcode.code128 \
    --hidden-import reportlab.graphics.barcode.code93 \
    --hidden-import reportlab.graphics.barcode.code39 \
    --hidden-import reportlab.graphics.barcode.usps \
    --hidden-import reportlab.graphics.barcode.usps4s \
    --hidden-import reportlab.graphics.barcode.eanbc \
    --hidden-import reportlab.graphics.barcode.fourstate \
    --hidden-import reportlab.graphics.barcode.ecc200datamatrix \
    -y -w -n e-tipitaka-gtk --onefile run.py

mkdir -p dist/e-tipitaka
mv dist/e-tipitaka-gtk dist/e-tipitaka/e-tipitaka
cp -r resources dist/e-tipitaka
cp -r fonts dist/e-tipitaka
