#!/bin/bash

xgettext --language=Python --keyword=_ --output=locale/E-Tipitaka.pot --from-code=UTF-8 `find . -name "*.py"`
