import os
import socket
import logging
import platform
import sys

import yaml
from esgf_utilities import pybash

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def exit_on_false(assertion, err_msg):
    ''' Exit if the assertion fails '''
    try:
        assert assertion, err_msg
    except AssertionError:
        logger.error(err_msg)
        sys.exit(1)

def check_if_root():
    '''Check to see if the user has root privileges'''

    print "Checking for root privileges..."

    err_msg = "This program must be run with root privileges"
    exit_on_false(os.geteuid() == 0, err_msg)

    logger.debug("Root privileges found")
    return True

def check_os():
    ''' Check if the operating system on server is Redhat or CentOS '''

    print "Checking operating system..."
    print "  {}".format(platform.platform())
    machine = platform.machine()
    req_machines = ['x86_64']
    err_msg = "Accepted machine types: {}, Found: {}".format(req_machines, machine)
    exit_on_false(machine in req_machines, err_msg)

    dist = platform.linux_distribution(full_distribution_name=0)
    name = dist[0].lower()
    req_names = ['rhel', 'redhat', 'centos', 'scientific']
    err_msg = "Accepted distributions: {}, Found: {}".format(req_names, name or "None")
    exit_on_false(name in req_names, err_msg)

    major = dist[1].split('.')[0]
    req_major = ['6']
    err_msg = "Accepted versions: {}, Found: {}".format(req_major, major or "None")
    exit_on_false(major in req_major, err_msg)

    logger.debug("dist: %s", dist)
    return True

def check_fqdn():
    ''' Check the machine's fully qualified domain name'''

    #NOTE This is a psuedo check.

    err_msg = "Error getting fully qualified domain name"
    try:
        fqdn = socket.getfqdn()
    except socket.error as err:
        logger.error("%s, %s", err_msg, str(err))
        sys.exit(1)
    exit_on_false(fqdn != '' and fqdn != None, err_msg)

    logger.debug("FQDN: %s", fqdn)
    return True

def check_prerequisites():
    '''
        A check for what is expected to be on the system a-priori that we are
        not going to install or be responsible for.
    '''
    # checking for OS, architecture, distribution and version
    print "Checking prerequisites..."
    check_os()
    check_if_root()
    check_fqdn()

    return True

def init_structure():
    '''Create directories to hold ESGF scripts, config files, and logs'''
    directories_to_check = [
        config["scripts_dir"],
        config["esg_backup_dir"],
        config["esg_tools_dir"],
        config["esg_log_dir"],
        config["esg_config_dir"],
        config["esg_etc_dir"],
        config["tomcat_conf_dir"]
    ]
    for directory in directories_to_check:
        if not os.path.isdir(directory):
            pybash.mkdir_p(directory)

    os.chmod(config["esg_etc_dir"], 0777)

    #Create esgf.properties file
    if not os.path.isfile(config["property_file"]):
        pybash.touch(config["property_file"])

    return True
