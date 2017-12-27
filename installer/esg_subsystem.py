#NOTE: Here we are enforcing a bit of a convention... The name of
#subsystem files must be in the form of esg-xxx-xxx where the script
#contains its "main" function named setup_xxx_xxx(). The string passed
#to this function is "xxx-xxx"
#
import os
import subprocess
import shutil
import urllib
import pwd
import grp
import stat
import requests
import esg_functions
import esg_bash2py
import esg_property_manager
import yaml
import zipfile
from git import Repo
from clint.textui import progress
import esg_logging_manager
import re

logger = esg_logging_manager.create_rotating_log(__name__)


with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

CATALINA_HOME = "/usr/local/tomcat"

def setup_subsystem(subsystem, distribution_directory, esg_dist_url, force_install=False):
    '''
    arg (1) - name of installation script root name. Ex:security which resolves to script file esg-security
    arg (2) - directory on the distribution site where script is fetched from Ex: orp
    usage: setup_subsystem security orp - looks for the script esg-security in the distriubtion dir orp
    '''

    subsystem_install_script_path = os.path.join(config["scripts_dir"],"esg-{subsystem}".format(subsystem=subsystem))

    #---
    #check that you have at one point in time fetched the subsystem's installation script
    #if indeed you have we will assume you would like to proceed with setting up the latest...
    #Otherwise we just ask you first before you pull down new code to your machine...
    #---

    if force_install:
        default = "y"
    else:
        default = "n"

    if os.path.exists(subsystem_install_script_path) or force_install:
        if default.lower() in ["y", "yes"]:
            run_installation = raw_input("Would you like to set up {subsystem} services? [Y/n]: ".format(subsystem=subsystem)) or "y"
        else:
            run_installation = raw_input("Would you like to set up {subsystem} services? [y/N]: ".format(subsystem=subsystem)) or "n"

        if run_installation.lower() in ["n", "no"]:
            print "Skipping installation of {subsystem}".format(subsystem=subsystem)
            return True

    print "-------------------------------"
    print "LOADING installer for {subsystem}... ".format(subsystem=subsystem)
    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        logger.debug("Changed directory to %s", os.getcwd())

        with esg_bash2py.pushd(config["scripts_dir"]):
            logger.debug("Changed directory to %s", os.getcwd())

            subsystem_full_name = "esg-{subsystem}".format(subsystem=subsystem)
            subsystem_remote_url = "{esg_dist_url}/{distribution_directory}/{subsystem_full_name}".format(esg_dist_url=esg_dist_url, distribution_directory=distribution_directory, subsystem_full_name=subsystem_full_name)
            if not esg_functions.download_update("{subsystem_full_name}".format(subsystem_full_name=subsystem_full_name), subsystem_remote_url):
                logger.error("Could not download %s", subsystem_full_name)
                return False
            try:
                os.chmod(subsystem_full_name, 0755)
            except OSError:
                logger.exception("Unable to change permissions on %s", subsystem_full_name)


    logger.info("script_dir contents: %s", os.listdir(config["scripts_dir"]))
    subsystem_underscore = subsystem.replace("-", "_")
    execute_subsystem_command = ". {scripts_dir}/{subsystem_full_name}; setup_{subsystem_underscore}".format(scripts_dir=config["scripts_dir"], subsystem_full_name=subsystem_full_name, subsystem_underscore=subsystem_underscore)
    setup_subsystem_process = subprocess.Popen(['bash', '-c', execute_subsystem_command])
    setup_subsystem_stdout, setup_subsystem_stderr = setup_subsystem_process.communicate()
    logger.debug("setup_subsystem_stdout: %s", setup_subsystem_stdout)
    logger.debug("setup_subsystem_stderr: %s", setup_subsystem_stderr)

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


def setup_orp():
    '''Setup the ORP subsystem'''
    print "\n*******************************"
    print "Setting up ORP"
    print "******************************* \n"

    if os.path.isdir("/usr/local/tomcat/webapps/esg-orp"):
        if esg_property_manager.get_property("setup_orp"):
            orp_install = esg_property_manager.get_property("setup_orp")
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
        esg_functions.change_permissions_recursive("/usr/local/tomcat/webapps/esg-orp", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # properties to read the Tomcat keystore, used to sign the authentication cookie
    # these values are the same for all ESGF nodes
    shutil.copyfile("esgf_orp_conf/esg-orp.properties", "/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg-orp.properties")


# ESGF OLD NODE MANAGER
# uset to extract dependency jars
def download_node_manager_war(node_manager_url):

    print "\n*******************************"
    print "Downloading Node Manager (old) war file"
    print "******************************* \n"

    r = requests.get(node_manager_url, stream=True)
    path = '/usr/local/tomcat/webapps/esgf-node-manager/esgf-node-manager.war'
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()


def setup_node_manager_old():

    if os.path.isdir("/usr/local/tomcat/webapps/esgf-node-manager"):
        node_manager_install = raw_input("Existing Node Manager installation found.  Do you want to continue with the Node Manager installation [y/N]: " ) or "no"
        if node_manager_install.lower() in ["no", "n"]:
            return

    print "\n*******************************"
    print "Setting up ESGF Node Manager (old)"
    print "******************************* \n"
    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esgf-node-manager")
    node_manager_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel", "esgf-node-manager", "esgf-node-manager.war")
    download_node_manager_war(node_manager_url)

    with esg_bash2py.pushd("/usr/local/tomcat/webapps/esgf-node-manager/"):
        with zipfile.ZipFile("/usr/local/tomcat/webapps/esgf-node-manager/esgf-node-manager.war", 'r') as zf:
            zf.extractall()
        os.remove("esgf-node-manager.war")

def check_thredds_version():
    '''Check the MANIFEST.MF file for the Thredds version'''
    with open("/usr/local/tomcat/webapps/thredds/META-INF/MANIFEST.MF", "r") as manifest_file:
        contents = manifest_file.readlines()
        matcher = re.compile("Implementation-Version.*")
        results_list = filter(matcher.match, contents)
        if results_list:
            version_number = results_list[0].split(":")[1].strip().split("-")[1]
            print "Found existing Thredds installation (Thredds version {version})".format(version=version_number)
            return version_number
        else:
            print "Thredds not found on system."

def download_thredds_war(thredds_url):

    print "\n*******************************"
    print "Downloading Thredds war file"
    print "******************************* \n"

    r = requests.get(thredds_url, stream=True)
    path = '/usr/local/tomcat/webapps/thredds/thredds.war'
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

def setup_thredds():

    if os.path.isdir("/usr/local/tomcat/webapps/thredds"):
        thredds_install = raw_input("Existing Thredds installation found.  Do you want to continue with the Thredds installation [y/N]: " ) or "no"
        if thredds_install.lower() in ["no", "n"]:
            return

    print "\n*******************************"
    print "Setting up Thredds"
    print "******************************* \n"
    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/thredds")
    thredds_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel", "thredds", "5.0", "5.0.1", "thredds.war")
    download_thredds_war(thredds_url)

    with esg_bash2py.pushd("/usr/local/tomcat/webapps/thredds"):
        with zipfile.ZipFile("/usr/local/tomcat/webapps/thredds/thredds.war", 'r') as zf:
            zf.extractall()
        os.remove("thredds.war")
        TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
        TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
        esg_functions.change_permissions_recursive("/usr/local/tomcat/webapps/thredds", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # TDS configuration root
    esg_bash2py.mkdir_p(os.path.join(config["thredds_content_dir"], "thredds"))

    # TDS memory configuration
    shutil.copyfile("thredds_conf/threddsConfig.xml", "/esg/content/thredds/threddsConfig.xml")

    # ESGF root catalog
    shutil.copyfile("thredds_conf/catalog.xml", "/esg/content/thredds/catalog.xml-esgcet")

    esg_bash2py.mkdir_p("/esg/content/thredds/esgcet")

    # TDS customized applicationContext.xml file with ESGF authorizer
    shutil.copyfile("thredds_conf/applicationContext.xml", "/usr/local/tomcat/webapps/thredds/WEB-INF/applicationContext.xml")

    # TDS jars necessary to support ESGF security filters
    # some jars are retrieved from the ESGF repository
    # other jars are copied from the unpacked ORP or NM distributions
    esgf_devel_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel")
    urllib.urlretrieve("{esgf_devel_url}/filters/XSGroupRole-1.0.0.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/XSGroupRole-1.0.0.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/commons-httpclient-3.1.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-httpclient-3.1.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/commons-lang-2.6.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-lang-2.6.jar")
    urllib.urlretrieve("{esgf_devel_url}/esg-orp/esg-orp-2.9.3.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/esg-orp-2.9.3.jar")
    urllib.urlretrieve("{esgf_devel_url}/esgf-node-manager/esgf-node-manager-common-1.0.0.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/esgf-node-manager-common-1.0.0.jar")
    urllib.urlretrieve("{esgf_devel_url}/esgf-node-manager/esgf-node-manager-filters-1.0.0.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/esgf-node-manager-filters-1.0.0.jar")
    urllib.urlretrieve("{esgf_devel_url}/esgf-security/esgf-security-2.7.10.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/esgf-security-2.7.10.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/jdom-legacy-1.1.3.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/jdom-legacy-1.1.3.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/opensaml-2.3.2.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/opensaml-2.3.2.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/openws-1.3.1.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/openws-1.3.1.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/xmltooling-1.2.2.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/xmltooling-1.2.2.jar")

    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/serializer-2.9.1.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/serializer-2.9.1.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/velocity-1.5.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/velocity-1.5.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/xalan-2.7.2.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/xalan-2.7.2.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/xercesImpl-2.10.0.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/xercesImpl-2.10.0.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/xml-apis-1.4.01.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/xml-apis-1.4.01.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/xmlsec-1.4.2.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/xmlsec-1.4.2.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/log4j-1.2.17.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/log4j-1.2.17.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/commons-io-2.4.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-io-2.4.jar")

    shutil.copyfile("/usr/local/tomcat/webapps/esgf-node-manager/WEB-INF/lib/commons-dbcp-1.4.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-dbcp-1.4.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esgf-node-manager/WEB-INF/lib/commons-dbutils-1.3.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-dbutils-1.3.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esgf-node-manager/WEB-INF/lib/commons-pool-1.5.4.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-pool-1.5.4.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esgf-node-manager/WEB-INF/lib/postgresql-8.4-703.jdbc3.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/postgresql-8.4-703.jdbc3.jar")

    # TDS customized logging (uses DEBUG)
    shutil.copyfile("thredds_conf/log4j2.xml", "/usr/local/tomcat/webapps/thredds/WEB-INF/classes/log4j2.xml")

    # data node scripts
    #TODO: Convert data node scripts to Python

    # change ownership of content directory
    TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
    TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
    esg_functions.change_permissions_recursive("/esg/content/thredds/", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # change ownership of source directory
    esg_functions.change_permissions_recursive("/usr/local/webapps/thredds", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # cleanup
    shutil.rmtree("/usr/local/tomcat/webapps/esgf-node-manager/")


def download_stats_api_war(stats_api_url):
    print "\n*******************************"
    print "Downloading ESGF Stats API war file"
    print "******************************* \n"
    r = requests.get(stats_api_url)

    path = '/usr/local/tomcat/webapps/esgf-stats-api/esgf-stats-api.war'
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

def setup_dashboard():

    if os.path.isdir("/usr/local/tomcat/webapps/esgf-stats-api"):
        stats_api_install = raw_input("Existing Stats API installation found.  Do you want to continue with the Stats API installation [y/N]: " ) or "no"
        if stats_api_install.lower() in ["no", "n"]:
            return
    print "\n*******************************"
    print "Setting up ESGF Stats API (dashboard)"
    print "******************************* \n"

    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esgf-stats-api")
    stats_api_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel", "esgf-stats-api", "esgf-stats-api.war")
    download_stats_api_war(stats_api_url)

    with esg_bash2py.pushd("/usr/local/tomcat/webapps/esgf-stats-api"):
        with zipfile.ZipFile("/usr/local/tomcat/webapps/esgf-stats-api/esgf-stats-api.war", 'r') as zf:
            zf.extractall()
        os.remove("esgf-stats-api.war")
        TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
        TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
        esg_functions.change_permissions_recursive("/usr/local/tomcat/webapps/esgf-stats-api", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # execute dashboard installation script (without the postgres schema)
    run_dashboard_script()

    # create non-privileged user to run the dashboard application
    # RUN groupadd dashboard && \
    #     useradd -s /sbin/nologin -g dashboard -d /usr/local/dashboard dashboard && \
    #     chown -R dashboard:dashboard /usr/local/esgf-dashboard-ip
    # RUN chmod a+w /var/run
    esg_functions.stream_subprocess_output("groupadd dashboard")
    esg_functions.stream_subprocess_output("useradd -s /sbin/nologin -g dashboard -d /usr/local/dashboard dashboard")
    DASHBOARD_USER_ID = pwd.getpwnam("dashboard").pw_uid
    DASHBOARD_GROUP_ID = grp.getgrnam("dashboard").gr_gid
    esg_functions.change_permissions_recursive("/usr/local/esgf-dashboard-ip", DASHBOARD_USER_ID, DASHBOARD_GROUP_ID)
    os.chmod("/var/run", stat.S_IWRITE)
    os.chmod("/var/run", stat.S_IWGRP)
    os.chmod("/var/run", stat.S_IWOTH)

    start_dashboard_service()

def start_dashboard_service():
    os.chmod("dashboard_conf/ip.service", 0555)
    esg_functions.stream_subprocess_output("dashboard_conf/ip.service start")


def clone_dashboard_repo():
    ''' Clone esgf-dashboard repo from Github'''
    if os.path.isdir("/usr/local/esgf-dashboard"):
        print "esgf-dashboard repo already exists."
        return
    print "\n*******************************"
    print "Cloning esgf-dashboard repo from Github"
    print "******************************* \n"
    from git import RemoteProgress
    class Progress(RemoteProgress):
        def update(self, op_code, cur_count, max_count=None, message=''):
            if message:
                print('Downloading: (==== {} ====)\r'.format(message))
                print "current line:", self._cur_line

    Repo.clone_from("https://github.com/ESGF/esgf-dashboard.git", "/usr/local/esgf-dashboard", progress=Progress())



def run_dashboard_script():
    #default values
    DashDir = "/usr/local/esgf-dashboard-ip"
    GeoipDir = "/usr/local/geoip"
    Fed="no"

    with esg_bash2py.pushd("/usr/local"):
        clone_dashboard_repo()
        os.chdir("esgf-dashboard")

        dashboard_repo_local = Repo(".")
        dashboard_repo_local.git.checkout("work_plana")

        os.chdir("src/c/esgf-dashboard-ip")

        print "\n*******************************"
        print "Running ESGF Dashboard Script"
        print "******************************* \n"

        esg_functions.stream_subprocess_output("./configure --prefix={DashDir} --with-geoip-prefix-path={GeoipDir} --with-allow-federation={Fed}".format(DashDir=DashDir, GeoipDir=GeoipDir, Fed=Fed))
        esg_functions.stream_subprocess_output("make")
        esg_functions.stream_subprocess_output("make install")

def download_solr_tarball(solr_tarball_url, SOLR_VERSION):
    print "\n*******************************"
    print "Download Solr version {SOLR_VERSION}".format(SOLR_VERSION=SOLR_VERSION)
    print "******************************* \n"
    r = requests.get(solr_tarball_url)

    path = '/tmp/solr-{SOLR_VERSION}.tgz'.format(SOLR_VERSION=SOLR_VERSION)
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

def extract_solr_tarball(solr_tarball_path, SOLR_VERSION):
    '''Extract the solr tarball to /usr/local and symlink it to /usr/local/solr'''
    print "\n*******************************"
    print "Extracting Solr"
    print "******************************* \n"

    with esg_bash2py.pushd("/usr/local"):
        esg_functions.extract_tarball(solr_tarball_path)
        os.remove(solr_tarball_path)
        esg_bash2py.symlink_force("solr-{SOLR_VERSION}".format(SOLR_VERSION=SOLR_VERSION), "solr")

def download_template_directory():
    '''download template directory structure for shards home'''
    ESGF_REPO = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf"
    with esg_bash2py.pushd("/usr/local/src"):
        r = requests.get("{ESGF_REPO}/dist/esg-search/solr-home.tar".format(ESGF_REPO=ESGF_REPO))

        path = 'solr-home.tar'
        with open(path, 'wb') as f:
            total_length = int(r.headers.get('content-length'))
            for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
                if chunk:
                    f.write(chunk)
                    f.flush()

        esg_functions.extract_tarball("/usr/local/src/solr-home.tar")

def setup_solr():
    '''Setup Apache Solr for faceted search'''

    print "\n*******************************"
    print "Setting up Solr"
    print "******************************* \n"

    # # Solr/Jetty web application
    SOLR_VERSION = "5.5.4"
    SOLR_INSTALL_DIR = "/usr/local/solr"
    SOLR_HOME = "/usr/local/solr-home"
    SOLR_DATA_DIR = "/esg/solr-index"
    SOLR_INCLUDE= "{SOLR_HOME}/solr.in.sh".format(SOLR_HOME=SOLR_HOME)

    #Download solr tarball
    solr_tarball_url = "http://archive.apache.org/dist/lucene/solr/{SOLR_VERSION}/solr-{SOLR_VERSION}.tgz".format(SOLR_VERSION=SOLR_VERSION)
    download_solr_tarball(solr_tarball_url, SOLR_VERSION)
    #Extract solr tarball
    extract_solr_tarball('/tmp/solr-{SOLR_VERSION}.tgz'.format(SOLR_VERSION=SOLR_VERSION), SOLR_VERSION)

    esg_bash2py.mkdir_p(SOLR_DATA_DIR)

    # download template directory structure for shards home
    download_template_directory()

    esg_bash2py.mkdir_p(SOLR_HOME)

    # create non-privilged user to run Solr server
    esg_functions.stream_subprocess_output("groupadd solr")
    esg_functions.stream_subprocess_output("useradd -s /sbin/nologin -g solr -d /usr/local/solr solr")

    SOLR_USER_ID = pwd.getpwnam("solr").pw_uid
    SOLR_GROUP_ID = grp.getgrnam("solr").gr_gid
    esg_functions.change_permissions_recursive("/usr/local/solr-{SOLR_VERSION}".format(SOLR_VERSION=SOLR_VERSION), SOLR_USER_ID, SOLR_GROUP_ID)
    esg_functions.change_permissions_recursive(SOLR_HOME, SOLR_USER_ID, SOLR_GROUP_ID)
    esg_functions.change_permissions_recursive(SOLR_DATA_DIR, SOLR_USER_ID, SOLR_GROUP_ID)

    #
    #Copy shard files
    shutil.copyfile("solr_scripts/add_shard.sh", "/usr/local/bin/add_shard.sh")
    shutil.copyfile("solr_scripts/remove_shard.sh", "/usr/local/bin/remove_shard.sh")

    # add shards
    esg_functions.call_subprocess("/usr/local/bin/add_shard.sh master 8984")
    esg_functions.call_subprocess("/usr/local/bin/add_shard.sh master 8983")

    # custom logging properties
    shutil.copyfile("solr_scripts/log4j.properties", "/{SOLR_INSTALL_DIR}/server/resources/log4j.properties".format(SOLR_INSTALL_DIR=SOLR_INSTALL_DIR))

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
    esg_search_war_url = "{ESGF_REPO}/esg-search/esg-search.war".format(ESGF_REPO=ESGF_REPO)
    download_esg_search_war(esg_search_war_url)
    #Extract esg-search war
    with esg_bash2py.pushd("/usr/local/tomcat/webapps/esg-search"):
        with zipfile.ZipFile("/usr/local/tomcat/webapps/esg-search/esg-search.war", 'r') as zf:
            zf.extractall()
        os.remove("esg-search.war")

    TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
    TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
    esg_functions.change_permissions_recursive("/usr/local/tomcat/webapps/esg-search", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

#TODO: This is duplicating checkout_publisher_branch in esg_publisher; Should be generalized
def checkout_cog_branch(cog_path, branch_name):
    '''Checkout a given branch of the COG repo'''
    publisher_repo_local = Repo(cog_path)
    publisher_repo_local.git.checkout(branch_name)
    return publisher_repo_local

def clone_cog_repo(COG_INSTALL_DIR):
    '''Clone the COG repo from Github'''
    print "\n*******************************"
    print "Cloning COG repo"
    print "******************************* \n"

    from git import RemoteProgress
    class Progress(RemoteProgress):
        def update(self, op_code, cur_count, max_count=None, message=''):
            if message:
                print('Downloading: (==== {} ====)\r'.format(message))
                print "current line:", self._cur_line

    Repo.clone_from("https://github.com/EarthSystemCoG/COG.git", COG_INSTALL_DIR, progress=Progress())
    # with esg_bash2py.pushd(COG_INSTALL_DIR):
    checkout_cog_branch(COG_INSTALL_DIR, "devel")
        # cog_repo_local = Repo(".")
        # cog_repo_local.git.checkout("devel")

def setup_cog():
    # choose CoG version
    COG_TAG = "v3.9.7"
    # # env variable to execute CoG initialization
    # # may be overridden from command line after first container startup
    INIT = True
    # setup CoG environment
    COG_DIR = "/usr/local/cog"
    esg_bash2py.mkdir_p(COG_DIR)

    COG_CONFIG_DIR = "{COG_DIR}/cog_config".format(COG_DIR=COG_DIR)
    esg_bash2py.mkdir_p(COG_CONFIG_DIR)

    COG_INSTALL_DIR= "{COG_DIR}/cog_install".format(COG_DIR=COG_DIR)
    esg_bash2py.mkdir_p(COG_INSTALL_DIR)

    # ENV LD_LIBRARY_PATH=/usr/local/lib
    #
    # # install Python virtual environment
    # RUN cd $COG_DIR && \
    #     virtualenv venv
    #
    # # download CoG specific tag or branch
    clone_cog_repo(COG_INSTALL_DIR)

    #
    # # install CoG dependencies
    # RUN cd $COG_INSTALL_DIR && \
    #     source $COG_DIR/venv/bin/activate && \
    #     pip install -r requirements.txt
    #
    # # setup CoG database and configuration
    # RUN cd $COG_INSTALL_DIR && \
    #     source $COG_DIR/venv/bin/activate && \
    #     python setup.py install
    #
    # # manually install additional dependencies
    # RUN cd $COG_DIR && \
    #     source $COG_DIR/venv/bin/activate && \
    #     git clone https://github.com/EarthSystemCoG/django-openid-auth.git && \
    #     cd django-openid-auth && \
    #     python setup.py install
    #
    # RUN cd $COG_DIR && \
    #     git clone https://github.com/globusonline/transfer-api-client-python.git && \
    #     cd transfer-api-client-python && \
    #     source $COG_DIR/venv/bin/activate && \
    #     python setup.py install && \
    #     git pull && \
    #     cd mkproxy && \
    #     make  && \
    #     cp mkproxy $COG_DIR/venv/lib/python2.7/site-packages/globusonline/transfer/api_client/x509_proxy/.
    #
    # # collect static files to ./static directory
    # # must use a minimal settings file (configured with sqllite3 database)
    # COPY conf/cog_settings.cfg /usr/local/cog/cog_config/cog_settings.cfg
    # RUN cd $COG_INSTALL_DIR && \
    #     source $COG_DIR/venv/bin/activate && \
    #     python manage.py collectstatic --no-input && \
    #     rm /usr/local/cog/cog_config/cog_settings.cfg
    #     #python setup.py -q setup_cog --esgf=false
    #
    # # for some unknown reason, must reinstall captcha
    # #RUN source $COG_DIR/venv/bin/activate && \
    # #    pip uninstall -y django-simple-captcha && \
    # #    pip install django-simple-captcha==0.5.1
    #
    # # expose default django port
    # EXPOSE 8000
    #
    # # create non-privileged user to run django
    # RUN groupadd -r cogadmin && \
    #     useradd -r -g cogadmin cogadmin && \
    #     mkdir -p ~cogadmin && \
    #     chown cogadmin:cogadmin ~cogadmin
    #
    # # change user prompt
    # RUN echo 'export PS1="[\u@\h]\$ "' >> ~cogadmin/.bashrc
    #
    # # change ownership of application directories
    # #RUN chown -R cogadmin:cogadmin $COG_DIR
    #
    # # expose software installation directories
    # # needed by apache httpd running cog through mod_wsgi
    # VOLUME $COG_DIR/venv
    # VOLUME $COG_INSTALL_DIR
    #
    # # startup
    # COPY  scripts/ /usr/local/bin/
    # COPY  conf/supervisord.cog.conf /etc/supervisor/conf.d/supervisord.cog.conf
    # #COPY  scripts/wait_for_postgres.sh /usr/local/bin/wait_for_postgres.sh
    # #COPY  scripts/process_esgf_config_archive.sh /usr/local/bin/process_esgf_config_archive.sh
    #
    # # wait for Postgred connection to be ready
    # ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
    # # will override these CMD options at run time
    # CMD ["localhost", "false", "true"]


def main():
    setup_orp()
    setup_node_manager_old()
    setup_thredds()
    setup_dashboard()


if __name__ == '__main__':
    main()
