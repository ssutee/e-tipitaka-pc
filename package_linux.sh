#!/bin/bash

./clean.sh
cd ..
tar czvf $1 --exclude=".git" E-Tipitaka-PC/ 
