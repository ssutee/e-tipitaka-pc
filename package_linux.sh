#!/bin/bash

./clean.sh
cd ..
tar czvf $1 --exclude=".git" --exclude=".gitignore" --exclude=".DS_Store" --exclude="run.sh" --exclude=".eggs" E-Tipitaka-PC/ 
