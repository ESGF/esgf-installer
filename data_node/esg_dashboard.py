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
from esgf_utilities import esg_property_manager
from esgf_utilities import pybash
from esgf_utilities.esg_env_manager import EnvWriter
from plumbum.commands import ProcessExecutionError

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def download_extract(url, dest_dir, owner_user, owner_group):
    r = requests.get(url)
    remote_file = pybash.trim_string_from_head(url)
    filename = os.path.join(os.sep, "tmp", remote_file)
    with open(filename, "wb") as localfile:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                localfile.write(chunk)
                localfile.flush()

    pybash.mkdir_p(dest_dir)
    with zipfile.ZipFile(filename) as archive:
        archive.extractall(dest_dir)

    uid = esg_functions.get_user_id(owner_user)
    gid = esg_functions.get_group_id(owner_group)
    esg_functions.change_ownership_recursive(dest_dir, uid, gid)

def migration_egg(url, cmd, args):
    with pybash.pushd(os.path.join(os.sep, "tmp")):
        egg_file = pybash.trim_string_from_head(url)

        esg_functions.download_update(egg_file, url)
        esg_functions.call_binary("easy_install", [egg_file])
    esg_functions.call_binary(cmd, args)

def setup_dashboard():

    if os.path.isdir("/usr/local/tomcat/webapps/esgf-stats-api"):
        stats_api_install = raw_input("Existing Stats API installation found.  Do you want to continue with the Stats API installation [y/N]: " ) or "no"
        if stats_api_install.lower() in ["no", "n"]:
            return
    print "\n*******************************"
    print "Setting up ESGF Stats API (dashboard)"
    print "******************************* \n"

    tomcat_webapps = os.path.join(os.sep, "usr", "local", "tomcat", "webapps")

    dist_url = esg_property_manager.get_property("esg.dist.url")
    dist_root_url = esg_property_manager.get_property("esg.root.url")


    stats_api_url = "{}/{}".format(dist_url, "esgf-stats-api/esgf-stats-api.war")
    dest_dir = os.path.join(tomcat_webapps, "esgf-stats-api")
    download_extract(stats_api_url, dest_dir, "tomcat", "tomcat")

    dashboard_url = "{}/{}".format(dist_root_url, "esgf-dashboard/esgf-dashboard.war")
    dest_dir = os.path.join(tomcat_webapps, "esgf-dashboard")
    download_extract(dashboard_url, dest_dir, "tomcat", "tomcat")

    # execute dashboard installation script (without the postgres schema)
    run_dashboard_script()

    # create non-privileged user to run the dashboard application
    esg_functions.add_unix_group("dashboard")
    useradd_options = ["-s", "/sbin/nologin", "-g", "dashboard", "-d", "/usr/local/dashboard", "dashboard"]
    esg_functions.add_unix_user(useradd_options)

    DASHBOARD_USER_ID = pwd.getpwnam("dashboard").pw_uid
    DASHBOARD_GROUP_ID = grp.getgrnam("dashboard").gr_gid
    esg_functions.change_ownership_recursive("/usr/local/esgf-dashboard-ip", DASHBOARD_USER_ID, DASHBOARD_GROUP_ID)
    os.chmod("/var/run", stat.S_IWRITE)
    os.chmod("/var/run", stat.S_IWGRP)
    os.chmod("/var/run", stat.S_IWOTH)

    dburl = "{user}:{password}@{host}:{port}/{db}".format(
        user=config["postgress_user"],
        password=esg_functions.get_postgres_password(),
        host=config["postgress_host"],
        port=config["postgress_port"],
        db=config["node_db_name"]
    )
    args = ["--dburl", dburl, "-c"]

    egg_file = "esgf_node_manager-0.1.5-py2.7.egg"
    remote = "{}/{}/{}".format(dist_root_url, "esgf-node-manager", egg_file)
    migration_egg(remote, "esgf_node_manager_initialize", args)

    egg_file = "esgf_dashboard-0.0.2-py2.7.egg"
    remote = "{}/{}/{}".format(dist_root_url, "esgf-dashboard", egg_file)
    migration_egg(remote, "esgf_dashboard_initialize", args)

    start_dashboard_service()

def start_dashboard_service():

    EnvWriter.prepend_to_path("LD_LIBRARY_PATH", "/usr/local/conda/envs/esgf-pub/lib")
    os.chmod("/usr/local/esgf-dashboard-ip/bin/ip.service", 0555)
    esg_functions.stream_subprocess_output("/usr/local/esgf-dashboard-ip/bin/ip.service start")


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
    dashdir = "/usr/local/esgf-dashboard-ip"
    esg_property_manager.set_property("dashboard.ip.app.home", dashdir)
    geoipdir = "/usr/local/geoip"
    fed = "no"
    esg_functions.call_binary("yum", ["install", "-y", "geoip-devel"])
    with pybash.pushd("/usr/local"):
        clone_dashboard_repo()
        os.chdir("esgf-dashboard")

        dashboard_repo_local = Repo(".")
        dashboard_repo_local.git.checkout("work_plana")

        os.chdir("src/c/esgf-dashboard-ip")

        print "\n*******************************"
        print "Running ESGF Dashboard Script"
        print "******************************* \n"

        esg_functions.stream_subprocess_output("./configure --prefix={} --with-geoip-prefix-path={} --with-allow-federation={}".format(dashdir, geoipdir, fed))
        print "make"
        esg_functions.call_binary("make", silent=True)
        print "make install"
        esg_functions.call_binary("make", ["install"], silent=True)

def main():
    setup_dashboard()


if __name__ == '__main__':
    main()
