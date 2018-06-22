import os
import zipfile
import logging
import shutil
import filecmp
import errno
import ConfigParser
import tarfile
import yaml
import requests
from clint.textui import progress
from git import Repo
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from base import esg_tomcat_manager
import solr

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def write_search_service_install_log(search_web_service_dir, esg_search_version):
    esg_functions.write_to_install_manifest("webapp:esg-search", search_web_service_dir, esg_search_version)

    esg_property_manager.set_property("index_service_endpoint", "http://{}/esg-search/search".format(esg_functions.get_esgf_host()))
    esg_property_manager.set_property("index_service_app_home", search_web_service_dir)
    esg_property_manager.set_property("index_master_port", "8984")
    esg_property_manager.set_property("index_slave_port", "8983")
    esg_property_manager.set_property("index_timeout_connection", "2000")
    esg_property_manager.set_property("index_timeout_read_datasets", "10000")
    esg_property_manager.set_property("index_timeout_read_files", "60000")

    esg_property_manager.set_property("publishing_service_endpoint", "https://{}/esg-search/remote/secure/client-cert/hessian/publishingService".format(esg_functions.get_esgf_host()))
    esg_property_manager.set_property("publishing_service_app_home", search_web_service_dir)

    esg_property_manager.set_property("esgf_publisher_resources_home", config["esg_config_dir"])
    esg_property_manager.set_property("esgf_publisher_resources_repo", "https://github.com/ESGF/esgf-publisher-resources.git")

def setup_publisher_resources():
    esgf_publisher_resources_repo = "https://github.com/ESGF/esgf-publisher-resources.git"
    esgf_publisher_resources_dir = os.path.join(config["esg_config_dir"],"esgf-publisher-resources")
    if not os.path.exists(esgf_publisher_resources_dir):
        Repo.clone_from(esgf_publisher_resources_repo, esgf_publisher_resources_dir)


def search_startup_hook():
    print "esg-search startup hook"
    try:
        esg_property_manager.get_property("index_auto_fetch_pub_resources")
    except ConfigParser.NoOptionError:
        esg_property_manager.set_property("index_auto_fetch_pub_resources", "true")
        setup_publisher_resources()


#--------------------
# Lifecycle functions
#--------------------
def start_search_services():
    print "Starting search services..."
    config_facets_props_path = "{}/facets.properties".format(config["esg_config_dir"])
    esg_search_facets_props_path = "{}/webapps/esg-search/WEB-INF/classes/esg/search/config/facets.properties".format(config["tomcat_install_dir"])
    if not os.path.exists(config_facets_props_path) and os.path.exists(esg_search_facets_props_path):
        shutil.copyfile(esg_search_facets_props_path, config_facets_props_path)

    solr.start_solr()

def stop_search_services():
    print "Stopping search services..."
    solr.stop_solr()

#---------------------------------------------------------
# Solr Search Service Setup and Configuration
#---------------------------------------------------------

def check_for_existing_solr_install():
    print "Checking for search service {}".format(config["esg_search_version"])
    try:
        installed_esg_search_version = esg_version_manager.get_current_webapp_version("esg-search")
    except IOError,error:
        if error.errno == errno.ENOENT:
            logger.info("No existing version of esg-search found.")

    if os.path.isdir("/usr/local/tomcat/webapps/esg-search"):
        try:
            esg_search_install = esg_property_manager.get_property("update.esg.search")
        except ConfigParser.NoOptionError:
            esg_search_install = raw_input("Existing esg-search installation found.  Do you want to continue with the esg-search installation [y/N]: " ) or "no"
        if esg_search_install.lower() in ["no", "n"]:
            print "Using existing esg-search installation. Skipping setup."
            return True
        else:
            try:
                backup_esg_search = esg_property_manager.get_property("backup.esg.search")
            except ConfigParser.NoOptionError:
                backup_esg_search = raw_input("Do you want to make a back up of the existing distribution?? [Y/n] ") or "y"
            if backup_esg_search.lower in ["y", "yes"]:
                esg_functions.backup("/usr/local/tomcat/webapps/esg-search")

def download_esg_search(esg_search_version, esg_dist_url):
    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        search_service_dist_url = "{}/esg-search/esg-search-{}.tar.gz".format(esg_dist_url, esg_search_version)
        search_service_dist_file = "esg-search-{}.tar.gz".format(esg_search_version)
        esg_functions.download_update(search_service_dist_file, search_service_dist_url)

        #Extract in workdir to get esg-search.war file
        try:
            esg_functions.extract_tarball(search_service_dist_file)
        except Exception, error:
            esg_functions.exit_with_error(error)

def copy_esg_search_war_to_tomcat(esg_search_version, search_web_service_dir, search_service_war_file):
    search_service_dist_dir = "esg-search-{}".format(esg_search_version)
    with esg_bash2py.pushd(os.path.join(config["workdir"],search_service_dist_dir)):
        esg_tomcat_manager.stop_tomcat()

        esg_bash2py.mkdir_p(search_web_service_dir)
        shutil.copyfile(search_service_war_file, os.path.join(search_web_service_dir, search_service_war_file))


def extract_esg_search_war(search_web_service_dir, search_service_war_file):
    with esg_bash2py.pushd(search_web_service_dir):
        print "Expanding war {search_service_war_file} in {pwd}".format(search_service_war_file=search_service_war_file, pwd=os.getcwd())
        with zipfile.ZipFile("/usr/local/tomcat/webapps/esg-search/esg-search.war", 'r') as zf:
            zf.extractall()
        os.remove("esg-search.war")

def update_solr_cores_schema(search_web_service_dir):
    print "Checking for Solr schema update"
    new_solr_xml = "{}/WEB-INF/solr-home/mycore/conf/schema.xml".format(search_web_service_dir)

    #The values are the solr cores
    solr_shards = {"master-8984": ["datasets", "files", "aggregations"] , "localhost-8982": ["datasets", "files", "aggregations"]}

    for shard, cores in solr_shards.items():
        for core in cores:
            old_solr_xml = "/usr/local/solr-home/{shard}/{core}/conf/schema.xml".format(shard=shard, core=core)
            if os.path.exists(old_solr_xml):
                if filecmp.cmp(old_solr_xml, new_solr_xml):
                    print "Files: {old_solr_xml}, {new_solr_xml} are identical, not upgrading".format(old_solr_xml=old_solr_xml, new_solr_xml=new_solr_xml)
                else:
                    print "Copying {new_solr_xml} -> {old_solr_xml}".format(old_solr_xml=old_solr_xml, new_solr_xml=new_solr_xml)
                    shutil.copyfile(new_solr_xml, old_solr_xml)

def setup_search_service():
    '''
    Install The Search Service...
    - Takes boolean arg: 0 = setup / install mode (default)
                         1 = updated mode

    In setup mode it is an idempotent install (default)
    In update mode it will always pull down latest after archiving old'''

    if check_for_existing_solr_install():
        return

    print "*******************************"
    print "Setting up The ESGF Search Service..."
    print "*******************************"
    search_web_service_dir = "/usr/local/tomcat/webapps/esg-search"
    search_service_war_file = "esg-search.war"
    esg_dist_url = esg_property_manager.get_property("esg.dist.url")

    download_esg_search(config["esg_search_version"], esg_dist_url)

    copy_esg_search_war_to_tomcat(config["esg_search_version"], search_web_service_dir, search_service_war_file)
    extract_esg_search_war(search_web_service_dir, search_service_war_file)
    update_solr_cores_schema(search_web_service_dir)

    TOMCAT_USER_ID = esg_functions.get_user_id("tomcat")
    TOMCAT_GROUP_ID = esg_functions.get_group_id("tomcat")

    esg_functions.change_ownership_recursive(search_web_service_dir, TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    write_search_service_install_log(search_web_service_dir, config["esg_search_version"])
    write_search_rss_properties()
    setup_publisher_resources()


    #Get utility script for crawling thredds sites
    fetch_crawl_launcher(esg_dist_url)
    fetch_index_optimization_launcher(esg_dist_url)

    #restart tomcat to put modifications in effect.
    # esg_tomcat_manager.start_tomcat()

def write_search_rss_properties():
    node_short_name = esg_property_manager.get_property("node.short.name")
    esgf_feed_datasets_title = node_short_name + " RSS"
    esgf_feed_datasets_desc = "Datasets Accessible from node: {}".format(node_short_name)
    esgf_feed_datasets_link = "http://{}/thredds/catalog.html".format(esg_functions.get_esgf_host())

    esg_property_manager.set_property("esgf_feed_datasets_title", esgf_feed_datasets_title)
    esg_property_manager.set_property("esgf_feed_datasets_desc", esgf_feed_datasets_desc)
    esg_property_manager.set_property("esgf_feed_datasets_link", esgf_feed_datasets_link)


def fetch_crawl_launcher(esg_dist_url):
    esgf_crawl_launcher = "esgf-crawl"
    with esg_bash2py.pushd(config["scripts_dir"]):
        esgf_crawl_launcher_url = "{}/esg-search/esgf-crawl".format(esg_dist_url)
        esg_functions.download_update(esgf_crawl_launcher, esgf_crawl_launcher_url)
        os.chmod(esgf_crawl_launcher, 0755)

def fetch_index_optimization_launcher(esg_dist_url):
    with esg_bash2py.pushd(config["scripts_dir"]):
        esgf_index_optimization_launcher = "esgf-optimize-index"
        esgf_index_optimization_launcher_url = "{}/esg-search/esgf-optimize-index".format(esg_dist_url)
        esg_functions.download_update(esgf_index_optimization_launcher, esgf_index_optimization_launcher_url)
        os.chmod(esgf_index_optimization_launcher, 0755)

def fetch_static_shards_file(esg_dist_url):
    static_shards_file = "esgf_shards_static.xml"
    static_shards_url = "{}/lists/esgf_shards_static.xml".format(esg_dist_url)
    esg_functions.download_update(static_shards_file, static_shards_url)


def download_esg_search_war(esg_search_war_url):
    print "\n*******************************"
    print "Downloading ESG Search war file"
    print "******************************* \n"

    r = requests.get(esg_search_war_url, stream=True)
    path = '/usr/local/tomcat/webapps/esg-search/esg-search.war'
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

def main():
    print "*******************************"
    print "Setting up The ESGF Search Sub-Project..."
    print "*******************************"
    setup_search_service()

if __name__ == '__main__':
    main()
