import os
import logging
import ConfigParser
import yaml
from esgf_utilities import pybash
from esgf_utilities import esg_functions
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from esgf_utilities.esg_exceptions import SubprocessError
from esgf_utilities.esg_env_manager import EnvWriter

logger = logging.getLogger("esgf_logger" + "." + __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

esg_root_url = esg_property_manager.get_property("esg.root.url")
java_version = config["java_version"]
JAVA_DIST_URL = "{}/java/{}/jdk{}-64.tar.gz".format(esg_root_url, java_version, java_version)

def set_default_java():
    '''Sets the default Java binary to the version installed with ESGF'''
    esg_functions.call_binary("alternatives", ["--install", "/usr/bin/java", "/usr/local/java/bin/java", "3"])
    esg_functions.call_binary("alternatives", ["--set", "java", "/usr/local/java/bin/java"])

def check_for_existing_java(java_path=os.path.join(config["java_install_dir"], "bin", "java")):
    '''Check if a valid java installation is currently on the system'''
    if pybash.is_exe(java_path):
        print "Detected an existing java installation at {java_path}...".format(java_path=java_path)
        return check_java_version(java_path)


def check_java_version(java_path=os.path.join(config["java_install_dir"], "bin", "java")):
    '''Checks the Java version on the system'''
    print "Checking Java version"
    logger.debug("java_path: %s", java_path)
    java_version_output = esg_functions.call_binary(java_path, ["-version"])
    version_line = java_version_output.split("\n")[0]
    version = version_line.split("version")[1].strip()
    installed_java_version = version.strip('\"')

    assert esg_version_manager.compare_versions(installed_java_version, config["java_version"])
    print "Installed java version meets the minimum requirement {}".format(config["java_version"])
    return installed_java_version


def download_java(java_tarfile):
    '''Download Java from distribution mirror'''
    print "Downloading Java from ", JAVA_DIST_URL
    if not esg_functions.download_update(java_tarfile, JAVA_DIST_URL):
        logger.error("ERROR: Could not download Java")
        raise RuntimeError


def write_java_env():
    '''Writes Java config to /etc/esg.env'''
    EnvWriter.export("JAVA_HOME", config["java_install_dir"])

def write_java_install_log():
    '''Writes Java config to install manifest'''
    esg_functions.write_to_install_manifest(
        "java",
        config["java_install_dir"],
        check_java_version()
    )


def setup_java():
    '''
        Installs Oracle Java from rpm using yum localinstall.
        Does nothing if an acceptible Java install is found.
    '''

    print "*******************************"
    print "Setting up Java {java_version}".format(java_version=config["java_version"])
    print "******************************* \n"

    if check_for_existing_java():
        try:
            setup_java_answer = esg_property_manager.get_property("update.java")
            logger.debug("setup_java_answer: %s", setup_java_answer)
        except ConfigParser.NoOptionError:
            setup_java_answer = raw_input(
                "Do you want to continue with Java installation and setup? [y/N]: ") or "N"

        if setup_java_answer.lower().strip() not in ["y", "yes"]:
            print "Skipping Java installation"
            return

    pybash.mkdir_p(config["workdir"])
    with pybash.pushd(config["workdir"]):

        java_tarfile = pybash.trim_string_from_head(JAVA_DIST_URL)
        jdk_directory = java_tarfile.split("-")[0]
        java_install_dir_parent = config["java_install_dir"].rsplit("/", 1)[0]

        # Check for Java tar file
        if not os.path.isfile(java_tarfile):
            print "Don't see java distribution file {java_dist_file_path}".format(java_dist_file_path=os.path.join(os.getcwd(), java_tarfile))
            download_java(java_tarfile)

        print "Extracting Java tarfile", java_tarfile
        esg_functions.extract_tarball(java_tarfile, java_install_dir_parent)

        # Create symlink to Java install directory (/usr/local/java)
        pybash.symlink_force(os.path.join(java_install_dir_parent,
                                          jdk_directory), config["java_install_dir"])

        os.chown(config["java_install_dir"], config["installer_uid"], config["installer_gid"])
        # recursively change permissions
        esg_functions.change_ownership_recursive(
            config["java_install_dir"], config["installer_uid"], config["installer_gid"])

    # set_default_java()
    # print check_java_version()
    write_java_install_log()
    write_java_env()
