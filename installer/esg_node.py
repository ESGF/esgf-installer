import os
import subprocess
import sys
import logging
import socket
from esg_exceptions import UnprivilegedUserError, WrongOSError, UnverifiedScriptError
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
import esg_subsystem
import esg_node_manager
import esg_logging_manager
import esg_init
import yaml


logger = esg_logging_manager.create_rotating_log(__name__)
print "logger:", logger

# config = esg_init.init()
with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

print "config:", config

logger.info("keystore_alias: %s", config["keystore_alias"])
# os.environ['DISCOVERONLY'] = Expand.colonMinus("DISCOVERONLY")
os.environ['LANG'] = "POSIX"
os.umask(022)

DEBUG = esg_bash2py.Expand.colonMinus("DEBUG", False)
VERBOSE = esg_bash2py.Expand.colonMinus("VERBOSE", "0")
# INSTALL_BIT=1
# TEST_BIT=2
# DATA_BIT=4
# INDEX_BIT=8
# IDP_BIT=16
# COMPUTE_BIT=32
# WRITE_ENV_BIT=64
# PRIVATE_BIT=128
# NOTE: remember to adjust (below) when adding new bits!!
# MIN_BIT=4
# MAX_BIT=64
# ALL_BIT=DATA_BIT+INDEX_BIT+IDP_BIT+COMPUTE_BIT


bit_boolean_dictionary = {"INSTALL_BIT": False, "TEST_BIT": False, "DATA_BIT": False, "INDEX_BIT": False,
                          "IDP_BIT": False, "COMPUTE_BIT": False, "WRITE_ENV_BIT": False, "MIN_BIT": 4, "MAX_BIT": 64}
ALL_BIT = bit_boolean_dictionary["DATA_BIT"] and bit_boolean_dictionary[
    "INDEX_BIT"] and bit_boolean_dictionary["IDP_BIT"] and bit_boolean_dictionary["COMPUTE_BIT"]
install_mode = 0
upgrade_mode = 0

node_type_list = []


def get_node_type():
    for key, value in bit_boolean_dictionary.items():
        if value:
            node_type_list.append(key)

devel = esg_bash2py.Expand.colonMinus("devel", True)
recommended_setup = 1

custom_setup = 0
use_local_files = 0

progname = "esg-node"
script_version = "v2.0-RC5.4.0-devel"
script_maj_version = "2.0"
script_release = "Centaur"
force_install = False

#--------------
# User Defined / Settable (public)
#--------------
#--------------

# os.environ['UVCDAT_ANONYMOUS_LOG'] = False

esg_root_id = esg_functions.get_esg_root_id()


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
    logger.info("before selecting distribution mirror: %s",
                config.esgf_dist_mirror)
    if any(argument in sys.argv for argument in ["install", "update", "upgrade"]):
        logger.debug("interactive")
        config.esgf_dist_mirror = esg_mirror_manager.get_esgf_dist_mirror(
            "interactive", install_type)
    else:
        logger.debug("fastest")
        config.esgf_dist_mirror = esg_mirror_manager.get_esgf_dist_mirror(
            "fastest", install_type)

    logger.info("selected distribution mirror: %s",
                config.esgf_dist_mirror)


def set_esg_dist_url():
    # Setting esg_dist_url with previously gathered information
    esg_dist_url_root = os.path.join(
        "http://", config.esgf_dist_mirror, "dist")
    logger.debug("esg_dist_url_root: %s", esg_dist_url_root)
    if devel is True:
        esg_dist_url = os.path.join("http://", esg_dist_url_root, "/devel")
    else:
        esg_dist_url = esg_dist_url_root

    logger.debug("esg_dist_url: %s", esg_dist_url)


def download_esg_installarg(esg_dist_url):
    ''' Downloading esg-installarg file '''
    if not os.path.isfile(config.esg_installarg_file) or force_install or os.path.getmtime(config.esg_installarg_file) < os.path.getmtime(os.path.realpath(__file__)):
        esg_installarg_file_name = esg_bash2py.trim_string_from_head(
            config.esg_installarg_file)
        esg_functions.download_update(config.esg_installarg_file, os.path.join(
            esg_dist_url, "esgf-installer", esg_installarg_file_name), force_download=force_install)
        try:
            if not os.path.getsize(config.esg_installarg_file) > 0:
                os.remove(config.esg_installarg_file)
            esg_bash2py.touch(config.esg_installarg_file)
        except IOError, error:
            logger.error(error)


def create_new_list_from_keys(dictionary):
    """ Return clean option list."""
    return [node_option.split("_BIT")[0].lower() for node_option in dictionary.keys()]


def check_selected_node_type(bit_boolean_dictionary, node_type_list):
    ''' Make sure a valid node_type has been selected before performing and install '''

    node_options_modified = create_new_list_from_keys(bit_boolean_dictionary)
    logger.debug("node_options_modified: %s", node_options_modified)
    for option in node_type_list:
        logger.debug("option: %s", option)
        if option in node_options_modified:
            continue
        else:
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
    return True


def init_connection():
    """ Initialize Connection to node."""
    logger.info("esg-node initializing...")
    try:
        logger.info(socket.getfqdn())
    except socket.error:
        logger.error(
            "Please be sure this host has a fully qualified hostname and reponds to socket.getfdqn() command")
        sys.exit()


def get_installation_type(script_version):
    # Determining if devel or master directory of the ESGF distribution mirror
    # will be use for download of binaries
    if "devel" in script_version:
        logger.debug("Using devel version")
        return "devel"
    else:
        return "master"


def get_user_response():
    """ Capture user response. """
    while True:
        default_install_answer = "Y"
        begin_installation = raw_input(
            "Are you ready to begin the installation? [Y/n] ") or default_install_answer

        if begin_installation.lower() == "n" or begin_installation.lower() == "no":
            print "Canceling installation"
            sys.exit(0)
        elif begin_installation.lower() == "y" or begin_installation.lower() == "yes":
            break
            # return "y"
        else:
            print "Invalid option.  Please select a valid option [Y/n]"


def install_log_info():
    if force_install:
        logger.info("(force install is ON)")
    # if node_type_bit & DATA_BIT != 0:
    if bit_boolean_dictionary["DATA_BIT"]:
        logger.info("(data node type selected)")
    if bit_boolean_dictionary["INDEX_BIT"]:
        # if node_type_bit & INDEX_BIT != 0:
        logger.info("(index node type selected)")
    if bit_boolean_dictionary["IDP_BIT"]:
        # if node_type_bit & IDP_BIT != 0:
        logger.info("(idp node type selected)")
    if bit_boolean_dictionary["COMPUTE_BIT"]:
        # if node_type_bit & COMPUTE_BIT != 0:
        logger.info("(compute node type selected)")


def system_component_installation():
    #---------------------------------------
    # Installation of basic system components.
    # (Only when one setup in the sequence is okay can we move to the next)
    #---------------------------------------
    # logger.debug(node_type_bit & INSTALL_BIT)
    # if node_type_bit & INSTALL_BIT !=0:
    if "install" in node_type_list:
        esg_setup.setup_java()
        esg_setup.setup_ant()
        esg_postgres.setup_postgres()
        esg_setup.setup_cdat()
        # logger.debug("node_type_bit & (DATA_BIT+COMPUTE_BIT) %s", node_type_bit & (DATA_BIT+COMPUTE_BIT))
        if bit_boolean_dictionary["DATA_BIT"] and bit_boolean_dictionary["COMPUTE_BIT"]:
            # if node_type_bit & (DATA_BIT+COMPUTE_BIT) != 0:
            esg_publisher.setup_esgcet()
            esg_tomcat_manager.setup_tomcat(devel)
            esg_apache_manager.setup_apache_frontend(devel)
    # setup_esgcet()
    # test_esgcet()


def main(node_type_list):
    # default distribution_url
    esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"

    # initialize connection
    init_connection()

    # determine installation type
    install_type = get_installation_type(script_version)

    # select_distribution_mirror(install_type)
    # set_esg_dist_url()
    # download_esg_installarg()

    # process command line arguments
    node_type_list = esg_cli_argument_manager.get_previous_node_type_config(
        config["esg_config_type_file"])
    logger.debug("node_type_list: %s", node_type_list)
    esg_cli_argument_manager.process_arguments(
        install_mode, upgrade_mode, node_type_list, devel, esg_dist_url)
    try:
        esg_setup.check_prerequisites()
    except UnprivilegedUserError:
        logger.info(
            "$([FAIL]) \n\tMust run this program with root's effective UID\n\n")
        sys.exit(1)
    except WrongOSError:
        logger.info(
            "ESGF can only be installed on versions 6 of Red Hat, CentOS or Scientific Linux x86_64 systems")
        sys.exit(1)

    esg_functions.verify_esg_node_script(os.path.basename(
        __file__), esg_dist_url, script_version, script_maj_version, devel)

    logger.debug("node_type_list: %s", node_type_list)

    print '''
    -----------------------------------
    ESGF Node Installation Program
    -----------------------------------'''

    # logger.debug("node_type_bit & INSTALL_BIT != 0: %s", node_type_bit & INSTALL_BIT != 0)
    # logger.debug("node_type_bit: %i, %s", node_type_bit, type(node_type_bit))
    # logger.debug("MIN_BIT: %i, %s", MIN_BIT, type(MIN_BIT))
    # logger.debug("MAX_BIT: %i", MAX_BIT)
    # logger.debug("node_type_bit >= MIN_BIT: %s",  node_type_bit >= MIN_BIT)
    # logger.debug("node_type_bit >= MIN_BIT and node_type_bit <= MAX_BIT: %s", node_type_bit >= MIN_BIT and node_type_bit <= MAX_BIT)

    esg_cli_argument_manager.get_previous_node_type_config(
        config["esg_config_type_file"])
    check_selected_node_type(bit_boolean_dictionary, node_type_list)

    # Display node information to user
    esgf_node_info()

    if devel is True:
        print "(Installing DEVELOPMENT tree...)"

    # Process User Response
    get_user_response()

    #
    esg_setup.init_structure()

    # log info
    install_log_info()

    esg_setup.initial_setup_questionnaire()
    #---------------------------------------
    # Installation of prerequisites.
    #---------------------------------------
    # TODO: Uncomment this; only removed for testing speedup
    # esg_setup.install_prerequisites()

    #---------------------------------------
    # Setup ESGF RPM repository
    #---------------------------------------
    print "*******************************"
    print "Setting up ESGF RPM repository"
    print "******************************* \n"

    # install dependencies
    system_component_installation()

    #---------------------------------------
    #Installation of basic system components.
    # (Only when one setup in the sequence is okay can we move to the next)
    #---------------------------------------
    # logger.debug(node_type_bit & INSTALL_BIT)
    # if node_type_bit & INSTALL_BIT !=0:
    if "install" in node_type_list:
        esg_setup.setup_java()
        esg_setup.setup_ant()
        esg_postgres.setup_postgres()
        esg_setup.setup_cdat()
        # logger.debug("node_type_bit & (DATA_BIT+COMPUTE_BIT) %s", node_type_bit & (DATA_BIT+COMPUTE_BIT))
        if bit_boolean_dictionary["DATA_BIT"] and bit_boolean_dictionary["COMPUTE_BIT"]:
        # if node_type_bit & (DATA_BIT+COMPUTE_BIT) != 0:
            esg_publisher.setup_esgcet()
        esg_tomcat_manager.setup_tomcat(devel)
        esg_apache_manager.setup_apache_frontend(devel)
        esg_subsystem.setup_subsystem("node-manager", "esgf-node-manager", esg_dist_url)
    # setup_esgcet()
    # test_esgcet()

    # yum_remove_rpm_forge_output = yum_remove_rpm_forge.communicate()


if __name__ == '__main__':
    main(node_type_list)
