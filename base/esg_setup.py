import sys
import os
import re
import socket
import logging
import platform
import netifaces
import yaml
from esgf_utilities.esg_exceptions import UnprivilegedUserError, WrongOSError, UnverifiedScriptError
from distutils.spawn import find_executable
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_functions
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

force_install = False

def check_if_root():
    '''Check to see if the user is root'''
    print "Checking that you have root privileges on %s... " % (socket.gethostname())
    root_check = os.geteuid()
    try:
        if root_check != 0:
            raise UnprivilegedUserError
        logger.debug("Root user found.")
    except UnprivilegedUserError:
        logger.exception("\nMust run this program with root's effective UID\n\n")
        esg_functions.exit_with_error(1)

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


def check_prerequisites():
    '''
        Checking for what we expect to be on the system a-priori that we are not going to install or be responsible for
    '''

    check_if_root()

    #----------------------------------------
    print "Checking requisites... "

    # checking for OS, architecture, distribution and version
    check_os()

def create_esg_directories():
    '''Create directories to hold ESGF scripts, config files, and logs'''
    directories_to_check = [config["scripts_dir"], config["esg_backup_dir"], config["esg_tools_dir"],
                            config[
                                "esg_log_dir"], config["esg_config_dir"], config["esg_etc_dir"],
                            config["tomcat_conf_dir"]]
    for directory in directories_to_check:
        if not os.path.isdir(directory):
            esg_bash2py.mkdir_p(directory)
    os.chmod(config["esg_etc_dir"], 0777)

def init_structure():

    create_esg_directories()

    #Create esgf.properties file
    if not os.path.isfile(config["config_file"]):
        esg_bash2py.touch(config["config_file"])

    #--------------
    # Setup variables....
    #--------------

    check_for_my_ip()

def _select_ip_address():
    choice = int(raw_input(""))
    return choice


def _render_ip_address_menu(ip_addresses):
    print "Detected multiple IP addresses bound to this host...\n"
    print "Please select the IP address to use for this installation\n"
    print "\t-------------------------------------------\n"
    for index, ip in enumerate(ip_addresses.iteritems(), 1):
        print "\t %i) %s" % (index, ip)
    print "\t-------------------------------------------\n"


def check_for_my_ip(force_install=False):
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
    for ip in ip_addresses:
        if ip == esgf_host_ip:
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


def set_default_java():
    esg_functions.stream_subprocess_output("alternatives --install /usr/bin/java java /usr/local/java/bin/java 3")
    esg_functions.stream_subprocess_output("alternatives --set java /usr/local/java/bin/java")

def check_for_existing_java():
    '''Check if a valid java installation is currently on the system'''
    java_path = find_executable("java", os.path.join(config["java_install_dir"],"bin"))
    if java_path:
        print "Detected an existing java installation at {java_path}...".format(java_path=java_path)
        return check_java_version(java_path)

def check_java_version(java_path):
    print "Checking Java version"
    try:
        java_version_output = esg_functions.call_subprocess("{java_path} -version".format(java_path=java_path))["stderr"]
    except KeyError:
        logger.exception("Could not check the Java version")
        esg_functions.exit_with_error(1)

    installed_java_version = re.search("1.8.0_\w+", java_version_output).group()
    if esg_version_manager.compare_versions(installed_java_version, config["java_version"]):
        print "Installed java version meets the minimum requirement "
    return java_version_output

def download_java(java_tarfile):
    print "Downloading Java from ", config["java_dist_url"]
    if not esg_functions.download_update(java_tarfile, config["java_dist_url"], force_install):
        logger.error("ERROR: Could not download Java")
        esg_functions.exit_with_error(1)

def write_java_install_log(java_path):
    java_version = re.search("1.8.0_\w+", check_java_version(java_path)).group()
    esg_functions.write_to_install_manifest("java", config["java_install_dir"], java_version)

def setup_java():
    '''
        Installs Oracle Java from rpm using yum localinstall.  Does nothing if an acceptible Java install is found.
    '''

    print "*******************************"
    print "Setting up Java {java_version}".format(java_version=config["java_version"])
    print "******************************* \n"

    if force_install:
        pass
    if check_for_existing_java():
            if esg_property_manager.get_property("install.java"):
                setup_java_answer = esg_property_manager.get_property("install.java")
            else:
                setup_java_answer = raw_input("Do you want to continue with Java installation and setup? [y/N]: ") or "N"
            if setup_java_answer.lower().strip() not in ["y", "yes"]:
                print "Skipping Java installation"
                return
            last_java_truststore_file = esg_functions.readlinkf(config["truststore_file"])

    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):

        java_tarfile = esg_bash2py.trim_string_from_head(config["java_dist_url"])
        jdk_directory = java_tarfile.split("-")[0]
        java_install_dir_parent = config["java_install_dir"].rsplit("/",1)[0]

        #Check for Java tar file
        if not os.path.isfile(java_tarfile):
            print "Don't see java distribution file {java_dist_file_path} either".format(java_dist_file_path=os.path.join(os.getcwd(),java_tarfile))
            download_java(java_tarfile)

        print "Extracting Java tarfile", java_tarfile
        esg_functions.extract_tarball(java_tarfile, java_install_dir_parent)

        #Create symlink to Java install directory (/usr/local/java)
        esg_bash2py.symlink_force(os.path.join(java_install_dir_parent, jdk_directory), config["java_install_dir"])

        os.chown(config["java_install_dir"], config["installer_uid"], config["installer_gid"])
        #recursively change permissions
        esg_functions.change_ownership_recursive(config["java_install_dir"], config["installer_uid"], config["installer_gid"])

    set_default_java()
    print check_java_version("java")
    write_java_install_log("java")
    # print check_java_version("{java_install_dir}/bin/java".format(java_install_dir=config["java_install_dir"]))


def write_ant_install_log():
    ant_version = esg_functions.call_subprocess("ant -version")["stderr"]
    esg_functions.write_to_install_manifest("ant", "/usr/bin/ant", ant_version)

def setup_ant():
    '''Install ant via yum'''

    print "\n*******************************"
    print "Setting up Ant"
    print "******************************* \n"

    if os.path.exists(os.path.join("/usr", "bin", "ant")):
        esg_functions.stream_subprocess_output("ant -version")
        if esg_property_manager.get_property("install.ant"):
            setup_ant_answer = esg_property_manager.get_property("install.ant")
        else:
            setup_ant_answer = raw_input("Do you want to continue with the Ant installation [y/N]: ") or esg_property_manager.get_property("install.ant") or "no"
        if setup_ant_answer.lower() in ["n", "no"]:
            return

    esg_functions.stream_subprocess_output("yum -y install ant")
    write_ant_install_log()

def setup_cdat():
    print "Checking for *UV* CDAT (Python+CDMS) {cdat_version} ".format(cdat_version=config["cdat_version"])
    try:
        sys.path.insert(0, os.path.join(
            config["cdat_home"], "bin", "python"))
        import cdat_info
        import cdms2
        #if semver.match(cdat_info.Version, ">="+config["cdat_version"])
        if esg_version_manager.check_version_atleast(cdat_info.Version, config["cdat_version"]) == 0 and not force_install:
            print "CDAT already installed [OK]"
            return True
    except ImportError:
        logger.exception("Unable to import cdms2")

    print "\n*******************************"
    print "Setting up CDAT - (Python + CDMS)... {cdat_version}".format(cdat_version=config["cdat_version"])
    print "******************************* \n"


    if os.access(os.path.join(config["cdat_home"], "bin", "uvcdat"), os.X_OK):
        print "Detected an existing CDAT installation..."
        cdat_setup_choice = raw_input(
            "Do you want to continue with CDAT installation and setup? [y/N] ")
        if cdat_setup_choice.lower().strip() not in ["y", "yes"]:
            print "Skipping CDAT installation and setup - will assume CDAT is setup properly"
            return True

    return True
