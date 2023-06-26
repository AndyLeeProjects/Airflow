#!/bin/bash

rm -rf automation_scripts data
mkdir automation_scripts
touch file_1.txt && mkdir data && mv file_1.txt data
mv *_*.py automation_scripts
