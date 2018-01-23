import os
import shutil
import pwd
import grp
import requests
import yaml
from clint.textui import progress
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py

current_directory = os.path.join(os.path.dirname(__file__))

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
    esg_functions.change_ownership_recursive("/usr/local/solr-{SOLR_VERSION}".format(SOLR_VERSION=SOLR_VERSION), SOLR_USER_ID, SOLR_GROUP_ID)
    esg_functions.change_ownership_recursive(SOLR_HOME, SOLR_USER_ID, SOLR_GROUP_ID)
    esg_functions.change_ownership_recursive(SOLR_DATA_DIR, SOLR_USER_ID, SOLR_GROUP_ID)

    #
    #Copy shard files
    shutil.copyfile(os.path.join(current_directory, "solr_scripts/add_shard.sh"), "/usr/local/bin/add_shard.sh")
    shutil.copyfile(os.path.join(current_directory, "solr_scripts/remove_shard.sh"), "/usr/local/bin/remove_shard.sh")

    os.chmod("/usr/local/bin/add_shard.sh", 0555)
    os.chmod("/usr/local/bin/remove_shard.sh", 0555)

    # add shards
    add_shards()

    # custom logging properties
    shutil.copyfile(os.path.join(current_directory, "solr_scripts/log4j.properties"), "{SOLR_INSTALL_DIR}/server/resources/log4j.properties".format(SOLR_INSTALL_DIR=SOLR_INSTALL_DIR))

    #start solr
    start_solr(SOLR_INSTALL_DIR, SOLR_HOME)

def main():
    setup_solr()

if __name__ == '__main__':
    main()
