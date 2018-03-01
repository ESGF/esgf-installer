import os
import zipfile
import logging
import yaml
import requests
from clint.textui import progress
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py


with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)





DEBUG=${DEBUG:-0}
VERBOSE=${VERBOSE:-0}

#--------------
#User Defined / Settable (public)
#--------------
install_prefix=${install_prefix:-"/usr/local"}
esg_solr_user=${SOLR_USER:-"solr"}
esg_solr_group=${SOLR_GROUP:-"solr"}
esg_functions_file=${install_prefix}/bin/esg-functions
esg_root_dir=${esg_root_dir:-"/esg"}
esg_config_dir=${esg_config_dir:-"${esg_root_dir}/config"}
tomcat_install_dir=${tomcat_install_dir:-${CATALINA_HOME:=${install_prefix}/tomcat}}
workdir=${workdir:-~/workbench/esg}
install_manifest=${install_manifest:-"${esg_root_dir}/esgf-install-manifest"}
esgf_shards_config_file=${esg_config_dir}/esgf_shards.config
esgf_shards_static_file=${esg_config_dir}/esgf_shards_static.xml
esgf_shards_dynamic_file=${esg_config_dir}/esgf_shards.xml
esgf_excludes_file=${esg_config_dir}/esgf_excludes.txt

esgf_publisher_resources_home=${esgf_publisher_resources_home:-${esgf_config_dir}}
esgf_publisher_resources_repo=${esgf_publisher_resources_repo:-https://github.com/ESGF/esgf-publisher-resources.git}
#--------------

date_format=${date_format:-"+%Y_%m_%d_%H%M%S"}
compress_extensions=${compress_extensions:-".tar.gz|.tar.bz2|.tgz|.bz2"}
force_install=${force_install:-0}

installer_uid=${installer_uid:-$(id ${HOME##*/} | sed 's/.*uid=\([0-9]*\).*/\1/')}
[ $? != 0 ] || [ -z "$installer_uid" ] && echo "installer_uid is not set" && exit 1
installer_gid=${installer_gid:-$(id ${HOME##*/} | sed 's/.*gid=\([0-9]*\).*/\1/')}
[ $? != 0 ] || [ -z "$installer_gid" ] && echo "installer_gid is not set" && exit 1
installer_home=${HOME}

esg_search_version=${esg_search_version:-"1.2.0"}
search_install_dir=${ESGF_INSTALL_DIR:-"${install_prefix}/esgf_search"}
seach_data_dir=${ESGF_DATA_DIR:="${esg_root_dir}/search_data"}
esgf_crawl_launcher="esgf-crawl"
esgf_index_optimization_launcher="esgf-optimize-index"

if [ ! -e ${esg_functions_file} ]; then
    checked_get ${esg_functions_file} ${esg_dist_url}$( ((devel == 1)) && echo "/devel" || echo "")/esgf-installer/${esg_functions_file##*/} $((force_install))
    [ ! -s "${esg_functions_file}" ] && rm ${esg_functions_file}
fi
[ -e ${esg_functions_file} ] && source ${esg_functions_file} && ((VERBOSE)) && printf "sourcing from: ${esg_functions_file} \n"

if [ -e /etc/esg.install_log ] && [ ! -e "${install_manifest}" ]; then
    echo "migrating install manifest to new location"
    mv -v /etc/esg.install_log  ${install_manifest}
fi

#---------------------------------------------------------
# The "main" method for this script
#---------------------------------------------------------
#arg (1) - install = 0 [default]
#          upgrade = 1
# The other args are a list of <hostname>:<port> of all the replica indexes you wish to create
setup_search() {
    echo
    echo "*******************************"
    echo "Setting up The ESGF Search Sub-Project..."
    echo "*******************************"
    echo



    write_as_property index_service_endpoint "http://${esgf_host:-$(hostname --fqdn)}/esg-search/search"
    write_as_property index_service_app_home ${search_web_service_dir}
    write_as_property index_master_port
    write_as_property index_slave_port
    write_as_property index_timeout_connection 2000
    write_as_property index_timeout_read_datasets 10000
    write_as_property index_timeout_read_files 60000

    write_as_property publishing_service_endpoint "https://${esgf_host:-$(hostname --fqdn)}/esg-search/remote/secure/client-cert/hessian/publishingService"
    write_as_property publishing_service_app_home ${search_web_service_dir}

    write_search_rss_properties

    setup_publisher_resources
    [ $? != 0 ] && echo " WARNING: Could not setup publisher resources" || echo " [OK] "
    write_as_property esgf_publisher_resources_home
    write_as_property esgf_publisher_resources_repo

    #Get utility script for crawling thredds sites
    fetch_crawl_launcher
    fetch_index_optimization_launcher

    echo "done"
    echo
    return 0
}

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
    esg_property_manager.set_property("esgf_publisher_resources_home", "https://github.com/ESGF/esgf-publisher-resources.git")

def setup_publisher_resources():
     esgf_publisher_resources_repo = "https://github.com/ESGF/esgf-publisher-resources.git"
     Repo.clone_from(esgf_publisher_resources_repo, config["esg_config_dir"])


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

start_search_services() {
    echo "Starting search services... $@"
    if [ ! -e "${esg_config_dir}/facets.properties" ] && [ -e "${tomcat_install_dir}/webapps/esg-search/WEB-INF/classes/esg/search/config/facets.properties" ]; then
        cp -v ${tomcat_install_dir}/webapps/esg-search/WEB-INF/classes/esg/search/config/facets.properties ${esg_config_dir}/facets.properties
    fi
    #start_zookeeper
    start_solr $(_load_shards_config)
}

stop_search_services() {
    echo "Stopping search services..."
    stop_solr $(_load_shards_config)
    #stop_zookeeper
}



#---------------------------------------------------------
# Solr Search Service Setup and Configuration
#---------------------------------------------------------

tomcat_install_dir=${tomcat_install_dir:-${install_prefix}/tomcat}
web_app_tld=${tomcat_install_dir}/webapps

search_web_service_name=esg-search
search_web_service_dir=${web_app_tld}/${search_web_service_name}
search_service_dist_url=${esg_dist_url}/${search_web_service_name}/${search_web_service_name}-${esg_search_version}.tar.gz



def setup_search_service():
    '''
    Install The Search Service...
    - Takes boolean arg: 0 = setup / install mode (default)
                         1 = updated mode

    In setup mode it is an idempotent install (default)
    In update mode it will always pull down latest after archiving old'''

    esg_search_version = "4.9.2"
    print "Checking for search service {}".format(esg_search_version)
    installed_esg_search_version = esg_property_manager.get_current_webapp_version("esg-search")

    if os.path.isdir("/usr/local/tomcat/webapps/esg-search"):
        if esg_property_manager.get_property("install.esg.search"):
            esg_search_install = esg_property_manager.get_property("install.esg.search")
        else:
            esg_search_install = raw_input("Existing esg-search installation found.  Do you want to continue with the esg-search installation [y/N]: " ) or "no"
        if esg_search_install.lower() in ["no", "n"]:
            print "Using existing esg-search installation. Skipping setup."
            return
        else:
            if esg_property_manager.get_property("backup.esg.search"):
                backup_esg_search = esg_property_manager.get_property("backup.esg.search")
            else:
                backup_esg_search = raw_input("Do you want to make a back up of the existing distribution?? [Y/n] ") or "y"
            if backup_esg_search.lower in ["y", "yes"]:
                esg_functions.backup("/usr/local/tomcat/webapps/esg-search")

    print "*******************************"
    print "Setting up The ESGF Search Service..."
    print "*******************************"

    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        search_service_dist_url = "https://aims1.llnl.gov/esgf/dist/devel/esg-search/esg-search-{}.tar.gz".format(esg_search_version)
        search_service_dist_file = "esg-search-{}.tar.gz".format(esg_search_version)
        esg_functions.download_update(search_service_dist_file, search_service_dist_url)

        #Extract in workdir to get esg-search.war file
        esg_functions.extract(search_service_dist_file)
        search_service_dist_dir = "esg-search-{}".format(esg_search_version)
        with esg_bash2py.pushd(search_service_dist_dir):
            esg_tomcat_manager.stop_tomcat()
            search_service_war_file = "esg-search.war"

            search_web_service_dir = "/usr/local/tomcat/webapps/esg-search"
            esg_bash2py.mkdir_p(search_web_service_dir)
            shutil.copyfile(search_service_war_file, os.path.join(search_web_service_dir, search_web_service_dir))

            with esg_bash2py.pushd(search_web_service_dir):
                print "Expanding war {search_service_war_file} in {pwd}".format(search_service_war_file=search_service_war_file, pwd=os.getcwd())
                esg_functions.extract(search_service_war_file)

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

    TOMCAT_USER_ID = esg_functions.get_user_id("tomcat")
    TOMCAT_GROUP_ID = esg_functions.get_group_id("tomcat")

    esg_functions.change_ownership_recursive(search_web_service_dir, TOMCAT_USER_ID, TOMCAT_GROUP_ID)



def write_search_rss_properties():
    node_short_name = esg_property_manager.get_property("node.short.name")
    esgf_feed_datasets_title = node_short_name + " RSS"
    esgf_feed_datasets_desc = "Datasets Accessible from node: {}".format(node_short_name)
    esgf_feed_datasets_link = "http://{}/thredds/catalog.html".format(esg_functions.get_esgf_host())

    esg_property_manager.set_property("esgf_feed_datasets_title", esgf_feed_datasets_title)
    esg_property_manager.set_property("esgf_feed_datasets_desc", esgf_feed_datasets_desc)
    esg_property_manager.set_property("esgf_feed_datasets_link", esgf_feed_datasets_link)


def fetch_crawl_launcher():
    esgf_crawl_launcher = "esgf-crawl"
    with esg_bash2py.pushd(config["scripts_dir"]):
        esgf_crawl_launcher_url = "https://aims1.llnl.gov/esgf/dist/devel/esg-search/esgf-crawl"
        esg_functions.download_update(esgf_crawl_launcher, esgf_crawl_launcher_url)
        os.chmod(esgf_crawl_launcher, 0755)

def fetch_index_optimization_launcher():
    with esg_bash2py.pushd(config["scripts_dir"]):
        esgf_index_optimization_launcher = "esgf-optimize-index"
        esgf_index_optimization_launcher_url = "https://aims1.llnl.gov/esgf/dist/devel/esg-search/esgf-optimize-index"
        esg_functions.download_update(esgf_index_optimization_launcher, esgf_index_optimization_launcher_url)
        os.chmod(esgf_index_optimization_launcher, 0755)

def fetch_static_shards_file():
    static_shards_file = "esgf_shards_static.xml"
    static_shards_url = "https://aims1.llnl.gov/esgf/dist/devel/lists/esgf_shards_static.xml"
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

def setup_esg_search():
    '''Setting up the ESG Search application'''

    print "\n*******************************"
    print "Setting up ESG Search"
    print "******************************* \n"

    ESGF_REPO = "http://aims1.llnl.gov/esgf"
    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esg-search")
    esg_search_war_url = "{ESGF_REPO}/dist/esg-search/esg-search.war".format(ESGF_REPO=ESGF_REPO)
    download_esg_search_war(esg_search_war_url)
    #Extract esg-search war
    with esg_bash2py.pushd("/usr/local/tomcat/webapps/esg-search"):
        with zipfile.ZipFile("/usr/local/tomcat/webapps/esg-search/esg-search.war", 'r') as zf:
            zf.extractall()
        os.remove("esg-search.war")

    TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
    TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
    esg_functions.change_ownership_recursive("/usr/local/tomcat/webapps/esg-search", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

def main():
    setup_esg_search()

if __name__ == '__main__':
    main()
