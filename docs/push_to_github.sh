#!/bin/bash


# while getopts ":m" opt; do
#   case ${opt} in
#     m ) # process option a
#       ;;
#     \? ) echo "Usage: cmd [-m]"
#       ;;
#   esac
# done

#Change to installer docs directory
pushd ../../esgf-installer-docs/html

#Add all html, js, module, and source files
git add *.html
git add *.js
git add _modules/*
git add _sources/*
git add *.inv

git commit -m 'updated autodocumentation'

git push
