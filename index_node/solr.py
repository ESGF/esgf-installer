import os
import shutil
import pwd
import grp
import psutil
import logging
import glob
import ConfigParser
import requests
import yaml
from clint.textui import progress
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities.esg_exceptions import SubprocessError

current_directory = os.path.join(os.path.dirname(__file__))

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

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

# #Helper Method to figure out the version of solr-home installation
# check_solr_version() {
#     [ "$(cat ${solr_install_dir}/VERSION)" = "${solr_version}" ]
# }

def start_solr(solr_config_type, port_number, SOLR_INSTALL_DIR="/usr/local/solr", SOLR_HOME="/usr/local/solr-home"):
    print "\n*******************************"
    print "Starting Solr"
    print "******************************* \n"
    # -f starts solr in the foreground; -d Defines a server directory;
    # -s Sets the solr.solr.home system property; -p Start Solr on the defined port;
    # -a Start Solr with additional JVM parameters,
    # -m Start Solr with the defined value as the min (-Xms) and max (-Xmx) heap size for the JVM
    if solr_config_type == "master":
        enable_nodes = "'-Denable.master=true'"
    elif solr_config_type == "localhost":
        enable_nodes = "'-Denable.localhost=true'"
    else:
        enable_nodes = "'-Denable.master=true -Denable.slave=true'"

    start_solr_command = "{SOLR_INSTALL_DIR}/bin/solr start -d {SOLR_INSTALL_DIR}/server -s {SOLR_HOME}/{solr_config_type}-{port_number} -p {port_number} -a {enable_nodes} -m 512m".format(SOLR_INSTALL_DIR=SOLR_INSTALL_DIR, SOLR_HOME=SOLR_HOME, solr_config_type=solr_config_type, port_number=port_number, enable_nodes=enable_nodes)
    print "start solr command:", start_solr_command
    esg_functions.stream_subprocess_output(start_solr_command)

    solr_status(SOLR_INSTALL_DIR)

def solr_status(SOLR_INSTALL_DIR):
    '''Check the status of solr'''
    esg_functions.stream_subprocess_output("{SOLR_INSTALL_DIR}/bin/solr status".format(SOLR_INSTALL_DIR=SOLR_INSTALL_DIR))

def check_solr_process(solr_config_type="master"):
    try:
        solr_pid = [proc for proc in psutil.net_connections() if proc.laddr.port == 8984][0].pid
        print " Solr process for {solr_config_type} running on port [{solr_server_port}] with pid {solr_pid}".format(solr_config_type, "8984", solr_pid)
        return True
    except:
        print "Solr not running"
        return False

def stop_solr(SOLR_INSTALL_DIR="/usr/local/solr"):
    '''Stop the solr process'''
    try:
        esg_functions.stream_subprocess_output("{}/bin/solr stop".format(SOLR_INSTALL_DIR))
    except SubprocessError:
        print "Could not stop solr with control script. Killing with PID"
        solr_pid_files = glob.glob("/usr/local/solr/bin/*.pid")
        for pid in solr_pid_files:
            solr_pid = open(pid, "r").read()
            if psutil.pid_exists(int(solr_pid)):
                try:
                    os.kill(int(solr_pid))
                except OSError, error:
                    print "Could not kill process"
                    esg_functions.exit_with_error(error)

    solr_status(SOLR_INSTALL_DIR)


def commit_shard_config(config_type, port_number, config_file="/esg/config/esgf_shards.config"):
    parser = ConfigParser.SafeConfigParser()
    parser.read(config_file)

    try:
        parser.add_section("esgf_solr_shards")
    except ConfigParser.DuplicateSectionError:
        logger.debug("section already exists")

    parser.set("esgf_solr_shards", config_type, port_number)
    with open(config_file, "w") as config_file_object:
        parser.write(config_file_object)

def read_shard_config(config_file="/esg/config/esgf_shards.config"):
    parser = ConfigParser.SafeConfigParser()
    parser.readfp(open(config_file))
    return parser.items("esgf_solr_shards")

def add_shards(config_type, port_number=None):
    print "\n*******************************"
    print "Adding Shards"
    print "******************************* \n"
    if config_type == "master":
        port_number = "8984"
    elif config_type == "slave":
        port_number = "8983"

    esg_functions.stream_subprocess_output("/usr/local/bin/add_shard.sh {} {}".format(config_type, port_number))

    commit_shard_config(config_type, port_number)


def write_solr_install_log(solr_config_type, solr_version, solr_install_dir):
    if solr_config_type == "master" or solr_config_type == "slave":
        esg_functions.write_to_install_manifest("esg_search:solr-{}".format(solr_config_type), solr_install_dir, solr_version)

'''
    Install solr flow:
    solr_config_types = ["master", "slave"]
    for config in solr_config_types:
        add_shard(config)


    add_shard(config_type):
        checks if config_type is already in esgf_shards_config_file (/esg/config/esgf_shards.config)
        if config_type is not "master" or "slave"; attempts to ping url http://${config_type%:*}:${target_index_search_port}/solr

        calls setup_solr(config_type)
        calls configure_solr()
        calls write_solr_install_log()
        calls _commit_configuration()

    setup_solr(config_type):
        calls solr_init(config_type) which Stupidly sets a bunch of global variables
        checks for existing solr-home installation
        Checks to see if a shard already exists on config_type's port
        Checks if solr is already installed, otherwise download it

    def solr_init(config_type, config_port=None):
        sets solr_config_type, solr_server_port, solr_install_dir, solr_data_dir, solr_server_dir, solr_logs_dir as global variables smh
    configure_solr():
        solr_init(config_type)

        loop through solr cores and update solr_config_files

'''

def setup_solr(index_config, SOLR_INSTALL_DIR="/usr/local/solr", SOLR_HOME="/usr/local/solr-home", SOLR_DATA_DIR = "/esg/solr-index"):
    '''Setup Apache Solr for faceted search'''

    print "\n*******************************"
    print "Setting up Solr"
    print "******************************* \n"

    # # Solr/Jetty web application
    SOLR_VERSION = "5.5.5"
    os.environ["SOLR_HOME"] = SOLR_HOME
    SOLR_INCLUDE= "{SOLR_HOME}/solr.in.sh".format(SOLR_HOME=SOLR_HOME)
    solr_config_types = index_config

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
    try:
        esg_functions.stream_subprocess_output("groupadd solr")
    except SubprocessError, error:
        logger.debug(error[0]["returncode"])
        if error[0]["returncode"] == 9:
            pass
    try:
        esg_functions.stream_subprocess_output("useradd -s /sbin/nologin -g solr -d /usr/local/solr solr")
    except SubprocessError, error:
        logger.debug(error[0]["returncode"])
        if error[0]["returncode"] == 9:
            pass

    SOLR_USER_ID = pwd.getpwnam("solr").pw_uid
    SOLR_GROUP_ID = grp.getgrnam("solr").gr_gid
    esg_functions.change_ownership_recursive("/usr/local/solr-{SOLR_VERSION}".format(SOLR_VERSION=SOLR_VERSION), SOLR_USER_ID, SOLR_GROUP_ID)
    esg_functions.change_ownership_recursive(SOLR_HOME, SOLR_USER_ID, SOLR_GROUP_ID)
    esg_functions.change_ownership_recursive(SOLR_DATA_DIR, SOLR_USER_ID, SOLR_GROUP_ID)

    #Copy shard files
    shutil.copyfile(os.path.join(current_directory, "solr_scripts/add_shard.sh"), "/usr/local/bin/add_shard.sh")
    shutil.copyfile(os.path.join(current_directory, "solr_scripts/remove_shard.sh"), "/usr/local/bin/remove_shard.sh")

    os.chmod("/usr/local/bin/add_shard.sh", 0555)
    os.chmod("/usr/local/bin/remove_shard.sh", 0555)

    # add shards
    for config_type in solr_config_types:
        logger.debug("config_type: %s", config_type)
        add_shards(config_type)
        write_solr_install_log(config_type, SOLR_VERSION, SOLR_INSTALL_DIR)

    # custom logging properties
    shutil.copyfile(os.path.join(current_directory, "solr_scripts/log4j.properties"), "{SOLR_INSTALL_DIR}/server/resources/log4j.properties".format(SOLR_INSTALL_DIR=SOLR_INSTALL_DIR))
    esg_bash2py.mkdir_p("/esg/solr-logs")

    #start solr
    solr_shards = read_shard_config()
    for config_type, port_number in solr_shards:
        start_solr(config_type, port_number, SOLR_INSTALL_DIR, SOLR_HOME)

def main(index_config):
    setup_solr(index_config)

if __name__ == '__main__':
    main(index_config=config["index_config"])
