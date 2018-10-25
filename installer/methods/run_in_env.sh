#!/usr/bin/env bash

env_name=$1
cmd=$2
source activate $env_name && \
    args="$cmd"
    # Enquote args to avoid special character problems
    for arg in ${@:3}; do
      args="$args '$arg'"
    done
    eval "$args"
    rc=$?
conda deactivate
exit $rc
