#!/bin/bash

# References
# http://kvz.io/blog/2013/11/21/bash-best-practices/
# http://jvns.ca/blog/2017/03/26/bash-quirks/

# exit when a command fails
set -o errexit

# exit if any pipe commands fail
set -o pipefail

set -E
set -o functrace
function handle_error {
    local retval=$?
    local line=${last_lineno:-$1}
    echo "Failed at $line: $BASH_COMMAND"
    echo "Trace: " "$@"
    echo "return code: " "$?"
    exit $retval
 }
trap 'handle_error $LINENO ${BASH_LINENO[@]}' ERR


install_miniconda(){
  # install Anaconda
  echo
  echo "-----------------------------------"
  echo "Installing Miniconda"
  echo "-----------------------------------"
  echo
  CONDA_HOME=/usr/local/conda

  pushd /tmp &&
    rm -rf $CONDA_HOME && \
        wget --no-check-certificate https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh && \
        sudo bash Miniconda2-latest-Linux-x86_64.sh -b -p $CONDA_HOME

        # create CDAT virtual environment with Anaconda
        echo
        echo "-----------------------------------"
        echo "Creating conda environment: esgf-installer"
        echo "-----------------------------------"
        echo
        PATH=${CONDA_HOME}/bin:$PATH
        conda create -y -n esgf-installer "python<3"

  popd

}

install_dependencies_pip(){
  echo
  echo "-----------------------------------"
  echo "Installing dependencies from pip"
  echo "-----------------------------------"
  echo
  # activate virtual env and fetch some pre-requisites
  source ${CONDA_HOME}/bin/activate esgf-installer && \

  # install other python pre-requisites
      pip install --upgrade pip
      pip install plumbum psycopg2 requests configparser

  source deactivate

}

install_dependencies_yum(){
  #install dependencies from yum
  echo
  echo "-----------------------------------"
  echo "Installing dependencies from yum"
  echo "-----------------------------------"
  echo

  yum -y remove rpmforge-release
  yum -y install epel-release

  yum -y install yum-plugin-priorities gcc gcc-c++ make automake autoconf wget

}

install_dependencies_yum; 
install_miniconda; 
install_dependencies_pip;
echo "Bootstrap complete!"