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
  if [ -d "/usr/local/conda" ]; then
    echo
    echo "-----------------------------------"
    echo "Miniconda already installed."
    echo "-----------------------------------"
    echo
    echo
    echo "-----------------------------------"
    echo "Installing dependencies to conda environment: esgf-pub"
    echo "-----------------------------------"
    echo
    /usr/local/conda/bin/conda install -y -n esgf-pub cdutil cmor -c pcmdi/label/nightly -c conda-forge
    return 0
  fi

  echo
  echo "-----------------------------------"
  echo "Installing Miniconda"
  echo "-----------------------------------"
  echo
  CDAT_HOME=/usr/local/conda

  pushd /tmp &&
    rm -rf $CDAT_HOME && \
        wget --no-check-certificate https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh && \
        sudo bash Miniconda2-latest-Linux-x86_64.sh -b -p $CDAT_HOME

        # create CDAT virtual environment with Anaconda
        echo
        echo "-----------------------------------"
        echo "Creating conda environment: esgf-pub"
        echo "-----------------------------------"
        echo
        PATH=${CDAT_HOME}/bin:$PATH
        conda create -y -n esgf-pub "python<3" cdutil cmor -c pcmdi/label/nightly -c conda-forge
  popd

}

install_dependencies_pip(){
  echo
  echo "-----------------------------------"
  echo "Installing dependencies from pip"
  echo "-----------------------------------"
  echo
  # activate virtual env and fetch some pre-requisites
  CDAT_HOME=/usr/local/conda
  source ${CDAT_HOME}/bin/activate esgf-pub && \

      pip install --upgrade pip
      pip install coloredlogs GitPython progressbar2 pyOpenSSL \
                  lxml requests psycopg2 decorator Tempita \
                  setuptools semver Pyyaml configparser psutil
      pip install -r requirements.txt

  source ${CDAT_HOME}/bin/deactivate

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

  yum -y install yum-plugin-priorities sqlite-devel freetype-devel git \
  curl-devel autoconf automake bison file flex gcc gcc-c++ gettext-devel \
  libtool uuid-devel libuuid-devel libxml2 libxml2-devel libxslt libxslt-devel \
  lsof make openssl-devel pam-devel pax readline-devel tk-devel wget zlib-devel \
  perl-Archive-Tar perl-XML-Parser libX11-devel libtool-ltdl-devel e2fsprogs-devel \
  gcc-gfortran libicu-devel libgtextutils-devel httpd httpd-devel mod_ssl libjpeg-turbo-devel *ExtUtils*

}

copy_autoinstall_file(){
  echo
  echo "-----------------------------------"
  echo "Copying esgf.properties.template to /esg/config/esgf.properties"
  echo "-----------------------------------"
  echo
  mkdir -p /esg/config
  cp -v esgf.properties.template /esg/config/esgf.properties

}

run_migration_script(){
  if [ -e "/usr/local/bin/esg-node" ] && [ $1 == "migrate" ]; then
    source /usr/local/conda/bin/activate esgf-pub
    echo
    echo "-----------------------------------"
    echo "Running ESGF 2->3 migration script"
    echo "-----------------------------------"
    echo
      python migration_backup_script.py
    source ${CDAT_HOME}/bin/deactivate
  fi
}


if [ ! -d "/usr/local/conda" ] || [ $1 == "migrate" ]; then
    install_dependencies_yum && install_miniconda && install_dependencies_pip && run_migration_script && copy_autoinstall_file
    echo "Bootstrap complete!"
fi
