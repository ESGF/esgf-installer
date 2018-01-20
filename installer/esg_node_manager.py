import sys
import os
import subprocess
import re
import shutil
from OpenSSL import crypto
import requests
import socket
import platform
import netifaces
import tld
import grp
import shlex
import hashlib
import urlparse
import glob
import pwd
import yaml
from time import sleep
from esg_exceptions import UnprivilegedUserError, WrongOSError, UnverifiedScriptError
import esg_bash2py
import esg_functions
import esg_bootstrap
import esg_property_manager
import esg_version_manager
import esg_postgres
import logging
from esg_tomcat_manager import stop_tomcat

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)



#--------------
# User Defined / Settable (public)
#--------------
#--------------

# Sourcing esg-installarg esg-functions file and esg-init file
# [ -e ${esg_functions_file} ] && source ${esg_functions_file} && ((VERBOSE)) && printf "sourcing from: ${esg_functions_file} \n"

force_install = False

esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
esgf_host = esg_functions.get_esgf_host()

node_manager_app_context_root = "esgf-node-manager"
node_dist_url = "{esg_dist_url}/esgf-node-manager/esgf-node-manager-{esgf_node_manager_version}.tar.gz".format(
    esg_dist_url=esg_dist_url, esgf_node_manager_version=config["esgf_node_manager_version"])
logger.debug("node_dist_url: %s", node_dist_url)


def init():

    esgf_node_manager_egg_file = "esgf_node_manager-{esgf_node_manager_db_version}-py{python_version}.egg".format(
        esgf_node_manager_db_version=config["esgf_node_manager_db_version"], python_version=config["python_version"])


    # get_property node_use_ssl && [ -z "${node_use_ssl}" ] && write_as_property node_use_ssl true
    node_use_ssl = esg_property_manager.get_property("node_use_ssl")
    esg_property_manager.write_as_property("node_use_ssl", True)

    # get_property node_manager_service_app_home ${tomcat_install_dir}/webapps/${node_manager_app_context_root}
    # write_as_property node_manager_service_app_home
    node_manager_service_app_home = esg_property_manager.get_property("node_manager_service_app_home", "{tomcat_install_dir}/webapps/{node_manager_app_context_root}".format(
        tomcat_install_dir=config["tomcat_install_dir"], node_manager_app_context_root=node_manager_app_context_root))
    esg_property_manager.write_as_property(
        "node_manager_service_app_home", node_manager_service_app_home)

    # write_as_property node_manager_service_endpoint "http$([ "${node_use_ssl}" = "true" ] && echo "s" || echo "")://${esgf_host}/${node_manager_app_context_root}/node"
    if node_use_ssl:
        node_manager_service_endpoint = "https://{esgf_host}/{node_manager_app_context_root}/node".format(
            esgf_host=esgf_host, node_manager_app_context_root=node_manager_app_context_root)
    else:
        node_manager_service_endpoint = "http://{esgf_host}/{node_manager_app_context_root}/node".format(
            esgf_host=esgf_host, node_manager_app_context_root=node_manager_app_context_root)
    esg_property_manager.write_as_property(
        "node_manager_service_endpoint", node_manager_service_endpoint)

    # get_property node_use_ips && [ -z "${node_use_ips}" ] && write_as_property node_use_ips true
    node_use_ips = esg_property_manager.get_property("node_use_ips")
    esg_property_manager.write_as_property("node_use_ips", True)

    # get_property node_poke_timeout && [ -z "${node_poke_timeout}" ] && write_as_property node_poke_timeout 6000
    node_poke_timeout = esg_property_manager.get_property("node_poke_timeout")
    esg_property_manager.write_as_property("node_poke_timeout", 6000)

    # Database information....
    node_db_node_manager_schema_name = "esgf_node_manager"

    # Notification component information...
    # mail_smtp_host=${mail_smtp_host:-smtp.`hostname --domain`} #standard guess.
    # Overwrite mail_smtp_host value if already defined in props file
    # get_property mail_smtp_host ${mail_smtp_host}
    config["mail_smtp_host"] = esg_property_manager.get_property("mail_smtp_host")

    # Launcher script for the esgf-sh
    esgf_shell_launcher = "esgf-sh"


def set_aside_web_app(app_home):
    pass


def choose_mail_admin_address():
    mail_admin_address = esg_property_manager.get_property("mail_admin_address")
    if not mail_admin_address or force_install:
        mail_admin_address_input = raw_input(
            "What email address should notifications be sent as? [{mail_admin_address}]: ".format(mail_admin_address=mail_admin_address))
    else:
        logger.info("mail_admin_address = [%s]", mail_admin_address)
        config["mail_admin_address"] = mail_admin_address


def setup_node_manager(mode="install"):
    #####
    # Install The Node Manager
    #####
    # - Takes boolean arg: 0 = setup / install mode (default)
    #                      1 = updated mode
    #
    # In setup mode it is an idempotent install (default)
    # In update mode it will always pull down latest after archiving old
    #
    print "Checking for node manager {esgf_node_manager_version}".format(esgf_node_manager_version=config["esgf_node_manager_version"])
    if esg_version_manager.check_webapp_version("esgf-node-manager", config["esgf_node_manager_version"]) == 0 and not force_install:
        print "\n Found existing version of the node-manager [OK]"
        return True

    init()

    print "*******************************"
    print "Setting up The ESGF Node Manager..."
    print "*******************************"

    # local upgrade=${1:-0}

    db_set = 0

    if force_install:
        default_answer = "N"
    else:
        default_answer = "Y"
    # local dosetup
    node_manager_service_app_home = esg_property_manager.get_property(
        "node_manager_service_app_home")
    if os.path.isdir(node_manager_service_app_home):
        db_set = 1
        print "Detected an existing node manager installation..."
        if default_answer == "Y":
            installation_answer = raw_input(
                "Do you want to continue with node manager installation and setup? [Y/n]") or default_answer
        else:
            installation_answer = raw_input(
                "Do you want to continue with node manager installation and setup? [y/N]") or default_answer
        if installation_answer.lower() not in ["y", "yes"]:
            print "Skipping node manager installation and setup - will assume it's setup properly"
            # resetting node manager version to what it is already, not what we prescribed in the script
            # this way downstream processes will use the *actual* version in play, namely the (access logging) filter(s)
            esgf_node_manager_version = esg_version_manager.get_current_webapp_version(
                "esgf_node_manager")
            return True

        backup_default_answer = "Y"
        backup_answer = raw_input("Do you want to make a back up of the existing distribution [{node_manager_app_context_root}]? [Y/n] ".format(
            node_manager_app_context_root=node_manager_app_context_root)) or backup_default_answer
        if backup_answer.lower in ["yes", "y"]:
            print "Creating a backup archive of this web application [{node_manager_service_app_home}]".format(node_manager_service_app_home=node_manager_service_app_home)
            esg_functions.backup(node_manager_service_app_home)

        backup_db_default_answer = "Y"
        backup_db_answer = raw_input("Do you want to make a back up of the existing database [{node_db_name}:esgf_node_manager]?? [Y/n] ".format(
            node_db_name=config["node_db_name"])) or backup_db_default_answer

        if backup_db_answer.lower() in ["yes", "y"]:
            print "Creating a backup archive of the manager database schema [{node_db_name}:esgf_node_manager]".format(node_db_name=config["node_db_name"])
            # TODO: Implement this
            # esg_postgres.backup_db() -db ${node_db_name} -s node_manager

    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        logger.debug("changed directory to : %s", os.getcwd())

        # strip off .tar.gz at the end
        #(Ex: esgf-node-manager-0.9.0.tar.gz -> esgf-node-manager-0.9.0)
        node_dist_file = esg_bash2py.trim_string_from_head(node_dist_url)
        logger.debug("node_dist_file: %s", node_dist_file)
        # Should just be esgf-node-manager-x.x.x
        node_dist_dir = node_dist_file

        # checked_get ${node_dist_file} ${node_dist_url} $((force_install))
        if not esg_functions.download_update(node_dist_file, node_dist_url, force_download=force_install):
            print "ERROR: Could not download {node_dist_url} :-(".format(node_dist_url=node_dist_url)
            esg_functions.exit_with_error(1)

        # make room for new install
        if force_install:
            print "Removing Previous Installation of the ESGF Node Manager... ({node_dist_dir})".format(node_dist_dir=node_dist_dir)
            try:
                shutil.rmtree(node_dist_dir)
                logger.info("Deleted directory: %s", node_dist_dir)
            except IOError, error:
                logger.error(error)
                logger.error("Could not delete directory: %s", node_dist_dir)
                esg_functions.exit_with_error(1)

            clean_node_manager_webapp_subsystem()

        print "\nunpacking {node_dist_file}...".format(node_dist_file=node_dist_file)
        # This probably won't work, because the extension has already been stripped, no idea how this even worked in the bash code smh
        try:
            tar = tarfile.open(node_dist_file)
            tar.extractall()
            tar.close()
        except Exception, error:
            logger.error(error)
            print "ERROR: Could not extract the ESG Node: {node_dist_file}".format(node_dist_file=node_dist_file)
            esg_functions.exit_with_error(1)

        # pushd ${node_dist_dir} >& /dev/null
        with esg_bash2py.pushd(node_dist_dir):
            logger.debug("changed directory to : %s", os.getcwd())
            stop_tomcat()

            # strip the version number off(#.#.#) the dir and append .war to get the name of war file
            #(Ex: esgf-node-manager-0.9.0 -> esgf-node-manager.war)
            # local trimmed_name=$(pwd)/${node_dist_dir%-*}
            split_dir_name_list = node_dist_dir.split("-")
            versionless_name = '-'.join(split_dir_name_list[:3])
            trimmed_name = os.path.join(os.getcwd(), versionless_name)
            node_war_file = trimmed_name + ".war"
            logger.debug("node_war_file: %s", node_war_file)

            #----------------------------
            # make room for new INSTALL
            # ((upgrade == 0)) && set_aside_web_app ${node_manager_service_app_home}
            if mode != "upgrade":
                set_aside_web_app(node_manager_service_app_home)
            #----------------------------
            # mkdir -p ${node_manager_service_app_home}
            esg_bash2py.mkdir_p(node_manager_service_app_home)
            # cd ${node_manager_service_app_home}
            os.chdir(node_manager_service_app_home)
            logger.debug("changed directory to : %s", os.getcwd())

            #----------------------------
            # fetch_file=esgf-node-manager.properties
            download_file_name = "esgf-node-manager.properties"

            # NOTE: The saving of the last config file must be done *BEFORE* we untar the new distro!
            # if ((upgrade)) && [ -e WEB-INF/classes/${fetch_file} ]; then
            if mode == "upgrade" and os.path.isfile("WEB-INF/classes/{download_file_name}".format(download_file_name=download_file_name)):
                # cp WEB-INF/classes/${fetch_file} WEB-INF/classes/${fetch_file}.saved
                esg_functions.create_backup_file(
                    "WEB-INF/classes/{download_file_name}".format(download_file_name=download_file_name), ".saved")
                # chmod 600 WEB-INF/classes/${fetch_file}*
                for file_name in glob.glob("WEB-INF/classes/{download_file_name}".format(download_file_name=download_file_name)):
                    try:
                        os.chmod(file_name, 0600)
                    except OSError, error:
                        logger.error(error)

            print "\nExpanding war {node_war_file} in {current_directory}".format(node_war_file=node_war_file, current_directory=os.getcwd())
            # $JAVA_HOME/bin/jar xf ${node_war_file}
            try:
                tar = tarfile.open(node_war_file)
                tar.extractall()
                tar.close()
            except Exception, error:
                logger.error(error)
                print "ERROR: Could not extract the ESG Node: {node_war_file}".format(node_war_file=node_war_file)
                esg_functions.exit_with_error(1)

            #----------------------------
            # Property file fetching and token replacement...
            #----------------------------
            # pushd WEB-INF/classes >& /dev/null
            with esg_bash2py.pushd("WEB-INF/classes"):
                # cat ${fetch_file}.tmpl >> ${config_file}
                with open(download_file_name + ".tmpl", "r") as download_file:
                    with open(config["config_file"], "w") as config_file:
                        download_file_contents = download_file.read()
                        config_file.write(download_file_contents)

                # chown -R ${tomcat_user} ${node_manager_service_app_home}
                # chgrp -R ${tomcat_group} ${node_manager_service_app_home}
                os.chown(esg_functions.readlinkf(node_manager_service_app_home), pwd.getpwnam(config["tomcat_user"]).pw_uid, grp.getgrnam(config["tomcat_group"]).gr_gid)
            #----------------------------

    # popd >& /dev/null

    # NOTE TODO: Create a function that reads the property file and for
    # every property that is not assigned and/or in a list of manidtory
    # properties go through and ask the user to assign a value. -gavin

    # if [ -z "${mail_admin_address}" ]; then
    #     while [ 1 ]; do
    #         local input
    #         read -p "What email address should notifications be sent as? " input
    #         [ -n "${input}" ] && mail_admin_address=${input}  && unset input && break
    #     done
    # fi

    # choose_mail_admin_address()

    if db_set > 0:
        if write_node_manager_config() != 0 or configure_postgress() != 0:
            esg_functions.exit_with_error(1)

    touch_generated_whitelist_files()
    write_node_manager_install_log()
    write_shell_contrib_command_file()

    fetch_shell_launcher()

#    setup_conda_env
    setup_py_pkgs()

    setup_nm_repo()

    esg_functions.exit_with_error(0)


def setup_nm_repo():
    pass


def setup_py_pkgs():
    pass


def fetch_shell_launcher():
    pass


def write_shell_contrib_command_file():
    pass


def write_node_manager_install_log():
    pass


def touch_generated_whitelist_files():
    pass


def configure_postgress():
    pass


def write_node_manager_config():
    pass

#--------------------------------------
# Clean / Uninstall this module...
#--------------------------------------


def clean_node_manager_webapp_subsystem():
    pass
