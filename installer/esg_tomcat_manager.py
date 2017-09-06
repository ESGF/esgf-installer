'''
Tomcat Management Functions
'''
import os
import subprocess
import sys
import hashlib
import shutil
import grp
import datetime
import socket
import re
import pwd
import tarfile
import urllib
import shlex
import filecmp
import glob
import yaml
import progressbar
from time import sleep
from OpenSSL import crypto
from lxml import etree
import esg_functions
import esg_bash2py
import esg_property_manager
import esg_logging_manager


logger = esg_logging_manager.create_rotating_log(__name__)

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

pbar = None
downloaded = 0
def show_progress(count, block_size, total_size):
    global pbar
    global downloaded
    if pbar is None:
        pbar = progressbar.ProgressBar(maxval=total_size)

    downloaded += block_size
    pbar.update(block_size)
    if downloaded == total_size:
        pbar.finish()
        pbar = None
        downloaded = 0

# # Tomcat 8
# ENV TOMCAT_VERSION 8.5.20
#
# RUN wget -O /tmp/apache-tomcat-${TOMCAT_VERSION}.tar.gz http://mirror.reverse.net/pub/apache/tomcat/tomcat-8/v${TOMCAT_VERSION}/bin/apache-tomcat-${TOMCAT_VERSION}.tar.gz && \
#     cd /usr/local && tar xzf /tmp/apache-tomcat-${TOMCAT_VERSION}.tar.gz && \
#     ln -s /usr/local/apache-tomcat-${TOMCAT_VERSION} /usr/local/tomcat && \
#     rm /tmp/apache-tomcat-${TOMCAT_VERSION}.tar.gz
TOMCAT_VERSION = "8.5.20"


def download_tomcat():
    tomcat_download_url = "http://mirror.reverse.net/pub/apache/tomcat/tomcat-8/v{TOMCAT_VERSION}/bin/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(
        TOMCAT_VERSION=TOMCAT_VERSION)
    print "downloading Tomcat"
    urllib.urlretrieve(
        tomcat_download_url, "/tmp/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(TOMCAT_VERSION=TOMCAT_VERSION))


def extract_tomcat_tarball(dest_dir="/usr/local"):
    with esg_bash2py.pushd(dest_dir):
        esg_functions.extract_tarball(
            "/tmp/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(TOMCAT_VERSION=TOMCAT_VERSION))

        # Create symlink
        create_symlink(TOMCAT_VERSION)
        os.remove(
            "/tmp/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(TOMCAT_VERSION=TOMCAT_VERSION))


def create_symlink(TOMCAT_VERSION):
    esg_bash2py.symlink_force(
        "/usr/local/apache-tomcat-{TOMCAT_VERSION}".format(TOMCAT_VERSION=TOMCAT_VERSION), "/usr/local/tomcat")


# ENV CATALINA_HOME /usr/local/tomcat
#
# # remove Tomcat example applications
# RUN cd /usr/local/tomcat/webapps && \
#     rm -rf docs examples host-manager manager
#
# # copy custom configuration
# # server.xml: includes references to keystore, truststore in /esg/config/tomcat
# # context.xml: increases the Tomcat cache to avoid flood of warning messages
# COPY conf/server.xml /usr/local/tomcat/conf/server.xml
# COPY conf/context.xml /usr/local/tomcat/conf/context.xml
# COPY certs/ /esg/config/tomcat/
#
# # custom env variables for starting Tomcat
# COPY conf/setenv.sh $CATALINA_HOME/bin
#
# # create non-privilged user to run Tomcat
# RUN groupadd tomcat
# RUN useradd -s /sbin/nologin -g tomcat -d /usr/local/tomcat tomcat
# RUN chown -R tomcat:tomcat /usr/local/apache-tomcat-${TOMCAT_VERSION}
# RUN chmod 775 /usr/local/tomcat/webapps
#
# EXPOSE 8080
# EXPOSE 8443
#
# # startup
# COPY conf/supervisord.tomcat.conf /etc/supervisor/conf.d/supervisord.tomcat.conf
# CMD ["supervisord", "--nodaemon", "-c", "/etc/supervisord.conf"]
def main():
    download_tomcat()
    extract_tomcat_tarball()
    pass
if __name__ == '__main__':
    main()
