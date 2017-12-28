import os
import subprocess
import sys
import logging
import socket
from esg_exceptions import UnprivilegedUserError, WrongOSError, UnverifiedScriptError
from distutils.spawn import find_executable
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
import esg_property_manager
import esg_logging_manager
import esg_init
import esg_questionnaire
import yaml


logger = esg_logging_manager.create_rotating_log(__name__)

with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

os.environ['LANG'] = "POSIX"
os.umask(022)

node_types = {"INSTALL": False, "DATA": False, "INDEX": False,
                          "IDP": False, "COMPUTE": False, "MIN": 4, "MAX": 64}
node_types["ALL"] = node_types["DATA"] and node_types[
    "INDEX"] and node_types["IDP"] and node_types["COMPUTE"]

node_type_list = []


def get_node_type():
    for key, value in node_types.items():
        if value:
            node_type_list.append(key)

devel = True
recommended_setup = 1

custom_setup = 0
use_local_files = 0

progname = "esg-node"
#TODO: Look at parent repo and set version from tag using semver
script_version = "v3.0"
script_maj_version = "3.0"
script_release = "Centaur"
force_install = False

#--------------
# User Defined / Settable (public)
#--------------
#--------------


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
        except IOError:
            logger.exception("Unable to access esg-installarg file")


def check_selected_node_type(node_types, node_type_list):
    ''' Make sure a valid node_type has been selected before performing and install '''

    # node_options_modified = create_new_list_from_keys(node_types)
    # logger.debug("node_options_modified: %s", node_options_modified)
    for option in node_type_list:
        logger.debug("option: %s", option)
        if option in node_types.keys():
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


def begin_installation():
    """ Capture user response. """
    while True:
        start_installation = raw_input(
            "Are you ready to begin the installation? [Y/n] ") or "Y"

        if start_installation.lower() in ["n", "no"]:
            print "Canceling installation"
            sys.exit(0)
        elif start_installation.lower() in ["y", "yes"]:
            break
        else:
            print "Invalid option.  Please select a valid option [Y/n]"


def install_log_info():
    if force_install:
        logger.info("(force install is ON)")
    if node_types["DATA"]:
        logger.info("(data node type selected)")
    if node_types["INDEX"]:
        logger.info("(index node type selected)")
    if node_types["IDP"]:
        logger.info("(idp node type selected)")
    if node_types["COMPUTE"]:
        logger.info("(compute node type selected)")


def system_component_installation():
    #---------------------------------------
    # Installation of basic system components.
    # (Only when one setup in the sequence is okay can we move to the next)
    #---------------------------------------

    if "INSTALL" in node_type_list:
        esg_setup.setup_java()
        esg_setup.setup_ant()
        esg_postgres.setup_postgres()
        esg_tomcat_manager.main()
        esg_apache_manager.main()
    if "DATA" in node_type_list:
        esg_subsystem.main()
        esg_publisher.main()
    if "DATA" in node_type_list and "COMPUTE" in node_type_list:
        #CDAT only used on with Publisher; move
        esg_setup.setup_cdat()

def check_for_conda():
    if not os.path.isdir("/usr/local/conda"):
        print "Please run the install_conda.sh script before attempting to install ESGF."
    if "conda" not in find_executable("python"):
        print 'Please activate the esgf-pub conda environment before running the install script by using the following command:'
        print "source /usr/local/conda/bin/activate esgf-pub"
        sys.exit(1)


def done_remark():
    '''Prints info to denote that the installation has completed'''
    print "\nFinished!..."
    print "In order to see if this node has been installed properly you may direct your browser to:"
    if "DATA" in node_type_list or "INSTALL" in node_type_list:
        esgf_host = esg_functions.get_esgf_host()
        print "http://{esgf_host}/thredds".format(esgf_host=esgf_host)
        print "http://{esgf_host}/esg-orp".format(esgf_host=esgf_host)
    if "INDEX" in node_type_list:
        print "http://${esgf_host}/"
    if "COMPUTE" in node_type_list:
        print "http://${esgf_host}/las"

    print "Your peer group membership -- :  [{node_peer_group}]".format(node_peer_group=esg_property_manager.get_property("node_peer_group"))
    print "Your specified \"index\" peer - :[{esgf_index_peer}]) (url = http://{esgf_index_peer}/)".format(esgf_index_peer=esg_property_manager.get_property("esgf_index_peer"))

#     if [ -d "${thredds_content_dir}/thredds" ]; then
#         echo
#         echo "[Note: Use UNIX group permissions on ${thredds_content_dir}/thredds/esgcet to enable users to be able to publish thredds catalogs from data therein]"
#         echo " %> chgrp -R <appropriate unix group for publishing users> ${thredds_content_dir}/thredds"
#     fi
#
    print '''
        -------------------------------------------------------
        Administrators of this node should subscribe to the
        esgf-node-admins@lists.llnl.gov by sending email to: "majordomo@lists.llnl.gov"
        with the body: "subscribe esgf-node-admins"
        -------------------------------------------------------
'''
#
#     #echo "(\"Test Project\" -> pcmdi.${esg_root_id}.${node_short_name}.test.mytest)"
#     echo ""


def setup_esgf_rpm_repo():
    #TODO: implement
    # echo '[esgf]' > /etc/yum.repos.d/esgf.repo
	# echo 'name=ESGF' >> /etc/yum.repos.d/esgf.repo
	# if [[ ${DISTRIB} == "CentOS" ]] || [[ ${DISTRIB} = "Scientific Linux" ]] ; then
	# 	echo "baseurl=${esgf_dist_mirror}/RPM/centos/6/x86_64" >> /etc/yum.repos.d/esgf.repo
	# elif [[ ${DISTRIB} == "Red Hat"* ]] ; then
	# 	echo "baseurl=${esgf_dist_mirror}/RPM/redhat/6/x86_64" >> /etc/yum.repos.d/esgf.repo
	# fi
	# echo 'failovermethod=priority' >> /etc/yum.repos.d/esgf.repo
    # 	echo 'enabled=1' >> /etc/yum.repos.d/esgf.repo
    # 	echo 'priority=90' >> /etc/yum.repos.d/esgf.repo
    # 	echo 'gpgcheck=0' >> /etc/yum.repos.d/esgf.repo
    # 	echo 'proxy=_none_' >> /etc/yum.repos.d/esgf.repo
    pass

def main(node_type_list):
    check_for_conda()
    # default distribution_url
    esg_dist_url = "http://aims1.llnl.gov/esgf/dist"

    # initialize connection
    init_connection()

    # determine installation type
    install_type = get_installation_type(script_version)
    print "install_type:", install_type

    # select_distribution_mirror(install_type)
    # set_esg_dist_url()
    # download_esg_installarg()

    # process command line arguments
    # node_type_list = esg_cli_argument_manager.get_previous_node_type_config(
    #     config["esg_config_type_file"])
    # logger.debug("node_type_list: %s", node_type_list)
    cli_info = esg_cli_argument_manager.process_arguments(node_type_list, devel, esg_dist_url)
    print "cli_info:", cli_info
    if cli_info:
        node_type_list = cli_info


    esg_setup.check_prerequisites()

    esg_functions.verify_esg_node_script(os.path.basename(
        __file__), esg_dist_url, script_version, script_maj_version, devel)

    logger.debug("node_type_list: %s", node_type_list)
    logger.info("node_type_list: %s", node_type_list)
    print "node_type_list after process_arguments:", node_type_list

    print '''
    -----------------------------------
    ESGF Node Installation Program
    -----------------------------------'''

    #If not type not set from CLI argument, look at previous node type setting
    if not [node_type for node_type in node_type_list if node_type in node_types.keys()]:
        previous_node_type = esg_cli_argument_manager.get_previous_node_type_config(
            config["esg_config_type_file"])
        print "previous_node_type:", previous_node_type
    check_selected_node_type(node_types, node_type_list)

    # Display node information to user
    esgf_node_info()

    if devel is True:
        print "(Installing DEVELOPMENT tree...)"

    # install_conda()

    # Process User Response
    # begin_installation()

    #
    esg_setup.init_structure()

    # log info
    install_log_info()

    esg_questionnaire.initial_setup_questionnaire()

    #---------------------------------------
    # Setup ESGF RPM repository
    #---------------------------------------
    print "*******************************"
    print "Setting up ESGF RPM repository"
    print "******************************* \n"

    setup_esgf_rpm_repo()

    # install dependencies
    system_component_installation()
    done_remark()


if __name__ == '__main__':
    main(node_type_list)
