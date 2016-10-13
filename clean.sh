#!/bin/bash

rm -rf dist build error.log
find . -regex ".*\.pyc" -exec rm -f {} \;
