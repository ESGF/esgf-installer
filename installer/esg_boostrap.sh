#!/bin/bash

#Bash strict mode
set -euo pipefail
IFS=$'\n\t'

# install Anaconda
echo
echo "-----------------------------------"
echo "Installing Miniconda"
echo "-----------------------------------"
echo
CDAT_HOME=/usr/local/conda
cd /tmp && rm -rf $CDAT_HOME && \
    wget --no-check-certificate https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh && \
    sudo bash Miniconda2-latest-Linux-x86_64.sh -b -p $CDAT_HOME

# create CDAT virtual environment with Anaconda
echo
echo "-----------------------------------"
echo "Creating conda environment: esgf-pub"
echo "-----------------------------------"
echo
PATH=${CDAT_HOME}/bin:$PATH
conda create -y -n esgf-pub -c conda-forge -c uvcdat cdutil

# activate virtual env and fetch some pre-requisites
source ${CDAT_HOME}/bin/activate esgf-pub && \
    conda install -y -c conda-forge lxml requests psycopg2 decorator Tempita myproxyclient

# install other python pre-requisites
source ${CDAT_HOME}/bin/activate esgf-pub && \
    pip install SQLAlchemy==0.7.10 && \
    pip install sqlalchemy_migrate && \
    pip install esgprep && \
    pip install -r requirements.txt


#install dependencies from yum
echo
echo "-----------------------------------"
echo "Installing dependencies from yum"
echo "-----------------------------------"
echo

yum -y remove rpmforge-release
yum -y install epel-release

[ $? != 0 ] && printf "[FAIL] \n\tCould not configure epel repository\n\n" && return 1

yum -y install yum-plugin-priorities sqlite-devel freetype-devel git \
curl-devel autoconf automake bison file flex gcc gcc-c++ gettext-devel \
libtool uuid-devel libuuid-devel libxml2 libxml2-devel libxslt libxslt-devel \
lsof make openssl-devel pam-devel pax readline-devel tk-devel wget zlib-devel \
perl-Archive-Tar perl-XML-Parser libX11-devel libtool-ltdl-devel e2fsprogs-devel \
gcc-gfortran libicu-devel libgtextutils-devel httpd httpd-devel mod_ssl libjpeg-turbo-devel *ExtUtils*

[ $? != 0 ] && printf "[FAIL] \n\tFailed to installed all dependencies from yum\n\n" && return 1
