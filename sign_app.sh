# code signing
#codesign --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/*
#codesign --deep --force --verify --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/MacOS/*
codesign --deep --force --verify --no-strict --verbose --sign "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app

# verify code signing
codesign -vvv -d dist/E-Tipitaka.app
