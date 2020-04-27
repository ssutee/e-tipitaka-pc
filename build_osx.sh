rm -rf build dist
rm -f config/*.fav config/history.log

pipenv run python setup.py py2app

# code signing
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/Python.framework
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libcrypto.1.0.0.dylib
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libgdbm.6.dylib
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libjpeg.9.dylib
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/liblzma.5.dylib
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libopenjp2.2.3.1.dylib
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libsqlite3.0.dylib
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libssl.1.0.0.dylib
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libtiff.5.dylib
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libz.1.2.11.dylib
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/MacOS/python
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/MacOS/E-Tipitaka
codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app

# verify code signing
codesign -vvv -d dist/E-Tipitaka.app

productbuild --component dist/E-Tipitaka.app /Applications --sign "Developer ID Installer: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.pkg
