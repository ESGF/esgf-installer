import os
import re
import socket
import logging
import platform
import netifaces
import yaml
from esgf_utilities.esg_exceptions import WrongOSError, UnprivilegedUserError
from esgf_utilities import pybash
from esgf_utilities import esg_functions
from esgf_utilities import esg_property_manager

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def check_if_root():
    '''Check to see if the user is root'''
    print "Checking that you have root privileges on %s... " % (socket.gethostname())
    root_check = os.geteuid()
    if root_check != 0:
        raise UnprivilegedUserError("\nMust run this program with root's effective UID\n\n")
    logger.debug("Root user found.")
    return True

def check_os():
    '''Check if the operating system on server is Redhat or CentOS;
    returns False Otherwise'''
    print "Checking operating system....."
    release_version = re.search(
        "(centos|redhat)-(\S*)-", platform.platform()).groups()
    logger.debug("Release Version: %s", release_version)
    try:
        if "6" not in release_version[1]:
            raise WrongOSError
    except WrongOSError:
        logger.exception("ESGF can only be installed on versions 6 of Red Hat, CentOS or Scientific Linux x86_64 systems")
        esg_functions.exit_with_error(1)
    else:
        print "Operating System = {OS} {version}".format(OS=release_version[0], version=release_version[1])
        return True


def check_prerequisites():
    '''
        Checking for what we expect to be on the system a-priori that we are not going to install or be responsible for
    '''

    if not check_if_root():
        return False

    #----------------------------------------
    print "Checking requisites... "

    # checking for OS, architecture, distribution and version
    return check_os()

def create_esg_directories():
    '''Create directories to hold ESGF scripts, config files, and logs'''
    directories_to_check = [config["scripts_dir"], config["esg_backup_dir"], config["esg_tools_dir"],
                            config[
                                "esg_log_dir"], config["esg_config_dir"], config["esg_etc_dir"],
                            config["tomcat_conf_dir"]]
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

def _select_ip_address():
    choice = int(raw_input(""))
    return choice


def _render_ip_address_menu(ip_addresses):
    print "Detected multiple IP addresses bound to this host...\n"
    print "Please select the IP address to use for this installation\n"
    print "\t-------------------------------------------\n"
    for index, ip_address in enumerate(ip_addresses.iteritems(), 1):
        print "\t %i) %s" % (index, ip_address)
    print "\t-------------------------------------------\n"


def check_for_my_ip(force_install=False):
    '''Check server's IP address'''
    logger.debug("Checking for IP address(es)...")
    matched = 0
    my_ip_address = None
    eth0 = netifaces.ifaddresses(netifaces.interfaces()[1])
    ip_addresses = [ip["addr"] for ip in eth0[netifaces.AF_INET]]

    try:
        esgf_host_ip
    except NameError:
        esgf_host_ip = esg_property_manager.get_property("esgf.host.ip")

    if esgf_host_ip and not force_install:
        logger.info("Using IP: %s", esgf_host_ip)
        return 0

    # We want to make sure that the IP address we have in our config
    # matches one of the IPs that are associated with this host
    for ip_address in ip_addresses:
        if ip_address == esgf_host_ip:
            matched += 1

    if matched == 0:
        logger.info(
            "Configured host IP address does not match available IPs...")

    if not esgf_host_ip or force_install or matched == 0:
        if len(ip_addresses) > 1:
            # ask the user to choose...
            while True:
                _render_ip_address_menu(ip_addresses)
                default = 0
                choice = _select_ip_address() or default
                my_ip_address = ip_addresses[choice]
                logger.info("selected address -> %s", my_ip_address)
                break
        else:
            my_ip_address = ip_addresses[0]

    esg_property_manager.set_property("esgf_host_ip", my_ip_address)
    esgf_host_ip = esg_property_manager.get_property("esgf.host.ip")
    return esgf_host_ip
