rm -rf build dist
rm -f config/*.fav config/history.log

pipenv run python setup.py py2app

cp -f /usr/local/opt/xz/lib/liblzma.5.dylib dist/E-Tipitaka.app/Contents/Framworks

