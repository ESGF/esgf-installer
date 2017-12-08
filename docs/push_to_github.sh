#!/bin/bash

#Change to installer docs directory
pushd ../../esgf-installer-docs/html

#Add all html, js, module, and source files
git add *.html
git add *.js
git add _modules/*
git add _sources/*

git commit -m 'updated autodocumentation'

git push
