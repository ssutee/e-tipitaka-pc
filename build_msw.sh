#!/bin/sh

pyinstaller \
    --hidden-import tkinter \
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
    -y -w -n e-tipitaka run.py

cp -r resources dist/e-tipitaka
cp -r fonts dist/e-tipitaka
