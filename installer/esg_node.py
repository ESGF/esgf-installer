import os
import subprocess
import requests
import sys
import pip
import hashlib
import shutil
import grp
import datetime
import logging
import socket
import urlparse
import argparse
import platform
import re
from git import Repo
from collections import deque
from time import sleep
import esg_functions
import esg_bash2py
import esg_functions
from esg_init import EsgInit



logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = EsgInit()
# os.environ['DISCOVERONLY'] = Expand.colonMinus("DISCOVERONLY")
os.environ['LANG'] = "POSIX"
os.umask(022)

DEBUG = esg_bash2py.Expand.colonMinus("DEBUG", "0")
VERBOSE = esg_bash2py.Expand.colonMinus("VERBOSE", "0")
INSTALL_BIT=1
TEST_BIT=2
DATA_BIT=4
INDEX_BIT=8
IDP_BIT=16
COMPUTE_BIT=32
WRITE_ENV_BIT=64
#PRIVATE_BIT=128
#NOTE: remember to adjust (below) when adding new bits!!
MIN_BIT=4
MAX_BIT=64
ALL_BIT=DATA_BIT+INDEX_BIT+IDP_BIT+COMPUTE_BIT

bit_dictionary = {"INSTALL_BIT":1, "TEST_BIT":2, "DATA_BIT":4, "INDEX_BIT":8, "IDP_BIT":16, "COMPUTE_BIT":32, "WRITE_ENV_BIT":64, "MIN_BIT":4, "MAX_BIT":64, "ALL_BIT":DATA_BIT+INDEX_BIT+IDP_BIT+COMPUTE_BIT}


def get_bit_value(node_type):
    if node_type == "install":
        return bit_dictionary["INSTALL_BIT"]
    elif node_type == "data":
        return bit_dictionary["DATA_BIT"]
    elif node_type == "index":
        return bit_dictionary["INDEX_BIT"]
    elif node_type == "idp":
        return bit_dictionary["IDP_BIT"]
    elif node_type == "compute":
        return bit_dictionary["COMPUTE_BIT"]
    elif node_type == "write_env":
        return bit_dictionary["WRITE_ENV_BIT"]
    elif node_type == "min":
        return bit_dictionary["MIN_BIT"]
    elif node_type == "max":
        return bit_dictionary["MAX_BIT"]
    elif node_type == "all":
        return bit_dictionary["ALL_BIT"]
    else:
        raise ValueError("Invalid bit reference")

devel = esg_bash2py.Expand.colonMinus("devel", 0)
recommended_setup = 1
custom_setup = 0
use_local_files = 0

progname = "esg-node"
script_version = "v2.0-RC5.4.0-devel"
script_maj_version = "2.0"
script_release = "Centaur"
envfile = "/etc/esg.env"
force_install = False


#--------------
# User Defined / Settable (public)
#--------------
# install_prefix=${install_prefix:-${ESGF_INSTALL_PREFIX:-"/usr/local"}}
install_prefix = esg_bash2py.Expand.colonMinus(
    config.install_prefix, esg_bash2py.Expand.colonMinus("ESGF_INSTALL_PREFIX", "/usr/local"))
#--------------

# os.environ['UVCDAT_ANONYMOUS_LOG'] = False

esg_root_id = None
try:
    esg_root_id = config.config_dictionary["esg_root_id"]
except KeyError:
    esg_root_id = esg_functions.get_property("esg_root_id")

node_short_name = None
try:
    node_short_name = config.config_dictionary["node_short_name"]
except:
    node_short_name = esg_functions.get_property("node_short_name")
# write_java_env() {
#     ((show_summary_latch++))
#     echo "export JAVA_HOME=${java_install_dir}" >> ${envfile}
#     prefix_to_path PATH ${java_install_dir}/bin >> ${envfile}
#     dedup ${envfile} && source ${envfile}
#     return 0
# }

# def write_java_env():
#   config.config_dictionary["show_summary_latch"]++
#   # target = open(filename, 'w')
#   target = open(config.config_dictionary['envfile'], 'w')
#   target.write("export JAVA_HOME="+config.config_dictionary["java_install_dir"])

'''
    ESGCET Package (Publisher)
'''


def setup_esgcet(upgrade_mode=None):
    print "Checking for esgcet (publisher) %s " % (config.config_dictionary["esgcet_version"])
    # TODO: come up with better name
    publisher_module_check = esg_functions.check_module_version(
        "esgcet", config.config_dictionary["esgcet_version"])

    # TODO: implement this if block
    # if os.path.isfile(config.config_dictionary["ESGINI"]):
    #   urls_mis_match=1
    #   # files= subprocess.Popen('ls -t | grep %s.\*.tgz | tail -n +$((%i+1)) | xargs' %(source_backup_name,int(num_of_backups)), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # esgini_dburl = files= subprocess.Popen("sed -n 's@^[^#]*[ ]*dburl[ ]*=[
    # ]*\(.*\)$@\1@p' %s | head -n1 | sed 's@\r@@'' "
    # %(config.config_dictionary["ESGINI"]), shell=True,
    # stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if publisher_module_check == 0 and not force_install:
        print "[OK]: Publisher already installed"
        return 0

    upgrade = upgrade_mode if upgrade_mode is not None else publisher_module_check

    if upgrade == 1 and not force_install:
        mode = "U"
    else:
        mode = "I"

    print '''
        *******************************
        Setting up ESGCET Package...(%s) [%s]
        *******************************
     ''' % (config.config_dictionary["esgcet_egg_file"], mode)

    if mode == "U":
        if config.config_dictionary["publisher_home"] == os.environ["HOME"] + "/.esgcet":
            print "user configuration", config.config_dictionary["publisher_home"]
        else:
            print "system configuration", config.config_dictionary["publisher_home"]

    default_upgrade_answer = None
    if force_install:
        default_upgrade_answer = "N"
    else:
        default_upgrade_answer = "Y"

    continue_installation_answer = None

    if os.path.isfile(os.path.join(config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"])):
        print "Detected an existing esgcet installation..."
        if default_upgrade_answer == "N":
            continue_installation_answer = raw_input(
                "Do you want to continue with esgcet installation and setup? [y/N]")
        else:
            continue_installation_answer = raw_input(
                "Do you want to continue with esgcet installation and setup? [Y/n]")

        if not continue_installation_answer.strip():
            continue_installation_answer = default_upgrade_answer

        if continue_installation_answer.lower() != "y":
            print "Skipping esgcet installation and setup - will assume esgcet is setup properly"
            return 0

    print "current directory: ", os.getcwd()
    starting_directory = os.getcwd()

    try:
        os.makedirs(config.config_dictionary["workdir"])
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass

    os.chdir(config.config_dictionary["workdir"])

    pip_list = [{"package": "lxml", "version": "3.3.5"}, {"package": "requests", "version": "1.2.3"}, {"package": "SQLAlchemy", "version": "0.7.10"},
                {"package": "sqlalchemy-migrate", "version": "0.6"}, {"package": "psycopg2",
                                                                      "version": "2.5"}, {"package": "Tempita", "version": "0.5.1"},
                {"package": "decorator", "version": "3.4.0"}, {"package": "pysolr", "version": "3.3.0"}, {"package": "drslib", "version": "0.3.1p3"}]

    for i, value in enumerate(pip_list):
        print "installing %s-%s" % (value["package"], value["version"])
        pip.main(["install", value["package"] + "==" + value["version"]])

    # clone publisher
    publisher_git_protocol = "git://"

    workdir_esg_publisher_directory = os.path.join(config.config_dictionary["workdir"], "esg-publisher")

    if force_install and os.path.isdir(workdir_esg_publisher_directory):
        try:
            shutil.rmtree(workdir_esg_publisher_directory)
        except:
            print "Could not delete directory: %s" % (workdir_esg_publisher_directory)

    if not os.path.isdir(workdir_esg_publisher_directory):

        print "Fetching the cdat project from GIT Repo... %s" % (config.config_dictionary["publisher_repo"])
        Repo.clone_from(config.config_dictionary[
                        "publisher_repo"], workdir_esg_publisher_directory)

        if not os.path.isdir(os.path.join(workdir_esg_publisher_directory, ".git")):

            publisher_git_protocol = "https://"
            print "Apparently was not able to fetch from GIT repo using git protocol... trying https protocol... %s" % (publisher_git_protocol)

            Repo.clone_from(config.config_dictionary["publisher_repo_https"], workdir_esg_publisher_directory)

            if not os.path.isdir(os.path.join(config.config_dictionary["workdir"], "esg-publisher", ".git")):
                print "Could not fetch from cdat's repo (with git nor https protocol)"
                esg_functions.checked_done(1)

    os.chdir(workdir_esg_publisher_directory)
    publisher_repo_local = Repo(workdir_esg_publisher_directory)
    publisher_repo_local.git.checkout("master")
    # pull from remote
    publisher_repo_local.remotes.origin.pull()
    # Checkout publisher tag
    try:
        publisher_repo_local.head.reference = publisher_repo_local.tags[
            config.config_dictionary["publisher_tag"]]
        publisher_repo_local.head.reset(index=True, working_tree=True)
    except:
        print " WARNING: Problem with checking out publisher (esgcet) revision [%s] from repository :-(" % (config.config_dictionary["esgcet_version"])

    # install publisher
    installation_command = "cd src/python/esgcet; %s/bin/python setup.py install" % (
        config.config_dictionary["cdat_home"])
    try:
        output = subprocess.call(installation_command, shell=True)
        if output != 0:
            esg_functions.checked_done(1)
    except:
        esg_functions.checked_done(1)

    if mode == "I":
        choice = None

        while choice != 0:
            print "Would you like a \"system\" or \"user\" publisher configuration: \n"
            print "\t-------------------------------------------\n"
            print "\t*[1] : System\n"
            print "\t [2] : User\n"
            print "\t-------------------------------------------\n"
            print "\t [C] : (Custom)\n"
            print "\t-------------------------------------------\n"

            choice = raw_input("select [1] > ")
            if choice == "1":
                config.config_dictionary[
                    "publisher_home"] = config.esg_config_dir + "/esgcet"
            elif choice == "2":
                config.config_dictionary[
                    "publisher_home"] = os.environ["HOME"] + "/.esgcet"
            elif choice.lower() == "c":
                # input = None
                publisher_config_directory_input = raw_input(
                    "Please enter the desired publisher configuration directory [%s] " % config.config_dictionary["publisher_home"])
                config.config_dictionary[
                    "publisher_home"] = publisher_config_directory_input
                publisher_config_filename_input = raw_input(
                    "Please enter the desired publisher configuration filename [%s] " % config.config_dictionary["publisher_config"])
                choice = "(Manual Entry)"
            else:
                print "Invalid Selection %s " % (choice)

            print "You have selected: %s" % (choice)
            print "Publisher configuration file -> [%s/%s]" % (config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"])
            is_correct = raw_input("Is this correct? [Y/n] ")
            if is_correct.lower() == "n":
                continue
            else:
                break

        config.config_dictionary["ESGINI"] = os.path.join(config.config_dictionary[
                                                          "publisher_home"], config.config_dictionary["publisher_config"])
        print "Publisher configuration file -> [%s/%s]" % (config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"])

        esgf_host = None
        try:
            esgf_host = config.config_dictionary["esgf_host"]
        except KeyError:
            esgf_host = esg_functions.get_property("esgf_host")

        global esg_root_id
        org_id_input = raw_input(
            "What is your organization's id? [%s]: " % esg_root_id)
        if org_id_input:
            esg_root_id = org_id_input

        print "%s/bin/esgsetup --config $( ((%s == 1 )) && echo '--minimal-setup' ) --rootid %s" % (config.config_dictionary["cdat_home"], recommended_setup, esg_root_id)

        try:
            os.mkdir(config.config_dictionary["publisher_home"])
        except OSError, exception:
            if exception.errno != 17:
                raise
            sleep(1)
            pass

        ESGINI = subprocess.Popen('''
            {publisher_home}/{publisher_config} {cdat_home}/bin/esgsetup --config 
            $( (({recommended_setup} == 1 )) && echo "--minimal-setup" ) --rootid {esg_root_id}
            sed -i s/"host\.sample\.gov"/{esgf_host}/g {publisher_home}/{publisher_config} 
            sed -i s/"LASatYourHost"/LASat{node_short_name}/g {publisher_home}/{publisher_config}
            '''.format(publisher_home=config.config_dictionary["publisher_home"], publisher_config=config.config_dictionary["publisher_config"], cdat_home=config.config_dictionary["cdat_home"],
                       recommended_setup=recommended_setup, esg_root_id=esg_root_id,
                       esgf_host=esgf_host, node_short_name=node_short_name), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ESGINI.communicate()
        if ESGINI.returncode != 0:
            print "ESGINI.returncode did not equal 0: ", ESGINI.returncode
            os.chdir(starting_directory)
            esg_functions.checked_done(1)

    print "chown -R %s:%s %s" % (config.config_dictionary["installer_uid"], config.config_dictionary["installer_gid"], config.config_dictionary["publisher_home"])
    try:
        os.chown(config.config_dictionary["publisher_home"], config.config_dictionary[
                 "installer_uid"], config.config_dictionary["installer_gid"])
    except:
        print "**WARNING**: Could not change owner successfully - this will lead to inability to use the publisher properly!"

    # Let's make sure the group is there before we attempt to assign a file to
    # it....
    try:
        tomcat_group_check = grp.getgrnam(
            config.config_dictionary["tomcat_group"])
    except KeyError:
        groupadd_command = "/usr/sbin/groupadd -r %s" % (
            config.config_dictionary["tomcat_group"])
        groupadd_output = subprocess.call(groupadd_command, shell=True)
        if groupadd_output != 0 or groupadd_output != 9:
            print "ERROR: *Could not add tomcat system group: %s" % (config.config_dictionary["tomcat_group"])
            os.chdir(starting_directory)
            esg_functions.checked_done(1)

    try:
        tomcat_group_id = grp.getgrnam(
            config.config_dictionary["tomcat_group"]).gr_gid
        os.chown(os.path.join(config.config_dictionary[
                 "publisher_home"], config.config_dictionary["publisher_config"]), -1, tomcat_group_id)
        os.chmod(os.path.join(config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"]), 0640)
    except:
        print "**WARNING**: Could not change group successfully - this will lead to inability to use the publisher properly!"

    start_postgress()

    # security_admin_password=$(cat ${esgf_secret_file} 2> /dev/null)
    security_admin_password = None
    with open(config.esgf_secret_file, 'rb') as f:
        security_admin_password = f.read()

    # get_property publisher_db_user ${publisher_db_user}
    publisher_db_user = None
    try:
        publisher_db_user = config.config_dictionary["publisher_db_user"]
    except KeyError:
        publisher_db_user = esg_functions.get_property("publisher_db_user")

    if mode == "I":
        if DEBUG != "0":
            print  '''ESGINI = 
                    %s/%s %s/bin/esgsetup $( ((%s == 1 )) && echo "--minimal-setup" ) 
                    --db $( [ -n "%s" ] && echo "--db-name %s" ) $( [ -n "%s" ] 
                    && echo "--db-admin %s" ) $([ -n "${pg_sys_acct_passwd:=%s}" ] 
                    && echo "--db-admin-password %s") 
                    $( [ -n "%s" ] && echo "--db-user %s" ) 
                    $([ -n "%s" ] && echo "--db-user-password %s") 
                    $( [ -n "%s" ] && echo "--db-host %s" ) 
                    $( [ -n "%s" ] && echo "--db-port %s" )" % 
            ''' % (config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"], config.config_dictionary["cdat_home"], recommended_setup,
                   config.config_dictionary["db_database"], config.config_dictionary[
                       "db_database"], config.config_dictionary["postgress_user"],
                   config.config_dictionary[
                       "postgress_user"], security_admin_password,
                   config.config_dictionary["pg_sys_acct_passwd"],
                   publisher_db_user, publisher_db_user,
                   config.config_dictionary["publisher_db_user_passwd"], config.config_dictionary[
                       "publisher_db_user_passwd"],
                   config.config_dictionary[
                       "postgress_host"], config.config_dictionary["postgress_host"],
                   config.config_dictionary["postgress_port"], config.config_dictionary["postgress_port"])

        else:
            print '''ESGINI = 
                    {publisher_home}/{publisher_config} {cdat_home}/bin/esgsetup 
                    $( (({recommended_setup} == 1 )) && echo "--minimal-setup" ) 
                    --db $( [ -n "{db_database}" ] && echo "--db-name {db_database}" ) 
                    $( [ -n "{postgress_user}" ] && echo "--db-admin {postgress_user}" ) 
                    $([ -n "{pg_sys_acct_passwd}" ] && echo "--db-admin-password {pg_sys_acct_passwd}") 
                    $( [ -n "{publisher_db_user}" ] && echo "--db-user {publisher_db_user}" ) 
                    $([ -n "{publisher_db_user_passwd}" ] && echo "--db-user-password {publisher_db_user_passwd_stars}") 
                    $( [ -n "{postgress_host}" ] && echo "--db-host {postgress_host}" ) 
                    $( [ -n "{postgress_port}" ] && echo "--db-port {postgress_port}" )" 
            '''.format(publisher_home=config.config_dictionary["publisher_home"], publisher_config=config.config_dictionary["publisher_config"], cdat_home=config.config_dictionary["cdat_home"],
                       recommended_setup=recommended_setup,
                       db_database=config.config_dictionary["db_database"],
                       postgress_user=config.config_dictionary[
                           "postgress_user"],
                       pg_sys_acct_passwd="******" if config.config_dictionary[
                           "pg_sys_acct_passwd"] else config.config_dictionary["security_admin_password"],
                       publisher_db_user=publisher_db_user,
                       publisher_db_user_passwd=config.config_dictionary[
                           "publisher_db_user_passwd"], publisher_db_user_passwd_stars="******",
                       postgress_host=config.config_dictionary[
                           "postgress_host"],
                       postgress_port=config.config_dictionary["postgress_port"])

    try:

        ESGINI = '''{publisher_home}/{publisher_config} {cdat_home}/bin/esgsetup 
                    $( (({recommended_setup} == 1 )) && echo "--minimal-setup" ) 
                    --db $( [ -n "{db_database}" ] && echo "--db-name {db_database}" ) 
                    $( [ -n "{postgress_user}" ] && echo "--db-admin {postgress_user}" ) 
                    $([ -n "{pg_sys_acct_passwd}" ] && echo "--db-admin-password {pg_sys_acct_passwd}") 
                    $( [ -n "{publisher_db_user}" ] && echo "--db-user {publisher_db_user}" ) 
                    $([ -n "{publisher_db_user_passwd}" ] && echo "--db-user-password {publisher_db_user_passwd}") 
                    $( [ -n "{postgress_host}" ] && echo "--db-host {postgress_host}" ) 
                    $( [ -n "{postgress_port}" ] && echo "--db-port {postgress_port}" )" 
                '''.format(publisher_home=config.config_dictionary["publisher_home"], publisher_config=config.config_dictionary["publisher_config"], cdat_home=config.config_dictionary["cdat_home"],
                           recommended_setup=recommended_setup,
                           db_database=config.config_dictionary["db_database"],
                           postgress_user=config.config_dictionary[
                               "postgress_user"],
                           pg_sys_acct_passwd=config.config_dictionary["pg_sys_acct_passwd"] if config.config_dictionary[
                               "pg_sys_acct_passwd"] else config.config_dictionary["security_admin_password"],
                           publisher_db_user=publisher_db_user,
                           publisher_db_user_passwd=config.config_dictionary[
                               "publisher_db_user_passwd"],
                           postgress_host=config.config_dictionary[
                               "postgress_host"],
                           postgress_port=config.config_dictionary["postgress_port"])

    except Exception, exception:
        print "exception occured with ESGINI: ", str(exception)
        os.chdir(starting_directory)
        esg_functions.checked_done(1)

    try:
        esginitialize_output = subprocess.call(
            "%s/bin/esginitialize -c" % (config.config_dictionary["cdat_home"]), shell=True)
        if esginitialize_output != 0:
            os.chdir(starting_directory)
            esg_functions.checked_done(1)
    except Exception, exception:
        print "exception occurred with esginitialize_output: ", str(exception)

    os.chdir(starting_directory)
    write_esgcet_env()
    write_esgcet_install_log()

    esg_functions.checked_done(0)


def write_esgcet_env():
    # print
    datafile = open(config.envfile, "a+")
    try:
	    datafile.write("export ESG_ROOT_ID=" + esg_root_id + "\n")
	    esg_functions.deduplicate(config.envfile)
    finally:
    	datafile.close()


def write_esgcet_install_log():
    datafile = open(config.install_manifest, "a+")
    try:
	    datafile.write(str(datetime.date.today()) + "python:esgcet=" +
	                   config.config_dictionary["esgcet_version"] + "\n")
	    esg_functions.deduplicate(config.install_manifest)
    finally:
    	datafile.close()

    esg_functions.write_as_property(
        "publisher_config", config.config_dictionary["publisher_config"])
    esg_functions.write_as_property(
        "publisher_home", config.config_dictionary["publisher_home"])
    esg_functions.write_as_property("monitor.esg.ini", os.path.join(config.config_dictionary[
                                    "publisher_home"], config.config_dictionary["publisher_config"]))
    return 0


def test_esgcet():
    print '''
        ----------------------------
        ESGCET Test... 
        ----------------------------
    '''
    starting_directory = os.getcwd()
    os.chdir(config.config_dictionary["workdir"])

    start_postgress()

    esgcet_testdir = os.path.join(config.config_dictionary[
                                  "thredds_root_dir"], "test")

    try:
        os.makedirs(esgcet_testdir)
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass
    except Exception, exception:
        print "Exception occurred when attempting to create the {esgcet_testdir} directory: {exception}".format(esgcet_testdir=esgcet_testdir, exception=exception)
        esg_functions.checked_done(1)

    os.chown(esgcet_testdir, config.config_dictionary[
             "installer_uid"], config.config_dictionary["installer_gid"])

    try:
        os.mkdir(config.config_dictionary["thredds_replica_dir"])
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass
    except Exception, exception:
        print "Exception occurred when attempting to create the {esgcet_testdir} directory: {exception}".format(esgcet_testdir=esgcet_testdir, exception=exception)
        esg_functions.checked_done(1)

    os.chown(config.config_dictionary["thredds_replica_dir"], config.config_dictionary[
             "installer_uid"], config.config_dictionary["installer_gid"])
    print "esgcet test directory: [%s]" % esgcet_testdir

    fetch_file = "sftlf.nc"
    if esg_functions.checked_get(os.path.join(esgcet_testdir, fetch_file), "http://" + config.config_dictionary["esg_dist_url_root"] + "/externals/" + fetch_file) > 0:
        print " ERROR: Problem pulling down %s from esg distribution" % (fetch_file)
        os.chdir(starting_directory)
        esg_functions.checked_done(1)

    # Run test...
    print "%s/bin/esginitialize -c " % (config.config_dictionary["cdat_home"])
    esginitialize_output = subprocess.call(
        "%s/bin/esginitialize -c" % (config.config_dictionary["cdat_home"]), shell=True)

    '''
        esgprep mapfile --dataset ipsl.fr.test.mytest --project test /esg/data/test
 mv ipsl.fr.test.mytest.map test_mapfile.txt
    '''
    print '''
        {cdat_home}/bin/esgprep mapfile --dataset ipsl.fr.test.mytest --project test {esgcet_testdir}; mv ipsl.fr.test.mytest.map test_mapfile.txt
        '''.format(cdat_home=config.config_dictionary["cdat_home"], esg_root_id=esg_root_id, node_short_name=node_short_name, esgcet_testdir=esgcet_testdir)
    esgprep_output = subprocess.call('''
        {cdat_home}/bin/esgprep mapfile --dataset ipsl.fr.test.mytest --project test {esgcet_testdir}; mv ipsl.fr.test.mytest.map test_mapfile.txt
        '''.format(cdat_home=config.config_dictionary["cdat_home"], esg_root_id=esg_root_id, node_short_name=node_short_name, esgcet_testdir=esgcet_testdir), shell=True)
    if esgprep_output != 0:
        print " ERROR: ESG Mapfile generation failed"
        os.chdir(starting_directory)
        esg_functions.checked_done(1)

    print "{cdat_home}/bin/esgpublish --service fileservice --map test_mapfile.txt --project test --thredds".format(cdat_home=config.config_dictionary["cdat_home"])
    esgpublish_output = subprocess.call("{cdat_home}/bin/esgpublish --service fileservice --map test_mapfile.txt --project test --thredds".format(
        cdat_home=config.config_dictionary["cdat_home"]), shell=True)
    if esgpublish_output != 0:
        print " ERROR: ESG publish failed"
        os.chdir(starting_directory)
        esg_functions.checked_done(1)

    os.chdir(starting_directory)
    esg_functions.checked_done(0)

# returns 1 if it is already running (if check_postgress_process returns 0
# - true)


def start_postgress():
    if esg_functions.check_postgress_process() == 0:
        print "Postgres is already running"
        return 1
    print "Starting Postgress..."
    status = subprocess.Popen("/etc/init.d/postgresql start",
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    status_output, err = status.communicate()
    print "status_output: ", status_output
    sleep(3)
    progress_process_status = subprocess.Popen(
        "/bin/ps -elf | grep postgres | grep -v grep", shell=True)
    progress_process_status_tuple = progress_process_status.communicate()
    esg_functions.checked_done(0)

#TODO: Rename and refactor this; there is already a function in esg_bootstrap.py called self_verify()
def self_verify(installation_type):
    pass

def setup_sensible_confs():
    pass

def read_sel():
    pass

def install_local_certs():
    pass

def generate_esgf_csrs():
    pass

def generate_esgf_csrs_ext():
    pass
def cert_howto():
    pass

def test_postgress():
    pass
def test_cdat():
    pass
def test_tomcat():
    pass
def test_tds():
    pass
def set_node_type_bit(selection_string):
    pass
def show_type():
    pass
def init_structure():
    pass
def start(node_bit):
    pass
def stop(node_bit):
    pass
def get_node_status():
    ''' 
        Return a tuple with the node's status and a numeric return code
    '''
    pass
def update_script(script_name, script_directory):
    '''
        arg (1) - name of installation script root name. Ex:security which resolves to script file esg-security
        arg (2) - directory on the distribution site where script is fetched from Ex: orp
        usage: update_script security orp - looks for the script esg-security in the distriubtion directory "orp"
    '''
    pass
def update_apache_conf():
    pass
def _define_acceptable_arguments():
    #TODO: Add mutually exclusive groups to prevent long, incompatible argument lists
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", dest="install", help="Goes through the installation process and automatically starts up node services", action="store_true")
    parser.add_argument("--update", help="Updates the node manager", action="store_true")
    parser.add_argument("--upgrade", help="Upgrade the node manager", action="store_true")
    parser.add_argument("--install-local-certs", dest="installlocalcerts", help="Install local certificates", action="store_true")
    parser.add_argument("--generate-esgf-csrs", dest="generateesgfcsrs", help="Generate CSRs for a simpleCA CA certificate and/or web container certificate", action="store_true")
    parser.add_argument("--generate-esgf-csrs-ext", dest="generateesgfcsrsext", help="Generate CSRs for a node other than the one you are running", action="store_true")
    parser.add_argument("--cert-howto", dest="certhowto", help="Provides information about certificate management", action="store_true")
    parser.add_argument("--verify", "--test", dest="verify", help="Runs the test code to verify installation", action="store_true")
    parser.add_argument("--fix-perms","--fixperms", dest="fixperms", help="Fix permissions", action="store_true")
    parser.add_argument("--type", "-t", "--flavor", dest="type", help="Set type", nargs="+", choices=["data", "index", "idp", "compute", "all"])
    parser.add_argument("--set-type",  dest="settype", help="Sets the type value to be used at next start up", nargs="+", choices=["data", "index", "idp", "compute", "all"])
    parser.add_argument("--get-type", "--show-type", dest="gettype", help="Returns the last stored type code value of the last run node configuration (data=4 +| index=8 +| idp=16)", action="store_true")
    parser.add_argument("--start", help="Start the node's services", action="store_true")
    parser.add_argument("--stop", "--shutdown", dest="stop", help="Stops the node's services", action="store_true")
    parser.add_argument("--restart", help="Restarts the node's services (calls stop then start :-/)", action="store_true")
    parser.add_argument("--status", help="Status on node's services", action="store_true")
    parser.add_argument("--update-sub-installer", dest="updatesubinstaller", help="Update a specified installation script", nargs=2, metavar=('script_name', 'script_directory'))
    parser.add_argument("--update-apache-conf", dest="updateapacheconf", help="Update Apache configuration", action="store_true")
    parser.add_argument("--write-env", dest="writeenv", help="Writes the necessary environment variables to file {envfile}".format(envfile = envfile), action="store_true")
    parser.add_argument("-v","--version", dest="version", help="Displays the version of this script", action="store_true")
    parser.add_argument("--recommended_setup", dest="recommendedsetup", help="Sets esgsetup to use the recommended, minimal setup", action="store_true")
    parser.add_argument("--custom_setup", dest="customsetup", help="Sets esgsetup to use a custom, user-defined setup", action="store_true")
    parser.add_argument("--use-local-files", dest="uselocalfiles", help="Sets a flag for using local files instead of attempting to fetch a remote file", action="store_true")
    parser.add_argument("--devel", help="Sets the installation type to the devel build", action="store_true")
    parser.add_argument("--prod", help="Sets the installation type to the production build", action="store_true")
    parser.add_argument("--clear-env-state", dest="clearenvstate", help="Removes the file holding the environment state of last install", action="store_true")
    args = parser.parse_args()
    return args

def process_arguments():
    install_mode = 0
    upgrade_mode = 0

    node_type_bit = 0
    selection_string = ""

    args = _define_acceptable_arguments()

    if args.install:
        if install_mode + upgrade_mode == 0:
            upgrade_mode = 0
            install_mode = 1
            node_type_bit += get_bit_value("install")
            logger.debug("Install Services")
    if args.update or args.upgrade:
        if install_mode + upgrade_mode == 0:
            upgrade_mode = 1 
            install_mode = 0
            logger.debug("Update Services")
            self_verify("update")
    if args.fixperms:
        logger.debug("fixing permissions")
        setup_sensible_confs
        sys.exit(0)
    if args.installlocalcerts:
        logger.debug("installing local certs")
        read_sel()
        install_local_certs()
        sys.exit(0)
    if args.generateesgfcsrs:
        logger.debug("generating esgf csrs")
        read_sel()
        generate_esgf_csrs()
        sys.exit(0)
    if args.generateesgfcsrsext:
        logger.debug("generating esgf csrs for other node")
        read_sel()
        generate_esgf_csrs_ext()
        sys.exit(0)
    if args.certhowto:
        logger.debug("cert howto")
        cert_howto()
        sys.exit(0)
    elif args.verify:
        logger.debug("Verify Services")
        if node_type_bit & get_bit_value("test") == 0:
            node_type_bit += get_bit_value("test")
        logger.debug("node_type_bit = %s", node_type_bit)
        test_postgress()
        test_cdat()
        test_esgcet()
        test_tomcat()
        test_tds()
        sys.exit(0)
    elif args.type:
        logger.debug("selecting type")
        logger.debug("args.type: %s", args.type)
        for arg in args.type:
            #TODO: refactor conditional to function with descriptive name
            if node_type_bit & get_bit_value(arg) == 0:
                node_type_bit += get_bit_value(arg)
                selection_string += " "+arg
        logger.info("node type set to: [%s] (%s) ", selection_string, node_type_bit)
        sys.exit(0)
    elif args.settype:
        logger.debug("Selecting type for next start up")
        for arg in args.settype:
            #TODO: refactor conditional to function with descriptive name
            if node_type_bit & get_bit_value(arg) == 0:
                node_type_bit += get_bit_value(arg)
                selection_string += " "+arg
        if not os.path.isdir(config.esg_config_dir):
            try:
                os.mkdir(config.esg_config_dir)
            except IOError, error:
                logger.error(error)
        logger.info("node type set to: [%s] (%s) ", selection_string, node_type_bit)
        set_node_type_bit(node_type_bit)
        sys.exit(0)
    elif args.gettype:
        read_sel()
        show_type()
        sys.exit(0)
    elif args.start:
        logger.debug("args: %s", args)
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        logger.debug("START SERVICES: %s", node_type_bit)
        init_structure()
        start(node_type_bit)
        sys.exit(0)
    elif args.stop:
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        logger.debug("STOP SERVICES")
        init_structure()
        stop(node_type_bit)
        sys.exit(0)
    elif args.restart:
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        logger.debug("RESTARTING SERVICES")
        init_structure()
        stop(node_type_bit)
        sleep(2)
        start(node_type_bit)
        sys.exit(0)
    elif args.status:
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        get_node_status()
        #TODO: Exit with status code dependent on what is returned from get_node_status()
        sys.exit(0)
    elif args.updatesubinstaller:
        self_verify("update")
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        init_structure()
        update_script(args[1], args[2])
        sys.exit(0)
    elif args.updateapacheconf:
        logger.debug("checking for updated apache frontend configuration")
        update_apache_conf()
        sys.exit(0)
    elif args.writeenv:
        if node_type_bit & WRITE_ENV_BIT == 0:
            node_type_bit += WRITE_ENV_BIT
    elif args.version:
        logger.info("Version: %s", script_version)
        logger.info("Release: %s", script_release)
        logger.info("Earth Systems Grid Federation (http://esgf.llnl.gov)")
        logger.info("ESGF Node Installation Script")
        sys.exit(0)
    elif args.recommendedsetup:
        recommended_setup = 1
        custom_setup = 0
    elif args.customsetup:
        recommended_setup = 0
        custom_setup = 1
    elif args.uselocalfiles:
        use_local_files = 1
    elif args.devel:
        devel = 1
    elif args.prod:
        devel = 0
    elif args.clearenvstate:
        self_verify("clear")
        # if check_prerequisites() is not 0:
        #     logger.error("Prerequisites for startup not satisfied.  Exiting.")
        #     sys.exit(1)
        if os.path.isfile(envfile):
            shutil.move(envfile, envfile+".bak")
            #empty out contents of the file
            open(envfile, 'w').close()

class UnprivilegedUserError(Exception):
    pass

class WrongOSError(Exception):
    pass

#checking for what we expect to be on the system a-priori
#that we are not going to install or be responsible for
def check_prerequisites():
    print '''
        \033[01;31m
      EEEEEEEEEEEEEEEEEEEEEE   SSSSSSSSSSSSSSS         GGGGGGGGGGGGGFFFFFFFFFFFFFFFFFFFFFF
      E::::::::::::::::::::E SS:::::::::::::::S     GGG::::::::::::GF::::::::::::::::::::F
      E::::::::::::::::::::ES:::::SSSSSS::::::S   GG:::::::::::::::GF::::::::::::::::::::F
      EE::::::EEEEEEEEE::::ES:::::S     SSSSSSS  G:::::GGGGGGGG::::GFF::::::FFFFFFFFF::::F
        E:::::E       EEEEEES:::::S             G:::::G       GGGGGG  F:::::F       FFFFFF\033[0m
    \033[01;33m    E:::::E             S:::::S            G:::::G                F:::::F
        E::::::EEEEEEEEEE    S::::SSSS         G:::::G                F::::::FFFFFFFFFF
        E:::::::::::::::E     SS::::::SSSSS    G:::::G    GGGGGGGGGG  F:::::::::::::::F
        E:::::::::::::::E       SSS::::::::SS  G:::::G    G::::::::G  F:::::::::::::::F
        E::::::EEEEEEEEEE          SSSSSS::::S G:::::G    GGGGG::::G  F::::::FFFFFFFFFF\033[0m
    \033[01;32m    E:::::E                         S:::::SG:::::G        G::::G  F:::::F
        E:::::E       EEEEEE            S:::::S G:::::G       G::::G  F:::::F
      EE::::::EEEEEEEE:::::ESSSSSSS     S:::::S  G:::::GGGGGGGG::::GFF:::::::FF
      E::::::::::::::::::::ES::::::SSSSSS:::::S   GG:::::::::::::::GF::::::::FF
      E::::::::::::::::::::ES:::::::::::::::SS      GGG::::::GGG:::GF::::::::FF
      EEEEEEEEEEEEEEEEEEEEEE SSSSSSSSSSSSSSS           GGGGGG   GGGGFFFFFFFFFFF.llnl.gov
    \033[0m
    '''

    print "Checking that you have root privs on %s... " % (socket.gethostname())
    root_check = os.geteuid()
    if root_check != 0:
        raise UnprivilegedUserError 
    print "[OK]"

    #----------------------------------------
    print "Checking requisites... "

     # checking for OS, architecture, distribution and version

    print "Checking operating system....."
    OS = platform.system()
    MACHINE = platform.machine()
    RELEASE_VERSION = re.search("(centos|redhat)-(\S*)-", platform.platform()).groups()
    logger.debug("Release Version: %s", RELEASE_VERSION)
    if "6" not in  RELEASE_VERSION[1]:
        raise WrongOSError
    else:
        print "Operating System = {OS}".format(OS=RELEASE_VERSION[0])
        print "[OK]"


def main():
    esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
    

    logger.info("esg-node initializing...")
    try:
        logger.info(socket.getfqdn())
    except socket.error:
        logger.error("Please be sure this host has a fully qualified hostname and reponds to socket.getfdqn() command")
        sys.exit()

    # Determining if devel or master directory of the ESGF distribution mirror will be use for download of binaries
    if "devel" in script_version:
        logger.debug("Using devel version")
        install_type = "devel"
    else:
        install_type = "master"

    # Determining ESGF distribution mirror
    # logger.info("before selecting distribution mirror: %s", config.config_dictionary["esgf_dist_mirror"])
    # if any(argument in sys.argv for argument in ["install", "update", "upgrade"]):
    #     logger.debug("interactive")
    #     config.config_dictionary["esgf_dist_mirror"] = esg_functions.get_esgf_dist_mirror("interactive", install_type)
    # else:
    #     logger.debug("fastest")
    #     config.config_dictionary["esgf_dist_mirror"] = esg_functions.get_esgf_dist_mirror("fastest", install_type)

    # logger.info("selected distribution mirror: %s", config.config_dictionary["esgf_dist_mirror"])

    # # Setting esg_dist_url with previously gathered information
    # esg_dist_url_root = os.path.join("http://", config.config_dictionary["esgf_dist_mirror"], "dist")
    # logger.debug("esg_dist_url_root: %s", esg_dist_url_root)
    # if devel is True:
    #     esg_dist_url = os.path.join("http://", esg_dist_url_root, "/devel")
    # else:
    #     esg_dist_url = esg_dist_url_root

    # logger.debug("esg_dist_url: %s", esg_dist_url)
    # # Downloading esg-installarg file
    # if not os.path.isfile(config.config_dictionary["esg_installarg_file"]) or force_install or os.path.getmtime(config.config_dictionary["esg_installarg_file"]) < os.path.getmtime(os.path.realpath(__file__)):
    #     esg_installarg_file_name = esg_functions.trim_string_from_head(config.config_dictionary["esg_installarg_file"])
    #     esg_functions.checked_get(config.config_dictionary["esg_installarg_file"], os.path.join(esg_dist_url, "esgf-installer", esg_installarg_file_name), force_get=force_install)
    #     try:
    #         if not os.path.getsize(config.config_dictionary["esg_installarg_file"]) > 0:
    #             os.remove(config.config_dictionary["esg_installarg_file"])
    #         esg_functions.touch(config.config_dictionary["esg_installarg_file"])
    #     except IOError, error:
    #         logger.error(error)

    #process command line arguments
    process_arguments()
    try:
        check_prerequisites()
    except UnprivilegedUserError:
        logger.info("$([FAIL]) \n\tMust run this program with root's effective UID\n\n")
    except WrongOSError:
        logger.info("ESGF can only be installed on versions 6 of Red Hat, CentOS or Scientific Linux x86_64 systems" )

    

    # setup_esgcet()
    # test_esgcet()


if __name__ == '__main__':
    main()
