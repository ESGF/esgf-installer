import os
import sys
import shutil
import logging
import argparse
import pprint
from time import sleep
import esg_functions
import esg_setup
import esg_apache_manager
import esg_logging_manager
import esg_bash2py
from esg_exceptions import NoNodeTypeError
import yaml

logger = esg_logging_manager.create_rotating_log(__name__)

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

progname = "esg-node"
script_version = "v3.0"
script_maj_version = "3.0"
script_release = "Centaur"

node_type_dictionary = {"INSTALL": False , "TEST": False, "DATA":False, "INDEX":False, "IDP":False, "COMPUTE":False, "MIN": False, "MAX": False}
installer_mode_dictionary = {"install_mode": False, "upgrade_mode": False}

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

#Formerly get_bit_value
def set_node_type_value(node_type, node_type_list, boolean_value):
    print "initial node_type_list in set_node_type_value", node_type_list
    if node_type == "install":
        node_type_dictionary["INSTALL"] = True
    elif node_type == "data":
        node_type_dictionary["DATA"] = True
    elif node_type == "index":
        node_type_dictionary["INDEX"] = True
    elif node_type == "idp":
        node_type_dictionary["IDP"] = True
    elif node_type == "compute":
        node_type_dictionary["COMPUTE"] = True
    elif node_type == "min":
        node_type_dictionary["MIN"] = True
    elif node_type == "max":
        node_type_dictionary["MAX"] = True
    elif node_type == "all":
        node_type_dictionary["ALL"] = True
    else:
        raise ValueError("Invalid node type reference")

    return get_node_type(node_type_list)

def get_node_type(node_type_list):
    for key, value in node_type_dictionary.items():
        if value:
            node_type_list.append(key)
    return node_type_list

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
    parser.add_argument("-v","--version", dest="version", help="Displays the version of this script", action="store_true")
    parser.add_argument("--recommended_setup", dest="recommendedsetup", help="Sets esgsetup to use the recommended, minimal setup", action="store_true")
    parser.add_argument("--custom_setup", dest="customsetup", help="Sets esgsetup to use a custom, user-defined setup", action="store_true")
    parser.add_argument("--use-local-files", dest="uselocalfiles", help="Sets a flag for using local files instead of attempting to fetch a remote file", action="store_true")
    parser.add_argument("--devel", help="Sets the installation type to the devel build", action="store_true")
    parser.add_argument("--prod", help="Sets the installation type to the production build", action="store_true")

    args = parser.parse_args()
    return (args, parser)


def get_previous_node_type_config(config_file):
    '''
        Helper method for reading the last state of node type config from config dir file "config_type"
        Every successful, explicit call to --type|-t gets recorded in the "config_type" file
        If the configuration type is not explicity set the value is read from this file.
    '''
    try:
        last_config_type = open(config_file, "r")
        node_type_list = last_config_type.read().split()
        logger.debug("node_type_list is now: %s", " ".join(node_type_list))
        if node_type_list:
            return node_type_list
        else:
            raise NoNodeTypeError
    except IOError:
        raise NoNodeTypeError
    except NoNodeTypeError:
        logger.exception('''No node type selected nor available! \n Consult usage with --help flag... look for the \"--type\" flag
        \n(must come BEFORE \"[start|stop|restart|update]\" args)\n\n''')
        sys.exit(1)



def set_node_type_config(node_type_list, config_file):
    '''Write the node type list as a string to file '''
    logger.debug("new node_type_list: %s", node_type_list)
    if node_type_list:
        try:
            config_type_file = open(config_file, "w")
            config_type_file.write(" ".join(node_type_list))
        except IOError:
            logger.exception("Unable to save node type \n")
        else:
            logger.debug("Wrote %s to file as new node_type_string", " ".join(node_type_list))
            config_type_file.close()


def process_arguments(node_type_list, devel, esg_dist_url):
    logger.debug("node_type_list at start of process_arguments: %s", node_type_list)
    logger.info("node_type_list at start of process_arguments: %s", node_type_list)
    print "node_type_list at start of process_arguments: %s", node_type_list

    args, parser = _define_acceptable_arguments()

    logging.debug(pprint.pformat(args))
    logger.info("args: %s", args)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if args.install:
        if args.type:
            for arg in args.type:
                node_type_list = set_node_type_value(arg, node_type_list, True)
        installer_mode_dictionary["upgrade_mode"] = False
        installer_mode_dictionary["install_mode"] = True
        set_node_type_value("install", node_type_list, True)
        print "node_type_list before returning from args.install:", node_type_list
        logger.debug("Install Services")
    if args.update or args.upgrade:
        installer_mode_dictionary["upgrade_mode"] = True
        installer_mode_dictionary["install_mode"] = False
        set_node_type_value("install", node_type_list, True)
        logger.debug("Update Services")
        esg_functions.verify_esg_node_script("esg_node.py", esg_dist_url, script_version, script_maj_version, devel,"update")
    if args.fixperms:
        logger.debug("fixing permissions")
        setup_sensible_confs()
        sys.exit(0)
    if args.installlocalcerts:
        logger.debug("installing local certs")
        get_previous_node_type_config(config["esg_config_type_file"])
        install_local_certs()
        sys.exit(0)
    if args.generateesgfcsrs:
        logger.debug("generating esgf csrs")
        get_previous_node_type_config(config["esg_config_type_file"])
        generate_esgf_csrs()
        sys.exit(0)
    if args.generateesgfcsrsext:
        logger.debug("generating esgf csrs for other node")
        get_previous_node_type_config(config["esg_config_type_file"])
        generate_esgf_csrs_ext()
        sys.exit(0)
    if args.certhowto:
        logger.debug("cert howto")
        cert_howto()
        sys.exit(0)
    elif args.type:
        logger.debug("selecting type")
        logger.debug("args.type: %s", args.type)
        print "args.type:", args.type
        for arg in args.type:
            set_node_type_value(arg, node_type_list, True)
        sys.exit(0)
    elif args.settype:
        logger.debug("Selecting type for next start up")
        for arg in args.settype:
            logger.debug("arg: %s", arg)
            node_type_list = []
            node_type_list = set_node_type_value(arg, node_type_list, True)
        esg_bash2py.mkdir_p(config["esg_config_dir"])
        # logger.info("node type set to: [%s] (%s) ", selection_string, node_type_bit)
        set_node_type_config(node_type_list, config["esg_config_type_file"])
        sys.exit(0)
    elif args.gettype:
        get_previous_node_type_config(config["esg_config_type_file"])
        show_type()
        sys.exit(0)
    elif args.start:
        logger.debug("args: %s", args)
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        logger.debug("START SERVICES: %s", node_type_list)
        esg_setup.init_structure()
        start(node_type_list)
        sys.exit(0)
    elif args.stop:
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        logger.debug("STOP SERVICES")
        esg_setup.init_structure()
        stop(node_type_list)
        sys.exit(0)
    elif args.restart:
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        logger.debug("RESTARTING SERVICES")
        esg_setup.init_structure()
        stop(node_type_list)
        sleep(2)
        start(node_type_list)
        sys.exit(0)
    elif args.status:
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        get_node_status()
        #TODO: Exit with status code dependent on what is returned from get_node_status()
        sys.exit(0)
    elif args.updatesubinstaller:
        esg_functions.verify_esg_node_script("esg_node.py", esg_dist_url, script_version, script_maj_version, devel,"update")
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        esg_setup.init_structure()
        update_script(args[1], args[2])
        sys.exit(0)
    # elif args.updateapacheconf:
    #     logger.debug("checking for updated apache frontend configuration")
    #     esg_apache_manager.update_apache_conf()
    #     sys.exit(0)
    elif args.version:
        logger.info("Version: %s", script_version)
        logger.info("Release: %s", script_release)
        logger.info("Earth Systems Grid Federation (http://esgf.llnl.gov)")
        logger.info("ESGF Node Installation Script")
        sys.exit(0)
    elif args.recommendedsetup:
        recommended_setup = True
        custom_setup = False
    elif args.customsetup:
        recommended_setup = False
        custom_setup = True
    elif args.uselocalfiles:
        use_local_files = True
    elif args.devel:
        devel = True
    elif args.prod:
        devel = False
