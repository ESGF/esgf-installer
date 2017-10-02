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
import yaml
import sys
import zipfile
from git import Repo
from time import sleep
from tqdm import tqdm
import esg_logging_manager

logger = esg_logging_manager.create_rotating_log(__name__)


with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

TOMCAT_USER_ID = pwd.getpwnam("tomcat").pw_uid
TOMCAT_GROUP_ID = grp.getgrnam("tomcat").gr_gid
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
            except OSError, error:
                logger.error(error)


    logger.info("script_dir contents: %s", os.listdir(config["scripts_dir"]))
    subsystem_underscore = subsystem.replace("-", "_")
    execute_subsystem_command = ". {scripts_dir}/{subsystem_full_name}; setup_{subsystem_underscore}".format(scripts_dir=config["scripts_dir"], subsystem_full_name=subsystem_full_name, subsystem_underscore=subsystem_underscore)
    setup_subsystem_process = subprocess.Popen(['bash', '-c', execute_subsystem_command])
    setup_subsystem_stdout, setup_subsystem_stderr = setup_subsystem_process.communicate()
    logger.debug("setup_subsystem_stdout: %s", setup_subsystem_stdout)
    logger.debug("setup_subsystem_stderr: %s", setup_subsystem_stderr)

def download_orp_war(orp_url):

    from clint.textui import progress

    r = requests.get(orp_url, stream=True)
    path = '/usr/local/tomcat/webapps/esg-orp/esg-orp.war'
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()
    # try:
    #     r = requests.get(orp_url, stream=True)
    #
    #     # Total size in bytes.
    #     total_size = int(r.headers.get('content-length', 0))
    #     print "total_size of war file:", total_size
    #
    #     with open('/usr/local/tomcat/webapps/esg-orp/esg-orp.war', 'wb') as f:
    #         for data in tqdm(r.iter_content(32*1024), total=total_size, unit='B', unit_scale=True):
    #             f.write(data)
    # except requests.exceptions.RequestException as e:  # This is the correct syntax
    #     print e
    #     sys.exit(1)


def setup_orp():
    '''Setup the ORP subsystem'''
    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esg-orp")

    #COPY esgf-orp/esg-orp.war /usr/local/tomcat/webapps/esg-orp/esg-orp.war
    orp_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel", "esg-orp", "esg-orp.war")
    print "orp_url:", orp_url
    # r = requests.get(orp_url)
    # with open("/usr/local/tomcat/webapps/esg-orp/esg-orp.war", "wb") as code:
    #     code.write(r.content)
    download_orp_war(orp_url)
    with esg_bash2py.pushd("/usr/local/tomcat/webapps/esg-orp"):
        # esg_functions.extract_tarball("esg-orp.war")
        with zipfile.ZipFile("/usr/local/tomcat/webapps/esg-orp/esg-orp.war", 'r') as zf:
            zf.extractall()
        os.remove("esg-orp.war")
        esg_functions.change_permissions_recursive("/usr/local/tomcat/webapps/esg-orp", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # properties to read the Tomcat keystore, used to sign the authentication cookie
    # these values are the same for all ESGF nodes
    shutil.copyfile("esgf_orp_conf/esg-orp.properties", "/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg-orp.properties")


# ESGF OLD NODE MANAGER
# uset to extract dependency jars
# RUN mkdir -p /usr/local/tomcat/webapps/esgf-node-manager
# ADD $ESGF_REPO/dist/devel/esgf-node-manager/esgf-node-manager.war /usr/local/tomcat/webapps/esgf-node-manager/
# RUN cd /usr/local/tomcat/webapps/esgf-node-manager/ && \
#     jar xvf esgf-node-manager.war

def setup_node_manager_old():
    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esgf-node-manager")
    node_manager_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel", "esgf-node-manager", "esgf-node-manager.war")
    # urllib.urlretrieve(orp_url, "/usr/local/tomcat/webapps/esg-orp/")
    r = requests.get(node_manager_url)
    with open("/usr/local/tomcat/webapps/esgf-node-manager/esgf-node-manager.war", "wb") as code:
        code.write(r.content)
    with esg_bash2py.pushd("/usr/local/tomcat/webapps/esgf-node-manager/"):
        esg_functions.extract_tarball("esgf-node-manager.war")
        os.remove("esgf-node-manager.war")

def setup_thredds():
    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/thredds")
    thredds_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel", "thredds", "5.0", "5.0.1", "thredds.war")
    urllib.urlretrieve(thredds_url, "/usr/local/tomcat/webapps/thredds/")
    with esg_bash2py.pushd("/usr/local/tomcat/webapps/thredds"):
        esg_functions.extract_tarball("thredds.war")
        os.remove("thredds.war")
        esg_functions.change_permissions_recursive("/usr/local/tomcat/webapps/thredds", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # TDS configuration root
    esg_bash2py.mkdir_p("/esg/content/thredds")

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
    urllib.urlretrieve("{esgf_devel_url}/filters/jdom-legacy-1.1.3.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/filters/jdom-legacy-1.1.3.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/opensaml-2.3.2.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/filters/opensaml-2.3.2.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/openws-1.3.1.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/filters/openws-1.3.1.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/xmltooling-1.2.2.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/filters/xmltooling-1.2.2.jar")

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
    esg_functions.change_permissions_recursive("/esg/content/thredds/", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # change ownership of source directory
    esg_functions.change_permissions_recursive("/usr/local/webapps/thredds", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # cleanup
    shutil.rmtree("/usr/local/tomcat/webapps/esgf-node-manager/")


def setup_dashboard():
    # install esgf-stats-api war file
    #COPY dashboard/esgf-stats-api.war /usr/local/tomcat/webapps/esgf-stats-api/esgf-stats-api.war
    # ADD $ESGF_REPO/dist/devel/esgf-stats-api/esgf-stats-api.war /usr/local/tomcat/webapps/esgf-stats-api/esgf-stats-api.war
    # RUN cd /usr/local/tomcat/webapps/esgf-stats-api && \
    #     jar xvf esgf-stats-api.war && \
    #     rm esgf-stats-api.war && \
    #     chown -R tomcat:tomcat /usr/local/tomcat/webapps/esgf-stats-api
    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esgf-stats-api")
    stats_api_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel", "esgf-stats-api", "esgf-stats-api.war")
    r = requests.get(stats_api_url)
    with open("/usr/local/tomcat/webapps/esgf-node-manager/esgf-stats-api.war", "wb") as code:
        code.write(r.content)
    with esg_bash2py.pushd("/usr/local/tomcat/webapps/esgf-stats-api"):
        esg_functions.extract_tarball("esgf-stats-api.war")
        os.remove("esgf-stats-api.war")
        esg_functions.change_permissions_recursive("/usr/local/tomcat/webapps/esgf-stats-api", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # execute dashboard installation script (without the postgres schema)
    run_dashboard_script()

    # create non-privileged user to run the dashboard application
    # RUN groupadd dashboard && \
    #     useradd -s /sbin/nologin -g dashboard -d /usr/local/dashboard dashboard && \
    #     chown -R dashboard:dashboard /usr/local/esgf-dashboard-ip
    # RUN chmod a+w /var/run
    esg_functions.call_subprocess("groupadd dashboard")
    esg_functions.call_subprocess("useradd -s /sbin/nologin -g dashboard -d /usr/local/dashboard dashboard")
    DASHBOARD_USER_ID = pwd.getpwnam("dashboard").pw_uid
    DASHBOARD_GROUP_ID = grp.getgrnam("dashboard").gr_gid
    esg_functions.change_permissions_recursive("/usr/local/esgf-dashboard-ip", DASHBOARD_USER_ID, DASHBOARD_GROUP_ID)
    os.chmod("/var/run", stat.S_IWRITE)
    os.chmod("/var/run", stat.S_IWGRP)
    os.chmod("/var/run", stat.S_IWOTH)

def start_dashboard_service():
    esg_functions.call_subprocess("dashboard_conf/ip.service start")


def clone_dashboard_repo():
    ''' Clone esgf-dashboard repo from Github'''
    Repo.clone_from("https://github.com/ESGF/esgf-dashboard.git", "/usr/local/esgf-dashboard")



def run_dashboard_script():
    #default values
    DashDir = "/usr/local/esgf-dashboard-ip"
    GeoipDir = "/usr/local/geoip"
    Fed="no"

    # cd /usr/local
    #
    # git clone https://github.com/ESGF/esgf-dashboard.git
    #
    # cd esgf-dashboard/
    #
    # git checkout -b work_plana origin/work_plana
    #
    # cd src/c/esgf-dashboard-ip
    #
    # ./configure --prefix=$DashDir --with-geoip-prefix-path=$GeoipDir --with-allow-federation=$Fed
    #
    # make
    # make install
    #
    with esg_bash2py.pushd("/usr/local"):
        clone_dashboard_repo()
        os.chdir("esgf-dashboard")

        dashboard_repo_local = Repo("esgf-dashboard")
        dashboard_repo_local.git.checkout("work_plana")

        os.chdir("src/c/esgf-dashboard-ip")

        esg_functions.call_subprocess("./configure --prefix={DashDir} --with-geoip-prefix-path={GeoipDir} --with-allow-federation={Fed}".format(DashDir=DashDir, GeoipDir=GeoipDir, Fed=Fed))
        esg_functions.call_subprocess("make")
        esg_functions.call_subprocess("make install")

def main():
    setup_orp()
    setup_node_manager_old()
    setup_thredds()
    setup_dashboard()





if __name__ == '__main__':
    main()
