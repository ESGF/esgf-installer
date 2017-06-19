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
import shlex
from esg_init import EsgInit
from time import sleep

logger = logging.getLogger('root')
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger.setLevel(logging.DEBUG)

# logging.basicConfig(format = "%(levelname): %(lineno)s %(funcName)s", level=logging.DEBUG)
# logger = logging.getLogger(__name__)

config = EsgInit()


def setup_subsystem(subsystem, distribution_directory, esg_dist_url, force_install=False):
    '''
    arg (1) - name of installation script root name. Ex:security which resolves to script file esg-security
    arg (2) - directory on the distribution site where script is fetched from Ex: orp
    usage: setup_subsystem security orp - looks for the script esg-security in the distriubtion dir orp
    '''
    
#     local subsystem=$1
#     [ -z "${subsystem}" ] && echo "setup_subsystem [${subsystem}] requires argument!!" && checked_done 1
#     local server_dir=${2:?"Must provide the name of the distribution directory where subsystem script lives - perhaps ${subsystem}?"}
#     local subsystem_install_script=${scripts_dir}/esg-${subsystem}
    subsystem_install_script_path = os.path.join(config.config_dictionary["scripts_dir"],"esg-{subsystem}".format(subsystem=subsystem))

#     #---
#     #check that you have at one point in time fetched the subsystem's installation script
#     #if indeed you have we will assume you would like to proceed with setting up the latest...
#     #Otherwise we just ask you first before you pull down new code to your machine...
#     #---
#     #local default="Y"
#     #((force_install)) && default="Y"
#     #local dosetup
    if force_install:
        default = "y"
    else:
        default = "n"
#     #if [ ! -e ${subsystem_install_script} ] || ((force_install)) ; then
#     #    echo
#     #    read -e -p "Would you like to set up ${subsystem} services? $([ "$default" = "N" ] && echo "[y/N]" || echo "[Y/n]")  " dosetup
#     #    [ -z "${dosetup}" ] && dosetup=${default}
#     #    if [ "${dosetup}" = "N" ] || [ "${dosetup}" = "n" ] || [ "${dosetup}" = "no" ]; then
#     #        return 0
#     #    fi
#     #fi
    if os.path.exists(subsystem_install_script_path) or force_install:
        if default.lower() in ["y", "yes"]:
            run_installation = raw_input("Would you like to set up {subsystem} services? [Y/n]: ".format(subsystem=subsystem)) or "y"
        else:
            run_installation = raw_input("Would you like to set up {subsystem} services? [y/N]: ".format(subsystem=subsystem)) or "n"

        if run_installation.lower() in ["n", "no"]:
            print "Skipping installation of {subsystem}".format(subsystem=subsystem)
            return True


#     echo
#     echo "-------------------------------"
#     echo "LOADING installer for ${subsystem}... "
#     mkdir -p ${workdir}
#     [ $? != 0 ] && checked_done 1
#     pushd ${workdir} >& /dev/null
    print "-------------------------------"
    print "LOADING installer for ${subsystem}... ".format(subsystem=subsystem)
    esg_bash2py.mkdir_p(config.config_dictionary["workdir"])
    with esg_bash2py.pushd(config.config_dictionary["workdir"]):
        logger.debug("Changed directory to %s", os.getcwd())

        with esg_bash2py.pushd(config.config_dictionary["scripts_dir"]):
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
                

    logger.info("script_dir contents: %s", os.listdir(config.config_dictionary["scripts_dir"]))

#     pushd ${scripts_dir} >& /dev/null
#     local fetch_file=esg-${subsystem}
#     verbose_print "checked_get ./${fetch_file} ${esg_dist_url}/${server_dir}/${fetch_file} $((force_install))"
#     checked_get ./${fetch_file} ${esg_dist_url}/${server_dir}/${fetch_file} $((force_install))

#     local ret=$?
#     (( $ret > 1 )) && popd && return 1
#     chmod 755 ${fetch_file}
#     popd >& /dev/null

#     #source subsystem file and go!
#     shift && debug_print "-->>> "
#     [ -n "${server_dir}" ] && shift && debug_print "-->>> "
#     debug_print "source ${scripts_dir}/${fetch_file} && setup_${subsystem//'-'/_} ${upgrade_mode} $@"
#     (source ${scripts_dir}/${fetch_file} && verbose_print ":-) " && setup_${subsystem//'-'/_} ${upgrade_mode} $@ )
#     checked_done $?
#     echo "-------------------------------"
#     echo
#     echo
# }