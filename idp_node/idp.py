import os
import zipfile
import logging
import ConfigParser
import stat
import yaml
from git import Repo
from esgf_utilities import esg_functions
from esgf_utilities import pybash
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
    '''Write IDP properties to install manifest and property file'''
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


def setup_idp():
    '''Setup IDP service'''
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

        try:
            backup_idp = esg_property_manager.get_property("backup.idp")
        except ConfigParser.NoOptionError:
            backup_idp = raw_input("Do you want to make a back up of the existing distribution?? [Y/n] ") or "y"

        if backup_idp.lower() in ["yes", "y"]:
            "Creating a backup archive of this web application {}".format(idp_service_app_home)
            esg_functions.backup(idp_service_app_home)

    pybash.mkdir_p(idp_service_app_home)
    with pybash.pushd(idp_service_app_home):
        idp_dist_file = os.path.join(os.getcwd(), "esgf-idp.war")
        esg_dist_url = esg_property_manager.get_property("esg.dist.url")
        idp_dist_url = "{}/esgf-idp/esgf-idp.war".format(esg_dist_url)
        esg_functions.download_update(idp_dist_file, idp_dist_url)

        if esg_tomcat_manager.check_tomcat_status():
            esg_tomcat_manager.stop_tomcat()

        print "Expanding war {idp_dist_file} in {pwd}".format(idp_dist_file=idp_dist_file, pwd=os.getcwd())
        with zipfile.ZipFile(idp_dist_file, 'r') as idp_dist_zip:
            idp_dist_zip.extractall()
        os.remove("esgf-idp.war")

        tomcat_user = esg_functions.get_user_id("tomcat")
        tomcat_group = esg_functions.get_group_id("tomcat")
        esg_functions.change_ownership_recursive(idp_service_app_home, tomcat_user, tomcat_group)

    with pybash.pushd(config["esg_config_dir"]):
        static_file = "esgf_idp_static.xml"
        url = "{}/xml/{}".format(config["esgf_config_repo"], static_file)
        esg_functions.download_update(static_file, url)

    with pybash.pushd(config["esg_config_dir"]):
        static_file = "esgf_ats_static.xml"
        url = "{}/xml/{}".format(config["esgf_config_repo"], static_file)
        esg_functions.download_update(static_file, url)

    write_idp_install_log(idp_service_app_home)
    esg_functions.write_security_lib_install_log()

    # esg_tomcat_manager.start_tomcat()

def clone_slcs():
    if os.path.exists("/usr/local/src/esgf-slcs-server-playbook"):
        print "SLCS repo already exists.  Skipping cloning from Github."
        return
    Repo.clone_from("https://github.com/ESGF/esgf-slcs-server-playbook.git", os.getcwd()+"/esgf-slcs-server-playbook")

#TODO: convert slcs to use Ansible python API
def setup_slcs():
    '''Setup the slcs_server'''
    print "*******************************"
    print "Setting up SLCS Oauth Server"
    print "*******************************"

    try:
        install_slcs = esg_property_manager.get_property("update.slcs")
    except ConfigParser.NoOptionError:
        install_slcs = raw_input("Would you like to install the SLCS OAuth server on this node? [y/N] ") or "n"

    if install_slcs.lower() in ["n", "no"]:
        print "Skipping installation of SLCS server"
        return

    esg_functions.call_binary("yum", ["-y", "install", "ansible"])

    #create slcs Database
    esg_postgres.create_database("slcsdb")

    with pybash.pushd("/usr/local/src"):
        clone_slcs()

        apache_user = esg_functions.get_user_id("apache")
        apache_group = esg_functions.get_group_id("apache")
        esg_functions.change_ownership_recursive("esgf-slcs-server-playbook", apache_user, apache_group)

        with pybash.pushd("esgf-slcs-server-playbook"):
            #TODO: extract to function
            publisher_repo_local = Repo(os.getcwd())
            publisher_repo_local.git.checkout("devel")

            esg_functions.change_ownership_recursive("/var/lib/globus-connect-server/myproxy-ca/", gid=apache_group)

            current_mode = os.stat("/var/lib/globus-connect-server/myproxy-ca/")
            #add group read and execute permissions
            os.chmod("/var/lib/globus-connect-server/myproxy-ca/", current_mode.st_mode | stat.S_IRGRP | stat.S_IXGRP)
            os.chmod("/var/lib/globus-connect-server/myproxy-ca/private", current_mode.st_mode | stat.S_IRGRP | stat.S_IXGRP)
            os.chmod("/var/lib/globus-connect-server/myproxy-ca/private/cakey.pem", current_mode.st_mode | stat.S_IRGRP)

            with open("playbook/overrides/production_venv_only.yml", "r+") as yaml_file:
                production_venv_only = yaml.load(yaml_file)
            production_venv_only["server_name"] = esg_functions.get_esgf_host()
            production_venv_only["server_email"] = esg_property_manager.get_property("mail_admin_address")
            db_password = esg_functions.get_postgres_password()
            production_venv_only["esgf_slcsdb"]["password"] = db_password
            production_venv_only["esgf_userdb"]["password"] = db_password

            with open('playbook/overrides/production_venv_only.yml', 'w') as yaml_file:
                yaml.dump(production_venv_only, yaml_file)

            esg_property_manager.set_property("short.lived.certificate.server", esg_functions.get_esgf_host())

            pybash.mkdir_p("/usr/local/esgf-slcs-server")
            esg_functions.change_ownership_recursive("/usr/local/esgf-slcs-server", "apache", "apache")

            #TODO: check if there's an ansible Python module
            esg_functions.call_binary("ansible-playbook", ["-i", "playbook/inventories/localhost", "-e", "@playbook/overrides/production_venv_only.yml", "playbook/playbook.yml"])

def main():
    '''Main function'''
    setup_idp()
    # setup_slcs()

if __name__ == '__main__':
    main()
