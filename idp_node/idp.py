import os
import zipfile
import logging
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from base import esg_tomcat_manager

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

def setup_idp():
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
