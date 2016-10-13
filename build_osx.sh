rm -rf build dist
rm -f config/*.fav config/history.log
export VERSIONER_PYTHON_PREFER_32_BIT=yes
ARCHFLAGS="-arch i386 -arch x86_64" arch -i386 python setup.py py2app --arch i386 

# code signing

#codesign -s "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libwx_osx_carbonu-3.0.0.2.0.dylib
codesign -s "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libwx_macud-2.8.0.8.0.dylib
codesign -s "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/libwx_macud-2.8.0.dylib
codesign -s "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/Frameworks/Python.framework
codesign -s "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app/Contents/MacOS/python
codesign -s "Developer ID Application: Sutee Sudprasert (A6DJDJ7527)" dist/E-Tipitaka.app

# verify code signing

codesign -vvv -d dist/E-Tipitaka.app

#ditto --rsrc --arc i386 dist/E-Tipitaka.app dist/E-Tipitaka-32bit.app
#rm -rf dist/E-Tipitaka.app
#mv dist/E-Tipitaka-32bit.app dist/E-Tipitaka.app
