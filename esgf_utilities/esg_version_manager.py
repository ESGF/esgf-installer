'''
    Component Version Management Utility Functions
'''
import os
import re
import logging
import yaml
import semver
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_functions

logger = logging.getLogger("esgf_logger" + "." + __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def compare_versions(version_1, version_2):
    '''Check to see if version_1 is greater than or equal to version_2'''
    version_1 = version_1.replace("_", "-")
    version_2 = version_2.replace("_", "-")
    if semver.compare(version_1, version_2) > -1:
        return True
    else:
        return False


def check_module_version(module_name, min_version):
    '''
        Checks the version of a given python module.

        Arguments:
        module_name: a string containing the name of a module that will have it's version checked
        min_version: the minimum acceptable version string
    '''
    try:
        module_version = __import__(module_name).__version__
    except (AttributeError, ImportError):
        logger.exception("Couldn't check module version")
        esg_functions.exit_with_error(1)
    else:
        if semver.compare(module_version, min_version) > 0:
            return True
        else:
            print "\nThe detected version of %s %s is less than %s \n" % (module_name, module_version, min_version)
            return False

# TODO: implement and test


def get_current_esgf_library_version(library_name):
    '''
        Some ESGF components, such as esgf-security, don't actually
        install a webapp or anything that carries an independent
        manifest or version command to check, so they must be checked
        against the ESGF install manifest instead.
    '''
    version_number = ""
    if not os.path.isfile(config["install_manifest"]):
        return None
    else:
        with open(config["install_manifest"], "r") as manifest_file:
            for line in manifest_file:
                line = line.rstrip()  # remove trailing whitespace such as '\n'
                version_number = re.search(r'(library)\w+', line)
        if version_number:
            print "version number: ", version_number
            return version_number
        else:
            return None


def get_current_webapp_version(webapp_name, version_command=None):
    version_property = esg_bash2py.Expand.colonMinus(version_command, "Version")
    print "version_property: ", version_property
    reg_ex = r"^(" + re.escape(version_property) + ".*)"
    with open(config["tomcat_install_dir"] + "/webapps/" + webapp_name + "/META-INF/MANIFEST.MF", "r") as manifest_file:
        for line in manifest_file:
            line = line.rstrip()  # remove trailing whitespace such as '\n'
            version_number = re.search(reg_ex, line)
            if version_number != None:
                name, version = version_number.group(1).split(":")
                return version.strip()
    return 1


def check_webapp_version(webapp_name, min_version, version_command=None):
    version_property = esg_bash2py.Expand.colonMinus(version_command, "Version")
    if not os.path.isdir(config["tomcat_install_dir"] + "/webapps/" + webapp_name):
        print "Web Application %s is not present or cannot be detected!" % (webapp_name)
        return False
    else:
        current_version = str(get_current_webapp_version(webapp_name, version_property)).strip()
        if not current_version:
            print " WARNING:(2) Could not detect version of %s" % (webapp_name)
        else:
            if semver.compare(current_version, min_version) > 0:
                return True
            else:
                print "\nSorry, the detected version of %s %s is older than required minimum version %s \n" % (webapp_name, current_version, min_version)
                return False
