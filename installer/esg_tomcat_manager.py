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
import errno
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
CATALINA_HOME = "/usr/local/tomcat"

def download_tomcat():
    if os.path.isdir("/usr/local/tomcat"):
        print "Tomcat directory found.  Skipping installation."
        return
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
        try:
            os.remove(
                "/tmp/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(TOMCAT_VERSION=TOMCAT_VERSION))
        except OSError, error:
            print "error:", error
            pass


def create_symlink(TOMCAT_VERSION):
    esg_bash2py.symlink_force(
        "/usr/local/apache-tomcat-{TOMCAT_VERSION}".format(TOMCAT_VERSION=TOMCAT_VERSION), "/usr/local/tomcat")


# ENV CATALINA_HOME /usr/local/tomcat
#
def remove_example_webapps():
# # remove Tomcat example applications
    with esg_bash2py.pushd("/usr/local/tomcat/webapps"):
        try:
            shutil.rmtree("docs")
            shutil.rmtree("examples")
            shutil.rmtree("host-manager")
            shutil.rmtree("manager")
        except OSError, error:
            if error.errno == errno.ENOENT:
                pass
            else:
                print "error:", error
# RUN cd /usr/local/tomcat/webapps && \
#     rm -rf docs examples host-manager manager
#
def copy_config_files():
# # copy custom configuration
# # server.xml: includes references to keystore, truststore in /esg/config/tomcat
# # context.xml: increases the Tomcat cache to avoid flood of warning messages
    shutil.copyfile("tomcat_conf/server.xml", "/usr/local/tomcat/conf/server.xml")
    shutil.copyfile("tomcat_conf/context.xml", "/usr/local/tomcat/conf/context.xml")
    shutil.copytree("certs/", "/esg/config/tomcat")

    shutil.copy("tomcat_conf/setenv.sh", os.path.join(CATALINA_HOME, "bin"))
# COPY conf/server.xml /usr/local/tomcat/conf/server.xml
# COPY conf/context.xml /usr/local/tomcat/conf/context.xml
# COPY certs/ /esg/config/tomcat/
#
# # custom env variables for starting Tomcat
# COPY conf/setenv.sh $CATALINA_HOME/bin
#
def create_tomcat_user():
    esg_functions.call_subprocess("groupadd tomcat")
    esg_functions.call_subprocess("useradd -s /sbin/nologin -g tomcat -d /usr/local/tomcat tomcat")
    tomcat_directory = "/usr/local/apache-tomcat-{TOMCAT_VERSION}".format(TOMCAT_VERSION=TOMCAT_VERSION)
    tomcat_user_id = pwd.getpwnam("tomcat").pw_uid
    tomcat_group_id = grp.getgrnam("tomcat").gr_gid
    esg_functions.change_permissions_recursive(tomcat_directory, tomcat_user_id, tomcat_group_id)

    os.chmod("/usr/local/tomcat/webapps", 0775)

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
    remove_example_webapps()
    copy_config_files()
    create_tomcat_user()
    # pass
if __name__ == '__main__':
    main()
