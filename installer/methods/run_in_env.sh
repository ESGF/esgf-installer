#!/usr/bin/env bash

env_name=$1
source activate $env_name && \
    eval ${@:2}
conda deactivate
