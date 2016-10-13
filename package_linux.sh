#!/bin/bash

./clean.sh
cd ..
tar czvf $1 --exclude=".git" --exclude=".gitignore" --exclude=".DS_Store" E-Tipitaka-PC/ 
