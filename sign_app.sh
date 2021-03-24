# code signing
cp -f ./liblzma.5.dylib dist/E-Tipitaka.app/Contents/Frameworks
codesign --deep --force --verify --no-strict --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app

# verify code signing
codesign -vvv -d dist/E-Tipitaka.app
