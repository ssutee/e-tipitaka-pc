#!/bin/bash

pkgbuild --root ./dist/E-Tipitaka.app --identifier "com.watnapp.etipitaka" --sign "Developer ID Installer: Sutee Sudprasert (A6DJDJ7527)" --install-location Applications/E-Tipitaka.app ./dist/E-Tipitaka.pkg

#productbuild --distribution ./Distribution.xml --package-path ./dist/E-Tipitaka.pkg ./dist/E-Tipitaka-Installer.pkg
#productsign --sign "Developer ID Installer: Sutee Sudprasert (A6DJDJ7527)" ./dist/E-Tipitaka-Installer.pkg ./dist/E-Tipitaka-Installer-Signed.pkg
