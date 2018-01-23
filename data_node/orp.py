import os
import shutil
import logging
import zipfile
import requests
import yaml
from clint.textui import progress
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

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



def setup_providers_dropdown():
    '''Do additional setup to configure CEDA-provided ORP with a dropdown list of IDPs'''
    known_providers_url = "https://aims1.llnl.gov/esgf/dist/lists/esgf_known_providers.xml"
    config_dir = os.path.join("{esg_root_dir}".format(esg_root_dir=config["esg_root_dir"]), "config")
    known_providers_file = os.path.join("{config_dir}".format(config_dir=config_dir),"esgf_known_providers.xml")

    # add /esg/config/ to common.loader in catalina.properties if not already present
    update_common_loader(config_dir)

    esg_functions.download_update(known_providers_file, known_providers_url)

    esg_property_manager.write_as_property("orp_provider_list", known_providers_file)

    tomcat_user_id = esg_functions.get_user_id("tomcat")
    tomcat_group_id = esg_functions.get_group_id("tomcat")
    os.chown("/esg/config/esgf.properties", tomcat_user_id, tomcat_group_id)


def setup_orp():
    '''Setup the ORP subsystem'''
    print "\n*******************************"
    print "Setting up ORP"
    print "******************************* \n"

    if os.path.isdir("/usr/local/tomcat/webapps/esg-orp"):
        if esg_property_manager.get_property("install_orp"):
            orp_install = esg_property_manager.get_property("install_orp")
        else:
            orp_install = raw_input("Existing ORP installation found.  Do you want to continue with the ORP installation [y/N]: ") or "no"
        if orp_install.lower() in ["no", "n"]:
            return
    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esg-orp")

    orp_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel", "esg-orp", "esg-orp.war")
    print "orp_url:", orp_url

    download_orp_war(orp_url)
    with esg_bash2py.pushd("/usr/local/tomcat/webapps/esg-orp"):
        with zipfile.ZipFile("/usr/local/tomcat/webapps/esg-orp/esg-orp.war", 'r') as zf:
            zf.extractall()
        os.remove("esg-orp.war")
        TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
        TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
        esg_functions.change_ownership_recursive("/usr/local/tomcat/webapps/esg-orp", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # properties to read the Tomcat keystore, used to sign the authentication cookie
    # these values are the same for all ESGF nodes
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "esgf_orp_conf/esg-orp.properties"), "/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg-orp.properties")

    setup_providers_dropdown()

def main():
    setup_orp()

if __name__ == '__main__':
    main()
