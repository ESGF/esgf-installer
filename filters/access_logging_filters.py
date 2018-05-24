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
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from esgf_utilities import esg_cert_manager
from esgf_utilities.esg_exceptions import SubprocessError
from base import esg_tomcat_manager
from base import esg_postgres

logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def setup_access_logging_filter():
    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        install_access_logging_filter()

    # esg_tomcat_manager.start_tomcat()


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
    service_name = esg_bash2py.trim_string_from_head(dest_dir)
    esg_filter_entry_pattern = "<!--@@esg_access_logging_filter_entry@@-->"

    print "*******************************"
    print "Installing ESGF Node's Access Logging Filters To: [{}]".format(dest_dir)
    print "*******************************"
    print "Filter installation destination dir = {}".format(dest_dir)
    print "Filter entry file = {}".format(esg_filter_entry_file)
    print "Filter entry pattern = {}".format(esg_filter_entry_pattern)

    #pre-checking... make sure the files we need in ${service_name}'s dir are there....
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF")):
        logger.error("WARNING: Could not find %s's installation dir - Filter Not Applied",service_name)
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

    get_mgr_libs(os.path.join(dest_dir, "WEB-INF", "lib"))

    if not esg_filter_entry_pattern in open(os.path.join(dest_dir, "WEB-INF", "web.xml")).read():
        logger.info("No Pattern Found In File [%s/WEB-INF/web.xml] - skipping this filter setup\n", dest_dir)
        return

    #TODO: break into separat function; extract esg_filter_entry_file from jar
    esg_functions.download_update(os.path.join(config["workdir"], "esgf-node-manager-common-1.0.1.jar"), "https://aims1.llnl.gov/esgf/dist/2.6/0/esgf-node-manager/esgf-node-manager-common-1.0.1.jar")
    esg_functions.download_update(os.path.join(config["workdir"], "esgf-node-manager-filters-1.0.1.jar"), "https://aims1.llnl.gov/esgf/dist/2.6/0/esgf-node-manager/esgf-node-manager-filters-1.0.1.jar")
    with esg_bash2py.pushd(config["workdir"]):
        with zipfile.ZipFile("esgf-node-manager-filters-1.0.1.jar", 'r') as zf:
            #Pull out the templated filter entry snippet file...
            zf.extract(esg_filter_entry_file)
        #going to need full path for pattern replacement below
        esg_filter_entry_file_path = os.path.join(os.getcwd(), esg_filter_entry_file)

        #Place (copy) the filter jar in the WEB-INF/lib
        print "Installing ESGF Node Manager Filter jar..."
        shutil.copyfile("esgf-node-manager-common-1.0.1.jar", os.path.join(dest_dir, "WEB-INF", "lib", "esgf-node-manager-common-1.0.1.jar"))
        shutil.copyfile("esgf-node-manager-filters-1.0.1.jar", os.path.join(dest_dir, "WEB-INF", "lib", "esgf-node-manager-filters-1.0.1.jar"))

    with esg_bash2py.pushd(os.path.join(dest_dir, "WEB-INF")):
        #Replace the filter's place holder token in ${service_name}'s web.xml file with the filter entry.
        #Use utility function...
        insert_file_at_pattern("web.xml", esg_filter_entry_file_path, esg_filter_entry_pattern)

        #Edit the web.xml file for ${service_name} to include these token replacement values
        parser = etree.XMLParser(remove_comments=False)
        tree = etree.parse("web.xml", parser)
        root = tree.getroot()
        exempt_extensions = ".xml"
        exempt_services = "thredds/wms, thredds/wcs, thredds/ncss, thredds/ncml, thredds/uddc, thredds/iso, thredds/dodsC"
        extensions = ".nc"
        esg_functions.stream_subprocess_output("eval \"perl -p -i -e 's/\\@service.name\\@/{}/g' web.xml\"".format(service_name))
        esg_functions.stream_subprocess_output("eval \"perl -p -i -e 's/\\@exempt_extensions\\@/{}/g' web.xml\"".format(exempt_extensions))
        esg_functions.stream_subprocess_output("eval \"perl -p -i -e 's#\\@exempt_services\\@#{}#g' web.xml\"".format(exempt_services))
        esg_functions.stream_subprocess_output("eval \"perl -p -i -e 's/\\@extensions\\@/${}/g' web.xml\"".format(extensions))

    tomcat_user = esg_functions.get_user_id("tomcat")
    tomcat_group = esg_functions.get_group_id("tomcat")
    esg_functions.change_ownership_recursive(os.path.join(dest_dir, "WEB-INF"), tomcat_user, tomcat_group)


#TODO: refactor
def insert_file_at_pattern(target_file, input_file, pattern):
    '''Replace a pattern inside the target file with the contents of the input file'''
    f=open(target_file)
    s=f.read()
    f.close()
    f=open(input_file)
    filter = f.read()
    f.close()
    s=s.replace(pattern,filter)
    f=open(target_file,'w')
    f.write(s)
    f.close()

def get_mgr_libs(dest_dir):
    print "Checking for / Installing required jars..."

    node_manager_app_home = "/usr/local/tomcat/webapps/esgf-node-manager"
    src_dir = os.path.join(node_manager_app_home, "WEB-INF", "lib")

    if not os.path.exists(dest_dir) or not os.path.exists(src_dir):
        logger.error("source and/or destination dir(s) not present!!! (punting)")
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

    esg_functions.download_update(os.path.join(dest_dir, node_manager_commons_jar), "https://aims1.llnl.gov/esgf/dist/2.6/0/esgf-node-manager/esgf-node-manager-common-1.0.1.jar")
    esg_functions.download_update(os.path.join(dest_dir, node_manager_filters_jar), "https://aims1.llnl.gov/esgf/dist/2.6/0/esgf-node-manager/esgf-node-manager-filters-1.0.1.jar")

    tomcat_user = esg_functions.get_user_id("tomcat")
    tomcat_group = esg_functions.get_group_id("tomcat")
    esg_functions.change_ownership_recursive(dest_dir, tomcat_user, tomcat_group)
