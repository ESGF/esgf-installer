import os
import shutil
import logging
import ConfigParser
import zipfile
import requests
import yaml
from clint.textui import progress
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from base import esg_tomcat_manager


logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

esg_dist_url = esg_property_manager.get_property("esg.dist.url")
orp_property_file_dist_url = "{}/esg-orp/esg-orp.properties".format(esg_dist_url)
orp_context_root = "esg-orp"
orp_service_app_home = "/usr/local/tomcat/webapps/{}".format(orp_context_root)
orp_service_endpoint = "https://{}/{}/html.htm".format(esg_functions.get_esgf_host(), orp_context_root)

#------------------------------------------
#Security services associated with ORP
#------------------------------------------
orp_security_authorization_service_host = esg_functions.get_esgf_host()
orp_security_authorization_service_port = "443"
orp_security_authorization_service_app_home = orp_service_app_home
orp_security_authorization_service_endpoint = "https://{}/esg-orp/saml/soap/secure/authorizationService.htm".format(orp_security_authorization_service_host)
#------------------------------------------

def update_existing_orp():
    try:
        orp_install = esg_property_manager.get_property("update.orp")
    except ConfigParser.NoOptionError:
        orp_install = raw_input("Do you want to continue with openid relying party installation and setup? [y/N]: ") or "no"

    if orp_install.lower() in ["no", "n"]:
        return False
    else:
        return True

def backup_orp():
    orp_backup = raw_input("Do you want to make a back up of the existing ORP distribution?? [Y/n] ") or "yes"
    if orp_backup.lower() in ["y", "yes"]:
        print "Creating a backup archive of this web application /usr/local/tomcat/webapps/esg-orp"
        esg_functions.backup("/usr/local/tomcat/webapps/esg-orp")

#DEPRECATED: No need to download the properties file from mirror, it already exists in the war file
def download_orp_properties(orp_properties_url):
    print "\n*******************************"
    print "Downloading ORP properties file"
    print "******************************* \n"

    r = requests.get(orp_properties_url, stream=True)
    path = "esg-orp.properties"
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

def backup_orp_properties():
    if os.path.exists("/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg-orp.properties"):
        shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg-orp.properties", "/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg-orp.properties.saved")

def extract_orp_war():
    print "Expanding war esg-orp.war in {}".format(os.getcwd())
    with zipfile.ZipFile("/usr/local/tomcat/webapps/esg-orp/esg-orp.war", 'r') as zf:
        zf.extractall()
    os.remove("esg-orp.war")


def get_orp_support_libs(dest_dir):
    '''Takes the destination directory you wish to have supported libs checked and downloaded to
    returns the number of files downloaded (in this case max of 2)
            0 if there was no update of libs necessary'''

    if os.path.exists(dest_dir):
        #----------------------------
        #Fetching Dependent Security Jars from Distribution Site...
        #----------------------------

        #esgf project generated jarfiles...
        esgf_security_jar = "esgf-security-{}.jar".format(config["esgf_security_version"])
        esgf_security_test_jar = "esgf-security-test-{}.jar".format(config["esgf_security_version"])
        #-----
        print "Downloading dependent library jars from ESGF Distribution Server (Security) to {} ...".format(dest_dir)
        esg_functions.download_update(os.path.join(dest_dir, esgf_security_jar), "{}/esgf-security/{}".format(esg_dist_url, esgf_security_jar))
        esg_functions.write_security_lib_install_log()
        esg_functions.download_update(os.path.join(dest_dir, esgf_security_test_jar), "{}/esgf-security/{}".format(esg_dist_url, esgf_security_test_jar))

        TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
        TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
        esg_functions.change_ownership_recursive(dest_dir, TOMCAT_USER_ID, TOMCAT_GROUP_ID)

def orp_startup_hook():
    '''This function is called by esg-node before starting tomcat!
    This is how we make sure we are always using the proper credentials.'''

    with open("/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg-orp.properties", 'r') as file_handle:
        filedata = file_handle.read()
    filedata = filedata.replace("@@keystoreFile@@", config["keystore_file"])
    filedata = filedata.replace("@@keystorePassword@@", esg_functions.get_java_keystore_password())
    filedata = filedata.replace("@@keystoreAlias@@", config["keystore_alias"])

    # Write the file out again
    with open("/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg-orp.properties", 'w') as file_handle:
        file_handle.write(filedata)


def setup_orp():
    print "Checking for Openid Relying Party {}".format(config["esg_orp_version"])
    if esg_version_manager.check_webapp_version("esg-orp", config["esg_orp_version"]):
        print "Detected an existing openid relying party installation..."
        if not update_existing_orp():
            print "Skipping node openid relying party installation and setup - will assume it's setup properly"
            return

    print "*******************************"
    print "Setting up The OpenID Relying Party..."
    print "*******************************"
    if os.path.isdir("/usr/local/tomcat/webapps/esg-orp"):
        print "Detected an existing openid relying party installation..."
        if not update_existing_orp():
            print "Skipping node openid relying party installation and setup - will assume it's setup properly"
            return

        backup_orp()

    esg_bash2py.mkdir_p(orp_service_app_home)
    try:
        if esg_property_manager.get_property("devel"):
            orp_url = "{}/devel/esg-orp/esg-orp.war"
    except ConfigParser.NoOptionError:
        orp_url = orp_url = "{}/esg-orp/esg-orp.war"
    download_orp_war(orp_url)

    esg_tomcat_manager.stop_tomcat()

    #NOTE: The saving of the last config file must be done *BEFORE* we untar the new distro!
    backup_orp_properties()

    with esg_bash2py.pushd(orp_service_app_home):
        extract_orp_war()

        orp_startup_hook()

        TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
        TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
        esg_functions.change_ownership_recursive("/usr/local/tomcat/webapps/esg-orp", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    setup_providers_dropdown(esg_dist_url)
    get_orp_support_libs("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib")

    write_orp_install_log()

    esg_tomcat_manager.start_tomcat()

def download_orp_war(orp_url):

    print "\n*******************************"
    print "Downloading ORP (Setting up The OpenID Relying Party) war file"
    print "******************************* \n"

    r = requests.get(orp_url, stream=True)
    path = '/usr/local/tomcat/webapps/esg-orp/esg-orp.war'
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

def update_common_loader(config_dir):
    '''add /esg/config/ to common.loader in catalina.properties if not already present'''
    catalina_properties_file ="{tomcat_install_dir}/conf/catalina.properties".format(tomcat_install_dir=config["tomcat_install_dir"])
    with open(catalina_properties_file) as f:
        for line in f:
            if "common.loader" in line:
                common_loader = line
                print "common_loader:", common_loader
                break
    if common_loader and config_dir in common_loader:
        logger.info("%s already listed in common.loader", config_dir)
        return
    else:
        logger.info("Adding %s to common.loader", config_dir)
        updated_common_loader = common_loader + "," + config_dir
        esg_functions.replace_string_in_file(catalina_properties_file, common_loader, updated_common_loader)



def setup_providers_dropdown(esg_dist_url):
    '''Do additional setup to configure CEDA-provided ORP with a dropdown list of IDPs'''
    known_providers_url = "{}/lists/esgf_known_providers.xml".format(esg_dist_url)
    config_dir = os.path.join("{esg_root_dir}".format(esg_root_dir=config["esg_root_dir"]), "config")
    known_providers_file = os.path.join("{config_dir}".format(config_dir=config_dir),"esgf_known_providers.xml")

    # add /esg/config/ to common.loader in catalina.properties if not already present
    update_common_loader(config_dir)

    esg_functions.download_update(known_providers_file, known_providers_url)

    esg_property_manager.set_property("orp_provider_list", known_providers_file)

    tomcat_user_id = esg_functions.get_user_id("tomcat")
    tomcat_group_id = esg_functions.get_group_id("tomcat")
    os.chown("/esg/config/esgf.properties", tomcat_user_id, tomcat_group_id)


def write_orp_install_log():
    esg_functions.write_to_install_manifest("webapp:esg-orp", "/usr/local/tomcat/webapps/{}", config["esg_orp_version"])
    esg_property_manager.set_property("orp_service_endpoint", orp_service_endpoint)
    esg_property_manager.set_property("orp_service_app_home", orp_service_app_home)
    esg_property_manager.set_property("orp_security_authorization_service_endpoint", orp_security_authorization_service_endpoint)
    esg_property_manager.set_property("orp_security_authorization_service_app_home", orp_security_authorization_service_app_home)


# def setup_orp():
#     '''Setup the ORP subsystem'''
#     print "\n*******************************"
#     print "Setting up ORP"
#     print "******************************* \n"
#
#     if os.path.isdir("/usr/local/tomcat/webapps/esg-orp"):
#         try:
#             orp_install = esg_property_manager.get_property("update.orp")
#         except ConfigParser.NoOptionError:
#             orp_install = raw_input("Existing ORP installation found.  Do you want to continue with the ORP installation [y/N]: ") or "no"
#
#         if orp_install.lower() in ["no", "n"]:
#             return
#     esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esg-orp")
#
#     orp_url = os.path.join(config["esgf_dist_mirror"], "dist", "devel", "esg-orp", "esg-orp.war")
#     print "orp_url:", orp_url
#
#     download_orp_war(orp_url)
#     with esg_bash2py.pushd("/usr/local/tomcat/webapps/esg-orp"):
#         with zipfile.ZipFile("/usr/local/tomcat/webapps/esg-orp/esg-orp.war", 'r') as zf:
#             zf.extractall()
#         os.remove("esg-orp.war")
#         TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
#         TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
#         esg_functions.change_ownership_recursive("/usr/local/tomcat/webapps/esg-orp", TOMCAT_USER_ID, TOMCAT_GROUP_ID)
#
#     # properties to read the Tomcat keystore, used to sign the authentication cookie
#     # these values are the same for all ESGF nodes
#     shutil.copyfile(os.path.join(os.path.dirname(__file__), "esgf_orp_conf/esg-orp.properties"), "/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg-orp.properties")
#
#     setup_providers_dropdown()

def main():
    setup_orp()

if __name__ == '__main__':
    main()
