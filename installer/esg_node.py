import os
import subprocess
import requests
import sys
import pip
import hashlib
import shutil
import grp
import datetime
import logging
import socket
import urlparse
import argparse
import platform
import re
import pwd
import psycopg2
import tarfile
import urllib
import shlex
import errno
import fileinput
import xmltodict
import untangle
import filecmp
import glob
import xml.etree.ElementTree
import git
import ca_py
from git import Repo
from collections import deque
from esg_exceptions import UnprivilegedUserError, WrongOSError, UnverifiedScriptError
from time import sleep
from OpenSSL import crypto
from lxml import etree
import esg_functions
import esg_bash2py
import esg_setup
import esg_postgres
import esg_publisher
import esg_cli_argument_manager
import esg_tomcat_manager
import esg_version_manager
import esg_mirror_manager
import esg_apache_manager
from esg_init import EsgInit


logging.basicConfig(format = "%(levelname): %(lineno)s %(funcName)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = EsgInit()

logger.info("keystore_alias: %s", config.config_dictionary["keystore_alias"])
# os.environ['DISCOVERONLY'] = Expand.colonMinus("DISCOVERONLY")
os.environ['LANG'] = "POSIX"
os.umask(022)

DEBUG = esg_bash2py.Expand.colonMinus("DEBUG", False)
VERBOSE = esg_bash2py.Expand.colonMinus("VERBOSE", "0")
INSTALL_BIT=1
TEST_BIT=2
DATA_BIT=4
INDEX_BIT=8
IDP_BIT=16
COMPUTE_BIT=32
WRITE_ENV_BIT=64
#PRIVATE_BIT=128
#NOTE: remember to adjust (below) when adding new bits!!
MIN_BIT=4
MAX_BIT=64
ALL_BIT=DATA_BIT+INDEX_BIT+IDP_BIT+COMPUTE_BIT


# bit_boolean_dictionary = "INSTALL_BIT": False , "TEST_BIT": False, "DATA_BIT":False, "INDEX_BIT":False, "IDP_BIT":False, "COMPUTE_BIT":False, "WRITE_ENV_BIT":False, "MIN_BIT":4, "MAX_BIT":64, "ALL_BIT":False}
install_mode = 0
upgrade_mode = 0

node_type_bit = 0



devel = esg_bash2py.Expand.colonMinus("devel", True)
recommended_setup = 1
custom_setup = 0
use_local_files = 0

progname = "esg-node"
script_version = "v2.0-RC5.4.0-devel"
script_maj_version = "2.0"
script_release = "Centaur"
envfile = "/etc/esg.env"
force_install = False


#--------------
# User Defined / Settable (public)
#--------------
# install_prefix=${install_prefix:-${ESGF_INSTALL_PREFIX:-"/usr/local"}}
install_prefix = esg_bash2py.Expand.colonMinus(
    config.install_prefix, esg_bash2py.Expand.colonMinus("ESGF_INSTALL_PREFIX", "/usr/local"))
#--------------

# os.environ['UVCDAT_ANONYMOUS_LOG'] = False

esg_root_id = esg_functions.get_esg_root_id()


def setup_sensible_confs():
    pass

def install_local_certs():
    pass

def generate_esgf_csrs():
    pass

def generate_esgf_csrs_ext():
    pass
def cert_howto():
    pass

def test_postgress():
    pass
def test_cdat():
    pass
def test_tomcat():
    pass
def test_tds():
    pass
def show_type():
    pass
def start(node_bit):
    pass
def stop(node_bit):
    pass
def get_node_status():
    ''' 
        Return a tuple with the node's status and a numeric return code
    '''
    pass
def update_script(script_name, script_directory):
    '''
        arg (1) - name of installation script root name. Ex:security which resolves to script file esg-security
        arg (2) - directory on the distribution site where script is fetched from Ex: orp
        usage: update_script security orp - looks for the script esg-security in the distriubtion directory "orp"
    '''
    pass


def verify_esg_node_script(esg_dist_url_root, update_action = None):
    ''' Verify the esg_node script is the most current version '''
    # Test to see if the esg-node script is currently being pulled from git, and if so skip verification
    if esg_functions.is_in_git(os.path.basename(__file__)) == 0:
        logger.info("Git repository detected; not checking checksum of esg-node")
        return

    if "devel" in script_version:
        devel = True
        remote_url = "{esg_dist_url_root}/esgf-installer/{script_maj_version}".format(esg_dist_url_root = esg_dist_url_root, script_maj_version = script_maj_version)
    else:
        devel = False
        remote_url = "{esg_dist_url_root}/devel/esgf-installer/{script_maj_version}".format(esg_dist_url_root = esg_dist_url_root, script_maj_version = script_maj_version)
    try:
        esg_functions._verify_against_mirror(remote_url, script_maj_version)
    except UnverifiedScriptError:
        logger.info('''WARNING: %s could not be verified!! \n(This file, %s, may have been tampered
            with or there is a newer version posted at the distribution server.
            \nPlease update this script.)\n\n''', os.path.basename(__file__), os.path.basename(__file__))

        if update_action is None:
            update_action = raw_input("Do you wish to Update and exit [u], continue anyway [c] or simply exit [x]? [u/c/X]: ")

        if update_action in ["C".lower(), "Y".lower()]:
            print  "Continuing..."
            return
        elif update_action in ["U".lower(), "update", "--update"]:
            print "Updating local script with script from distribution server..."

            if devel is True:
                bootstrap_path = "/usr/local/bin/esg-bootstrap --devel"
            else:
                bootstrap_path = "/usr/local/bin/esg-bootstrap"
            invoke_bootstrap = subprocess.Popen(bootstrap_path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            invoke_bootstrap.communicate()
            # if invoke_bootstrap.returncode == 0:
            #     esg_functions.checked_get()
            print "Please re-run this updated script: {current_script_name}".format(current_script_name = os.path.basename(__file__))
            sys.exit(invoke_bootstrap.returncode)
        elif update_action is "X".lower():
            print "Exiting..."
            sys.exit(1)
        else:
            print "Unknown option: {update_action} - Exiting".format(update_action = update_action)
            sys.exit(1)

    return True



def esgf_node_info():

    print '''
        The goal of this script is to automate as many tasks as possible
     regarding the installation, maintenance and use of the ESGF
     software stack that is know as the \"ESGF Node\".  A software
     stack is a collection of tools that work in concert to perform a
     particular task or set of tasks that are semantically united. The
     software stack is comprised of: Tomcat, Thredds, CDAT & CDMS,
     PostgreSQL, MyProxy, and several ESGF.org custom software
     applications running on a LINUX (RedHat/CentOS) operating system.

     Through the installation process there are different accounts
     that are created that facilitate the communication between the
     software stack entities.  These credentials are internal to the
     stack.  It is recommended that you use the defaults provided
     throughout this installation.  The security impact with regards
     to the visibility and accessibility of the constituent components
     of the stack depends on other factors to be addressed by your
     organization.

     Please be sure that you have gotten your created an account on
     your ESGF IDP Peer.

     The primary IDP Peer for ESGF is pcmdi.llnl.gov
     You may register for an account at PCMDI at the following URL:
     http://pcmdi.llnl.gov/esgf-web-fe/createAccount

     Note: Account creation is prerequisite for publication!

     ESGF P2P Node:                                             ESGF P2P Node:
      ---------                                                   ---------
     |Tomcat   |                                                 |Tomcat   |
     |-Node Mgr|   <================= P2P =================>     |-Node Mgr|
     |-Thredds |                                                 |-Thredds |
     |-ORP     |                                                 |-ORP     |
     |---------|                                                 |---------|
     |CDAT/CDMS|                                                 |CDAT/CDMS|
     |---------|                                                 |---------|
     |Postgres |                                                 |Postgres |
     |---------|                                                 |---------|
     | MyProxy |  <===(HTTPS)===> [ESGF Peer Node(s)]*           | MyProxy |
     |---------|                                                 |---------|
     | GridFTP |  <=============> [End User(s)]*                 | GridFTP |
     >---------<                                                 >---------<
     | CentOS  |                                                 | CentOS  |
     |(Virtual)|                                                 |(Virtual)|
     | Machine |                                                 | Machine |
     |---------|                                                 |---------|
      ---------                                                   ---------

     (Visit http://esgf.llnl.gov , http://github.com/ESGF/esgf.github.io/wiki for more information)

                                                                                    
\033[01;31m
  EEEEEEEEEEEEEEEEEEEEEE   SSSSSSSSSSSSSSS         GGGGGGGGGGGGGFFFFFFFFFFFFFFFFFFFFFF
  E::::::::::::::::::::E SS:::::::::::::::S     GGG::::::::::::GF::::::::::::::::::::F
  E::::::::::::::::::::ES:::::SSSSSS::::::S   GG:::::::::::::::GF::::::::::::::::::::F
  EE::::::EEEEEEEEE::::ES:::::S     SSSSSSS  G:::::GGGGGGGG::::GFF::::::FFFFFFFFF::::F
    E:::::E       EEEEEES:::::S             G:::::G       GGGGGG  F:::::F       FFFFFF\033[0m
\033[01;33m    E:::::E             S:::::S            G:::::G                F:::::F
    E::::::EEEEEEEEEE    S::::SSSS         G:::::G                F::::::FFFFFFFFFF
    E:::::::::::::::E     SS::::::SSSSS    G:::::G    GGGGGGGGGG  F:::::::::::::::F
    E:::::::::::::::E       SSS::::::::SS  G:::::G    G::::::::G  F:::::::::::::::F
    E::::::EEEEEEEEEE          SSSSSS::::S G:::::G    GGGGG::::G  F::::::FFFFFFFFFF\033[0m
\033[01;32m    E:::::E                         S:::::SG:::::G        G::::G  F:::::F
    E:::::E       EEEEEE            S:::::S G:::::G       G::::G  F:::::F
  EE::::::EEEEEEEE:::::ESSSSSSS     S:::::S  G:::::GGGGGGGG::::GFF:::::::FF
  E::::::::::::::::::::ES::::::SSSSSS:::::S   GG:::::::::::::::GF::::::::FF
  E::::::::::::::::::::ES:::::::::::::::SS      GGG::::::GGG:::GF::::::::FF
  EEEEEEEEEEEEEEEEEEEEEE SSSSSSSSSSSSSSS           GGGGGG   GGGGFFFFFFFFFFF.org
\033[0m
     -ESGF.org \n\n

    '''


def select_distribution_mirror(install_type):
     # Determining ESGF distribution mirror
    logger.info("before selecting distribution mirror: %s", config.config_dictionary["esgf_dist_mirror"])
    if any(argument in sys.argv for argument in ["install", "update", "upgrade"]):
        logger.debug("interactive")
        config.config_dictionary["esgf_dist_mirror"] = esg_mirror_manager.get_esgf_dist_mirror("interactive", install_type)
    else:
        logger.debug("fastest")
        config.config_dictionary["esgf_dist_mirror"] = esg_mirror_manager.get_esgf_dist_mirror("fastest", install_type)

    logger.info("selected distribution mirror: %s", config.config_dictionary["esgf_dist_mirror"])

def set_esg_dist_url():
     # # Setting esg_dist_url with previously gathered information
    esg_dist_url_root = os.path.join("http://", config.config_dictionary["esgf_dist_mirror"], "dist")
    logger.debug("esg_dist_url_root: %s", esg_dist_url_root)
    if devel is True:
        esg_dist_url = os.path.join("http://", esg_dist_url_root, "/devel")
    else:
        esg_dist_url = esg_dist_url_root

    logger.debug("esg_dist_url: %s", esg_dist_url)

def download_esg_installarg(esg_dist_url):
    # # Downloading esg-installarg file
    if not os.path.isfile(config.config_dictionary["esg_installarg_file"]) or force_install or os.path.getmtime(config.config_dictionary["esg_installarg_file"]) < os.path.getmtime(os.path.realpath(__file__)):
        esg_installarg_file_name = esg_bash2py.trim_string_from_head(config.config_dictionary["esg_installarg_file"])
        esg_functions.checked_get(config.config_dictionary["esg_installarg_file"], os.path.join(esg_dist_url, "esgf-installer", esg_installarg_file_name), force_get=force_install)
        try:
            if not os.path.getsize(config.config_dictionary["esg_installarg_file"]) > 0:
                os.remove(config.config_dictionary["esg_installarg_file"])
            esg_bash2py.touch(config.config_dictionary["esg_installarg_file"])
        except IOError, error:
            logger.error(error)

def check_selected_node_type():
    ''' Make sure a valid node_type has been selected before performing and install '''
    if node_type_bit & INSTALL_BIT != 0 and not (node_type_bit >= MIN_BIT and node_type_bit <= MAX_BIT):
        print '''
                Sorry no suitable node type has been selected
                Please run the script again with --set-type and provide any number of type values (\"data\", \"index\", \"idp\", \"compute\" [or \"all\"]) you wish to install
                (no quotes - and they can be specified in any combination or use \"all\" as a shortcut)

                Ex:  esg-node --set-type data
                esg-node install

                or do so as a single command line:

                Ex:  esg-node --type data install

                Use the --help | -h option for more information

                Note: The type value is recorded upon successfully starting the node.
                the value is used for subsequent launches so the type value does not have to be
                always specified.  A simple \"esg-node start\" will launch with the last type used
                that successfully launched.  Thus ideal for use in the boot sequence (chkconfig) scenario.
                (more documentation available at https://github.com/ESGF/esgf-installer/wiki)\n\n
              '''
        sys.exit(1)

def main():
    esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
    

    logger.info("esg-node initializing...")
    try:
        logger.info(socket.getfqdn())
    except socket.error:
        logger.error("Please be sure this host has a fully qualified hostname and reponds to socket.getfdqn() command")
        sys.exit()

    # Determining if devel or master directory of the ESGF distribution mirror will be use for download of binaries
    if "devel" in script_version:
        logger.debug("Using devel version")
        install_type = "devel"
    else:
        install_type = "master"

    # select_distribution_mirror(install_type)
    # set_esg_dist_url()    
    # download_esg_installarg()
    

    #process command line arguments
    esg_cli_argument_manager.process_arguments(install_mode, upgrade_mode, node_type_bit)
    try:
        esg_setup.check_prerequisites()
    except UnprivilegedUserError:
        logger.info("$([FAIL]) \n\tMust run this program with root's effective UID\n\n")
        sys.exit(1)
    except WrongOSError:
        logger.info("ESGF can only be installed on versions 6 of Red Hat, CentOS or Scientific Linux x86_64 systems" )
        sys.exit(1)
    
    verify_esg_node_script(esg_dist_url)

    logger.debug("node_type_bit: %s", node_type_bit)
    


    print '''
    -----------------------------------
    ESGF Node Installation Program
    -----------------------------------'''

    logger.debug("node_type_bit & INSTALL_BIT != 0: %s", node_type_bit & INSTALL_BIT != 0)
    logger.debug("node_type_bit: %i, %s", node_type_bit, type(node_type_bit))
    logger.debug("MIN_BIT: %i, %s", MIN_BIT, type(MIN_BIT))
    logger.debug("MAX_BIT: %i", MAX_BIT)
    logger.debug("node_type_bit >= MIN_BIT: %s",  node_type_bit >= MIN_BIT)
    logger.debug("node_type_bit >= MIN_BIT and node_type_bit <= MAX_BIT: %s", node_type_bit >= MIN_BIT and node_type_bit <= MAX_BIT)

        
    esg_cli_argument_manager.get_previous_node_type_config()
    check_selected_node_type()

    esgf_node_info()

    default_install_answer = "Y"
    if devel is True:
        print "(Installing DEVELOPMENT tree...)"
    while True:
        begin_installation = raw_input("Are you ready to begin the installation? [Y/n] ") or default_install_answer
        if begin_installation.lower() == "n" or begin_installation.lower() == "no":
            print "Canceling installation"
            sys.exit(0)
        elif begin_installation.lower() == "y" or begin_installation.lower() == "yes":
            break
        else:
            print "Invalid option.  Please select a valid option [Y/n]"

    esg_setup.init_structure()

    if force_install:
        logger.info("(force install is ON)")
    if node_type_bit & DATA_BIT != 0:
        logger.info("(data node type selected)")
    if node_type_bit & INDEX_BIT != 0:
        logger.info("(index node type selected)")
    if node_type_bit & IDP_BIT != 0:
        logger.info("(idp node type selected)")
    if node_type_bit & COMPUTE_BIT != 0:
        logger.info("(compute node type selected)")

    esg_setup.initial_setup_questionnaire()
    #---------------------------------------
    #Installation of prerequisites.
    #---------------------------------------
    #TODO: Uncomment this; only removed for testing speedup
    # esg_setup.install_prerequisites()
    

    #---------------------------------------
    #Setup ESGF RPM repository
    #---------------------------------------    
    print '''
    *******************************
    Setting up ESGF RPM repository
    ******************************* '''

    #---------------------------------------
    #Installation of basic system components.
    # (Only when one setup in the sequence is okay can we move to the next)
    #---------------------------------------
    if node_type_bit & INSTALL_BIT !=0:
        esg_setup.setup_java()
        esg_setup.setup_ant()
        esg_postgres.setup_postgres()
        esg_setup.setup_cdat()
        logger.debug("node_type_bit & (DATA_BIT+COMPUTE_BIT) %s", node_type_bit & (DATA_BIT+COMPUTE_BIT))
        if node_type_bit & (DATA_BIT+COMPUTE_BIT) != 0:
            esg_publisher.setup_esgcet()
        esg_tomcat_manager.setup_tomcat()
        esg_apache_manager.setup_apache_frontend(devel)
    # setup_esgcet()
    # test_esgcet()
    
    # yum_remove_rpm_forge_output = yum_remove_rpm_forge.communicate()


if __name__ == '__main__':
    main()
