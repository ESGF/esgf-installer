#!/bin/bash

# References
# http://kvz.io/blog/2013/11/21/bash-best-practices/
# http://jvns.ca/blog/2017/03/26/bash-quirks/

# exit when a command fails
set -o errexit

# exit if any pipe commands fail
set -o pipefail

create_docs_directory () {
  echo "Creating esgf-installer-docs directory"
  #Create esgf-installer-docs directory if it doesn't exist
  mkdir -p ../../esgf-installer-docs/
  pushd ../../esgf-installer-docs/
    git clone https://github.com/ESGF/esgf-installer.git -b gh-pages --single-branch html
    cd html || return

    #remove all existing files from gh-pages branch
    git symbolic-ref HEAD refs/heads/gh-pages
    rm .git/index
    #-d removes untracked directories and files; -x Don’t use the standard ignore rules read from .gitignore (per directory) and $GIT_DIR/info/exclude, but do still use the ignore rules given with -e options. This allows removing all untracked files, including build products.
    git clean --force -d -x

    #Peform a pull to update from remote branch
    git pull --force origin gh-pages
  popd
}

#If esgf-installer-docs directory doesn't exist, set it up
if [ ! -d ../../esgf-installer-docs/html ]; then
  create_docs_directory
fi

#Generate the new html pages for the documentation
make html

while getopts ":m:" opt; do
  case ${opt} in
    m) comment="$OPTARG"
      ;;
    \? ) echo "Usage: cmd [-m]"
      ;;
  esac
done


#Change to installer docs directory
pushd ../../esgf-installer-docs/html

#Add all html, js, module, and source files
git add *.html
git add *.js
git add _modules/*
git add _sources/*
git add *.inv
git add .buildinfo
git add .nojekyll
git add _static/*

#Commit message
if [ -z "$comment" ]
  then
    git commit -m 'updated autodocumentation'
  else
    git commit -m "$comment"
fi
#Push to Github Pages
git push -u origin gh-pages
