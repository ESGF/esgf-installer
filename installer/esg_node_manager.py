import sys
import os
import subprocess
import re
import shutil
from OpenSSL import crypto
import logging
import requests
import socket
import platform
import netifaces
import tld
import grp
import shlex
import hashlib
import urlparse
from time import sleep
from esg_init import EsgInit
from esg_exceptions import UnprivilegedUserError, WrongOSError, UnverifiedScriptError
import esg_bash2py
import esg_functions
import esg_bootstrap
import esg_env_manager
import esg_property_manager
import esg_version_manager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
config = EsgInit()

envfile="/etc/esg.env"

#--------------
#User Defined / Settable (public)
#--------------
install_prefix="/usr/local"
cdat_home=${cdat_home:-${install_prefix}/cdat}
esg_root_dir=${esg_root_dir:-"/esg"}
workdir=${workdir:-~/workbench/esg}
install_manifest=${install_manifest:-"${esg_root_dir}/esgf-install-manifest"}
esg_functions_file=${install_prefix}/bin/esg-functions
#--------------

# Sourcing esg-installarg esg-functions file and esg-init file
# [ -e ${esg_functions_file} ] && source ${esg_functions_file} && ((VERBOSE)) && printf "sourcing from: ${esg_functions_file} \n"

date_format=${date_format:-"+%Y_%m_%d_%H%M%S"}
compress_extensions=${compress_extensions:-".tar.gz|.tar.bz2|.tgz|.bz2"}
force_install=${force_install:-0}

tomcat_user=${tomcat_user:-tomcat}
tomcat_group=${tomcat_group:-$tomcat_user}
tomcat_install_dir=${CATALINA_HOME:-${install_prefix}/tomcat}
python_version=${python_version:-"2.6"}
config_file=${esg_root_dir}/config/esgf.properties
esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"



def init():
    #[ -n "${envfile}" ] && [ -e "${envfile}" ] && source ${envfile} && ((VERBOSE)) && printf "node manager: sourcing environment from: ${envfile} \n"

    esgf_node_manager_egg_file="esgf_node_manager-{esgf_node_manager_db_version}-py{python_version}.egg".format(esgf_node_manager_db_version=config.config_dictionary["esgf_node_manager_db_version"], python_version=config.config_dictionary["python_version"])

    node_dist_url="{esg_dist_url}/esgf-node-manager/esgf-node-manager-{esgf_node_manager_version}.tar.gz".format(esg_dist_url=esg_dist_url, esgf_node_manager_version=config.config_dictionary["esgf_node_manager_version"])

    node_manager_app_context_root="esgf-node-manager"

    # get_property node_use_ssl && [ -z "${node_use_ssl}" ] && write_as_property node_use_ssl true
    node_use_ssl = esg_property_manager.get_property("node_use_ssl")
    esg_property_manager.write_as_property("node_use_ssl", True)

    # get_property node_manager_service_app_home ${tomcat_install_dir}/webapps/${node_manager_app_context_root}
    node_manager_service_app_home = esg_property_manager.get_property("node_manager_service_app_home", "{tomcat_install_dir}/webapps/{node_manager_app_context_root}".format(tomcat_install_dir=config.config_dictionary["tomcat_install_dir"], node_manager_app_context_root=node_manager_app_context_root))
    write_as_property node_manager_service_app_home
    write_as_property node_manager_service_endpoint "http$([ "${node_use_ssl}" = "true" ] && echo "s" || echo "")://${esgf_host}/${node_manager_app_context_root}/node"

    get_property node_use_ips && [ -z "${node_use_ips}" ] && write_as_property node_use_ips true
    get_property node_poke_timeout && [ -z "${node_poke_timeout}" ] && write_as_property node_poke_timeout 6000

    #Database information....
    node_db_name=${node_db_name:-"esgcet"}
    node_db_node_manager_schema_name="esgf_node_manager"

    postgress_driver=${postgress_driver:-org.postgresql.Driver}
    postgress_protocol=${postgress_protocol:-jdbc:postgresql:}
    postgress_host=${PGHOST:-localhost}
    postgress_port=${PGPORT:-5432}
    postgress_user=${PGUSER:-dbsuper}
    pg_sys_acct_passwd=${pg_sys_acct_passwd:=${pg_secret:=changeme}}

    #Notification component information...
    mail_smtp_host=${mail_smtp_host:-smtp.`hostname --domain`} #standard guess.
    #Overwrite mail_smtp_host value if already defined in props file
    get_property mail_smtp_host ${mail_smtp_host}
    mail_admin_address=${mail_admin_address}

    #Launcher script for the esgf-sh
    esgf_shell_launcher="esgf-sh"
