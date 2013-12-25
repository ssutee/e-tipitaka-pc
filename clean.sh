#!/bin/bash

rm -rf dist build
find . -regex ".*\.pyc" -exec rm -f {} \;
