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



devel = esg_bash2py.Expand.colonMinus("devel", 0)
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


def _verify_against_remote(esg_dist_url_root):
    python_script_name = os.path.basename(__file__)
    python_script_md5_name = re.sub(r'_', "-", python_script_name)
    python_script_md5_name = re.search("\w*-\w*", python_script_md5_name)
    logger.info("python_script_name: %s", python_script_md5_name)

    remote_file_md5 = requests.get("{esg_dist_url_root}/esgf-installer/{script_maj_version}/{python_script_md5_name}.md5".format(esg_dist_url_root= esg_dist_url_root, script_maj_version= script_maj_version, python_script_md5_name= python_script_md5_name ) ).content
    remote_file_md5 = remote_file_md5.split()[0].strip()

    local_file_md5 = None

    hasher = hashlib.md5()
    with open(python_script_name, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
        local_file_md5 = hasher.hexdigest()
        print "local_file_md5: ", local_file_md5.strip()

    if local_file_md5 != remote_file_md5:
        raise UnverifiedScriptError
    else:
        print "[VERIFIED]"
        return True

#TODO: Rename and refactor this; there is already a function in esg_bootstrap.py called self_verify()
def self_verify(esg_dist_url_root, update_action = None):
    # Test to see if the esg-node script is currently being pulled from git, and if so skip verification
    if esg_functions.is_in_git(os.path.basename(__file__)) == 0:
        logger.info("Git repository detected; not checking checksum of esg-node")
        return

    if "devel" in script_version:
        devel = 0
        remote_url = "{esg_dist_url_root}/esgf-installer/{script_maj_version}".format(esg_dist_url_root = esg_dist_url_root, script_maj_version = script_maj_version)
    else:
        devel = 1
        remote_url = "{esg_dist_url_root}/devel/esgf-installer/{script_maj_version}".format(esg_dist_url_root = esg_dist_url_root, script_maj_version = script_maj_version)
    try:
        _verify_against_remote(remote_url)
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

            if devel == 0:
                bootstrap_path = "/usr/local/bin/esg-bootstrap"
            else:
                bootstrap_path = "/usr/local/bin/esg-bootstrap --devel"
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

    # Determining ESGF distribution mirror
    # logger.info("before selecting distribution mirror: %s", config.config_dictionary["esgf_dist_mirror"])
    # if any(argument in sys.argv for argument in ["install", "update", "upgrade"]):
    #     logger.debug("interactive")
    #     config.config_dictionary["esgf_dist_mirror"] = esg_functions.get_esgf_dist_mirror("interactive", install_type)
    # else:
    #     logger.debug("fastest")
    #     config.config_dictionary["esgf_dist_mirror"] = esg_functions.get_esgf_dist_mirror("fastest", install_type)

    # logger.info("selected distribution mirror: %s", config.config_dictionary["esgf_dist_mirror"])

    # # Setting esg_dist_url with previously gathered information
    # esg_dist_url_root = os.path.join("http://", config.config_dictionary["esgf_dist_mirror"], "dist")
    # logger.debug("esg_dist_url_root: %s", esg_dist_url_root)
    # if devel is True:
    #     esg_dist_url = os.path.join("http://", esg_dist_url_root, "/devel")
    # else:
    #     esg_dist_url = esg_dist_url_root

    # logger.debug("esg_dist_url: %s", esg_dist_url)
    # # Downloading esg-installarg file
    # if not os.path.isfile(config.config_dictionary["esg_installarg_file"]) or force_install or os.path.getmtime(config.config_dictionary["esg_installarg_file"]) < os.path.getmtime(os.path.realpath(__file__)):
    #     esg_installarg_file_name = esg_functions.trim_string_from_head(config.config_dictionary["esg_installarg_file"])
    #     esg_functions.checked_get(config.config_dictionary["esg_installarg_file"], os.path.join(esg_dist_url, "esgf-installer", esg_installarg_file_name), force_get=force_install)
    #     try:
    #         if not os.path.getsize(config.config_dictionary["esg_installarg_file"]) > 0:
    #             os.remove(config.config_dictionary["esg_installarg_file"])
    #         esg_functions.touch(config.config_dictionary["esg_installarg_file"])
    #     except IOError, error:
    #         logger.error(error)

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
    
    self_verify(esg_dist_url)

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
    
    #TODO: Break this into a function
    #If we are doing an install - make sure a type is selected
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

    esgf_node_info()

    default_install_answer = "Y"
    if devel == 1:
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
        setup_tomcat()
        setup_apache_frontend()
    # setup_esgcet()
    # test_esgcet()
    
    # yum_remove_rpm_forge_output = yum_remove_rpm_forge.communicate()


def setup_apache_frontend():
    print '''
    *******************************
    Setting up Apache Frontend
    ******************************* \n'''

    old_directory = os.getcwd()
    try:
        local_work_directory = os.environ["ESGF_INSTALL_WORKDIR"]
    except KeyError, error:
        logger.debug(error)
        local_work_directory = os.path.join(config.config_dictionary["installer_home"], "workbench", "esg")

    os.chdir(local_work_directory)
    logger.debug("changed directory to %s:", os.getcwd())
    esg_bash2py.mkdir_p("apache_frontend")
    os.chdir("apache_frontend")
    logger.debug("changed directory to %s:", os.getcwd())
    print "Fetching the Apache Frontend Repo from GIT Repo... %s" % (config.config_dictionary["apache_frontend_repo"])
    try:
        Repo.clone_from(config.config_dictionary["apache_frontend_repo"], "apache_frontend")
    except git.exc.GitCommandError, error:
        logger.error(error)
        logger.error("Git repo already exists.")

    if os.path.isdir(os.path.join("apache_frontend", ".git")):
        logger.error("Successfully cloned repo from %s", config.config_dictionary["apache_frontend_repo"])
        # os.chdir("apache-frontend")
        # logger.debug("changed directory to %s:", os.getcwd())
        apache_frontend_repo_local = Repo("/usr/local/src/esgf/workbench/esg/apache_frontend/apache_frontend")
        if devel == 1:
            apache_frontend_repo_local.git.checkout("devel")
        else:
            apache_frontend_repo_local.git.checkout("master")

        try:
            host_name = esgf_host
        except NameError, error:
            logger.error(error)
            host_name = socket.gethostname()

        stop_httpd_command = "/etc/init.d/httpd stop"
        stop_httpd_process = subprocess.Popen(shlex.split(stop_httpd_command))
        stop_httpd_process_stdout, stop_httpd_process_stderr =  stop_httpd_process.communicate()

        check_config_command = "chkconfig --levels 2345 httpd off"
        check_config_process = subprocess.Popen(shlex.split(check_config_command))
        check_config_process_stdout, check_config_process_stderr =  check_config_process.communicate()

        ip_addresses = []

        while True:
            ip_address = raw_input("Enter a single ip address which would be cleared to access admin restricted pages.\nYou will be prompted if you want to enter more ip-addresses: ")
            ip_addresses.append(ip_address)

            add_more_ips = raw_input("Do you wish to allow more ip addresses to access admin restricted pages? y/n")
            if add_more_ips.lower() != "y":
                break

        allowed_ip_address_string = "".join("Allow from " + address + "\t" for address in ip_addresses)
        logger.debug("allowed_ip_address_string: %s", allowed_ip_address_string)

        #Replace permitted-ips placeholder with permitted ips-values
        with open("/etc/httpd/conf/esgf-httpd.conf", "r") as esgf_httpd_conf_file:
            filedata = esgf_httpd_conf_file.read()
            filedata.replace("#insert-permitted-ips-here", "#permitted-ips-start-here\n" +allowed_ip_address_string +"\t#permitted-ips-end-here")

        with open("/etc/httpd/conf/esgf-httpd.conf", "w") as file:
                file.write(filedata)


        # add_ips_to_conf_file_command = "sed -i 's/\#insert-permitted-ips-here/\#permitted-ips-start-here\n{allowed_ip_address_string}\t\#permitted-ips-end-here/' /etc/httpd/conf/esgf-httpd.conf".format(allowed_ip_address_string = allowed_ip_address_string)
        # add_ips_to_conf_file_process = subprocess.Popen(shlex.split(add_ips_to_conf_file_command))
        # add_ips_to_conf_file_stdout, add_ips_to_conf_file_stderr = add_ips_to_conf_file_process.communicate()
        # logger.debug("add_ips_to_conf_file_stdout: %s", add_ips_to_conf_file_stdout)
        # logger.debug("add_ips_to_conf_file_stderr: %s", add_ips_to_conf_file_stderr)

        #Write the contents of /etc/tempcerts/cacert.pem  to /etc/certs/esgf-ca-bundle.crt
        esgf_ca_bundle_file = open("/etc/certs/esgf-ca-bundle.crt", "a")
        with open ("/etc/tempcerts/cacert.pem", "r") as cacert_file:
            cacert_contents = cacert_file.read()
            esgf_ca_bundle_file.write(cacert_contents)
        esgf_ca_bundle_file.close()

        start_httpd_command = "/etc/init.d/esgf-httpd start"
        start_httpd_process = subprocess.Popen(shlex.split(start_httpd_command))
        start_httpd_stdout, start_httpd_stderr = start_httpd_process.communicate()
    else:
        config_file = "/etc/httpd/conf/esgf-httpd.conf"
        if os.path.isfile(config_file):
            esgf_httpd_version_command = "`grep ESGF-HTTPD-CONF $conf_file | awk '{print $4}'`"
            esgf_httpd_version_process = subprocess.Popen(shlex.split(esgf_httpd_version_command))
            esgf_httpd_version_stdout, esgf_httpd_version_stderr = esgf_httpd_version_process.communicate()
            if not esgf_httpd_version_stdout:
                logger.error("esgf-httpd.conf is missing versioning, attempting to update.")
                update_apache_conf()
            else:
                if esg_functions.check_version_atleast(esgf_httpd_version_stdout, config.config_dictionary["apache_frontend_version"]) == 0:
                    logger.info("esgf-httpd.conf version is sufficient")
                else:
                    logger.info("esgf-httpd version is out-of-date, attempting to update.")
                    update_apache_conf()
        else:
            logger.info("esgf-httpd.conf file not found, attempting to update. This condition is not expected to occur and should be reported to ESGF support")
            update_apache_conf()



def update_apache_conf():
    try:
        local_work_directory = os.environ["ESGF_INSTALL_WORKDIR"]
    except KeyError, error:
        logger.debug(error)
        local_work_directory = os.path.join(config.config_dictionary["installer_home"], "workbench", "esg")

    config_file = "/etc/httpd/conf/esgf-httpd.conf"

    with esg_functions.pushd(local_work_directory):
        logger.debug("changed to directory: %s", os.getcwd())
        if not os.path.isdir("apache_frontend"):
            esg_bash2py.mkdir_p("apache_frontend")
            with esg_functions.pushd("apache_frontend"):
                logger.debug("changed to directory: %s", os.getcwd())
                Repo.clone_from(config.config_dictionary["apache_frontend_repo"], "apache_frontend")
            logger.debug("changed to directory: %s", os.getcwd())
        else:
            with esg_functions.pushd("apache_frontend"):
                logger.debug("changed to directory: %s", os.getcwd())
                shutil.rmtree("apache-frontend")
                Repo.clone_from(config.config_dictionary["apache_frontend_repo"], "apache_frontend")
            logger.debug("changed to directory: %s", os.getcwd())
        with esg_functions.pushd("apache_frontend/apache-frontend"):
            logger.debug("changed to directory: %s", os.getcwd())
            apache_frontend_repo_local = Repo("apache-frontend")
            if devel == 1:
                apache_frontend_repo_local.git.checkout("devel")
            else:
                apache_frontend_repo_local.git.checkout("master")

            if os.path.isfile(config_file):
                logger.info("Backing up previous version of %s", config_file)
                date_string = str(datetime.date.today())
                config_file_backup_name = config_file+date_string+".bak"
                if os.path.isfile(config_file_backup_name):
                    logger.info("WARNING:  esgf-httpd.conf already backed up today.")
                    shutil.copyfile(config_file_backup_name, config_file_backup_name+".1")
                else:
                    shutil.copyfile(config_file, config_file_backup_name)

            wsgi_path = "/opt/esgf/python/lib/python2.7/site-packages/mod_wsgi/server/mod_wsgi-py27.so"
            allowed_ips_sed_process = subprocess.Popen(shlex.split("sed -n '/\#permitted-ips-start-here/,/\#permitted-ips-end-here/p' /etc/httpd/conf/esgf-httpd.conf"), stdout=subprocess.PIPE)
            allowed_ips_grep_process = subprocess.Popen(shlex.split("grep Allow"), stdin = allowed_ips_sed_process.stdout, stdout=subprocess.PIPE)
            allowed_ips_sort_process = subprocess.Popen(shlex.split("sort -u"), stdin = allowed_ips_grep_process)

            allowed_ips_sed_process.stdout.close()
            allowed_ips_grep_process.stdout.close()
            allowed_ips_stdout, allowed_ips_stderr = allowed_ips_sort_process.communicate()
            logger.debug("allowed_ips_stdout: %s", allowed_ips_stdout)
            logger.debug("allowed_ips_stderr: %s", allowed_ips_stderr)

            permitted_ips_command = 'sed "s/\#permitted-ips-end-here/\#permitted-ips-end-here\n\t\#insert-permitted-ips-here/" /etc/httpd/conf/esgf-httpd.conf >etc/httpd/conf/esgf-httpd.conf;'
            permitted_ips_process = subprocess.Popen(shlex.split(permitted_ips_command))
            permitted_ips_stdout, permitted_ips_stderr = permitted_ips_process.communicate()
            logger.debug("permitted_ips_stdout: %s", permitted_ips_stdout)
            logger.debug("permitted_ips_stderr: %s", permitted_ips_stderr)
            with open("etc/httpd/conf/esgf-httpd.conf", "a") as httpd_conf_file:
                httpd_conf_file.write(permitted_ips_stdout)

            wsgi_path_module_sed_command = 'sed -i "s/\(.*\)LoadModule wsgi_module {wsgi_path}\(.*\)/\1LoadModule wsgi_module placeholder_so\2/" etc/httpd/conf/esgf-httpd.conf;'.format(wsgi_path = wsgi_path)
            wsgi_path_module_sed_process = subprocess.Popen(shlex.split(wsgi_path_module_sed_command))
            wsgi_path_module_sed_stdout, wsgi_path_module_sed_stderr = wsgi_path_module_sed_process.communicate()
            logger.debug("wsgi_path_module_sed_stdout: %s", wsgi_path_module_sed_stdout)
            logger.debug("wsgi_path_module_sed_stderr: %s", wsgi_path_module_sed_stderr)

            #TODO: Terrible names; figure out what they are representing and rename 
            include_httpd_locals_file = "Include /etc/httpd/conf/esgf-httpd-locals.conf"
            include_httpd_local_file = "Include /etc/httpd/conf/esgf-httpd-local.conf"

            #TODO: Another terrible name
            uncommented_include_httpd_locals_file = False
            uncommented_include_httpd_local_file = False

            #TODO: for now, adding full path to avoid confusion with the two etc directories
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "r") as file:
                filedata = file.read()
                if not "#Include /etc/httpd/conf/esgf-httpd-locals.conf" in filedata:
                    uncommented_include_httpd_locals_file = True
                    filedata = filedata.replace("Include /etc/httpd/conf/esgf-httpd-locals.conf", "#Include /etc/httpd/conf/esgf-httpd-locals.conf")
                if not '#Include /etc/httpd/conf/esgf-httpd-local.conf' in filedata:
                    uncommented_include_httpd_local_file = True 
                    filedata = filedata.replace("Include /etc/httpd/conf/esgf-httpd-local.conf", "#Include /etc/httpd/conf/esgf-httpd-local.conf")
            
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "w") as file:
                file.write(filedata)

            #Write first 22 lines? to different file
            original_server_lines_file = open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/original_server_lines", "w")
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "r") as esgf_httpd_conf_file:
                for i in range(22):
                    original_server_lines_file.write(esgf_httpd_conf_file.readline())

            original_server_lines_file.close()

            default_server_lines_file = open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/default_server_lines", "w")
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/tc/httpd/conf/esgf-httpd.conf.tmpl", "r") as esgf_httpd_conf_template:
                for i in range(22):
                    default_server_lines_file.write(esgf_httpd_conf_template.readline())


            #delete lines 1 through 22 from the files
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "r") as esgf_httpd_conf_file:
                lines = esgf_httpd_conf_file.readlines()
            lines = lines[22:]
            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "w") as esgf_httpd_conf_file:
                esgf_httpd_conf_file.write(lines)

            with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf.tmpl", "r") as esgf_httpd_conf_template:
                lines = esgf_httpd_conf_file.readlines()
            lines = lines[22:]
            esgf_httpd_conf_template.write(lines)

            #check if esgf-httpd.conf and esgf-httpd.conf.tmpl are equivalent, i.e. take the diff
            if filecmp.cmp("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf.tmpl"):
                #we have changes; add allowed ips, ext file selection and wsgi path to latest template and apply
                logger.info("Detected changes. Will update and reapply customizations. An esg-node restart would be needed to read in the changes.")

                #write /etc/httpd/conf/esgf-httpd.conf.tmpl into /etc/httpd/conf/origsrvlines
                original_server_lines_file = open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/original_server_lines", "a")
                with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf.tmpl") as esgf_httpd_conf_template:
                    content = esgf_httpd_conf_template.read()
                original_server_lines_file.write(content)
                original_server_lines_file.close()

                shutil.move("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/original_server_lines", "/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf.tmpl")
                shutil.copyfile("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf.tmpl", "/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf")

                replace_wsgi_module_placeholder_command = 'sed -i "s/\(.*\)LoadModule wsgi_module placeholder_so\(.*\)/\1LoadModule wsgi_module {wsgi_path}\2/" etc/httpd/conf/esgf-httpd.conf;'.format(wsgi_path = wsgi_path)
                replace_wsgi_module_placeholder_process = subprocess.Popen(shlex.split(replace_wsgi_module_placeholder_command))
                replace_wsgi_module_placeholder_stdout, replace_wsgi_module_placeholder_stderr = replace_wsgi_module_placeholder_process.communicate()

                insert_permitted_ips_command = 'sed -i "s/\#insert-permitted-ips-here/\#permitted-ips-start-here\n{allowed_ips}\n\t#permitted-ips-end-here/" etc/httpd/conf/esgf-httpd.conf;'.format(allowed_ips = allowed_ips_stdout)
                insert_permitted_ips_process = subprocess.Popen(shlex.split(insert_permitted_ips_command))
                insert_permitted_ips_stdout, insert_permitted_ips_stderr = insert_permitted_ips_process.communicate()

                if uncommented_include_httpd_locals_file or uncommented_include_httpd_local_file:
                    with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "r") as file:
                        filedata = file.read()
                        filedata = filedata.replace("#Include /etc/httpd/conf/esgf-httpd-locals.conf", "Include /etc/httpd/conf/esgf-httpd-locals.conf") 
                        filedata = filedata.replace("#Include /etc/httpd/conf/esgf-httpd-local.conf", "Include /etc/httpd/conf/esgf-httpd-local.conf")
                    
                    with open("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "w") as file:
                        file.write(filedata)

                shutil.copyfile("/etc/httpd/conf/esgf-httpd.conf", "/etc/httpd/conf/esgf-httpd.conf.bak")
                shutil.copyfile("/usr/local/src/esgf/workbench/esg/apache_frontend/apache-frontend/etc/httpd/conf/esgf-httpd.conf", "/etc/httpd/conf/esgf-httpd.conf")
            else:
                logger.info("No changes detected in apache frontend conf.")
    










def call_subprocess(command_string, command_stdin = None):
    logger.debug("command_string: %s", command_string)
    command_process = subprocess.Popen(shlex.split(command_string), stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    if command_stdin:
        command_process_stdout, command_process_stderr =  command_process.communicate(input = command_stdin)
    else:
        command_process_stdout, command_process_stderr =  command_process.communicate()
    logger.debug("command_process_stdout: %s", command_process_stdout)
    logger.debug("command_process_stderr: %s", command_process_stderr)
    logger.debug("command_process.returncode: %s", command_process.returncode)
    return {"stdout" : command_process_stdout, "stderr" : command_process_stderr, "returncode": command_process.returncode}




def subprocess_pipe_commands(command_list):
    subprocess_list = []
    for index, command in enumerate(command_list):
        if index > 0:
            subprocess_command = subprocess.Popen(command, stdin = subprocess_list[index -1].stdout, stdout=subprocess.PIPE)
            subprocess_list.append(subprocess_command)
        else:
            subprocess_command = subprocess.Popen(command, stdout=subprocess.PIPE)
            subprocess_list.append(subprocess_command)
    subprocess_list_length = len(subprocess_list)
    for index ,process in enumerate(subprocess_list):
        if index != subprocess_list_length -1:
            process.stdout.close()
        else:
            subprocess_stdout, subprocess_stderr = process.communicate()
    return subprocess_stdout

if __name__ == '__main__':
    main()
