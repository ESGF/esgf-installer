#NOTE: Here we are enforcing a bit of a convention... The name of
#subsystem files must be in the form of esg-xxx-xxx where the script
#contains its "main" function named setup_xxx_xxx(). The string passed
#to this function is "xxx-xxx"
#
import os
import subprocess
import logging
import grp
import pwd
import psycopg2
import esg_functions
import esg_setup
import esg_version_manager
import esg_bash2py
import esg_node_manager
import shlex
import yaml
from time import sleep
import esg_logging_manager

logger = esg_logging_manager.create_rotating_log(__name__)


with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


def setup_subsystem(subsystem, distribution_directory, esg_dist_url, force_install=False):
    '''
    arg (1) - name of installation script root name. Ex:security which resolves to script file esg-security
    arg (2) - directory on the distribution site where script is fetched from Ex: orp
    usage: setup_subsystem security orp - looks for the script esg-security in the distriubtion dir orp
    '''

    subsystem_install_script_path = os.path.join(config["scripts_dir"],"esg-{subsystem}".format(subsystem=subsystem))

#     #---
#     #check that you have at one point in time fetched the subsystem's installation script
#     #if indeed you have we will assume you would like to proceed with setting up the latest...
#     #Otherwise we just ask you first before you pull down new code to your machine...
#     #---

    if force_install:
        default = "y"
    else:
        default = "n"

    if os.path.exists(subsystem_install_script_path) or force_install:
        if default.lower() in ["y", "yes"]:
            run_installation = raw_input("Would you like to set up {subsystem} services? [Y/n]: ".format(subsystem=subsystem)) or "y"
        else:
            run_installation = raw_input("Would you like to set up {subsystem} services? [y/N]: ".format(subsystem=subsystem)) or "n"

        if run_installation.lower() in ["n", "no"]:
            print "Skipping installation of {subsystem}".format(subsystem=subsystem)
            return True

    print "-------------------------------"
    print "LOADING installer for {subsystem}... ".format(subsystem=subsystem)
    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        logger.debug("Changed directory to %s", os.getcwd())

        with esg_bash2py.pushd(config["scripts_dir"]):
            logger.debug("Changed directory to %s", os.getcwd())

            subsystem_full_name = "esg-{subsystem}".format(subsystem=subsystem)
            subsystem_remote_url = "{esg_dist_url}/{distribution_directory}/{subsystem_full_name}".format(esg_dist_url=esg_dist_url, distribution_directory=distribution_directory, subsystem_full_name=subsystem_full_name)
            if not esg_functions.download_update("{subsystem_full_name}".format(subsystem_full_name=subsystem_full_name), subsystem_remote_url):
                logger.error("Could not download %s", subsystem_full_name)
                return False
            try:
                os.chmod(subsystem_full_name, 0755)
            except OSError, error:
                logger.error(error)


    logger.info("script_dir contents: %s", os.listdir(config["scripts_dir"]))
    subsystem_underscore = subsystem.replace("-", "_")
    execute_subsystem_command = ". {scripts_dir}/{subsystem_full_name}; setup_{subsystem_underscore}".format(scripts_dir=config["scripts_dir"], subsystem_full_name=subsystem_full_name, subsystem_underscore=subsystem_underscore)
    setup_subsystem_process = subprocess.Popen(['bash', '-c', execute_subsystem_command])
    setup_subsystem_stdout, setup_subsystem_stderr = setup_subsystem_process.communicate()
    logger.debug("setup_subsystem_stdout: %s", setup_subsystem_stdout)
    logger.debug("setup_subsystem_stderr: %s", setup_subsystem_stderr)
