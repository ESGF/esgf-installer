'''Description: Installation of the esg-security infrastructure.'''
import os
import logging
import shutil
import ConfigParser
import zipfile
import OpenSSL
from lxml import etree
import stat
import glob
import psutil
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import pybash
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from esgf_utilities import esg_cert_manager
from base import esg_tomcat_manager
from base import esg_postgres

logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def setup_access_logging_filter():
    '''Main function'''
    pybash.mkdir_p(config["workdir"])
    with pybash.pushd(config["workdir"]):
        install_access_logging_filter()


def download_jar_files(esg_dist_url, dest_dir):
    esg_functions.download_update(os.path.join(config["workdir"], "esgf-node-manager-common-1.0.1.jar"), "{}/esgf-node-manager/esgf-node-manager-common-1.0.1.jar".format(esg_dist_url))
    esg_functions.download_update(os.path.join(config["workdir"], "esgf-node-manager-filters-1.0.1.jar"), "{}/esgf-node-manager/esgf-node-manager-filters-1.0.1.jar".format(esg_dist_url))
    with pybash.pushd(config["workdir"]):
        #Place (copy) the filter jar in the WEB-INF/lib
        print "Installing ESGF Node Manager Filter jar..."
        shutil.copyfile("esgf-node-manager-common-1.0.1.jar", os.path.join(dest_dir, "WEB-INF", "lib", "esgf-node-manager-common-1.0.1.jar"))
        shutil.copyfile("esgf-node-manager-filters-1.0.1.jar", os.path.join(dest_dir, "WEB-INF", "lib", "esgf-node-manager-filters-1.0.1.jar"))

def edit_web_xml(service_name, esg_filter_entry_pattern, dest_dir="/usr/local/tomcat/webapps/thredds", esg_filter_entry_file="esg-access-logging-filter-web.xml"):
    esg_filter_entry_file_path = os.path.join(current_directory, esg_filter_entry_file)

    with pybash.pushd(os.path.join(dest_dir, "WEB-INF")):
        #Replace the filter's place holder token in ${service_name}'s web.xml file with the filter entry.
        #Use utility function...
        esg_functions.insert_file_at_pattern("web.xml", esg_filter_entry_file_path, esg_filter_entry_pattern)

        #Edit the web.xml file for ${service_name} to include these token replacement values
        exempt_extensions = ".xml"
        exempt_services = "thredds/wms, thredds/wcs, thredds/ncss, thredds/ncml, thredds/uddc, thredds/iso, thredds/dodsC"
        extensions = ".nc"

        with open("web.xml", 'r') as file_handle:
            filedata = file_handle.read()
        filedata = filedata.replace("@service.name@", service_name)
        filedata = filedata.replace("@exempt_extensions@", exempt_extensions)
        filedata = filedata.replace("@exempt_services@", exempt_services)
        filedata = filedata.replace("@extensions@", extensions)

        # Write the file out again
        with open("web.xml", 'w') as file_handle:
            file_handle.write(filedata)


def install_access_logging_filter(dest_dir="/usr/local/tomcat/webapps/thredds", esg_filter_entry_file="esg-access-logging-filter-web.xml"):
    '''Takes 2 arguments:
    dest_dir  - The top level directory of the webapp where filter is to be installed.
    esg_filter_entry_file - The file containing the filter entry xml snippet (optional: defaulted)

    Installs esg filter into ${service_name}'s web.xml file, directly after
    the AuthorizationTokenValidationFilter's mapping, by replacing a
    place holder token with the contents of the filter snippet file
    "esg-filter-web.xml".  Copies the filter jar file to the ${service_name}'s
    lib dir
    '''
    service_name = pybash.trim_string_from_head(dest_dir)
    esg_filter_entry_pattern = "<!--@@esg_access_logging_filter_entry@@-->"

    print "*******************************"
    print "Installing ESGF Node's Access Logging Filters To: [{}]".format(dest_dir)
    print "*******************************"
    print "Filter installation destination dir = {}".format(dest_dir)
    print "Filter entry file = {}".format(esg_filter_entry_file)
    print "Filter entry pattern = {}".format(esg_filter_entry_pattern)

    #pre-checking... make sure the files we need in ${service_name}'s dir are there....
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF")):
        logger.error("Could not find %s's installation dir - Filter Not Applied", service_name)
        return False
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF", "lib")):
        logger.error("Could not find WEB-INF/lib installation dir - Filter Not Applied")
        return False
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF", "lib")):
        logger.error("Could not find WEB-INF/lib installation dir - Filter Not Applied")
        return False
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF", "web.xml")):
        logger.error("No web.xml file found for %s - Filter Not Applied", service_name)
        return False

    esg_tomcat_manager.stop_tomcat()

    esg_dist_url = esg_property_manager.get_property("esg.dist.url")
    get_node_manager_libs(os.path.join(dest_dir, "WEB-INF", "lib"), esg_dist_url)

    if not esg_filter_entry_pattern in open(os.path.join(dest_dir, "WEB-INF", "web.xml")).read():
        logger.info("No Pattern Found In File [%s/WEB-INF/web.xml] - skipping this filter setup\n", dest_dir)
        return

    download_jar_files(esg_dist_url, dest_dir)
    edit_web_xml(service_name, esg_filter_entry_pattern)

    tomcat_user = esg_functions.get_user_id("tomcat")
    tomcat_group = esg_functions.get_group_id("tomcat")
    esg_functions.change_ownership_recursive(os.path.join(dest_dir, "WEB-INF"), tomcat_user, tomcat_group)


def get_node_manager_libs(dest_dir, esg_dist_url):
    '''Get libraries need for Node Manager; formerly called get_mgr_libs()'''
    print "Checking for / Installing required jars..."

    node_manager_app_home = "/usr/local/tomcat/webapps/esgf-node-manager"
    src_dir = os.path.join(node_manager_app_home, "WEB-INF", "lib")

    if not os.path.exists(src_dir):
        logger.warning("Cannot copy jars from Node Manager because the Node Manager is not installed. Skipping.")
        return

    #Jar versions...
    commons_dbcp_version = "1.4"
    commons_dbutils_version = "1.3"
    commons_pool_version = "1.5.4"

    #----------------------------
    #Jar Libraries Needed To Be Present For Node Manager (AccessLogging) Filter Support
    #----------------------------
    dbcp_jar = "commons-dbcp-{}.jar".format(commons_dbcp_version)
    dbutils_jar = "commons-dbutils-{}.jar".format(commons_dbutils_version)
    pool_jar = "commons-pool-{}.jar".format(commons_pool_version)
    postgress_jar = "postgresql-9.4-1201.jdbc41.jar"

    #move over libraries...
    print "getting (copying) library jars from the Node Manager App to {} ...".format(dest_dir)

    shutil.copyfile(os.path.join(src_dir, dbcp_jar), os.path.join(dest_dir, dbcp_jar))
    shutil.copyfile(os.path.join(src_dir, dbutils_jar), os.path.join(dest_dir, dbutils_jar))
    shutil.copyfile(os.path.join(src_dir, pool_jar), os.path.join(dest_dir, pool_jar))
    shutil.copyfile(os.path.join(src_dir, postgress_jar), os.path.join(dest_dir, postgress_jar))

    #----------------------------
    #Fetching Node Manager Jars from Distribution Site...
    #----------------------------
    node_manager_commons_jar = "esgf-node-manager-common-{}.jar".format(config["esgf_node_manager_version"])
    node_manager_filters_jar = "esgf-node-manager-filters-{}.jar".format(config["esgf_node_manager_version"])

    print "getting (downloading) library jars from Node Manager Distribution Server to {} ...".format(dest_dir)

    esg_functions.download_update(os.path.join(dest_dir, node_manager_commons_jar), "{}/esgf-node-manager/esgf-node-manager-common-1.0.1.jar".format(esg_dist_url))
    esg_functions.download_update(os.path.join(dest_dir, node_manager_filters_jar), "{}/esgf-node-manager/esgf-node-manager-filters-1.0.1.jar".format(esg_dist_url))

    tomcat_user = esg_functions.get_user_id("tomcat")
    tomcat_group = esg_functions.get_group_id("tomcat")
    esg_functions.change_ownership_recursive(dest_dir, tomcat_user, tomcat_group)
