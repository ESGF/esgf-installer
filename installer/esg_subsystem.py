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
import getpass
from lxml import etree
import zipfile
from git import Repo
from clint.textui import progress
import esg_logging_manager
import re

logger = esg_logging_manager.create_rotating_log(__name__)


with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
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

def create_password_hash(tomcat_user_password):
    '''Creates a hash for a Tomcat user's password using Tomcat's digest.sh script'''
    password_hash = esg_functions.call_subprocess("/usr/local/tomcat/bin/digest.sh -a SHA {tomcat_user_password}".format(tomcat_user_password=tomcat_user_password))
    print "password hash:",  password_hash["stdout"]
    return password_hash["stdout"].split(":")[1]

def update_tomcat_users_file(tomcat_username, password_hash, tomcat_users_file=os.path.join(config["tomcat_conf_dir"], "tomcat-users.xml")):
    '''Adds a new user to the tomcat-users.xml file'''
    tree = etree.parse(tomcat_users_file)
    root = tree.getroot()
    updated_dnode_user = False
    for param in root.iter():
        if param == "user" and param.get("username") == "dnode_user":
            param.set("password", password_hash)
            updated_dnode_user = True

    if not updated_dnode_user:
        new_user = etree.SubElement(root, "user")
        new_user.set("username", tomcat_username)
        new_user.set("password", password_hash)
        new_user.set("roles", "tdsConfig")

    tree.write(open(tomcat_users_file, "wb"), pretty_print=True)

def add_another_user():
    '''Helper function for deciding to add more Tomcat users or not'''
    valid_selection = False
    done_adding_users = None
    while not valid_selection:
        another_user = raw_input("Would you like to add another user? [y/N]:") or "n"
        if another_user.lower().strip() in ["n", "no"]:
            valid_selection = True
            done_adding_users = True
        if another_user.lower().strip() in ["y", "yes"]:
            valid_selection = True
            done_adding_users = False
        else:
            print "Invalid selection"
            continue
    return done_adding_users

def add_tomcat_user():
    '''Add a user to the default Tomcat user database (tomcat-users.xml) for container-managed authentication'''
    print "Create user credentials\n"
    done_adding_users = False
    while not done_adding_users:
        if esg_property_manager.get_property("tomcat_user"):
            tomcat_username = esg_property_manager.get_property("tomcat_user")
        else:
            default_user = "dnode_user"
            tomcat_username = raw_input("Please enter username for tomcat [{default_user}]:  ".format(default_user= default_user)) or default_user

        valid_password = False
        while not valid_password:
            tomcat_user_password = esg_functions.get_security_admin_password()
            if not tomcat_user_password:
                tomcat_user_password = getpass.getpass("Please enter password for user, \"{tomcat_username}\" [********]:   ".format(tomcat_username=tomcat_username))

            if esg_functions.is_valid_password(tomcat_user_password):
                valid_password = True

        password_hash = create_password_hash(tomcat_user_password)

        update_tomcat_users_file(tomcat_username, password_hash)

        done_adding_users = add_another_user()

def get_webxml_file():
    '''Get the templated web.xml file... (with tokens for subsequent filter entries: see [esg-]security-[token|tokenless]-filters[.xml] files)'''
    web_xml_path = os.path.join("{tomcat_install_dir}".format(tomcat_install_dir=config["tomcat_install_dir"]), "webapps", "thredds", "WEB-INF","web.xml")
    web_xml_download_url = "https://aims1.llnl.gov/esgf/dist/devel/thredds/thredds.web.xml"
    esg_functions.download_update(web_xml_path, web_xml_download_url)

    TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
    TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()

    esg_functions.change_permissions_recursive("/usr/local/tomcat/webapps/thredds/web.xml", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

def update_mail_admin_address():
    mail_admin_address = esg_property_manager.get_property("mail_admin_address")
    esg_functions.stream_subprocess_output('sed -i "s/support@my.group/$mail_admin_address/g" /esg/content/thredds/threddsConfig.xml')


def esgsetup_thredds():
    esgsetup_command = '''esgsetup --config --minimal-setup --thredds --publish --gateway pcmdi11.llnl.gov --thredds-password {security_admin_password}'''.format(security_admin_password=esg_functions.get_security_admin_password())
    try:
        esg_functions.stream_subprocess_output(esgsetup_command)
    except Exception:
        logger.exception("Could not finish esgsetup")
        esg_functions.exit_with_error(1)

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

    add_tomcat_user()

    esg_bash2py.mkdir_p("{tomcat_conf_dir}/Catalina/localhost".format(tomcat_conf_dir=config["tomcat_conf_dir"]))
    shutil.copyfile("thredds_conf/thredds.xml", "{tomcat_conf_dir}/Catalina/localhost/thredds.xml".format(tomcat_conf_dir=config["tomcat_conf_dir"]))

    get_webxml_file()

    # TDS configuration root
    esg_bash2py.mkdir_p(os.path.join(config["thredds_content_dir"], "thredds"))

    # TDS memory configuration
    shutil.copyfile("thredds_conf/threddsConfig.xml", "/esg/content/thredds/threddsConfig.xml")

    update_mail_admin_address()

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

    esgsetup_thredds()

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

def extract_solr_tarball(solr_tarball_path, SOLR_VERSION, target_path="/usr/local"):
    '''Extract the solr tarball to {target_path} and symlink it to /usr/local/solr'''
    print "\n*******************************"
    print "Extracting Solr"
    print "******************************* \n"

    with esg_bash2py.pushd(target_path):
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

def start_solr(SOLR_INSTALL_DIR, SOLR_HOME):
    print "\n*******************************"
    print "Starting Solr"
    print "******************************* \n"
    # -f starts solr in the foreground; -d Defines a server directory;
    # -s Sets the solr.solr.home system property; -p Start Solr on the defined port;
    # -a Start Solr with additional JVM parameters,
    # -m Start Solr with the defined value as the min (-Xms) and max (-Xmx) heap size for the JVM
    start_solr_command = "{SOLR_INSTALL_DIR}/bin/solr start -d {SOLR_INSTALL_DIR}/server -s {SOLR_HOME}/master-8984 -p 8984 -a '-Denable.master=true' -m 512m".format(SOLR_INSTALL_DIR=SOLR_INSTALL_DIR, SOLR_HOME=SOLR_HOME)
    print "start solr command:", start_solr_command
    esg_functions.stream_subprocess_output(start_solr_command)
    solr_status(SOLR_INSTALL_DIR)

def solr_status(SOLR_INSTALL_DIR):
    '''Check the status of solr'''
    esg_functions.stream_subprocess_output("{SOLR_INSTALL_DIR}/bin/solr status".format(SOLR_INSTALL_DIR=SOLR_INSTALL_DIR))

def stop_solr(SOLR_INSTALL_DIR):
    '''Stop the solr process'''
    solr_process = esg_functions.call_subprocess("{SOLR_INSTALL_DIR}/bin/solr stop")
    if solr_process["returncode"] != 1:
        print "Could not stop solr"
        solr_status(SOLR_INSTALL_DIR)
        esg_functions.exit_with_error(solr_process["stderr"])
    else:
        solr_status(SOLR_INSTALL_DIR)

def add_shards():
    print "\n*******************************"
    print "Adding Shards"
    print "******************************* \n"
    esg_functions.stream_subprocess_output("/usr/local/bin/add_shard.sh master 8984")
    esg_functions.stream_subprocess_output("/usr/local/bin/add_shard.sh slave 8983")

def setup_solr(SOLR_INSTALL_DIR="/usr/local/solr", SOLR_HOME="/usr/local/solr-home", SOLR_DATA_DIR = "/esg/solr-index"):
    '''Setup Apache Solr for faceted search'''

    print "\n*******************************"
    print "Setting up Solr"
    print "******************************* \n"

    # # Solr/Jetty web application
    SOLR_VERSION = "5.5.4"
    os.environ["SOLR_HOME"] = SOLR_HOME
    SOLR_INCLUDE= "{SOLR_HOME}/solr.in.sh".format(SOLR_HOME=SOLR_HOME)

    #Download solr tarball
    solr_tarball_url = "http://archive.apache.org/dist/lucene/solr/{SOLR_VERSION}/solr-{SOLR_VERSION}.tgz".format(SOLR_VERSION=SOLR_VERSION)
    download_solr_tarball(solr_tarball_url, SOLR_VERSION)
    #Extract solr tarball
    solr_extract_to_path = SOLR_INSTALL_DIR.rsplit("/",1)[0]
    extract_solr_tarball('/tmp/solr-{SOLR_VERSION}.tgz'.format(SOLR_VERSION=SOLR_VERSION), SOLR_VERSION, target_path=solr_extract_to_path)

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

    os.chmod("/usr/local/bin/add_shard.sh", 0555)
    os.chmod("/usr/local/bin/remove_shard.sh", 0555)

    # add shards
    add_shards()

    # custom logging properties
    shutil.copyfile("solr_scripts/log4j.properties", "{SOLR_INSTALL_DIR}/server/resources/log4j.properties".format(SOLR_INSTALL_DIR=SOLR_INSTALL_DIR))

    #start solr
    start_solr(SOLR_INSTALL_DIR, SOLR_HOME)

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
    checkout_cog_branch(COG_INSTALL_DIR, "devel")

def setup_django_openid_auth(target_directory):
    print "\n*******************************"
    print "Setting up Django OpenID Auth"
    print "******************************* \n"
    Repo.clone_from("https://github.com/EarthSystemCoG/django-openid-auth.git", target_directory)
    with esg_bash2py.pushd(target_directory):
        esg_functions.stream_subprocess_output("python setup.py install")

def transfer_api_client_python(target_directory):
    print "\n*******************************"
    print "Setting up Transfer API Client"
    print "******************************* \n"
    Repo.clone_from("https://github.com/globusonline/transfer-api-client-python.git", target_directory)
    with esg_bash2py.pushd(target_directory):
        esg_functions.stream_subprocess_output("python setup.py install")
        repo = Repo(os.path.join(target_directory))
        git = repo.git
        git.pull()
        with esg_bash2py.pushd("mkproxy"):
            esg_functions.stream_subprocess_output("make")
            shutil.copyfile("mkproxy", "/usr/local/conda/envs/esgf-pub/lib/python2.7/site-packages/globusonline/transfer/api_client/x509_proxy/mkproxy")

def change_cog_dir_owner(COG_DIR, COG_CONFIG_DIR):
    # change ownership of COG_CONFIG_DIR/site_media
    apache_user = esg_functions.get_user_id("apache")
    apache_group = esg_functions.get_group_id("apache")
    esg_functions.change_permissions_recursive("{COG_DIR}".format(COG_DIR=COG_DIR), apache_user, apache_group)
    esg_functions.change_permissions_recursive("{COG_CONFIG_DIR}".format(COG_CONFIG_DIR=COG_CONFIG_DIR), apache_user, apache_group)

    # # create location where Python eggs can be unpacked by user 'apache'
    PYTHON_EGG_CACHE_DIR = "/var/www/.python-eggs"
    esg_functions.change_permissions_recursive("{PYTHON_EGG_CACHE_DIR}".format(PYTHON_EGG_CACHE_DIR=PYTHON_EGG_CACHE_DIR), apache_user, apache_group)

def setup_cog(COG_DIR="/usr/local/cog"):
    # choose CoG version
    COG_TAG = "v3.9.7"
    # setup CoG environment
    esg_bash2py.mkdir_p(COG_DIR)

    COG_CONFIG_DIR = "{COG_DIR}/cog_config".format(COG_DIR=COG_DIR)
    esg_bash2py.mkdir_p(COG_CONFIG_DIR)

    COG_INSTALL_DIR= "{COG_DIR}/cog_install".format(COG_DIR=COG_DIR)
    esg_bash2py.mkdir_p(COG_INSTALL_DIR)

    os.environ["LD_LIBRARY_PATH"] = "/usr/local/lib"
    clone_cog_repo(COG_INSTALL_DIR)

    # install CoG dependencies
    with esg_bash2py.pushd(COG_INSTALL_DIR):
        esg_functions.stream_subprocess_output("pip install -r requirements.txt")
    # setup CoG database and configuration
        esg_functions.stream_subprocess_output("python setup.py install")
    # manually install additional dependencies
    setup_django_openid_auth(os.path.join(COG_INSTALL_DIR, "django-openid-auth"))

    transfer_api_client_python(os.path.join(COG_INSTALL_DIR, "transfer-api-client-python"))

    # create or upgrade CoG installation
    esg_functions.stream_subprocess_output("python setup.py setup_cog --esgf=$ESGF")

    # collect static files to ./static directory
    # must use a minimal settings file (configured with sqllite3 database)
    shutil.copyfile("cog_conf/cog_settings.cfg", "{COG_DIR}/cog_config/cog_settings.cfg".format(COG_DIR=COG_DIR))
    esg_functions.stream_subprocess_output("python manage.py collectstatic --no-input")
    os.remove("{COG_DIR}/cog_config/cog_settings.cfg".format(COG_DIR=COG_DIR))

    # create non-privileged user to run django
    esg_functions.stream_subprocess_output("groupadd -r cogadmin")
    esg_functions.stream_subprocess_output("useradd -r -g cogadmin cogadmin")
    esg_bash2py.mkdir_p("~cogadmin")
    esg_functions.stream_subprocess_output("chown cogadmin:cogadmin ~cogadmin")

    # change user prompt
    with open("~cogadmin/.bashrc", "a") as cogadmin_bashrc:
        cogadmin_bashrc.write('export PS1="[\u@\h]\$ "')

    change_cog_dir_owner(COG_DIR, COG_CONFIG_DIR)

    # startup
    shutil.copyfile("cog_scripts/wait_for_postgres.sh", "/usr/local/bin/wait_for_postgres.sh")
    shutil.copyfile("cog_scripts/process_esgf_config_archive.sh", "/usr/local/bin/process_esgf_config_archive.sh")

def main():
    setup_orp()
    # setup_node_manager_old()
    setup_thredds()
    setup_dashboard()


if __name__ == '__main__':
    main()
