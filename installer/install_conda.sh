#!/bin/bash

#Bash strict mode
set -euo pipefail
IFS=$'\n\t'
# install Anaconda
CDAT_HOME=/usr/local/conda
cd /tmp && rm -rf $CDAT_HOME && \
    wget --no-check-certificate https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh && \
    sudo bash Miniconda2-latest-Linux-x86_64.sh -b -p $CDAT_HOME

# create CDAT virtual environment with Anaconda
PATH=${CDAT_HOME}/bin:$PATH
conda create -y -n esgf-pub -c conda-forge -c uvcdat cdutil

# activate virtual env and fetch some pre-requisites
# source ${CDAT_HOME}/bin/activate esgf-pub && \
#     conda install -y -c conda-forge lxml requests psycopg2 decorator Tempita myproxyclient
#
# # install other python pre-requisites
# source ${CDAT_HOME}/bin/activate esgf-pub && \
#     pip install SQLAlchemy==0.7.10 && \
#     pip install sqlalchemy_migrate && \
#     pip install esgprep
