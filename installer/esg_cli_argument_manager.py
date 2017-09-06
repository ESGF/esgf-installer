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
import yaml

logger = esg_logging_manager.create_rotating_log(__name__)

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

progname = "esg-node"
script_version = "v2.0-RC5.4.0-devel"
script_maj_version = "2.0"
script_release = "Centaur"

node_type_dictionary = {"INSTALL_BIT": False , "TEST_BIT": False, "DATA_BIT":False, "INDEX_BIT":False, "IDP_BIT":False, "COMPUTE_BIT":False, "WRITE_ENV_BIT":False, "MIN_BIT": False, "MAX_BIT": False}
installater_mode_dictionary = {"install_mode": False, "upgrade_mode": False}

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

#Formerly get_bit_value
def set_node_type_value(node_type, node_type_list, boolean_value):
    if node_type == "install":
        node_type_dictionary["INSTALL_BIT"] = True
    elif node_type == "data":
        node_type_dictionary["DATA_BIT"] = True
    elif node_type == "index":
        node_type_dictionary["INDEX_BIT"] = True
    elif node_type == "idp":
        node_type_dictionary["IDP_BIT"] = True
    elif node_type == "compute":
        node_type_dictionary["COMPUTE_BIT"] = True
    elif node_type == "write_env":
        node_type_dictionary["WRITE_ENV_BIT"] = True
    elif node_type == "min":
        node_type_dictionary["MIN_BIT"] = True
    elif node_type == "max":
        node_type_dictionary["MAX_BIT"] = True
    # elif node_type == "all":
    #     node_type_dictionary["ALL_BIT"] = True
    else:
        raise ValueError("Invalid node type reference")

    return get_node_type(node_type_list)

def get_node_type(node_type_list):
    for key, value in node_type_dictionary.items():
        if value:
            node_type = key.split("_BIT")[0].lower()
            logger.debug("node_type: %s", node_type)
            node_type_list.append(node_type)
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
    parser.add_argument("--write-env", dest="writeenv", help="Writes the necessary environment variables to file {envfile}".format(envfile = config["envfile"]), action="store_true")
    parser.add_argument("-v","--version", dest="version", help="Displays the version of this script", action="store_true")
    parser.add_argument("--recommended_setup", dest="recommendedsetup", help="Sets esgsetup to use the recommended, minimal setup", action="store_true")
    parser.add_argument("--custom_setup", dest="customsetup", help="Sets esgsetup to use a custom, user-defined setup", action="store_true")
    parser.add_argument("--use-local-files", dest="uselocalfiles", help="Sets a flag for using local files instead of attempting to fetch a remote file", action="store_true")
    parser.add_argument("--devel", help="Sets the installation type to the devel build", action="store_true")
    parser.add_argument("--prod", help="Sets the installation type to the production build", action="store_true")
    parser.add_argument("--clear-env-state", dest="clearenvstate", help="Removes the file holding the environment state of last install", action="store_true")

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
        # logger.debug("readlines from file: %s", last_config_type.readlines())
        node_type_list = last_config_type.read().split()
        logger.debug("node_type_list is now: %s", " ".join(node_type_list))
        return node_type_list
    except IOError, error:
        logger.error(error)

    try:
        node_type_list
    except NameError, error:
        print "error:", error
    # if not node_type_list:
        print '''ERROR: No node type selected nor available! \n Consult usage with --help flag... look for the \"--type\" flag
        \n(must come BEFORE \"[start|stop|restart|update]\" args)\n\n'''
        sys.exit(1)

def set_node_type_config(node_type_list, config_file):
    '''Write the node type list as a string to file '''
    logger.debug("new node_type_list: %s", node_type_list)
    if node_type_list:
        try:
            config_type_file = open(config_file, "w")
            logger.debug("Writing %s to file as new node_type_string", " ".join(node_type_list))
            config_type_file.write(" ".join(node_type_list))
        except IOError, error:
            logger.error(error)

def process_arguments(install_mode, upgrade_mode, node_type_list, devel, esg_dist_url):
    selection_string = ""
    logger.debug("node_type_list at start of process_arguments: %s", node_type_list)

    args, parser = _define_acceptable_arguments()
    print "type of args:", type(args)

    logging.debug(pprint.pformat(args))
    logger.info("args: %s", args)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if args.install:
            installater_mode_dictionary["upgrade_mode"] = False
            installater_mode_dictionary["install_mode"] = True
            set_node_type_value("install", node_type_list, True)
            # if node_type_bit & bit_dictionary["INSTALL_BIT"] == 0:
            #     node_type_bit += get_bit_value("install")
            logger.debug("Install Services")
    if args.update or args.upgrade:
            installater_mode_dictionary["upgrade_mode"]= True
            installater_mode_dictionary["install_mode"] = False
            set_node_type_value("install", node_type_list, True)
            # if node_type_bit & bit_dictionary["INSTALL_BIT"] == 0:
            #     node_type_bit += get_bit_value("install")
            logger.debug("Update Services")
            esg_functions.verify_esg_node_script("esg_node.py", esg_dist_url, script_version, script_maj_version, devel,"update")
    if args.fixperms:
        logger.debug("fixing permissions")
        setup_sensible_confs
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
    elif args.verify:
        logger.debug("Verify Services")
        set_node_type_value("test", node_type_list, True)
        # if node_type_bit & get_bit_value("test") == 0:
        #     node_type_bit += get_bit_value("test")
        # logger.debug("node_type_bit = %s", node_type_bit)
        test_postgress()
        test_cdat()
        # test_esgcet()
        test_tomcat()
        test_tds()
        sys.exit(0)
    elif args.type:
        logger.debug("selecting type")
        logger.debug("args.type: %s", args.type)
        for arg in args.type:
            #TODO: refactor conditional to function with descriptive name
            set_node_type_value(arg, node_type_list, True)
            # if node_type_bit & get_bit_value(arg) == 0:
            #     node_type_bit += get_bit_value(arg)
                # selection_string += " "+arg
        # logger.info("node type set to: [%s] (%s) ", selection_string, node_type_bit)
        sys.exit(0)
    elif args.settype:
        logger.debug("Selecting type for next start up")
        for arg in args.settype:
            logger.debug("arg: %s", arg)
            node_type_list = []
            node_type_list = set_node_type_value(arg, node_type_list, True)
            #TODO: refactor conditional to function with descriptive name
            # if node_type_bit & get_bit_value(arg) == 0:
            #     node_type_bit += get_bit_value(arg)
            #     selection_string += " "+arg
        if not os.path.isdir(config["esg_config_dir"]):
            try:
                os.mkdir(config["esg_config_dir"])
            except IOError, error:
                logger.error(error)
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
    elif args.updateapacheconf:
        logger.debug("checking for updated apache frontend configuration")
        esg_apache_manager.update_apache_conf()
        sys.exit(0)
    elif args.writeenv:
        if node_type_dictionary["WRITE_ENV_BIT"]:
            print 'node_type_dictionary["WRITE_ENV_BIT"]', node_type_dictionary["WRITE_ENV_BIT"]
        # if node_type_bit & bit_dictionary["WRITE_ENV_BIT"] == 0:
        #     node_type_bit += bit_dictionary["WRITE_ENV_BIT"]
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
    elif args.clearenvstate:
        esg_functions.verify_esg_node_script("esg_node.py", esg_dist_url, script_version, script_maj_version, devel,"clear")
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        if os.path.isfile(config["envfile"]):
            shutil.move(config["envfile"], config["envfile"]+".bak")
            #empty out contents of the file
            open(config["envfile"], 'w').close()
