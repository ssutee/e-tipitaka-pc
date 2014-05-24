rm -rf build dist
rm -f config/*.fav config/history.log
export VERSIONER_PYTHON_PREFER_32_BIT=yes
ARCHFLAGS="-arch i386 -arch x86_64" arch -i386 python setup.py py2app
ditto --rsrc --arc i386 dist/E-Tipitaka.app dist/E-Tipitaka-32bit.app
rm -rf dist/E-Tipitaka.app
mv dist/E-Tipitaka-32bit.app dist/E-Tipitaka.app
