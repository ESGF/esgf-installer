import os
import pwd
import grp
import stat
import logging
import zipfile
import requests
import yaml
from git import Repo
from clint.textui import progress
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

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
        esg_functions.change_ownership_recursive("/usr/local/tomcat/webapps/esgf-stats-api", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # execute dashboard installation script (without the postgres schema)
    run_dashboard_script()

    # create non-privileged user to run the dashboard application
    esg_functions.stream_subprocess_output("groupadd dashboard")
    esg_functions.stream_subprocess_output("useradd -s /sbin/nologin -g dashboard -d /usr/local/dashboard dashboard")
    DASHBOARD_USER_ID = pwd.getpwnam("dashboard").pw_uid
    DASHBOARD_GROUP_ID = grp.getgrnam("dashboard").gr_gid
    esg_functions.change_ownership_recursive("/usr/local/esgf-dashboard-ip", DASHBOARD_USER_ID, DASHBOARD_GROUP_ID)
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

def main():
    setup_dashboard()


if __name__ == '__main__':
    main()
