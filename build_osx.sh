rm -rf build dist
rm -f config/*.fav config/history.log

pipenv run python setup.py py2app

