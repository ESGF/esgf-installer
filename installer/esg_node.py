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
import esg_setup
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

install_mode = 0
upgrade_mode = 0

node_type_bit = 0


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
	    esg_functions.deduplicate_settings_in_file(config.envfile)
    finally:
    	datafile.close()


def write_esgcet_install_log():
    datafile = open(config.install_manifest, "a+")
    try:
	    datafile.write(str(datetime.date.today()) + "python:esgcet=" +
	                   config.config_dictionary["esgcet_version"] + "\n")
	    esg_functions.deduplicate_settings_in_file(config.install_manifest)
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

def stop_postgress():
    if esg_setup._is_managed_db:
        print "Please be sure external database is NOT running at this point..."
        return True
    if esg_functions.check_postgress_process() == 1:
        print "Postgres already stopped"
        return True
    print "Stopping Postgres...."
    status = subprocess.Popen("/etc/init.d/postgresql stop",
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    status_output, err = status.communicate()
    print "status_output: ", status_output
    sleep(3)
    check_shmmax()
    progress_process_status = subprocess.Popen(
        "/bin/ps -elf | grep postgres | grep -v grep", shell=True)
    progress_process_status_tuple = progress_process_status.communicate()
    esg_functions.checked_done(0)

def check_shmmax(min_shmmax = 48):
    '''
       NOTE: This is another **RedHat/CentOS** specialty thing (sort of)
       arg1 - min value of shmmax in MB (see: /etc/sysctl.conf) 
    '''
    kernel_shmmax = esg_functions.get_property("kernel_shmmax", 48)
    set_value_mb = min_shmmax
    set_value_bytes = set_value_mb *1024*1024
    cur_value_bytes = subprocess.check_output("sysctl -q kernel.shmmax | tr -s '='' | cut -d= -f2", stdout=subprocess.PIPE)
    cur_value_bytes = cur_value_bytes.strip()

    if cur_value_bytes < set_value_bytes:
        print "Current system shared mem value too low [{cur_value_bytes} bytes] changing to [{set_value_bytes} bytes]".format(cur_value_bytes = cur_value_bytes, set_value_bytes = set_value_bytes)
        subprocess.call("sysctl -w kernel.shmmax=${set_value_bytes}".format(set_value_bytes = set_value_bytes))
        subprocess.call("sed -i.bak 's/\(^[^# ]*[ ]*kernel.shmmax[ ]*=[ ]*\)\(.*\)/\1'${set_value_bytes}'/g' /etc/sysctl.conf")
        esg_functions.write_as_property("kernal_shmmax", set_value_mb)


def setup_sensible_confs():
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
def show_type():
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
    return (args, parser)

def process_arguments():
    global install_mode
    global upgrade_mode

    global node_type_bit
    selection_string = ""

    args, parser = _define_acceptable_arguments()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if args.install:
        if install_mode + upgrade_mode == 0:
            upgrade_mode = 0
            install_mode = 1
            if node_type_bit & INSTALL_BIT == 0:
                node_type_bit += get_bit_value("install")
            logger.debug("Install Services")
    if args.update or args.upgrade:
        if install_mode + upgrade_mode == 0:
            upgrade_mode = 1 
            install_mode = 0
            if node_type_bit & INSTALL_BIT == 0:
                node_type_bit += get_bit_value("install")
            logger.debug("Update Services")
            self_verify("update")
    if args.fixperms:
        logger.debug("fixing permissions")
        setup_sensible_confs
        sys.exit(0)
    if args.installlocalcerts:
        logger.debug("installing local certs")
        get_previous_node_type_config()
        install_local_certs()
        sys.exit(0)
    if args.generateesgfcsrs:
        logger.debug("generating esgf csrs")
        get_previous_node_type_config()
        generate_esgf_csrs()
        sys.exit(0)
    if args.generateesgfcsrsext:
        logger.debug("generating esgf csrs for other node")
        get_previous_node_type_config()
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
        set_node_type_config(node_type_bit)
        sys.exit(0)
    elif args.gettype:
        get_previous_node_type_config()
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

class UnverifiedScriptError(Exception):
    pass

def _verify_against_remote(esg_dist_url_root):
    python_script_name = os.path.basename(__file__)
    python_script_md5_name = re.sub(r'_', "-", python_script_name)
    python_script_md5_name = re.search("\w*-\w*", python_script_md5_name)
    logger.info("python_script_name: %s", python_script_md5_name)

    remote_file_md5 = requests.get("{esg_dist_url_root}/esgf-installer/{script_maj_version}/{python_script_md5_name}.md5".format(esg_dist_url_root= esg_dist_url_root, script_maj_version= script_maj_version, python_script_md5_name= python_script_md5_name ) ).content
    remote_file_md5 = remote_file_md5.split()[0].strip()

    local_file_md5 = None

    hasher = hashlib.md5()
    with open(python_script_name, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
        local_file_md5 = hasher.hexdigest()
        print "local_file_md5: ", local_file_md5.strip()

    if local_file_md5 != remote_file_md5:
        raise UnverifiedScriptError
    else:
        print "[VERIFIED]"
        return True

#TODO: Rename and refactor this; there is already a function in esg_bootstrap.py called self_verify()
def self_verify(esg_dist_url_root, update_action = None):
    # Test to see if the esg-node script is currently being pulled from git, and if so skip verification
    if esg_functions.is_in_git(os.path.basename(__file__)) == 0:
        logger.info("Git repository detected; not checking checksum of esg-node")
        return

    if "devel" in script_version:
        devel = 0
        remote_url = "{esg_dist_url_root}/esgf-installer/{script_maj_version}".format(esg_dist_url_root = esg_dist_url_root, script_maj_version = script_maj_version)
    else:
        devel = 1
        remote_url = "{esg_dist_url_root}/devel/esgf-installer/{script_maj_version}".format(esg_dist_url_root = esg_dist_url_root, script_maj_version = script_maj_version)
    try:
        _verify_against_remote(remote_url)
    except UnverifiedScriptError:
        logger.info('''WARNING: %s could not be verified!! \n(This file, %s, may have been tampered
            with or there is a newer version posted at the distribution server.
            \nPlease update this script.)\n\n''', os.path.basename(__file__), os.path.basename(__file__))

        if update_action is None:
            update_action = raw_input("Do you wish to Update and exit [u], continue anyway [c] or simply exit [x]? [u/c/X]: ")

        if update_action in ["C".lower(), "Y".lower()]:
            print  "Continuing..."
            return
        elif update_action in ["U".lower(), "update", "--update"]:
            print "Updating local script with script from distribution server..."

            if devel == 0:
                bootstrap_path = "/usr/local/bin/esg-bootstrap"
            else:
                bootstrap_path = "/usr/local/bin/esg-bootstrap --devel"
            invoke_bootstrap = subprocess.Popen(bootstrap_path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            invoke_bootstrap.communicate()
            # if invoke_bootstrap.returncode == 0:
            #     esg_functions.checked_get()
            print "Please re-run this updated script: {current_script_name}".format(current_script_name = os.path.basename(__file__))
            sys.exit(invoke_bootstrap.returncode)
        elif update_action is "X".lower():
            print "Exiting..."
            sys.exit(1)
        else:
            print "Unknown option: {update_action} - Exiting".format(update_action = update_action)
            sys.exit(1)

    return True

def check_prerequisites():
    '''
        Checking for what we expect to be on the system a-priori that we are not going to install or be responsible for
    '''
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
        print "Operating System = {OS} {version}".format(OS=RELEASE_VERSION[0], version=RELEASE_VERSION[1])
        print "[OK]"

#TODO: Refactor this to return value vs using global variable
def get_previous_node_type_config():
    ''' 
        Helper method for reading the last state of node type config from config dir file "config_type"
        Every successful, explicit call to --type|-t gets recorded in the "config_type" file
        If the configuration type is not explicity set the value is read from this file.
    '''
    global node_type_bit
    if node_type_bit < MIN_BIT or node_type_bit > MAX_BIT:
        logger.info("node_type_bit is out of range: %s", node_type_bit)
        logger.info("Acceptable range is between %s and %s", MIN_BIT, MAX_BIT)
        try:
            last_config_type = open(config.esg_config_type_file)
            node_type_bit += int(last_config_type.readline())
            logger.debug("node_type_bit is now: %i", node_type_bit)
        except IOError, error:
            logger.error(error)

    if node_type_bit == 0:
        print '''ERROR: No node type selected nor available! \n Consult usage with --help flag... look for the \"--type\" flag 
        \n(must come BEFORE \"[start|stop|restart|update]\" args)\n\n'''
        sys.exit(1)

def set_node_type_config(node_type_bit):
    '''
            Write the node type numeric value to file
            (Yes... gratuitous error and bounds checking)
    '''
    logger.debug("new node_type_bit: %s", node_type_bit)
    hit_bits = 0

    #valididty check for type... in range power of 2
    #MIN and MAX BIT range... if so then valid and an be written down.
    if node_type_bit < MIN_BIT or node_type_bit > MAX_BIT:
        logger.debug("WARNING: Selection %s is out of range $MIN_BIT - $MAX_BIT", node_type_bit)

    #Check if the new sel has any bits turned on in the range of our type bits
    type_bit = MIN_BIT
    while type_bit <= MAX_BIT:
        if node_type_bit & type_bit != 0:
            hit_bits += type_bit
        type_bit *= 2

    logger.debug("[hit_bits = %s] =? [node_type_bit = %s]", hit_bits, node_type_bit)

    if hit_bits:
        try:
            config_type_file = open(config.esg_config_type_file, "w")
            logger.debug("Writing %s to file as new node_type_bit", hit_bits)
            config_type_file.write(str(hit_bits))
        except IOError, error:
            logger.error(error)


def esgf_node_info():

    print '''
        The goal of this script is to automate as many tasks as possible
     regarding the installation, maintenance and use of the ESGF
     software stack that is know as the \"ESGF Node\".  A software
     stack is a collection of tools that work in concert to perform a
     particular task or set of tasks that are semantically united. The
     software stack is comprised of: Tomcat, Thredds, CDAT & CDMS,
     PostgreSQL, MyProxy, and several ESGF.org custom software
     applications running on a LINUX (RedHat/CentOS) operating system.

     Through the installation process there are different accounts
     that are created that facilitate the communication between the
     software stack entities.  These credentials are internal to the
     stack.  It is recommended that you use the defaults provided
     throughout this installation.  The security impact with regards
     to the visibility and accessibility of the constituent components
     of the stack depends on other factors to be addressed by your
     organization.

     Please be sure that you have gotten your created an account on
     your ESGF IDP Peer.

     The primary IDP Peer for ESGF is pcmdi.llnl.gov
     You may register for an account at PCMDI at the following URL:
     http://pcmdi.llnl.gov/esgf-web-fe/createAccount

     Note: Account creation is prerequisite for publication!

     ESGF P2P Node:                                             ESGF P2P Node:
      ---------                                                   ---------
     |Tomcat   |                                                 |Tomcat   |
     |-Node Mgr|   <================= P2P =================>     |-Node Mgr|
     |-Thredds |                                                 |-Thredds |
     |-ORP     |                                                 |-ORP     |
     |---------|                                                 |---------|
     |CDAT/CDMS|                                                 |CDAT/CDMS|
     |---------|                                                 |---------|
     |Postgres |                                                 |Postgres |
     |---------|                                                 |---------|
     | MyProxy |  <===(HTTPS)===> [ESGF Peer Node(s)]*           | MyProxy |
     |---------|                                                 |---------|
     | GridFTP |  <=============> [End User(s)]*                 | GridFTP |
     >---------<                                                 >---------<
     | CentOS  |                                                 | CentOS  |
     |(Virtual)|                                                 |(Virtual)|
     | Machine |                                                 | Machine |
     |---------|                                                 |---------|
      ---------                                                   ---------

     (Visit http://esgf.llnl.gov , http://github.com/ESGF/esgf.github.io/wiki for more information)

                                                                                    
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
  EEEEEEEEEEEEEEEEEEEEEE SSSSSSSSSSSSSSS           GGGGGG   GGGGFFFFFFFFFFF.org
\033[0m
     -ESGF.org \n\n

    '''

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
        sys.exit(1)
    except WrongOSError:
        logger.info("ESGF can only be installed on versions 6 of Red Hat, CentOS or Scientific Linux x86_64 systems" )
        sys.exit(1)
    
    self_verify(esg_dist_url)

    logger.debug("node_type_bit: %s", node_type_bit)
    


    print  '''-----------------------------------
                ESGF Node Installation Program
            -----------------------------------'''

    logger.debug("node_type_bit & INSTALL_BIT != 0: %s", node_type_bit & INSTALL_BIT != 0)
    logger.debug("node_type_bit: %i, %s", node_type_bit, type(node_type_bit))
    logger.debug("MIN_BIT: %i, %s", MIN_BIT, type(MIN_BIT))
    logger.debug("MAX_BIT: %i", MAX_BIT)
    logger.debug("node_type_bit >= MIN_BIT: %s",  node_type_bit >= MIN_BIT)
    logger.debug("node_type_bit >= MIN_BIT and node_type_bit <= MAX_BIT: %s", node_type_bit >= MIN_BIT and node_type_bit <= MAX_BIT)

        
    get_previous_node_type_config()
    
    #TODO: Break this into a function
    #If we are doing an install - make sure a type is selected
    if node_type_bit & INSTALL_BIT != 0 and not (node_type_bit >= MIN_BIT and node_type_bit <= MAX_BIT):
        print '''
                Sorry no suitable node type has been selected
                Please run the script again with --set-type and provide any number of type values (\"data\", \"index\", \"idp\", \"compute\" [or \"all\"]) you wish to install
                (no quotes - and they can be specified in any combination or use \"all\" as a shortcut)

                Ex:  esg-node --set-type data
                esg-node install

                or do so as a single command line:

                Ex:  esg-node --type data install

                Use the --help | -h option for more information

                Note: The type value is recorded upon successfully starting the node.
                the value is used for subsequent launches so the type value does not have to be
                always specified.  A simple \"esg-node start\" will launch with the last type used
                that successfully launched.  Thus ideal for use in the boot sequence (chkconfig) scenario.
                (more documentation available at https://github.com/ESGF/esgf-installer/wiki)\n\n
              '''
        sys.exit(1)

    esgf_node_info()

    default_install_answer = "Y"
    if devel == 1:
        print "(Installing DEVELOPMENT tree...)"
    while True:
        begin_installation = raw_input("Are you ready to begin the installation? [Y/n] ") or default_install_answer
        if begin_installation.lower() == "n" or begin_installation.lower() == "no":
            print "Canceling installation"
            sys.exit(0)
        elif begin_installation.lower() == "y" or begin_installation.lower() == "yes":
            break
        else:
            print "Invalid option.  Please select a valid option [Y/n]"

    esg_setup.init_structure()

    if force_install:
        logger.info("(force install is ON)")
    if node_type_bit & DATA_BIT != 0:
        logger.info("(data node type selected)")
    if node_type_bit & INDEX_BIT != 0:
        logger.info("(index node type selected)")
    if node_type_bit & IDP_BIT != 0:
        logger.info("(idp node type selected)")
    if node_type_bit & COMPUTE_BIT != 0:
        logger.info("(compute node type selected)")

    esg_setup.initial_setup_questionnaire()
    #---------------------------------------
    #Installation of prerequisites.
    #---------------------------------------

    print '''
    *******************************
	Installing prerequisites
	******************************* 
    '''
    yum_remove_rpm_forge = subprocess.Popen(["yum", "-y", "remove", "rpmforge-release"],stdout=subprocess.PIPE)
    print "yum_remove_rpm_forge_output: ", yum_remove_rpm_forge.communicate()[0]
    print "remove_return_code: ", yum_remove_rpm_forge.returncode
    
    yum_install_epel = subprocess.Popen(["yum", "-y", "install", "epel-release"], stdout=subprocess.PIPE)
    print "yum_install_epel: ", yum_install_epel.communicate()[0]
    if yum_install_epel.returncode != 0:
        print "$([FAIL]) \n\tCould not configure epel repository\n\n"
        sys.exit(1)

    yum_install_list = ["yum", "-y", "install", "yum-plugin-priorities", "sqlite-devel", "freetype-devel", "git", "curl-devel", 
    "autoconf", "automake", "bison", "file", "flex", "gcc", "gcc-c++", 
    "gettext-devel", "libtool", "uuid-devel", "libuuid-devel", "libxml2", 
    "libxml2-devel", "libxslt", "libxslt-devel", "lsof", "make", 
    "openssl-devel", "pam-devel", "pax", "readline-devel", "tk-devel", 
    "wget", "zlib-devel", "perl-Archive-Tar", "perl-XML-Parser", 
    "libX11-devel", "libtool-ltdl-devel", "e2fsprogs-devel", "gcc-gfortran",
    "libicu-devel", "libgtextutils-devel", "httpd,"" httpd-devel", 
    "mod_ssl", "libjpeg-turbo-devel", "myproxy", '*ExtUtils*']

    yum_install_prerequisites = subprocess.Popen(yum_install_list, stdout=subprocess.PIPE)
    print "yum_install_from_list: ", yum_install_prerequisites.communicate()[0]
    if yum_install_prerequisites.returncode != 0:
        print "$([FAIL]) \n\tCould not install or update prerequisites\n\n"
        sys.exit(1)


    #---------------------------------------
    #Setup ESGF RPM repository
    #---------------------------------------    
    print '''
    *******************************
    Setting up ESGF RPM repository
    ******************************* '''

    #---------------------------------------
    #Installation of basic system components.
    # (Only when one setup in the sequence is okay can we move to the next)
    #---------------------------------------
    if node_type_bit & INSTALL_BIT !=0:
        print "Setting up Java"
        setup_java()
        setup_ant()
    # setup_esgcet()
    # test_esgcet()
    
    # yum_remove_rpm_forge_output = yum_remove_rpm_forge.communicate()

def setup_java():
    yum_install_java = subprocess.Popen(["yum", "-y", "install", "java"], stdout=subprocess.PIPE)
    print "yum_install_java: ", yum_install_java.communicate()[0]
    print "yum_install_java return code: ", yum_install_java.returncode

def setup_ant():
    yum_install_ant = subprocess.Popen(["yum", "-y", "install", "ant"], stdout=subprocess.PIPE)
    print "yum_install_ant: ", yum_install_ant.communicate()[0]
    print "yum_install_ant return code: ", yum_install_ant.returncode
if __name__ == '__main__':
    main()
