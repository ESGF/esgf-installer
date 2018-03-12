import os
import zipfile
import logging
import stat
import yaml
from git import Repo
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from base import esg_tomcat_manager
from base import esg_postgres

#####
# Install The ESGF Idp Services
#####
# - Takes boolean arg: 0 = setup / install mode (default)
#                      1 = updated mode
#
# In setup mode it is an idempotent install (default)
# In update mode it will always pull down latest after archiving old
#

logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def write_idp_install_log(idp_service_app_home):
    esgf_idp_version = "1.1.4"
    idp_service_host = esg_functions.get_esgf_host()
    idp_service_port = "443"
    idp_service_endpoint = "https://{}:443/esgf-idp/idp/openidServer.htm".format(idp_service_host)
    idp_security_attribute_service_endpoint = "https://{}:443/esgf-idp/saml/soap/secure/attributeService.htm".format(idp_service_host)
    idp_security_registration_service_endpoint = "https://{}:443/esgf-idp/secure/registrationService.htm".format(idp_service_host)

    esg_functions.write_to_install_manifest("webapp:esgf-idp", idp_service_app_home, esgf_idp_version)
    esg_property_manager.set_property("idp_service_app_home", idp_service_app_home)
    esg_property_manager.set_property("idp_service_endpoint", idp_service_endpoint)
    esg_property_manager.set_property("idp_security_attribute_service_app_home", idp_service_app_home)
    esg_property_manager.set_property("idp_security_attribute_service_endpoint", idp_security_attribute_service_endpoint)
    esg_property_manager.set_property("idp_security_registration_service_app_home", idp_service_app_home)
    esg_property_manager.set_property("idp_security_registration_service_endpoint", idp_security_registration_service_endpoint)


def write_security_lib_install_log():
    pass

def setup_idp(esg_dist_url):
    print "*******************************"
    print "Setting up The ESGF Idp Services"
    print "*******************************"
    idp_service_app_home = os.path.join(config["tomcat_install_dir"], "webapps", "esgf-idp")

    if os.path.isdir(idp_service_app_home):
        print "Detected an existing idp services installation..."
        continue_install = raw_input("Do you want to continue with idp services installation and setup? [Y/n]: ") or "y"
        if continue_install.lower() in ["n", "no"]:
            print "Skipping IDP installation."
            return

    backup_idp = raw_input("Do you want to make a back up of the existing distribution?? [Y/n] ") or "y"
    if backup_idp.lower() in ["yes", "y"]:
        "Creating a backup archive of this web application {}".format(idp_service_app_home)
        esg_functions.backup(idp_service_app_home)

    esg_bash2py.mkdir_p(idp_service_app_home)
    with esg_bash2py.pushd(idp_service_app_home):
        idp_dist_file = os.path.join(os.getcwd(), "esgf-idp.war")
        idp_dist_url = "{}/esgf-idp/esgf-idp.war".format(esg_dist_url)
        esg_functions.download_update(idp_dist_file, idp_dist_url)

        esg_tomcat_manager.stop_tomcat()

        print "Expanding war {idp_dist_file} in {pwd}".format(idp_dist_file=idp_dist_file, pwd=os.getcwd())
        with zipfile.ZipFile(idp_dist_file, 'r') as zf:
            zf.extractall()
        os.remove("esgf-idp.war")

        tomcat_user = esg_functions.get_user_id("tomcat")
        tomcat_group = esg_functions.get_group_id("tomcat")
        esg_functions.change_ownership_recursive(idp_service_app_home, tomcat_user, tomcat_group)

    write_idp_install_log(idp_service_app_home)
    write_security_lib_install_log()


def setup_slcs():
    print "*******************************"
    print "Setting up SLCS Oauth Server"
    print "*******************************"

    continue_install = raw_input("Would you like to install the SLCS OAuth server on this node? [y/N] ") or "y"
    if continue_install.lower() in ["n", "no"]:
        print "Skipping installation of SLCS server"
        return

    esg_functions.stream_subprocess_output("yum  -y install ansible")

    #create slcs Database
    esg_postgres.create_database("slcsdb")

    with esg_bash2py.pushd("/usr/local/src"):
        Repo.clone_from("https://github.com/ESGF/esgf-slcs-server-playbook.git", os.getcwd())

        apache_user = esg_functions.get_user_id("apache")
        apache_group = esg_functions.get_group_id("apache")
        esg_functions.change_ownership_recursive("esgf-slcs-server-playbook", apache_user, apache_group)

        with esg_bash2py.pushd("esgf-slcs-server-playbook"):
            #TODO: extract to function
            publisher_repo_local = Repo(os.getcwd())
            publisher_repo_local.git.checkout("devel")

            esg_functions.change_ownership_recursive("/var/lib/globus-connect-server/myproxy-ca/", gid=apache_group)

            #add group read and execute permissions
            os.chmod("/var/lib/globus-connect-server/myproxy-ca/", current_mode.st_mode, stat.S_IRGRP | stat.S_IXGRP)
            os.chmod("/var/lib/globus-connect-server/myproxy-ca/private", current_mode.st_mode, stat.S_IRGRP | stat.S_IXGRP)
            os.chmod("/var/lib/globus-connect-server/myproxy-ca/private/cakey.pem", current_mode.st_mode, stat.S_IRGRP)

            with open("playbook/overrides/production_venv_only.yml", "r+") as yaml_file:
                production_venv_only = yaml_file.load()
            production_venv_only["server_name"] = esg_functions.get_esgf_host()
            production_venv_only["server_email"] = esg_property_manager.get_property("mail_admin_address")
            db_password = esg_functions.get_postgres_password()
            production_venv_only["esgf_slcsdb"]["password"] = db_password
            production_venv_only["esgf_userdb"]["password"] = db_password

            with open('playbook/overrides/production_venv_only.yml', 'w') as yaml_file:
                yaml.dump(production_venv_only, yaml_file)

            esg_property_manager.set_property("short.lived.certificate.server", esgf_host)

            esg_bash2py.mkdir_p("/usr/local/esgf-slcs-server")
            esg_functions.change_ownership_recursive("/usr/local/esgf-slcs-server", "apache", "apache")

            #TODO: check if there's an ansible Python module
            esg_functions.stream_subprocess_output('ansible-playbook -i playbook/inventories/localhost -e "@playbook/overrides/production_venv_only.yml" playbook/playbook.yml')


def setup_globus_services(config_type):
    print "*******************************"
    print "Setting up Globus... (config type: $config_type)"
    print "*******************************"



#arg1 - config_type ("datanode" |
#                    "gateway"  ["install"|"update"])
setup_globus_services() {


    local dosetup
    local default_val="Y"

    if [ -x /usr/bin/globus-version ]; then
        echo "Detected an existing Globus installation"
        echo "Checking for Globus ${globus_version}"
        echo "Current Globus version: $(/usr/bin/globus-version)"
        check_version_atleast $(/usr/bin/globus-version) ${globus_version}
        [ $? == 0 ] && default_val="n" && echo "Globus version appears sufficiently current"
    fi

    if [ -x ${globus_install_dir}/bin/globus-version ]; then
        echo "Detected an existing old Globus installation at ${globus_install_dir}"
        echo "Old globus version: $(/usr/bin/globus-version)"
    fi

    read -e -p "Do you want to continue with the Globus installation and setup? $([ "$default_val" = "Y" ] && echo "[Y/n]" || echo "[y/N]") " dosetup
    [ -z "${dosetup}" ] && dosetup=$default_val

    if [ "${dosetup}" != "Y" ] && [ "${dosetup}" != "y" ]; then
        echo "Skipping Globus installation and setup - will assume Globus is setup properly"
        return 0
    fi
    echo

    echo "setup_globus_services for ${config_type} - ${globus_word_size}bit arch : [$*]"
    mkdir -p ${globus_location}/bin
    if [ "${config_type}" = "datanode" ]; then

        echo
        echo "*******************************"
        echo "Setting up ESGF Globus GridFTP Service(s)"
        echo "*******************************"
        echo

        create_globus_account
        install_globus datanode
        setup_gcs_io firstrun
        [ $? -ne 0 ] && return 3
        setup_gridftp_metrics_logging

        config_gridftp_server && config_gridftp_metrics_logging "end-user"
        [ $? != 0 ] && echo " WARNING: Unable to complete gridftp configuration!!" && return 2

        [ -e /usr/sbin/globus-gridftp-server ] && \
            write_as_property gridftp_app_home /usr/sbin/globus-gridftp-server || \
            echo "WARNING: Cannot find executable /usr/sbin/globus-gridftp-server"

    elif [ "${config_type}" = "gateway" ]; then

        echo
        echo "*******************************"
        echo "Setting up The ESGF Globus MyProxy Services"
        echo "*******************************"
        echo

        shift
        install_globus gateway
        setup_gcs_id firstrun
        [ $? -ne 0 ] && return 3
        config_myproxy_server $@
        [ $? != 0 ] && return 3

    else
        echo "You must provide a configuration type arg [datanode | gateway]"
        return 1
    fi

    return 0
}

def setup_globus(installation_type):
    '''Globus Toolkit ->  MyProxy (client) & GridFTP (server)
    installation_type: either a data node or an IDP node
    The rest of the args are the following...
    for data-node configuration (GridFTP stuff): ["bdm"|"end-user"] see esg-globus script
    for idp configuration (MyProxy stuff): [gen-self-cert] <dir> | <regen-simpleca> [fetch-certs|gen-self-cert|keep-certs] | ["install"|"update"]'''
    logger.debug("my_setup_globus for install type: %s", installation_type)

    esg_bash2py.mkdir_p(config["workdir"])
    esg_bash2py.pushd(config["workdir"]):
        esg_bash2py.pushd(config["scripts_dir"]):
            globus_file = "esg-globus"
            globus_file_url = "https://aims1.llnl.gov/esgf/dist/externals/bootstrap/esg-globus"
            esg_functions.download_update(globus_file, globus_file_url)
            os.chmod(globus_file, 0755)

    directive = "notype"

    if installation_type == "DATA":
        logger.info("Globus Setup for Data-Node... (GridFTP server) ")
        directive = "datanode"

        with esg_bash2py.pushd(config["workdir"]):

        local ret=1

        if [ $((sel & DATA_BIT))  != 0 ]; then
            echo -n "Globus Setup for Data-Node... (GridFTP server) "
            directive="datanode"
            pushd ${workdir} >& /dev/null
            (source ${scripts_dir}/${fetch_file} && setup_globus_services "${directive}" $@)
            ret=$?
            popd >& /dev/null
            [ ${ret} = 0 ] && write_globus_env || checked_done 1
            touch ${globus_location}/esg_${progname}_installed
        fi

        ret=1

        if [ $((sel & IDP_BIT)) != 0 ]; then
            echo -n "Globus Setup for Index-Node... (MyProxy server) "
            directive="gateway"
            pushd ${workdir} >& /dev/null
            local setup_mode="update"
            [ $((sel & INSTALL_BIT)) != 0 ] && setup_mode="install"
            (source ${scripts_dir}/${fetch_file} && setup_globus_services "${directive}" $@ "${setup_mode}")
            ret=$?
            popd >& /dev/null
            [ ${ret} = 0 ] && write_globus_env || checked_done 1
            touch ${globus_location}/esg_${progname}_installed
        fi
        return 0
    }

def main(esg_dist_url):
    setup_idp(esg_dist_url)
    setup_slcs()

if __name__ == '__main__':
    main()
