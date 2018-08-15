import os
import re
import socket
import logging
import platform
import netifaces
import yaml
from esgf_utilities import pybash
from esgf_utilities import esg_functions

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def check_if_root():
    '''Check to see if the user has root privileges'''

    print "Checking for root privileges on {host}...".format(host=socket.gethostname())

    err_msg = "\nThis program must be run with root privileges\n\n"
    assert (os.geteuid() == 0), err_msg

    logger.debug("Root privileges found")

def check_os():
    ''' Check if the operating system on server is Redhat or CentOS '''

    print "Checking operating system..."

    release_version = re.search(
        r"(centos|redhat)-(\S*)-",
        platform.platform()
    ).groups()

    logger.debug("Release Version: %s", release_version)

    err_msg = """
        ESGF can only be installed on versions 6 of Red Hat,
        CentOS or Scientific Linux x86_64 systems
    """
    assert ("6" in release_version[1]), err_msg

    print "Operating System = {OS} {version}".format(
        OS=release_version[0],
        version=release_version[1]
    )


def check_prerequisites():
    '''
        A check for what is expected to be on the system a-priori that we are
        not going to install or be responsible for.
    '''

    print "Checking prerequisites..."
    checks = [check_if_root, check_os]
    for check in checks:
        try:
            check()
        except AssertionError as err:
            logger.exception(str(err))
            esg_functions.exit_with_error(1)

    # checking for OS, architecture, distribution and version
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
