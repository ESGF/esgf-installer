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
from esg_init import EsgInit

logging.basicConfig(format = "%(levelname): %(lineno)s %(funcName)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

bit_dictionary = {"INSTALL_BIT":1, "TEST_BIT":2, "DATA_BIT":4, "INDEX_BIT":8, "IDP_BIT":16, "COMPUTE_BIT":32, "WRITE_ENV_BIT":64, "MIN_BIT":4, "MAX_BIT":64, "ALL_BIT":60}


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

def get_bit_value(node_type):
    if node_type == "install":
        return bit_dictionary["INSTALL_BIT"]
    elif node_type == "data":
        return bit_dictionary["DATA_BIT"]
    elif node_type == "index":
        return bit_dictionary["INDEX_BIT"]
    elif node_type == "idp":
        return bit_dictionary["IDP_BIT"]
    elif node_type == "compute":
        return bit_dictionary["COMPUTE_BIT"]
    elif node_type == "write_env":
        return bit_dictionary["WRITE_ENV_BIT"]
    elif node_type == "min":
        return bit_dictionary["MIN_BIT"]
    elif node_type == "max":
        return bit_dictionary["MAX_BIT"]
    elif node_type == "all":
        return bit_dictionary["ALL_BIT"]
    else:
        raise ValueError("Invalid bit reference")

def _define_acceptable_arguments():
    #TODO: Add mutually exclusive groups to prevent long, incompatible argument lists
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", dest="install", help="Goes through the installation process and automatically starts up node services", action="store_true")
    parser.add_argument("--update", help="Updates the node manager", action="store_true")
    parser.add_argument("--upgrade", help="Upgrade the node manager", action="store_true")
    parser.add_argument("--install-local-certs", dest="installlocalcerts", help="Install local certificates", action="store_true")
    parser.add_argument("--generate-esgf-csrs", dest="generateesgfcsrs", help="Generate CSRs for a simpleCA CA certificate and/or web container certificate", action="store_true")
    parser.add_argument("--generate-esgf-csrs-ext", dest="generateesgfcsrsext", help="Generate CSRs for a node other than the one you are running", action="store_true")
    parser.add_argument("--cert-howto", dest="certhowto", help="Provides information about certificate management", action="store_true")
    parser.add_argument("--verify", "--test", dest="verify", help="Runs the test code to verify installation", action="store_true")
    parser.add_argument("--fix-perms","--fixperms", dest="fixperms", help="Fix permissions", action="store_true")
    parser.add_argument("--type", "-t", "--flavor", dest="type", help="Set type", nargs="+", choices=["data", "index", "idp", "compute", "all"])
    parser.add_argument("--set-type",  dest="settype", help="Sets the type value to be used at next start up", nargs="+", choices=["data", "index", "idp", "compute", "all"])
    parser.add_argument("--get-type", "--show-type", dest="gettype", help="Returns the last stored type code value of the last run node configuration (data=4 +| index=8 +| idp=16)", action="store_true")
    parser.add_argument("--start", help="Start the node's services", action="store_true")
    parser.add_argument("--stop", "--shutdown", dest="stop", help="Stops the node's services", action="store_true")
    parser.add_argument("--restart", help="Restarts the node's services (calls stop then start :-/)", action="store_true")
    parser.add_argument("--status", help="Status on node's services", action="store_true")
    parser.add_argument("--update-sub-installer", dest="updatesubinstaller", help="Update a specified installation script", nargs=2, metavar=('script_name', 'script_directory'))
    parser.add_argument("--update-apache-conf", dest="updateapacheconf", help="Update Apache configuration", action="store_true")
    parser.add_argument("--write-env", dest="writeenv", help="Writes the necessary environment variables to file {envfile}".format(envfile = envfile), action="store_true")
    parser.add_argument("-v","--version", dest="version", help="Displays the version of this script", action="store_true")
    parser.add_argument("--recommended_setup", dest="recommendedsetup", help="Sets esgsetup to use the recommended, minimal setup", action="store_true")
    parser.add_argument("--custom_setup", dest="customsetup", help="Sets esgsetup to use a custom, user-defined setup", action="store_true")
    parser.add_argument("--use-local-files", dest="uselocalfiles", help="Sets a flag for using local files instead of attempting to fetch a remote file", action="store_true")
    parser.add_argument("--devel", help="Sets the installation type to the devel build", action="store_true")
    parser.add_argument("--prod", help="Sets the installation type to the production build", action="store_true")
    parser.add_argument("--clear-env-state", dest="clearenvstate", help="Removes the file holding the environment state of last install", action="store_true")
    
    args = parser.parse_args()
    return (args, parser)


#TODO: Refactor this to return value vs using global variable
def get_previous_node_type_config():
    ''' 
        Helper method for reading the last state of node type config from config dir file "config_type"
        Every successful, explicit call to --type|-t gets recorded in the "config_type" file
        If the configuration type is not explicity set the value is read from this file.
    '''
    global node_type_bit
    if node_type_bit < MIN_BIT or node_type_bit > MAX_BIT:
        logger.info("node_type_bit is out of range: %s", node_type_bit)
        logger.info("Acceptable range is between %s and %s", MIN_BIT, MAX_BIT)
        try:
            last_config_type = open(config.esg_config_type_file)
            node_type_bit += int(last_config_type.readline())
            logger.debug("node_type_bit is now: %i", node_type_bit)
        except IOError, error:
            logger.error(error)

    if node_type_bit == 0:
        print '''ERROR: No node type selected nor available! \n Consult usage with --help flag... look for the \"--type\" flag 
        \n(must come BEFORE \"[start|stop|restart|update]\" args)\n\n'''
        sys.exit(1)

def set_node_type_config(node_type_bit):
    '''
            Write the node type numeric value to file
            (Yes... gratuitous error and bounds checking)
    '''
    logger.debug("new node_type_bit: %s", node_type_bit)
    hit_bits = 0

    #valididty check for type... in range power of 2
    #MIN and MAX BIT range... if so then valid and an be written down.
    if node_type_bit < MIN_BIT or node_type_bit > MAX_BIT:
        logger.debug("WARNING: Selection %s is out of range $MIN_BIT - $MAX_BIT", node_type_bit)

    #Check if the new sel has any bits turned on in the range of our type bits
    type_bit = MIN_BIT
    while type_bit <= MAX_BIT:
        if node_type_bit & type_bit != 0:
            hit_bits += type_bit
        type_bit *= 2

    logger.debug("[hit_bits = %s] =? [node_type_bit = %s]", hit_bits, node_type_bit)

    if hit_bits:
        try:
            config_type_file = open(config.esg_config_type_file, "w")
            logger.debug("Writing %s to file as new node_type_bit", hit_bits)
            config_type_file.write(str(hit_bits))
        except IOError, error:
            logger.error(error)

def process_arguments(install_mode, upgrade_mode, node_type_bit):
    selection_string = ""

    args, parser = _define_acceptable_arguments()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if args.install:
        if install_mode + upgrade_mode == 0:
            upgrade_mode = 0
            install_mode = 1
            if node_type_bit & bit_dictionary["INSTALL_BIT"] == 0:
                node_type_bit += get_bit_value("install")
            logger.debug("Install Services")
    if args.update or args.upgrade:
        if install_mode + upgrade_mode == 0:
            upgrade_mode = 1 
            install_mode = 0
            if node_type_bit & bit_dictionary["INSTALL_BIT"] == 0:
                node_type_bit += get_bit_value("install")
            logger.debug("Update Services")
            self_verify("update")
    if args.fixperms:
        logger.debug("fixing permissions")
        setup_sensible_confs
        sys.exit(0)
    if args.installlocalcerts:
        logger.debug("installing local certs")
        get_previous_node_type_config()
        install_local_certs()
        sys.exit(0)
    if args.generateesgfcsrs:
        logger.debug("generating esgf csrs")
        get_previous_node_type_config()
        generate_esgf_csrs()
        sys.exit(0)
    if args.generateesgfcsrsext:
        logger.debug("generating esgf csrs for other node")
        get_previous_node_type_config()
        generate_esgf_csrs_ext()
        sys.exit(0)
    if args.certhowto:
        logger.debug("cert howto")
        cert_howto()
        sys.exit(0)
    elif args.verify:
        logger.debug("Verify Services")
        if node_type_bit & get_bit_value("test") == 0:
            node_type_bit += get_bit_value("test")
        logger.debug("node_type_bit = %s", node_type_bit)
        test_postgress()
        test_cdat()
        test_esgcet()
        test_tomcat()
        test_tds()
        sys.exit(0)
    elif args.type:
        logger.debug("selecting type")
        logger.debug("args.type: %s", args.type)
        for arg in args.type:
            #TODO: refactor conditional to function with descriptive name
            if node_type_bit & get_bit_value(arg) == 0:
                node_type_bit += get_bit_value(arg)
                selection_string += " "+arg
        logger.info("node type set to: [%s] (%s) ", selection_string, node_type_bit)
        sys.exit(0)
    elif args.settype:
        logger.debug("Selecting type for next start up")
        for arg in args.settype:
            #TODO: refactor conditional to function with descriptive name
            if node_type_bit & get_bit_value(arg) == 0:
                node_type_bit += get_bit_value(arg)
                selection_string += " "+arg
        if not os.path.isdir(config.esg_config_dir):
            try:
                os.mkdir(config.esg_config_dir)
            except IOError, error:
                logger.error(error)
        logger.info("node type set to: [%s] (%s) ", selection_string, node_type_bit)
        set_node_type_config(node_type_bit)
        sys.exit(0)
    elif args.gettype:
        get_previous_node_type_config()
        show_type()
        sys.exit(0)
    elif args.start:
        logger.debug("args: %s", args)
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        logger.debug("START SERVICES: %s", node_type_bit)
        esg_setup.init_structure()
        start(node_type_bit)
        sys.exit(0)
    elif args.stop:
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        logger.debug("STOP SERVICES")
        esg_setup.init_structure()
        stop(node_type_bit)
        sys.exit(0)
    elif args.restart:
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        logger.debug("RESTARTING SERVICES")
        esg_setup.init_structure()
        stop(node_type_bit)
        sleep(2)
        start(node_type_bit)
        sys.exit(0)
    elif args.status:
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        get_node_status()
        #TODO: Exit with status code dependent on what is returned from get_node_status()
        sys.exit(0)
    elif args.updatesubinstaller:
        self_verify("update")
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        esg_setup.init_structure()
        update_script(args[1], args[2])
        sys.exit(0)
    elif args.updateapacheconf:
        logger.debug("checking for updated apache frontend configuration")
        update_apache_conf()
        sys.exit(0)
    elif args.writeenv:
        if node_type_bit & WRITE_ENV_BIT == 0:
            node_type_bit += WRITE_ENV_BIT
    elif args.version:
        logger.info("Version: %s", script_version)
        logger.info("Release: %s", script_release)
        logger.info("Earth Systems Grid Federation (http://esgf.llnl.gov)")
        logger.info("ESGF Node Installation Script")
        sys.exit(0)
    elif args.recommendedsetup:
        recommended_setup = 1
        custom_setup = 0
    elif args.customsetup:
        recommended_setup = 0
        custom_setup = 1
    elif args.uselocalfiles:
        use_local_files = 1
    elif args.devel:
        devel = 1
    elif args.prod:
        devel = 0
    elif args.clearenvstate:
        self_verify("clear")
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        if os.path.isfile(envfile):
            shutil.move(envfile, envfile+".bak")
            #empty out contents of the file
            open(envfile, 'w').close()