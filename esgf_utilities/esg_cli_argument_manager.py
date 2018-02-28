import os
import sys
import shutil
import logging
import argparse
import psutil
import pprint
from time import sleep
import yaml
from esgf_utilities import esg_functions
from base import esg_setup
from base import esg_apache_manager
from base import esg_tomcat_manager
from base import esg_postgres
from esgf_utilities import esg_bash2py
from esgf_utilities.esg_exceptions import NoNodeTypeError

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

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
        Return a tuple with the node's status
    '''
    node_running = True
    node_type = get_node_type()
    postgres_status = esg_postgres.postgres_status()
    if postgres_status:
        print "Postgres is running"
        print postgres_status[1]
    else:
        print "Postgres is stopped"
        print postgres_status[1]
        node_running = False

    tomcat_status = esg_tomcat_manager.check_tomcat_status()
    if tomcat_status:
        print "Tomcat is running"
        tomcat_pid = int(tomcat_status.strip())
        tomcat_process = psutil.Process(tomcat_pid)
        pinfo = tomcat_process.as_dict(attrs=['pid', 'username', 'cpu_percent', 'name'])
        print pinfo
    else:
        print "Tomcat is stopped."
        node_running = False

    apache_status = esg_apache_manager.check_apache_status()
    if apache_status:
        print "Httpd is running"
    else:
        print "httpd is stopped"
        node_running = False

    print "\n*******************************"
    print "ESGF Node Status"
    print "******************************* \n"
    if node_running:
        print "Node is running"
    else:
        print "Node is stopped"

    #TODO conditionally reflect the status of globus (gridftp) process
        #This is here for sanity checking...
    show_esgf_process_list()
    pass

def show_esgf_process_list():
    print "\n*******************************"
    print "Active ESGF processes"
    print "******************************* \n"
    procs = ["postgres", "jsvc", "globus-gr", "java", "myproxy", "httpd", "postmaster"]
    esgf_processes = [p.info for p in psutil.process_iter(attrs=['pid', 'name', 'username', 'cmdline']) if any(proc_name in p.info['name'] for proc_name in procs)]
    for process in esgf_processes:
        print process


def update_script(script_name, script_directory):
    '''
        arg (1) - name of installation script root name. Ex:security which resolves to script file esg-security
        arg (2) - directory on the distribution site where script is fetched from Ex: orp
        usage: update_script security orp - looks for the script esg-security in the distriubtion directory "orp"
    '''
    pass

#Formerly get_bit_value
def set_node_type_value(node_type, config_file=config["esg_config_type_file"]):

    node_type = [node.upper() for node in node_type]
    with open(config_file, "w") as esg_config_file:
        esg_config_file.write(" ".join(node_type))


def get_node_type(config_file=config["esg_config_type_file"]):
    '''
        Helper method for reading the last state of node type config from config dir file "config_type"
        Every successful, explicit call to --type|-t gets recorded in the "config_type" file
        If the configuration type is not explicity set the value is read from this file.
    '''
    try:
        last_config_type = open(config_file, "r")
        node_type_list = last_config_type.read().split()
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

def process_arguments(node_type_list, devel, esg_dist_url):
    args, parser = _define_acceptable_arguments()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if args.install:
        if args.type:
            set_node_type_value(args.type)
        installer_mode_dictionary["upgrade_mode"] = False
        installer_mode_dictionary["install_mode"] = True
        logger.debug("Install Services")
        node_type_list = get_node_type()
        return node_type_list + ["INSTALL"]
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
        get_node_type(config["esg_config_type_file"])
        install_local_certs()
        sys.exit(0)
    if args.generateesgfcsrs:
        logger.debug("generating esgf csrs")
        get_node_type(config["esg_config_type_file"])
        generate_esgf_csrs()
        sys.exit(0)
    if args.generateesgfcsrsext:
        logger.debug("generating esgf csrs for other node")
        get_node_type(config["esg_config_type_file"])
        generate_esgf_csrs_ext()
        sys.exit(0)
    if args.certhowto:
        logger.debug("cert howto")
        cert_howto()
        sys.exit(0)
    elif args.type:
        set_node_type_value(args.type)
        sys.exit(0)
    elif args.settype:
        logger.debug("Selecting type for next start up")
        for arg in args.settype:
            logger.debug("arg: %s", arg)
            node_type_list = []
            node_type_list = set_node_type_value(arg, node_type_list, True)
        esg_bash2py.mkdir_p(config["esg_config_dir"])
        set_node_type_config(node_type_list, config["esg_config_type_file"])
        sys.exit(0)
    elif args.gettype:
        get_node_type(config["esg_config_type_file"])
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
        get_node_status()
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
