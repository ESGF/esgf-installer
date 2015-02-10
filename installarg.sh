#!/bin/bash
#
# "Hello, I want to have an argument."
# "No you don't."
# "Yes, I do!"
#
# Sourceable code for handling options in ESGF install scripts.
#
# Source this from the main installer file at the point where argument
# parsing needs to happen.  For this to work, the main script MUST
# have two variables set at the top of the file:
#   VERSION=xxx
#   INSTALLPATH=xxx
#
# The following environment variables will be set for use by the
# sourcing script:
#   PRINT_NEW_VERSION
#   PRINT_OLD_VERSION
#   INSTALLPATH (only if option specified)
#
# If PRINT_NEW_VERSION or PRINT_OLD_VERSION is set to true, this
# fragment will print the detected version and immediately exit.
#
#
# Written by Zed Pobre <zed.pobre@nasa.gov> in 2015 as a work-for-hire
# for the US Federal Government.  This code is in the Public Domain.
#

# Helper function for printing a version number to stdout without any
# leading 'v'
echoversion () {
    echo "$@" | sed 's/^v*\(.*\)/\1/'
}

# First stage of option parsing
# (This doesn't actually set the variables until the eval below)
PARSED_OPTIONS=$(getopt -n "$0" -o '' --long "newversion,oldversion,installpath:" -- "$@")

#Bad arguments, something has gone wrong with the getopt command.
if [ $? -ne 0 ];
then
    echo "Option parsing failed!"
    exit 1
fi

# This actually converts the valid options back into arguments at the
# front of the list
eval set -- "$PARSED_OPTIONS"

# Now we go through all of those until we get '--'
# This will loop infinitely if the argument list isn't prepared
# properly, so don't forget to check that getopt was actually
# successfull first.
while [ -n "$1" ]; do
    case "$1" in

    --newversion)
        PRINT_NEW_VERSION=1
        shift;;

    --oldversion)
        PRINT_OLD_VERSION=1
        shift;;

    --installpath)
        # We need to actually check for an argument for this
        if [ -n "$2" ]; then
            INSTALLPATH=$2
        else
            echo "--installpath needs an argument"
            exit 2
        fi
        shift 2;;

    --)
        shift
        break;;
    esac
done


if [ $PRINT_NEW_VERSION ] ; then
    echoversion $VERSION
    exit 0
fi

if [ $PRINT_OLD_VERSION ] ; then
    if [ -f "${INSTALLPATH}/${0}" ] ; then
        OLDVERSION=$(grep '^VERSION=' "${INSTALLPATH}/${0}" | cut -d= -f2)
        echoversion $OLDVERSION
    else
        exit 1
    fi
    exit 0
fi
