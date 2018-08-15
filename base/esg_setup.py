import os
import socket
import logging
import platform
import sys

import yaml
from esgf_utilities import pybash
from esgf_utilities import esg_functions

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def check_if_root():
    '''Check to see if the user has root privileges'''

    print "Checking for root privileges..."

    err_msg = "This program must be run with root privileges"
    assert (os.geteuid() == 0), err_msg

    logger.debug("Root privileges found")

def check_os():
    ''' Check if the operating system on server is Redhat or CentOS '''

    print "Checking operating system..."
    print "  {}".format(platform.platform())
    machine = platform.machine()
    req_machines = ['x86_64']
    assert machine in req_machines, "Accepted machine types: {}, Found: {}".format(req_machines, machine)

    uname = platform.uname()
    name = uname[0].lower()
    req_names = ['rhel', 'redhat', 'centos', 'scientific']
    assert name in req_names, "Accepted distrobutions: {}, Found: {}".format(req_names, name)

    major = uname[2].split('.')[0]
    req_major = ['6']
    assert major in req_major, "Accepted versions: {}, Found: {}".format(req_major, major)

    logger.debug("uname: %s", uname)


def check_prerequisites():
    '''
        A check for what is expected to be on the system a-priori that we are
        not going to install or be responsible for.
    '''
    # checking for OS, architecture, distribution and version
    print "Checking prerequisites..."
    checks = [check_os, check_if_root]
    for check in checks:
        try:
            check()
        except AssertionError as err:
            logger.error(str(err))
            sys.exit(1)

    return True

def create_esg_directories():
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

def init_structure():

    create_esg_directories()

    #Create esgf.properties file
    if not os.path.isfile(config["property_file"]):
        pybash.touch(config["property_file"])

    #--------------
    # Setup variables....
    #--------------

    esg_functions.get_public_ip()
