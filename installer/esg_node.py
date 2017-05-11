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
import pwd
import psycopg2
import tarfile
import urllib
import shlex
import errno
import fileinput
import xmltodict
import untangle
import filecmp
import glob
import xml.etree.ElementTree
from git import Repo
from collections import deque
from time import sleep
from OpenSSL import crypto
from lxml import etree
import esg_functions
import esg_bash2py
import esg_setup
from esg_init import EsgInit



logging.basicConfig(format = "%(levelname): %(lineno)s %(funcName)s", level=logging.DEBUG)
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
        mode = "upgrade"
    else:
        mode = "install"

    print '''
    *******************************
    Setting up ESGCET Package...(%s) [%s]
    *******************************
     ''' % (config.config_dictionary["esgcet_egg_file"], mode)

    if mode == "upgrade":
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
            logger.error("Return code was %s for %s", output, installation_command)
            esg_functions.checked_done(1)
    except Exception, exception:
        logger.error(exception)
        esg_functions.checked_done(1)

    if mode == "install":
        choice = None

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

        logger.info("%s/bin/esgsetup --config $( ((%s == 1 )) && echo '--minimal-setup' ) --rootid %s", config.config_dictionary["cdat_home"], recommended_setup, esg_root_id)

        try:
            os.mkdir(config.config_dictionary["publisher_home"])
        except OSError, exception:
            if exception.errno != 17:
                raise
            sleep(1)
            pass

        #generate esg.ini file using esgsetup script; #Makes call to esgsetup - > Setup the ESG publication configuration
        generate_esg_ini_command = '''
            {cdat_home}/bin/esgsetup --config $( (({recommended_setup} == 1 )) && echo "--minimal-setup" ) --rootid {esg_root_id}
            sed -i s/"host\.sample\.gov"/{esgf_host}/g {publisher_home}/{publisher_config} 
            sed -i s/"LASatYourHost"/LASat{node_short_name}/g {publisher_home}/{publisher_config}
            '''.format(publisher_home=config.config_dictionary["publisher_home"], publisher_config=config.config_dictionary["publisher_config"], cdat_home=config.config_dictionary["cdat_home"],
                       recommended_setup=recommended_setup, esg_root_id=esg_root_id,
                       esgf_host=esgf_host, node_short_name=node_short_name)

        esg_ini_file_process = subprocess.Popen(generate_esg_ini_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout_data, stderr_data = esg_ini_file_process.communicate()
        if esg_ini_file_process.returncode != 0:
            logger.error("ESGINI.returncode did not equal 0: %s %s", esg_ini_file_process.returncode, generate_esg_ini_command)
            raise RuntimeError("%r failed, status code %s stdout %r stderr %r" % (
                       generate_esg_ini_command, esg_ini_file_process.returncode, stdout_data, stderr_data)) 
            os.chdir(starting_directory)
            esg_functions.checked_done(1)

    logger.info("chown -R %s:%s %s", config.config_dictionary["installer_uid"], config.config_dictionary["installer_gid"], config.config_dictionary["publisher_home"])
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
        security_admin_password = f.read().strip()

    # get_property publisher_db_user ${publisher_db_user}
    publisher_db_user = None
    try:
        publisher_db_user = config.config_dictionary["publisher_db_user"]
    except KeyError:
        publisher_db_user = esg_functions.get_property("publisher_db_user")

    if mode == "install":
        #Makes call to esgsetup - > Setup the ESG publication configuration
        if DEBUG != "0":
            generate_esg_ini_command = '''
                %s/%s %s/bin/esgsetup $( ((%s == 1 )) && echo "--minimal-setup" ) 
                --db $( [ -n "%s" ] && echo "--db-name %s" ) 
                $( [ -n "%s" ] && echo "--db-admin %s" ) 
                $([ -n "${pg_sys_acct_passwd:=%s}" ] && echo "--db-admin-password %s") 
                $( [ -n "%s" ] && echo "--db-user %s" ) 
                $([ -n "%s" ] && echo "--db-user-password %s") 
                $( [ -n "%s" ] && echo "--db-host %s" ) 
                $( [ -n "%s" ] && echo "--db-port %s" )"
            '''.format(config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"], config.config_dictionary["cdat_home"], recommended_setup,
            config.config_dictionary["db_database"], config.config_dictionary["db_database"], 
            config.config_dictionary["postgress_user"], config.config_dictionary["postgress_user"], 
            security_admin_password, config.config_dictionary["pg_sys_acct_passwd"],
            publisher_db_user, publisher_db_user,
            config.config_dictionary["publisher_db_user_passwd"], config.config_dictionary["publisher_db_user_passwd"],
            config.config_dictionary["postgress_host"], config.config_dictionary["postgress_host"],
            config.config_dictionary["postgress_port"], config.config_dictionary["postgress_port"])
            logger.info("generate_esg_ini_command: %s", generate_esg_ini_command)

        else:
            esg_ini_command = generate_esg_config_file()
            print "esg_ini_command: ", esg_ini_command
            # generate_esg_ini_command = ''' 
            #         {cdat_home}/bin/esgsetup 
            #         $( (({recommended_setup} == 1 )) && echo "--minimal-setup" ) 
            #         --db $( [ -n "{db_database}" ] && echo "--db-name {db_database}" ) 
            #         $( [ -n "{postgress_user}" ] && echo "--db-admin {postgress_user}" ) 
            #         $([ -n "{pg_sys_acct_passwd}" ] && echo "--db-admin-password {pg_sys_acct_passwd}") 
            #         $( [ -n "{publisher_db_user}" ] && echo "--db-user {publisher_db_user}" ) 
            #         $([ -n "{publisher_db_user_passwd}" ] && echo "--db-user-password {publisher_db_user_passwd_stars}") 
            #         $( [ -n "{postgress_host}" ] && echo "--db-host {postgress_host}" ) 
            #         $( [ -n "{postgress_port}" ] && echo "--db-port {postgress_port}" )" 
            # '''.format(publisher_home=config.config_dictionary["publisher_home"], publisher_config=config.config_dictionary["publisher_config"], cdat_home=config.config_dictionary["cdat_home"],
            #            recommended_setup=recommended_setup, db_database=config.config_dictionary["db_database"],
            #            postgress_user=config.config_dictionary["postgress_user"],
            #            pg_sys_acct_passwd="******" if config.config_dictionary["pg_sys_acct_passwd"] else config.config_dictionary["security_admin_password"],
            #            publisher_db_user=publisher_db_user,
            #            publisher_db_user_passwd=config.config_dictionary["publisher_db_user_passwd"], publisher_db_user_passwd_stars="******",
            #            postgress_host=config.config_dictionary["postgress_host"],
            #            postgress_port=config.config_dictionary["postgress_port"])

            # generate_esg_ini_command.replace('\n', ' ')
            # logger.info("generate_esg_ini_command: %s", generate_esg_ini_command)

    try:
        esg_ini_file_process = subprocess.Popen(esg_ini_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout_data, stderr_data = esg_ini_file_process.communicate()
        if esg_ini_file_process.returncode != 0:
            logger.error("ESGINI.returncode did not equal 0: %s %s", esg_ini_file_process.returncode, esg_ini_command)
            raise RuntimeError("%r failed, status code %s stdout %r stderr %r" % (
                       esg_ini_command, esg_ini_file_process.returncode, stdout_data, stderr_data)) 

    except Exception, exception:
        print "exception occured with ESGINI: ", str(exception)
        os.chdir(starting_directory)
        esg_functions.checked_done(1)

    try:
        #Call the esginitialize script -> Initialize the ESG node database.
        esginitialize_output = subprocess.call(
            "%s/bin/esginitialize -c" % (config.config_dictionary["cdat_home"]), shell=True)
        if esginitialize_output != 0:
            logger.error("esginitialize_output: %s", esginitialize_output)
            os.chdir(starting_directory)
            esg_functions.checked_done(1)
    except Exception, exception:
        print "exception occurred with esginitialize_output: ", str(exception)

    os.chdir(starting_directory)
    write_esgcet_env()
    write_esgcet_install_log()

    esg_functions.checked_done(0)


def generate_esg_config_file():
    # get_property publisher_db_user ${publisher_db_user}
    publisher_db_user = None
    try:
        publisher_db_user = config.config_dictionary["publisher_db_user"]
    except KeyError:
        publisher_db_user = esg_functions.get_property("publisher_db_user")

    security_admin_password = None
    with open(config.esgf_secret_file, 'rb') as f:
        security_admin_password = f.read().strip()

    generate_esg_ini_command = "{cdat_home}/bin/esgsetup --db".format(cdat_home=config.config_dictionary["cdat_home"])
    if recommended_setup == 1:
        generate_esg_ini_command += " --minimal-setup"
    if config.config_dictionary["db_database"]:
        generate_esg_ini_command += " --db-name %s" % (config.config_dictionary["db_database"])
    if config.config_dictionary["postgress_user"]:
        generate_esg_ini_command += " --db-admin %s" % (config.config_dictionary["postgress_user"])

    if security_admin_password:
        generate_esg_ini_command += " --db-admin-password %s" % (security_admin_password)
    elif config.config_dictionary["pg_sys_acct_passwd"]:
        generate_esg_ini_command += " --db-admin-password %s" % (config.config_dictionary["pg_sys_acct_passwd"])

    if publisher_db_user:
        generate_esg_ini_command += " --db-user %s" % (publisher_db_user)
    if config.config_dictionary["publisher_db_user_passwd"]:
        generate_esg_ini_command += " --db-user-password %s" % (config.config_dictionary["publisher_db_user_passwd"])
    if config.config_dictionary["postgress_host"]:
        generate_esg_ini_command += " --db-host %s" % (config.config_dictionary["postgress_host"])
    if config.config_dictionary["postgress_port"]:
        generate_esg_ini_command += " --db-port %s" % (config.config_dictionary["postgress_port"])

    logger.info("generate_esg_ini_command in function: %s", generate_esg_ini_command)
    return generate_esg_ini_command

    # generate_esg_ini_command = ''' 
    #                 {cdat_home}/bin/esgsetup 
    #                 $( (({recommended_setup} == 1 )) && echo "--minimal-setup" ) 
    #                 --db $( [ -n "{db_database}" ] && echo "--db-name {db_database}" ) 
    #                 $( [ -n "{postgress_user}" ] && echo "--db-admin {postgress_user}" ) 
    #                 $([ -n "{pg_sys_acct_passwd}" ] && echo "--db-admin-password {pg_sys_acct_passwd}") 
    #                 $( [ -n "{publisher_db_user}" ] && echo "--db-user {publisher_db_user}" ) 
    #                 $([ -n "{publisher_db_user_passwd}" ] && echo "--db-user-password {publisher_db_user_passwd_stars}") 
    #                 $( [ -n "{postgress_host}" ] && echo "--db-host {postgress_host}" ) 
    #                 $( [ -n "{postgress_port}" ] && echo "--db-port {postgress_port}" )" 
    #         '''.format(publisher_home=config.config_dictionary["publisher_home"], publisher_config=config.config_dictionary["publisher_config"], cdat_home=config.config_dictionary["cdat_home"],
    #                    recommended_setup=recommended_setup, db_database=config.config_dictionary["db_database"],
    #                    postgress_user=config.config_dictionary["postgress_user"],
    #                    pg_sys_acct_passwd="******" if config.config_dictionary["pg_sys_acct_passwd"] else config.config_dictionary["security_admin_password"],
    #                    publisher_db_user=publisher_db_user,
    #                    publisher_db_user_passwd=config.config_dictionary["publisher_db_user_passwd"], publisher_db_user_passwd_stars="******",
    #                    postgress_host=config.config_dictionary["postgress_host"],
    #                    postgress_port=config.config_dictionary["postgress_port"])


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
        return True
    print "Starting Postgress..."
    for file in os.listdir("/etc/init.d/"):
        if "postgresql" in file:
            postgresql_executable_name = file
            logger.info("postgresql_executable_name: %s", postgresql_executable_name)
    postgres_start_command = shlex.split("/etc/init.d/{postgresql_executable_name} start".format(postgresql_executable_name = postgresql_executable_name))
    status = subprocess.Popen(postgres_start_command)
    status_output, err = status.communicate()
    # print "status_output: ", status_output
    logger.info("status_output: %s", status_output)
    logger.error("err: %s ", err)
    sleep(3)
    progress_process_status = subprocess.Popen(
        "/bin/ps -elf | grep postgres | grep -v grep", shell=True)
    progress_process_status_tuple = progress_process_status.communicate()
    logger.info("progress_process_status_tuple: %s", progress_process_status_tuple)
    esg_functions.checked_done(0)
    return True

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
    


    print '''
    -----------------------------------
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
    #TODO: Uncomment this; only removed for testing speedup
    # install_prerequisites()
    

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
        setup_java()
        setup_ant()
        setup_postgres()
        setup_cdat()
        logger.debug("node_type_bit & (DATA_BIT+COMPUTE_BIT) %s", node_type_bit & (DATA_BIT+COMPUTE_BIT))
        if node_type_bit & (DATA_BIT+COMPUTE_BIT) != 0:
            setup_esgcet()
        setup_tomcat()
    # setup_esgcet()
    # test_esgcet()
    
    # yum_remove_rpm_forge_output = yum_remove_rpm_forge.communicate()

def install_prerequisites():
    print '''
    *******************************
    Installing prerequisites
    ******************************* 
    '''
    yum_remove_rpm_forge = subprocess.Popen(["yum", "-y", "remove", "rpmforge-release"],stdout=subprocess.PIPE)
    stream_subprocess_output(yum_remove_rpm_forge)
    # print "yum_remove_rpm_forge_output: ", yum_remove_rpm_forge.communicate()[0]
    # print "remove_return_code: ", yum_remove_rpm_forge.returncode
    
    yum_install_epel = subprocess.Popen(["yum", "-y", "install", "epel-release"], stdout=subprocess.PIPE)
    stream_subprocess_output(yum_install_epel)
    # print "yum_install_epel: ", yum_install_epel.communicate()[0]
    # if yum_install_epel.returncode != 0:
    #     print "$([FAIL]) \n\tCould not configure epel repository\n\n"
    #     sys.exit(1)

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
    stream_subprocess_output(yum_install_prerequisites)
    # print "yum_install_from_list: ", yum_install_prerequisites.communicate()[0]
    # if yum_install_prerequisites.returncode != 0:
    #     print "$([FAIL]) \n\tCould not install or update prerequisites\n\n"
    #     sys.exit(1)


def stream_subprocess_output(subprocess_object):
    with subprocess_object.stdout:
        for line in iter(subprocess_object.stdout.readline, b''):
            print line,
    subprocess_object.wait() # wait for the subprocess to exit
    # for stdout_line in iter(subprocess_object.stdout.readline, ""):
    #     yield stdout_line 
    # subprocess_object.stdout.close()
    # return_code = subprocess_object.wait()
    # if return_code:
    #     raise subprocess.CalledProcessError(return_code, command_list)

def symlink_force(target, link_name):
    try:
        os.symlink(target, link_name)
    except OSError, e:
        if e.errno == errno.EEXIST:
            os.remove(link_name)
            os.symlink(target, link_name)
        else:
            raise e

def setup_java():
    print '''
    *******************************
    Setting up Java {java_version}
    ******************************* '''.format(java_version = config.config_dictionary["java_version"])
    if os.path.exists(os.path.join("/usr", "java", "jdk{java_version}".format(java_version = config.config_dictionary["java_version"]))):
        logger.info("Found existing Java installation.  Skipping set up.")
        return
    java_major_version = config.config_dictionary["java_version"].split(".")[1]
    java_minor_version = config.config_dictionary["java_version"].split("_")[1]
     # wget --no-check-certificate --no-cookies --header "Cookie: oraclelicense=accept-securebackup-cookie" http://download.oracle.com/otn-pub/java/jdk/8u112-b15/jdk-8u112-linux-x64.rpm
    download_oracle_java_string = 'wget --no-check-certificate --no-cookies --header "Cookie: oraclelicense=accept-securebackup-cookie" http://download.oracle.com/otn-pub/java/jdk/{java_major_version}u{java_minor_version}-b15/jdk-{java_major_version}u{java_minor_version}-linux-x64.rpm'.format(java_major_version =  java_major_version, java_minor_version = java_minor_version)
    subprocess.call(shlex.split(download_oracle_java_string))
    command_list = ["yum", "-y", "localinstall", "jdk-{java_major_version}u{java_minor_version}-linux-x64.rpm".format(java_major_version =  java_major_version, java_minor_version = java_minor_version)]
    # urllib.urlretrieve("http://download.oracle.com/otn-pub/java/jdk/8u121-b13/jdk-8u121-linux-x64.rpm", "jdk-8u121-linux-x64.rpm")
    yum_install_java = subprocess.Popen(command_list, stdout=subprocess.PIPE, universal_newlines=True, bufsize=1)
    stream_subprocess_output(yum_install_java)
    # os.symlink("/usr/java/jdk1.8.0_92/", config.config_dictionary["java_install_dir"])
    symlink_force("/usr/java/jdk{java_version}/".format(java_version = config.config_dictionary["java_version"]), config.config_dictionary["java_install_dir"])
    # print "yum_install_java: ", yum_install_java.communicate()[0]
    # print "yum_install_java return code: ", yum_install_java.returncode

def setup_ant():
    print '''
    *******************************
    Setting up Ant
    ******************************* '''
    if os.path.exists(os.path.join("/usr", "bin", "ant")):
        logger.info("Found existing Ant installation.  Skipping set up.")
        return
    command_list = ["yum", "-y", "install", "ant"]
    yum_install_ant = subprocess.Popen(command_list, stdout=subprocess.PIPE)
    stream_subprocess_output(yum_install_ant)
    # print "yum_install_ant: ", yum_install_ant.communicate()[0]
    # print "yum_install_ant return code: ", yum_install_ant.returncode

def setup_postgres():
    print '''
    *******************************
    Setting up Postgres
    ******************************* '''
    if esg_setup._is_managed_db():
        return True

    print "Checking for postgresql >= {postgress_min_version} ".format(postgress_min_version = config.config_dictionary["postgress_min_version"])
    postgres_binary_path = os.path.join(config.config_dictionary["postgress_bin_dir"], "postgres")
    logger.debug("postgres_binary_path: %s", postgres_binary_path)
    try:
        found_valid_version = esg_functions.check_for_acceptible_version(postgres_binary_path, config.config_dictionary["postgress_min_version"], version_command = "-V")
        if found_valid_version and not force_install:
            print "Valid existing Postgres installation found"
            print "[OK]"
            return True
    except OSError, error:
        logger.error(error)

    # upgrade  = None
    # if not found_valid_version:
    #     upgrade 

    #---------------------------------------
    #Setup PostgreSQL RPM repository
    #---------------------------------------

    backup_db_input = raw_input("Do you want to backup the curent database? [Y/n]") 
    if backup_db_input.lower() == "y" or backup_db_input.lower() == "yes":
        backup_db()


    yum_install_postgres = subprocess.Popen(["yum", "-y", "install", "postgresql", "postgresql-server", "postgresql-devel"], stdout=subprocess.PIPE)
    print "yum_install_postgres: ", yum_install_postgres.communicate()[0]
    print "yum_install_postgres return code: ", yum_install_postgres.returncode

    print "Restarting Database..."
    stop_postgress()
    esg_functions.checked_done(start_postgress())

    ########
    #Create the system account for postgress to run as.
    ########
    pg_sys_acct_homedir="/var/lib/pgsql"
    if not pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid:
        print " Hmmm...: There is no postgres system account user \"{pg_sys_acct}\" present on system, making one...".format(pg_sys_acct = config.config_dictionary["pg_sys_acct"])
        #NOTE: "useradd/groupadd" are a RedHat/CentOS thing... to make this cross distro compatible clean this up.
        groupadd_command = "/usr/sbin/groupadd -r %s" % (
            config.config_dictionary["pg_sys_acct_group"])
        groupadd_output = subprocess.call(groupadd_command, shell=True)
        if groupadd_output != 0 or groupadd_output != 9:
            print "ERROR: *Could not add postgres system group: %s" % (config.config_dictionary["pg_sys_acct_group"])
            esg_functions.checked_done(1)
        if not config.config_dictionary["pg_sys_acct_passwd"]:
            while True:
                pg_sys_acct_passwd_input = raw_input("Create password for postgress system account: ")
                if not pg_sys_acct_passwd_input:
                    print "Please enter a password: "
                    continue
                else:
                    config.config_dictionary["pg_sys_acct_passwd"] = pg_sys_acct_passwd_input
                    break
        print "Creating account..."
        useradd_command = '''/usr/sbin/useradd -r -c'PostgreSQL Service ESGF' 
        -d $pg_sys_acct_homedir -g $pg_sys_acct_group -p 
        $pg_sys_acct_passwd -s /bin/bash $pg_sys_acct'''.format(pg_sys_acct_homedir = pg_sys_acct_homedir,
           pg_sys_acct_group = config.config_dictionary["pg_sys_acct_group"], 
           pg_sys_acct_passwd = config.config_dictionary["pg_sys_acct_passwd"],
           pg_sys_acct = config.config_dictionary["pg_sys_acct"] )
        useradd_output = subprocess.call(useradd_command, shell=True)
        if useradd_output != 0 or useradd_output != 9:
            print "ERROR: Could not add postgres system account user"
            esg_functions.checked_done(1)
        with open(config.pg_secret_file, "w") as secret_file:
            secret_file.write(config.config_dictionary["pg_sys_acct_passwd"])

    else:
        postgress_user_shell = pwd.getpwnam(config.config_dictionary["pg_sys_acct"])[6]
        if postgress_user_shell != "/bin/bash":
            print "Noticed that the existing postgres user [{pg_sys_acct}] does not have the bash shell... Hmmm... making it so ".format(pg_sys_acct = config.config_dictionary["pg_sys_acct"])
            change_shell_command = "sed -i 's#\('{pg_sys_acct}'.*:\)\(.*\)$#\1/\bin/\bash#' /etc/passwd".format(pg_sys_acct = config.config_dictionary["pg_sys_acct"])
            subprocess.call(change_shell_command, shell=True)
            if pwd.getpwnam(config.config_dictionary["pg_sys_acct"])[6] == "/bin/bash":
                print "[OK]"
            else:
                print "[FAIL]"

    if os.path.isfile(config.pg_secret_file):
        os.chmod(config.pg_secret_file, 0640)
        os.chown(config.pg_secret_file, config.config_dictionary[
                 "installer_uid"], grp.getgrnam(
            config.config_dictionary["tomcat_group"]).gr_gid)

    sleep(3)
    #double check that the account is really there!
    if not pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid:
        print " ERROR: Problem with $pg_sys_acct creation!!!"
        esg_functions.checked_done(1) 

    os.chown(config.config_dictionary["postgress_install_dir"], pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid, 
        grp.getgrnam(config.config_dictionary["pg_sys_acct_group"]).gr_gid)


    #Create the database:
    try:
        os.mkdir(os.path.join(config.config_dictionary["postgress_install_dir"], "data"))
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass
    
    try:
        os.chown(os.path.join(config.config_dictionary["postgress_install_dir"], "data"), pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid, -1)
    except:
        print " ERROR: Could not change ownership of postgres' data to \"$pg_sys_acct\" user".format(pg_sys_acct = config.config_dictionary["pg_sys_acct"])
        esg_functions.checked_done(1)

    os.chmod(os.path.join(config.config_dictionary["postgress_install_dir"], "data"), 0700)
    initialize_db_command = 'su $pg_sys_acct -c "$postgress_bin_dir/initdb -D $postgress_install_dir/data"'
    subprocess.call(initialize_db_command, shell = True)
    try:
        os.mkdir(os.path.join(config.config_dictionary["postgress_install_dir"], "log"))
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass
    
    try:
        os.chown(os.path.join(config.config_dictionary["postgress_install_dir"], "log"), pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid, -1)
    except:
        print " ERROR: Could not change ownership of postgres' log to \"$pg_sys_acct\" user".format(pg_sys_acct = config.config_dictionary["pg_sys_acct"])

    #Start the database
    start_postgress()

    if not os.access(os.path.join(config.config_dictionary["postgress_bin_dir"], "psql"), os.X_OK):
        print " ERROR: psql not found after install!"
        esg_functions.checked_done(1) 

    #Check to see if there is a ${postgress_user} already on the system if not, make one
    try:
        conn=psycopg2.connect("dbname='postgres' user='postgres' password={pg_sys_acct_passwd}".format(pg_sys_acct_passwd = config.config_dictionary["pg_sys_acct_passwd"])) 
    except Exception, error:
        logger.error(error)
        print "I am unable to connect to the database."
        esg_functions.checked_done(1)

    cur = conn.cursor()
    cur.execute("select count(*) from pg_roles where rolname={postgress_user}".format(postgress_user = config.config_dictionary["postgress_user"]))
    rows = cur.fetchall()
    if rows[0][0] > 0:
        print "${postgress_user} exists!! :-)".format(config.config_dictionary["postgress_user"])
    else:
        while True:
            postgres_user_password = _choose_postgres_user_password()
            try:
                cur.execute("create user {postgress_user} with superuser password '{postgres_user_password}';".format(postgress_user = config.config_dictionary["postgress_user"], 
                    postgres_user_password = postgres_user_password))
                break
            except:
                print "Could not create {postgress_user} account in database".format(postgress_user = config.config_dictionary["postgress_user"])
                continue

    starting_directory = os.getcwd()
    os.chdir(os.path.join(config.config_dictionary["postgress_install_dir"], "data"))
    
    #Get files
    esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
    hba_conf_file = "pg_hba.conf"
    if esg_functions.checked_get(hba_conf_file, os.path.join(esg_dist_url,"externals", "bootstrap",hba_conf_file), force_install) > 1:
        os.chdir(starting_directory)
        esg_functions.checked_done(1)
    os.chmod(hba_conf_file, 0600)

    postgres_conf_file = "postgresql.conf"
    if esg_functions.checked_get(postgres_conf_file, os.path.join(esg_dist_url,"externals", "bootstrap",postgres_conf_file), force_install) > 1:
        os.chdir(starting_directory)
        esg_functions.checked_done(1)
    os.chmod(postgres_conf_file, 0600)


    #-----
    #NOTE: This database is an internal database to this esg
    #application stack... I don't think it would even be prudent to
    #offer then opportunity for someone to bind to the public
    #interface.  If they choose to do so after the fact, then they are
    #making that conscious decision, but I won't make it a part of
    #this process.

    #@@postgress_host@@ #Token in file...

    #local input
    #read -e -p "Please Enter the IP address or name of this host [${postgress_host}]:> " input
    #[ ! -z "${input}" ] && postgress_host=${input}
    #printf "\nUsing IP: ${postgress_host}\n"
    #eval "perl -p -i -e 's/\\@\\@postgress_host\\@\\@/${postgress_host}/g' ${fetch_file}"
    #-----

    #@@postgress_port@@ #Token in file...

    postgres_port_input = raw_input("Please Enter PostgreSQL port number [{postgress_port}]:> ".format(postgress_port = config.config_dictionary["postgress_port"])) or  config.config_dictionary["postgress_port"]
    print "\nSetting Postgress Port: {postgress_port} ".format(postgress_port = postgres_port_input)
    postgres_port_returncode = subprocess.call('''eval "perl -p -i -e 's/\\@\\@postgress_port\\@\\@/{postgress_port}/g' ${postgres_conf_file}" '''.format(postgress_port = config.config_dictionary["postgress_port"], postgres_conf_file = postgres_conf_file)) 
    if postgres_port_returncode == 0:
        print "Postgres port set: [OK]"
    else:
        print "Postgres port set: [FAIL]"

    print "Setting Postgress Log Dir: {postgress_install_dir} ".format(postgress_install_dir = config.config_dictionary["postgress_install_dir"])    
    postgres_log_dir_returncode = subprocess.call('''eval "perl -p -i -e 's/\\@\\@postgress_install_dir\\@\\@/{postgress_install_dir}/g' ${postgres_conf_file}" '''.format(postgress_install_dir = config.config_dictionary["postgress_install_dir"], postgres_conf_file = postgres_conf_file)) 
    if postgres_log_dir_returncode == 0:
        print "Postgres Log Dir set: [OK]"
    else:
        print "Postgres Log Dir set: [FAIL]"

    os.chown(config.config_dictionary["postgress_install_dir"], pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid, 
        grp.getgrnam(config.config_dictionary["pg_sys_acct_group"]).gr_gid)

    os.chdir(starting_directory)

    check_shmmax()
    write_postgress_env()
    write_postgress_install_log()
    esg_functions.checked_done(0)


def setup_cdat():
    print "Checking for *UV* CDAT (Python+CDMS) {cdat_version} ".format(cdat_version = config.config_dictionary["cdat_version"])
    try:
        sys.path.insert(0, os.path.join(config.config_dictionary["cdat_home"], "bin", "python"))
        import cdat_info
        if esg_functions.check_version_atleast(cdat_info.Version, config.config_dictionary["cdat_version"]) == 0 and not force_install:
            print "CDAT already installed [OK]"
            return True
    except ImportError, error:
        logger.error(error)

    print '''
    *******************************
    Setting up CDAT - (Python + CDMS)... ${cdat_version}
    ******************************* '''.format(cdat_version = config.config_dictionary["cdat_version"])

    if os.access(os.path.join(config.config_dictionary["cdat_home"], "bin", "uvcdat"), os.X_OK):
        print "Detected an existing CDAT installation..."
        cdat_setup_choice = raw_input("Do you want to continue with CDAT installation and setup? [y/N] ")
        if cdat_setup_choice.lower() != "y" or cdat_setup_choice.lower() != "yes":
            print "Skipping CDAT installation and setup - will assume CDAT is setup properly"
            return True

    try:
        os.makedirs(config.config_dictionary["workdir"])
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass

    starting_directory = os.getcwd()
    os.chdir(config.config_dictionary["workdir"])

    yum_install_uvcdat = subprocess.Popen(["yum", "-y", "install", "uvcdat"],stdout=subprocess.PIPE)
    print "yum_install_uvcdat_output: ", yum_install_uvcdat.communicate()[0]
    print "yum_install_return_code: ", yum_install_uvcdat.returncode
    if yum_install_uvcdat.returncode != 0:
        print "[FAIL] \n\tCould not install or update uvcdat\n\n"
        return False

    curl_output = subprocess.call("curl -k -O https://bootstrap.pypa.io/ez_setup.py", shell=True)
    setup_tools_output = subprocess.call("{cdat_home}/bin/python ez_setup.py".format(cdat_home = config.config_dictionary["cdat_home"]), shell=True)
    pip_setup_output = subprocess.call("{cdat_home}/bin/easy_install pip".format(cdat_home = config.config_dictionary["cdat_home"]), shell=True)

    os.chdir(starting_directory)

    return True

def setup_tomcat(upgrade_flag = False):
    # print "Checking for tomcat >= ${tomcat_min_version} ".format(tomcat_min_version = config.config_dictionary["tomcat_min_version"])
    # esg_functions.check_app
    print "*******************************"
    print "Setting up Apache Tomcat...(v{tomcat_version})".format(tomcat_version = config.config_dictionary["tomcat_version"])
    print "*******************************"

    last_install_directory = esg_functions.readlinkf(config.config_dictionary["tomcat_install_dir"])

    if force_install:
        default = "y"
    else:
        default = "n"

    if os.access(os.path.join(config.config_dictionary["tomcat_install_dir"], "bin", "jsvc"), os.X_OK):
        print "Detected an existing tomcat installation..."
        if default == "y":
            continue_installation_answer = raw_input( "Do you want to continue with Tomcat installation and setup? [Y/n]") or default
        else:
            continue_installation_answer = raw_input( "Do you want to continue with Tomcat installation and setup? [y/N]") or default

        if continue_installation_answer.lower() != "y" or not continue_installation_answer.lower() != "yes":
            print "Skipping tomcat installation and setup - will assume tomcat is setup properly"
            return 0


    try:
        os.makedirs(config.config_dictionary["workdir"])
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass

    starting_directory = os.getcwd()
    os.chdir(config.config_dictionary["workdir"])

    tomcat_dist_file = config.config_dictionary["tomcat_dist_url"].rsplit("/",1)[-1]
    tomcat_dist_dir = re.sub("\.tar.gz", "", tomcat_dist_file)

    #There is this pesky case of having a zero sized dist file...
    if os.path.exists(tomcat_dist_file):
        if os.stat(tomcat_dist_file).st_size == 0:
            os.remove(tomcat_dist_file)

    #Check to see if we have a tomcat distribution directory
    tomcat_parent_dir = re.search("^/\w+/\w+", config.config_dictionary["tomcat_install_dir"]).group()
    logger.info("tomcat_parent_dir: %s", tomcat_parent_dir)
    logger.info("tomcat_dist_dir: %s", tomcat_dist_dir)

    if not os.path.exists(os.path.join(tomcat_parent_dir, tomcat_dist_dir)):
        print "Don't see tomcat distribution dir {tomcat_parent_dir}/{tomcat_dist_dir}".format(tomcat_parent_dir = tomcat_parent_dir, tomcat_dist_dir =  tomcat_dist_dir)
        if not os.path.isfile(tomcat_dist_file):
            print "Don't see tomcat distribution file {pwd}/{tomcat_dist_file} either".format(pwd = os.getcwd(), tomcat_dist_file = tomcat_dist_file)
            print "Downloading Tomcat from {tomcat_dist_url}".format(tomcat_dist_url = config.config_dictionary["tomcat_dist_url"])
            # tomcat_dist_file_archive = requests.get(config.config_dictionary["tomcat_dist_url"])
            urllib.urlretrieve(config.config_dictionary["tomcat_dist_url"], tomcat_dist_file)
            # logger.info("tomcat_dist_file_archive: %s", tomcat_dist_file_archive)
            print "unpacking {tomcat_dist_file}...".format(tomcat_dist_file = tomcat_dist_file)
            tar = tarfile.open(tomcat_dist_file)
            tar.extractall(tomcat_parent_dir)
            tar.close()
            # shutil.move(tomcat_dist_file, tomcat_parent_dir)


    #If you don't see the directory but see the tar.gz distribution
    #then expand it
    if os.path.isfile(tomcat_dist_file) and not os.path.exists(os.path.join(tomcat_parent_dir, tomcat_dist_dir)):
        print "unpacking ${tomcat_dist_file}...".format(tomcat_dist_file = tomcat_dist_file)
        tar = tarfile.open(tomcat_dist_file)
        tar.extractall(tomcat_parent_dir)
        tar.close()
        # shutil.move(tomcat_dist_file, tomcat_parent_dir)

    if not os.path.exists(config.config_dictionary["tomcat_install_dir"]):
        logger.info("Did not find existing Tomcat installation directory.  Creating %s ", config.config_dictionary["tomcat_install_dir"])
        os.chdir(tomcat_parent_dir)
        try:
            os.symlink(tomcat_dist_dir, config.config_dictionary["tomcat_install_dir"])
        except OSError, error:
            logger.error(" ERROR: Could not create sym link %s/%s -> %s", tomcat_parent_dir, tomcat_dist_dir, config.config_dictionary["tomcat_install_dir"])
            logger.error(error)
        finally:
            os.chdir(config.config_dictionary["workdir"])
    else:
        logger.info("Found previous Tomcat installation directory. Creating new symlink from %s/%s -> %s", tomcat_parent_dir, tomcat_dist_dir, config.config_dictionary["tomcat_install_dir"])
        try:
            os.unlink(config.config_dictionary["tomcat_install_dir"])
        except OSError, error:
            shutil.move(config.config_dictionary["tomcat_install_dir"], config.config_dictionary["tomcat_install_dir"] + "." + str(datetime.date.today())+".bak")
        finally:
            os.chdir(tomcat_parent_dir)
            try:
                os.symlink(tomcat_dist_dir, config.config_dictionary["tomcat_install_dir"])
            except OSError, error:
                logger.error(" ERROR: Could not create sym link %s/%s -> %s", tomcat_parent_dir, tomcat_dist_dir, config.config_dictionary["tomcat_install_dir"])
                logger.error(error)
            finally:
                os.chdir(config.config_dictionary["workdir"])

    #If there is no tomcat user on the system create one (double check that usradd does the right thing)
    if not pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_uid:
        logger.info(" WARNING: There is no tomcat user \"%s\" present on system", config.config_dictionary["tomcat_user"])
        #NOTE: "useradd/groupadd" are a RedHat/CentOS thing... to make this cross distro compatible clean this up.
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

        useradd_command = '''/usr/sbin/useradd -r -c'Tomcat Server Identity' -g {tomcat_group} {tomcat_user} '''.format(tomcat_group = config.config_dictionary["tomcat_group"], tomcat_user = config.config_dictionary["tomcat_user"])
        useradd_output = subprocess.call(useradd_command, shell=True)
        if useradd_output != 0 or useradd_output != 9:
            print "ERROR: Could not add tomcat system account user {tomcat_user}".format(tomcat_user = config.config_dictionary["tomcat_user"])
            os.chdir(starting_directory)
            esg_functions.checked_done(1)

    try:
        os.chdir(config.config_dictionary["tomcat_install_dir"])
        logger.debug("Changed directory to %s", os.getcwd())
    except OSError, error:
        logger.error(error)

    #----------
    #build jsvc (if necessary)
    #----------
    print "Checking for jsvc... "
    try:
        os.chdir("bin")
        logger.debug("Changed directory to %s", os.getcwd())
    except OSError, error:
        logger.error(error)

    #https://issues.apache.org/jira/browse/DAEMON-246
    try:
        os.environ["LD_LIBRARY_PATH"]=os.environ["LD_LIBRARY_PATH"] + ":/lib" + config.config_dictionary["word_size"]
    except KeyError, error:
        logger.error(error)

    if os.access(os.path.join("./", "jsvc"), os.X_OK):
        print "Found jsvc; no need to build"
        print "[OK]"
    else:
        print "jsvc Not Found"
        esg_functions.stop_tomcat()
        print "Building jsvc... (JAVA_HOME={java_install_dir})".format(java_install_dir = config.config_dictionary["java_install_dir"])

        if os.path.isfile("commons-daemon-native.tar.gz"):
            print "unpacking commons-daemon-native.tar.gz..."
            tar = tarfile.open("commons-daemon-native.tar.gz")
            tar.extractall()
            tar.close()
            try:
                os.chdir("commons-daemon-1.0.15-native-src")
                #It turns out they shipped with a conflicting .o file in there (oops) so I have to remove it manually.
                logger.debug("Changed directory to %s", os.getcwd())
                os.remove("./native/libservice.a")
            except OSError, error:
                logger.error(error)
            subprocess.call(shlex.split("make clean"))
        elif os.path.isfile("jsvc.tar.gz "):
            print "unpacking jsvc.tar.gz..."
            tar = tarfile.open("jsvc.tar.gz")
            tar.extractall()
            tar.close()
            try:
                os.chdir("jsvc-src")
                logger.debug("Changed directory to %s", os.getcwd())
            except OSError, error:
                logger.error(error)
            subprocess.call("autoconf")
        else:
            print "NOT ABLE TO INSTALL JSVC!"
            esg_functions.checked_done(1)

    tomcat_configure_script_path = os.path.join(os.getcwd(), "unix", "configure")
    logger.info("tomcat_configure_script_path: %s", tomcat_configure_script_path)
    try:
        os.chmod(tomcat_configure_script_path, 0755)
    except OSError, error:
        logger.error(error)
        logger.error("Check if /usr/local/tomcat/configure script exists or if it is symlinked.")
        sys.exit(1)
    configure_string = "{configure} --with-java={java_install_dir}".format(configure = tomcat_configure_script_path, java_install_dir = config.config_dictionary["java_install_dir"])
    subprocess.call(shlex.split(configure_string))
    subprocess.call(shlex.split(" make -j {number_of_cpus}".format(number_of_cpus = config.config_dictionary["number_of_cpus"])))

    if not os.path.isfile("/usr/lib/libcap.so") and os.path.isfile("/lib{word_size}/libcap.so".format(word_size = config.config_dictionary["word_size"])):
        os.symlink("/lib{word_size}/libcap.so".format(word_size = config.config_dictionary["word_size"]), "/usr/lib/libcap.so")

    os.chdir(config.config_dictionary["tomcat_install_dir"])

    #----------------------------------
    # Upgrade logic...
    #----------------------------------
    if upgrade_flag:
        esg_functions.stop_tomcat()
        previous_tomcat_version = re.search("tomcat-(\S+)", esg_functions.readlinkf(last_install_directory))
        new_tomcat_version = re.search("tomcat-(\S+)", esg_functions.readlinkf(config.config_dictionary["tomcat_install_dir"]))
        print "Upgrading tomcat installation from {previous_tomcat_version} to {new_tomcat_version}".format(previous_tomcat_version = previous_tomcat_version, new_tomcat_version = new_tomcat_version)

        print "copying webapps... "
        src_files = os.listdir(os.path.join(last_install_directory, "webapps"))
        for file_name in src_files:
            full_file_name = os.path.join(last_install_directory, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, config.config_dictionary["tomcat_install_dir"])

        print "copying configuration... "
        src_files = os.listdir(os.path.join(last_install_directory, "conf"))
        for file_name in src_files:
            full_file_name = os.path.join(last_install_directory, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, config.config_dictionary["tomcat_install_dir"])

        print "copying logs... "
        src_files = os.listdir(os.path.join(last_install_directory, "logs"))
        for file_name in src_files:
            full_file_name = os.path.join(last_install_directory, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, config.config_dictionary["tomcat_install_dir"])

        print "upgrade migration complete"
    else:
        try:
            if os.stat(config.ks_secret_file).st_size != 0:
                with open(config.ks_secret_file, 'rb') as f:
                    keystore_password = f.read().strip()
                configure_tomcat(keystore_password, esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist")
        except OSError, error:
            logger.error(error)
            logger.info("Attempting to get configure Tomcat with the security_admin_password")
            with open(config.esgf_secret_file, 'rb') as f:
                security_admin_password = f.read().strip()
            configure_tomcat(security_admin_password, esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist")
    try:
        os.chown(esg_functions.readlinkf(config.config_dictionary["tomcat_install_dir"]), pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_uid, grp.getgrnam(
            config.config_dictionary["tomcat_group"]).gr_gid)
    except Exception, error:
        print "**WARNING**: Could not change owner/group of {tomcat_install_dir} successfully".format(tomcat_install_dir = esg_functions.readlinkf(config.config_dictionary["tomcat_install_dir"]))
        logger.error(error)
             
    #-------------------------------
    # For Security Reasons...
    #-------------------------------
    os.chdir(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps"))
    print "Checking for unnecessary webapps with dubious security implications as a precaution..."
    obsolete_directory_list =["examples", "docs",  "host-manager", "manager"]
    for directory in obsolete_directory_list:
        if not os.path.exists(directory):
            continue
        directory_full_path = esg_functions.readlinkf(directory)
        print "Removing {directory_full_path}".format(directory_full_path = directory_full_path)
        try:
            shutil.rmtree(directory_full_path)
            print "{directory_full_path} successfully deleted [OK]".format(directory_full_path = directory_full_path)
        except Exception, error:
            print "[FAIL]"
            logger.error(error)

    os.chdir(config.config_dictionary["tomcat_install_dir"])

    setup_root_app()

    esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
    esg_functions.checked_get(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps","ROOT","robots.txt"), "{esg_dist_url}/robots.txt".format(esg_dist_url = esg_dist_url))
    esg_functions.checked_get(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps","ROOT","favicon.ico"), "{esg_dist_url}/favicon.ico".format(esg_dist_url = esg_dist_url))

    migrate_tomcat_credentials_to_esgf(keystore_password, esg_dist_url)
    sleep(1)
    esg_functions.start_tomcat()

    if tomcat_port_check():
        print "Tomcat ports checkout [OK]"
    else:
        print "[FAIL]"
        os.chdir(starting_directory)
        esg_functions.checked_done(1)


    os.chdir(starting_directory)
    write_tomcat_env()
    write_tomcat_install_log()

    return True

def configure_tomcat(keystore_password, esg_dist_url):
    #----------------------------
    # TOMCAT Configuration...
    #----------------------------

    print "*******************************"
    print "Configuring Tomcat... (for Node Manager)"
    print "*******************************"

    starting_directory = os.getcwd()
    os.chdir(os.path.join(config.config_dictionary["tomcat_install_dir"], "conf"))

    fetch_file_name = "server.xml"
    fetch_file_path = os.path.join(config.config_dictionary["tomcat_install_dir"], "conf", fetch_file_name)

    if esg_functions.checked_get(fetch_file_path, "{esg_dist_url}/externals/bootstrap/node.{fetch_file_name}-v{tomcat_version}".format(esg_dist_url = esg_dist_url, fetch_file_name = fetch_file_name, tomcat_version = esg_functions.trim_string_from_tail(config.config_dictionary["tomcat_version"]))) != 0:
        os.chdir(starting_directory)
        esg_functions.checked_done(1)

    os.chmod(fetch_file_path, 0600)
    os.chown(fetch_file_path, pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_uid, grp.getgrnam(config.config_dictionary["tomcat_group"]).gr_gid)

    print "Looking for keystore [${keystore_file}]...".format(keystore_file = config.config_dictionary["keystore_file"])
    if os.path.isfile(config.config_dictionary["keystore_file"]):
        print "Found keystore file"
    else:
        print "Could not find keystore file"

    #Create a keystore in $tomcat_conf_dir
    print "Keystore setup: "

    if not keystore_password:
        with open(config.ks_secret_file, 'rb') as f:
            keystore_password = f.read().strip()

    if not os.path.isfile(config.config_dictionary["keystore_file"]):
        print "Launching Java's keytool:"

        if not len(keystore_password) > 0:
            verify_password = None
            while True:
                keystore_password_input = raw_input("Please enter the password for this keystore   : ")
                if not keystore_password_input:
                    print "Invalid password"
                    continue

                keystore_password_input_confirmation = raw_input("Please re-enter the password for this keystore: ")
                if keystore_password_input == keystore_password_input_confirmation:
                    keystore_password = keystore_password_input
                    break
                else:
                    print "Sorry, values did not match. Please try again."
                    continue


        #NOTE:
        #As Reference on Distingueshed Names (DNs)
        #http://download.oracle.com/javase/1.4.2/docs/tooldocs/windows/keytool.html
        #According to that document, case does not matter but ORDER DOES!
        #See script scope declaration of this variable (default_dname [suffix] = "OU=ESGF.ORG, O=ESGF")

        use_distinguished_name = "Y"
        try:
            distinguished_name    
        except NameError:
            distinguished_name = config.config_dictionary["default_distinguished_name"]

        distringuished_name_input = raw_input("Would you like to use the DN: [{distinguished_name}]?  [Y/n]".format(distinguished_name = distinguished_name))

        if distringuished_name_input.lower in ("n", "no", "y", "yes"):
            use_distinguished_name = distringuished_name_input

        logger.debug("Your selection is %s", distringuished_name_input)
        logger.debug("distinguished_name = %s", distinguished_name)

        if not distinguished_name or use_distinguished_name.lower == "n":
            java_keytool_command = "{java_install_dir}/bin/keytool -genkey -alias ${keystore_alias} -keyalg RSA \
            -keystore ${keystore_file} \
            -validity 365 -storepass ${keystore_password}".format(java_install_dir = config.config_dictionary["java_install_dir"], 
                keystore_alias = config.config_dictionary["keystore_alias"], keystore_file =config.config_dictionary["keystore_file"], keystore_password = keystore_password)
            keytool_return_code = subprocess.call(shlex.split(java_keytool_command))
            if keytool_return_code != 0:
                print " ERROR: keytool genkey command failed" 
                os.chdir(starting_directory)
            esg_functions.checked_done(1)
        else:
            # distringuished_name_sed_output = subprocess.check_output("echo {distinguished_name} | sed -n 's#.*CN=\([^,]*\),.*#\1#p'".format(distinguished_name = distinguished_name))
            if re.search("(CN=)(\S+)(,)", distinguished_name).group(2):
                try:
                    esgf_host = config.config_dictionary["esgf_host"]
                except KeyError:
                    esgf_host = socket.getfqdn()
                distinguished_name = "CN={esgf_host}, {distinguished_name}".format(esgf_host = esgf_host, distinguished_name = distinguished_name)
                print "Using keystore DN = ${distinguished_name}".format(distinguished_name = distinguished_name)
                java_keytool_command = '{java_install_dir}/bin/keytool -genkey -dname "{distinguished_name}" -alias \
                {keystore_alias} -keyalg RSA -keystore {keystore_file} -validity 365 \
                -storepass {store_password} -keypass {store_password}'.format(java_install_dir = config.config_dictionary["java_install_dir"], 
                keystore_alias = config.config_dictionary["keystore_alias"], keystore_file = config.config_dictionary["keystore_file"], keystore_password = keystore_password)
                keytool_return_code = subprocess.call(shlex.split(java_keytool_command))
                if keytool_return_code != 0:
                    print " ERROR: keytool genkey command failed" 
                    os.chdir(starting_directory)
                esg_functions.checked_done(1)
    else:
        print "Using existing keystore \"{keystore_file}\"".format(keystore_file =config.config_dictionary["keystore_file"])

    setup_temp_ca()
    #Fetch/Copy truststore to $tomcat_conf_dir
    #(first try getting it from distribution server otherwise copy Java's)
    if not os.path.isfile(config.config_dictionary["truststore_file"]):
        # i.e. esg-truststore.ts
        truststore_file_name = esg_functions.trim_string_from_tail(config.config_dictionary["truststore_file"])
        if esg_functions.checked_get(truststore_file_name, "http://{esg_dist_url_root}/certs/${fetch_file_name}".format(esg_dist_url_root = config.config_dictionary["esg_dist_url_root"], fetch_file_name = fetch_file_name)) > 1:
            print " INFO: Could not download certificates ${fetch_file_name} for tomcat - will copy local java certificate file".format(fetch_file_name = fetch_file_name)
            print "(note - the truststore password will probably not match!)"
            try:
                shutil.copyfile(os.path.join(config.config_dictionary["java_install_dir"], "jre", "lib", "security", "cacerts"), config.config_dictionary["truststore_file"])
            except Exception, error:
                print " ERROR: Could not fetch or copy {fetch_file_name} for tomcat!!".format(fetch_file_name = fetch_file_name)
                logger.error(error)

    #NOTE: The truststore uses the java default password: "changeit"
    #Edit the server.xml file to contain proper location of certificates
    logger.debug("Editing %s/conf/server.xml accordingly...", config.config_dictionary["tomcat_install_dir"])
    edit_tomcat_server_xml(keystore_password)


    add_my_cert_to_truststore("--keystore-pass",keystore_password)

    try:
        os.chown(esg_functions.readlinkf(config.config_dictionary["tomcat_install_dir"]), pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_uid, grp.getgrnam(
            config.config_dictionary["tomcat_group"]).gr_gid)
    except Exception, error:
        print "**WARNING**: Could not change owner/group of {tomcat_install_dir} successfully".format(tomcat_install_dir = esg_functions.readlinkf(config.config_dictionary["tomcat_install_dir"]))
        logger.error(error)
        esg_functions.checked_done(1)

    try:
        os.chown(esg_functions.readlinkf(config.config_dictionary["tomcat_conf_dir"]), pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_uid, grp.getgrnam(
            config.config_dictionary["tomcat_group"]).gr_gid)
    except Exception, error:
        print "**WARNING**: Could not change owner/group of {tomcat_conf_dir} successfully".format(tomcat_conf_dir = esg_functions.readlinkf(config.config_dictionary["tomcat_conf_dir"]))
        logger.error(error)
        esg_functions.checked_done(1)

    os.chdir(starting_directory)


def edit_tomcat_server_xml(keystore_password):
    server_xml_path = os.path.join(config.config_dictionary["tomcat_install_dir"],"conf", "server.xml")
    tree = etree.parse(server_xml_path)
    root = tree.getroot()
    logger.info("root: %s", etree.tostring(root))

    # et = xml.etree.ElementTree.parse(server_xml_path)
    # root = et.getroot()
    pathname = root.find(".//Resource[@pathname]")
    logger.info("pathname: %s", etree.tostring(pathname))
    pathname.set('pathname', config.config_dictionary["tomcat_users_file"])
    logger.info("pathname: %s",etree.tostring(root.find(".//Resource[@pathname]")))
    connector_element = root.find(".//Connector[@truststoreFile]")
    connector_element.set('truststoreFile', config.config_dictionary["truststore_file"])
    connector_element.set('truststorePass', config.config_dictionary["truststore_password"])
    connector_element.set('keystoreFile', config.config_dictionary["keystore_file"])
    connector_element.set('keystorePass', keystore_password)
    connector_element.set('keyAlias', config.config_dictionary["keystore_alias"])
    logger.info("connector_element: %s",etree.tostring(connector_element))
    tree.write(open(server_xml_path, "wb"), pretty_print = True)
    tree.write(os.path.join(config.config_dictionary["tomcat_install_dir"],"conf", "test_output.xml"), pretty_print = True)


def add_my_cert_to_truststore(action, value):
    '''
        This takes our certificate from the keystore and adds it to the
        truststore.  This is done for other services that use originating
        from this server talking to another service on this same host.  This
        is the interaction scenario with part of the ORP security mechanism.
        The param here is the password of the *keystore*  <----Stale comment; doesn't match functionality
    '''
    _glean_keystore_info()

    #TODO: refactor to better name
    local_keystore_file = config.config_dictionary["keystore_file"]
    local_keystore_password = config.config_dictionary["keystore_password"]
    local_keystore_alias = config.config_dictionary["keystore_alias"]
    local_truststore_file = config.config_dictionary["truststore_file"]
    local_truststore_password = config.config_dictionary["truststore_password"]
    check_private_keystore_flag = True

    if action in ["--keystore", "-ks"]:
        local_keystore_file = value
        logger.debug("keystore_file: %s", local_keystore_file)
    elif action in ["--keystore-pass", "-kpass"]:
        local_keystore_password = value
        logger.debug("keystore_pass_value: %s", local_keystore_password)
    elif action in ["alias", "-a"]:
        local_keystore_password = value
        logger.debug("key_alias_value: %s", local_keystore_password)
    elif action in ["--truststore", "-ts"]:
        local_truststore_file = value
        logger.debug("truststore_file_value: %s", local_truststore_file)
    elif action in ["--truststore-pass", "-tpass"]:
        local_truststore_file = value
        logger.debug("truststore_pass_value: %s", local_truststore_file)
    elif action in ["--no-check"]:
        check_private_keystore_flag = False
    else:
        logger.error("Invalid action given: %s", action)
        return False

    logger.debug("keystore_file: %s", local_keystore_file)
    logger.debug("keystore_pass_value: %s", local_keystore_password)
    logger.debug("key_alias_value: %s", local_keystore_alias)
    logger.debug("truststore_file_value: %s", local_truststore_file)
    logger.debug("truststore_pass_value: %s", local_truststore_password)
    logger.debug("check_private_keystore_flag: %s", check_private_keystore_flag)

    try:
        with open(config.ks_secret_file, 'rb') as f:
            keystore_password_in_file = f.read().strip()
    except IOError, error:
        logger.error(error)
        keystore_password_in_file = None

    if keystore_password_in_file != local_keystore_file:
        while True:
            store_password_input = raw_input("Please enter the password for this keystore   : ")
            if store_password_input == "changeit":
                break
            if not store_password_input:
                print "Invalid password [{store_password_input}]".format(store_password_input = store_password_input)
                continue
            store_password_input_confirmation = raw_input("Please re-enter the password for this keystore: ")
            if store_password_input == store_password_input_confirmation:
                java_keytool_command = "{java_install_dir}/bin/keytool -list -keystore {local_keystore_file} \
                -storepass {local_keystore_password}".format(java_install_dir = config.config_dictionary["java_install_dir"],
                local_keystore_file = local_keystore_file.strip(), local_keystore_password = local_keystore_password)
                logger.debug("java_keytool_command: %s", java_keytool_command)
                keytool_return_code = subprocess.call(shlex.split(java_keytool_command))
                if keytool_return_code != 0:
                    print "([FAIL]) Could not access private keystore {local_keystore_file} with provided password. Try again...".format(local_keystore_file = local_keystore_file)
                    continue
                local_keystore_password = store_password_input
                break
            else:
                print "Sorry, values did not match"

    if check_private_keystore_flag:
        #only making this call to test password
        java_keytool_command = "{java_install_dir}/bin/keytool -v -list -keystore {local_keystore_file} \
        -storepass {local_keystore_password}".format(java_install_dir = config.config_dictionary["java_install_dir"],
        local_keystore_file = local_keystore_file.strip(), local_keystore_password = local_keystore_password)
        logger.debug("java_keytool_command: %s", java_keytool_command)
        keytool_return_code = subprocess.call(shlex.split(java_keytool_command))
        if keytool_return_code != 0:
            print "([FAIL]) Could not access private keystore {local_keystore_file} with provided password. (re-run --add-my-cert-to-truststore)".format(local_keystore_file = local_keystore_file)
            return False
        else:
            logger.info("[OK]")

        logger.debug("Peforming checks against configured values...")
        keystore_password_hasher = hashlib.md5()
        keystore_password_hasher.update(config.config_dictionary["keystore_password"])
        keystore_password_md5 = keystore_password_hasher.hexdigest()

        local_keystore_password_hasher = hashlib.md5()
        local_keystore_password_hasher.update(local_keystore_password)
        local_keystore_password_md5 = local_keystore_password_hasher.hexdigest()
        logger.debug(keystore_password_md5 == local_keystore_password_md5)

        if config.config_dictionary["keystore_password"] != local_keystore_password:
            logger.info("\nWARNING: password entered does not match what's in the app server's configuration file\n")
            # Update server.xml
            server_xml_object = untangle.parse(os.path.join(config.config_dictionary["tomcat_install_dir"], "conf", "server.xml"))
            server_xml_object.Server.Connector[1]["keystorePass"] = local_keystore_password
            print "  Adjusted app server's config file... "
            config.config_dictionary["keystore_password"] = server_xml_object.Server.Connector[1]["keystorePass"]
            if config.config_dictionary["keystore_password"] != local_keystore_password:
                logger.info("[OK]")
            else:
                logger.error("[FAIL]")

    #----------------------------------------------------------------
    #Re-integrate my public key (I mean, my "certificate") from my keystore into the truststore (the place housing all public keys I allow to talk to me)
    #----------------------------------------------------------------
    if os.path.exists(local_truststore_file):
        print "Re-Integrating keystore's certificate into truststore.... "
        print "Extracting keystore's certificate... "
        java_keytool_command = "{java_install_dir}/bin/keytool -export -alias {local_keystore_alias}  -file {local_keystore_file}.cer -keystore {local_keystore_file} \
-storepass {local_keystore_password}".format(java_install_dir = config.config_dictionary["java_install_dir"],
        local_keystore_file = local_keystore_file, local_keystore_password = local_keystore_password, local_keystore_alias =  local_keystore_alias)
        logger.debug("java_keytool_command: %s", java_keytool_command)
        keytool_return_code = subprocess.call(shlex.split(java_keytool_command))
        if keytool_return_code == 0:
            logger.info("[OK]")
        else:
            logger.error("[FAIL]")
            sys.exit(1)

    java_keytool_command = "{java_install_dir}/bin/keytool -v -list -keystore {local_truststore_file} \
        -storepass {local_truststore_password}".format(java_install_dir = config.config_dictionary["java_install_dir"],
        local_truststore_file = local_truststore_file, local_truststore_password = local_truststore_password)
    grep_for_alias_commmand = "egrep -i '^Alias[ ]+name:[ ]+'{local_keystore_alias}'$'".format(local_keystore_alias = local_keystore_alias)
    keytool_subprocess = subprocess.Popen(shlex.split(java_keytool_command), stdout = subprocess.PIPE)
    grep_for_alias_subprocess = subprocess.Popen(shlex.split(grep_for_alias_commmand), stdin = keytool_subprocess.stdout, stdout = subprocess.PIPE)

    # Allow proc1 to receive a SIGPIPE if proc2 exits.
    keytool_subprocess.stdout.close()
    stdout_processes, stderr_processes = grep_for_alias_subprocess.communicate() 
    logger.info("stdout_processes: %s", stdout_processes)
    logger.info("stderr_processes: %s", stderr_processes)
    logger.info("grep_for_alias_subprocess.returncode: %s", grep_for_alias_subprocess.returncode)

    if grep_for_alias_subprocess.returncode == 0:
        print "Detected Alias \"{local_keystore_alias}\" Present... Removing... Making space for certificate... ".format(local_keystore_alias = local_keystore_alias)
        delete_keytool_alias_command = "{java_install_dir}/bin/keytool -delete -alias {local_keystore_alias} -keystore {local_truststore_file} \
        -storepass {local_truststore_password}".format(java_install_dir = config.config_dictionary["java_install_dir"],
        local_truststore_file = local_truststore_file, local_truststore_password = local_truststore_password, local_keystore_alias =  local_keystore_alias)
        delete_keytool_alias_return_code = subprocess.call(shlex.split(delete_keytool_alias_command))
        if delete_keytool_alias_return_code != 1:
            logger.error(" ERROR: problem deleting %s key from keystore!", local_keystore_alias)
            return False

    print "Importing keystore's certificate into truststore... "
    import_keystore_cert_command = "{java_install_dir}/bin/keytool -import -v -trustcacerts -alias {local_keystore_alias} -keypass {local_keystore_password} -file {local_keystore_file}.cer -keystore {local_truststore_file} \
        -storepass {local_truststore_password} -noprompt".format(java_install_dir = config.config_dictionary["java_install_dir"], local_keystore_alias = local_keystore_alias, 
        local_keystore_password = local_keystore_password, local_keystore_file = local_keystore_file,
        local_truststore_file = local_truststore_file, local_truststore_password = local_truststore_password)
    import_keystore_cert_return_code = subprocess.call(shlex.split(import_keystore_cert_command))
    if import_keystore_cert_return_code == 0:
        logger.info("[OK]")
    else:
        logger.error("[FAIL]")
        sys.exit(1)
    sync_with_java_truststore(local_truststore_file)
    print "cleaning up after ourselves... "
    try:
        os.remove(local_keystore_file+".cer")
    except Exception, error:
        logger.error("[FAIL]: %s", error)

    os.chown(local_truststore_file, pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_uid, grp.getgrnam(
            config.config_dictionary["tomcat_group"]).gr_gid)


    return True



    # def _define_acceptable_arguments():
    #TODO: Add mutually exclusive groups to prevent long, incompatible argument lists
    # truststore_arg_parser = argparse.ArgumentParser()
    # truststore_arg_parser.add_argument("--keystore", "-ks" dest="keystore", help="Goes through the installation process and automatically starts up node services", action="store_true")
    # truststore_arg_parser.add_argument("--keystore-pass", "-kpass", dest= "keystorepass" help="Updates the node manager", action="store_true")
    # truststore_arg_parser.add_argument("--alias", "-a", dest="alias" help="Upgrade the node manager", action="store_true")
    # truststore_arg_parser.add_argument("--truststore", "-ts", dest="truststore", help="Install local certificates", action="store_true")
    # truststore_arg_parser.add_argument("--truststore-pass", "-tpass", dest="truststorepass", help="Install local certificates", action="store_true")
    # truststore_arg_parser.add_argument("--no-check", dest="nocheck", help="Install local certificates", action="store_true")


def sync_with_java_truststore(external_truststore = config.config_dictionary["truststore_file"]):
    if not os.path.exists(os.path.join(os.environ["JAVA_HOME"], "jre", "lib", "security", "jssecacerts")) and os.path.exists(os.path.join(os.environ["JAVA_HOME"], "jre", "lib", "security", "cacerts")):
        shutil.copyfile(os.path.join(os.environ["JAVA_HOME"], "jre", "lib", "security", "cacerts"), os.path.join(os.environ["JAVA_HOME"], "jre", "lib", "security", "jssecacerts"))

    java_truststore = os.path.join(os.environ["JAVA_HOME"], "jre", "lib", "security", "jssecacerts")
    print "Syncing {external_truststore} with {java_truststore} ... ".format(external_truststore = external_truststore, java_truststore = java_truststore)
    if not os.path.exists(external_truststore):
        logger.error("[FAIL]: Cannot locate %s", external_truststore)
        return False

    if filecmp.cmp(external_truststore, java_truststore):
        logger.info("Files are equivalent: [OK]")
        return True
    if os.path.exists(java_truststore):
        shutil.copyfile(java_truststore, java_truststore+".bak")
    shutil.copyfile(external_truststore, java_truststore)
    os.chmod(java_truststore, 0644)
    os.chown(java_truststore, config.config_dictionary["installer_uid"], config.config_dictionary["installer_gid"])


def _glean_keystore_info():
    '''
        Util "private" function for use **AFTER** tomcat has been configured!!!!
        Reads tomcat's server.xml file at sets the appropriate vars based on contained values
        Will *only* set global vars if it was successfully gleaned from server.xml.
    '''
    if os.access(os.path.join(config.config_dictionary["tomcat_install_dir"], "conf", "server.xml"), os.R_OK):
        logger.debug("inspecting tomcat config file ")

        server_xml_object = etree.parse(os.path.join(config.config_dictionary["tomcat_install_dir"], "conf", "server.xml"))
        root = server_xml_object.getroot()
        connector_element = root.find(".//Connector[@truststoreFile]")

        logger.info("keystoreFile: %s", connector_element.get('keystoreFile'))
        config.config_dictionary["keystore_file"] = connector_element.get('keystoreFile')
        logger.debug("keystore_file_value: %s", config.config_dictionary["keystore_file"])

        config.config_dictionary["keystore_password"] = connector_element.get('keystorePass')
        logger.debug("keystore_pass_value: %s", config.config_dictionary["keystore_password"])

        config.config_dictionary["keystore_alias"] = connector_element.get('keyAlias')
        logger.debug("key_alias_value: %s", config.config_dictionary["keystore_alias"])

        config.config_dictionary["truststore_file"] = connector_element.get('truststoreFile')
        logger.debug("truststore_file_value: %s", config.config_dictionary["truststore_file"])

        config.config_dictionary["truststore_password"] = connector_element.get('truststorePass')
        logger.debug("truststore_pass_value: %s", config.config_dictionary["truststore_password"])

        return True
    else:
        print "Could not glean values store... :-("
        return False


def setup_temp_ca():
    try:
        esgf_host = config.config_dictionary["esgf_host"]
    except KeyError:
        esgf_host = esg_functions.get_property("esgf_host")

    host_name = esgf_host

    try:
        os.makedirs("/etc/tempcerts")
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass

    os.chdir("/etc/tempcerts")
    logger.debug("Changed directory to %s", os.getcwd())

    shutil.rmtree(os.path.join(os.getcwd(), "CA"))
    extensions_to_delete = (".pem", ".gz", ".ans", ".tmpl")
    files = os.listdir(os.getcwd())
    for file in files:
        if file.endswith(extensions_to_delete):
            try:
                os.remove(os.path.join(os.getcwd(), file))
                logger.debug("removed %s", os.path.join(os.getcwd(), file))
            except OSError, error:
                logger.error(error)

    os.mkdir("CA")
    write_ca_ans_templ() 
    write_reqhost_ans_templ()

    setuphost_ans = open("setuphost.ans", "w+")
    setuphost_ans.write("y\ny")
    setuphost_ans.close()

    setupca_ans_tmpl = open("setupca.ans.tmpl", "r")
    setupca_ans = open("setupca.ans", "w+")
    for line in setupca_ans_tmpl:
        setupca_ans.write(line.replace("placeholder.fqdn", host_name))
    setupca_ans_tmpl.close()
    setupca_ans.close()

    reqhost_ans_tmpl = open("reqhost.ans.tmpl", "r")
    reqhost_ans = open("reqhost.ans", "w+")
    for line in reqhost_ans_tmpl:
        reqhost_ans.write(line.replace("placeholder.fqdn", host_name))
    reqhost_ans_tmpl.close()
    reqhost_ans.close()

    if devel:
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/devel/esgf-installer/CA.pl".format(esg_coffee_dist_url_root = config.config_dictionary["esg_coffee_dist_url_root"]), "CA.pl")
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/devel/esgf-installer/openssl.cnf".format(esg_coffee_dist_url_root = config.config_dictionary["esg_coffee_dist_url_root"]), "openssl.cnf")
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/devel/esgf-installer/myproxy-server.config".format(esg_coffee_dist_url_root = config.config_dictionary["esg_coffee_dist_url_root"]), "myproxy-server.config")
    else:
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/esgf-installer/CA.pl".format(esg_coffee_dist_url_root = config.config_dictionary["esg_coffee_dist_url_root"]), "CA.pl")
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/esgf-installer/openssl.cnf".format(esg_coffee_dist_url_root = config.config_dictionary["esg_coffee_dist_url_root"]), "openssl.cnf")
        urllib.urlretrieve("http://{esg_coffee_dist_url_root}/esgf-installer/myproxy-server.config".format(esg_coffee_dist_url_root = config.config_dictionary["esg_coffee_dist_url_root"]), "myproxy-server.config")

    #pipe_in_setup_ca = subprocess.Popen(shlex.split("setupca.ans"), stdout = subprocess.PIPE)
    new_ca_process = subprocess.Popen(shlex.split("perl CA.pl -newca "))
    # x(new_ca_process)

    stdout_processes, stderr_processes = new_ca_process.communicate()
    logger.info("stdout_processes: %s", stdout_processes)
    logger.info("stderr_processes: %s", stderr_processes)
    if subprocess.call(shlex.split("openssl rsa -in CA/private/cakey.pem -out clearkey.pem -passin pass:placeholderpass")) == 0:
        logger.debug("moving clearkey")
        shutil.move("clearkey.pem", "/etc/tempcerts/CA/private/cakey.pem")
    with open("reqhost.ans", "wb") as reqhost_ans_file:
        subprocess.call(shlex.split("perl CA.pl -newreq-nodes"), stdin = reqhost_ans_file)
    with open("setuphost.ans", "wb") as setuphost_ans_file:
        subprocess.call(shlex.split("perl CA.pl -sign "), stdin = setuphost_ans_file)
    with open("cacert.pem", "wb") as cacert_file:
        subprocess.call(shlex.split("openssl x509 -in CA/cacert.pem -inform pem -outform pem"), stdout = cacert_file)
    shutil.copyfile("CA/private/cakey.pem", "cakey.pem")
    with open("hostcert.pem", "wb") as hostcert_file:
        subprocess.call(shlex.split("openssl x509 -in newcert.pem -inform pem -outform pem"), stdout = hostcert_file )
    shutil.move("newkey.pem", "hostkey.pem")

    try:
        os.chmod("cakey.pem", 0400)
        os.chmod("hostkey.pem", 0400)
    except OSError, error:
        logger.error(error)

    subprocess.call(shlex.split("rm -f new*.pem"))

    ESGF_OPENSSL="/usr/bin/openssl"
    cert = "cacert.pem"
    temp_subject = '/O=ESGF/OU=ESGF.ORG/CN=placeholder'
    # quoted_temp_subject = subprocess.check_output("`echo {temp_subject} | sed 's/[./*?|]/\\\\&/g'`;".format(temp_subject = temp_subject))

    # cert_subject = subprocess.check_output("`openssl x509 -in $cert -noout -subject|cut -d ' ' -f2-`;")
    cert_info = crypto.load_certificate(crypto.FILETYPE_PEM, open(esg_functions.readlinkf(cert)).read())
    cert_subject = cert_info.get_subject()
    cert_subject = re.sub(" <X509Name object '|'>", "", str(cert_subject)).strip()
    logger.info("cert_subject: %s", cert_subject)
    # quoted_cert_subject = subprocess.check_output("`echo {cert_subject} | sed 's/[./*?|]/\\\\&/g'`;".format(cert_subject = cert_subject))
    # print "quotedcertsubj=~{quoted_cert_subject}~".format(quoted_cert_subject = quoted_cert_subject)

    local_hash = subprocess.Popen(shlex.split("{ESGF_OPENSSL} x509 -in {cert} -noout -hash".format(ESGF_OPENSSL =  ESGF_OPENSSL, cert = cert)), stdout = subprocess.PIPE)
    local_hash_output, local_hash_err = local_hash.communicate()
    local_hash_output = local_hash_output.strip()
    logger.debug("local_hash_output: %s", local_hash_output)
    logger.debug("local_hash_err: %s", local_hash_err)
    
    target_directory = "globus_simple_ca_{local_hash}_setup-0".format(local_hash = local_hash_output)
    try:
        os.makedirs(target_directory)
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass

    shutil.copyfile(cert, os.path.join(target_directory, "{local_hash}.0".format(local_hash = local_hash_output)))

    print_templ()

    #Find and replace the temp_subject with the cert_subject in the signing_policy_template and rewrite to new file.

    # subprocess.call(shlex.split('sed "s/\(.*\)$quotedtmpsubj\(.*\)/\1$quotedcertsubj\2/" signing_policy_template >$tgtdir/${localhash}.signing_policy;'))
    
    signing_policy_template = open("signing_policy_template", "r")
    signing_policy = open("signing_policy", "w+")
    for line in signing_policy_template:
        signing_policy.write(line.replace(temp_subject, cert_subject))
    signing_policy_template.close()
    signing_policy.close()

    # shutil.copyfile(os.path.join(target_directory,local_hash_output,".signing_policy"), "signing_policy")

    subprocess.call(shlex.split("tar -cvzf globus_simple_ca_{local_hash}_setup-0.tar.gz {target_directory}".format(local_hash = local_hash_output, target_directory = target_directory)))
    subprocess.call(shlex.split("rm -rf {target_directory};".format(target_directory = target_directory)))
    subprocess.call(shlex.split("rm -f signing_policy_template;"))


    try:
        os.makedirs("/etc/certs")
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass
    try:
        shutil.copy("openssl.cnf", os.path.join("/etc", "certs"))

        logger.info("glob_list: %s", glob.glob("host*.pem"))
        for file in glob.glob("host*.pem"):
            shutil.copy(file, os.path.join("/etc", "certs"))

        shutil.copyfile("cacert.pem", os.path.join("/etc", "certs", "cachain.pem"))
    except IOError, error:
        logger.error(error)

    try:
        os.makedirs("/etc/esgfcerts")
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass


def setup_root_app():

    if os.path.isdir(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps", "ROOT")) and 'REFRESH' in open(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps", "ROOT","index.html")).read():
        print "ROOT app in place... [OK]"
        return True
    else:
        print "Oops, Don't see ESGF ROOT web application"
        esg_functions.backup(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps", "ROOT"))

        print "*******************************"
        print "Setting up Apache Tomcat...(v${tomcat_version}) ROOT webapp"
        print "*******************************"

        esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
        root_app_dist_url = "{esg_dist_url}/ROOT.tgz".format(esg_dist_url = esg_dist_url)

        try:
            os.makedirs(config.config_dictionary["workdir"])
        except OSError, exception:
            if exception.errno != 17:
                raise
            sleep(1)
            pass

        starting_directory = os.getcwd()
        os.chdir(config.config_dictionary["workdir"])

        print "Downloading ROOT application from {root_app_dist_url}".format(root_app_dist_url = root_app_dist_url)
        if esg_functions.checked_get(root_app_dist_url) > 0:
            print " ERROR: Could not download ROOT app archive"
            os.chdir(starting_directory)
            esg_functions.checked_done(1)

        print "unpacking ${root_app_dist_url}...".format(root_app_dist_url = esg_functions.trim_string_from_tail(root_app_dist_url))
        try:
            tar = tarfile.open(esg_functions.trim_string_from_tail(root_app_dist_url))
            tar.extractall()
            tar.close()
            shutil.move(esg_functions.trim_string_from_tail(root_app_dist_url), os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps"))
        except Exception, error:
            print " ERROR: Could not extract {root_app_dist_url}".format(esg_functions.readlinkf(esg_functions.trim_string_from_tail(root_app_dist_url)))

        if os.path.exists(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps", "esgf-node-manager")):
            shutil.copyfile(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps", "ROOT","index.html"), os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps", "ROOT","index.html.nm"))
        if os.path.exists(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps", "esgf-web-fe")):
            shutil.copyfile(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps", "ROOT","index.html"), os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps", "ROOT","index.html.fe"))

        os.chown(esg_functions.readlinkf(os.path.join(config.config_dictionary["tomcat_install_dir"], "webapps", "ROOT")), pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_uid, grp.getgrnam(
            config.config_dictionary["tomcat_group"]).gr_gid)

        print "ROOT application \"installed\""
        os.chdir(starting_directory)
        return True

def write_ca_ans_templ():
    file = open("setupca.ans.tmpl", "w+")
    file.write('''

        placeholder.fqdn-CA


        ''')
    file.close()

def write_reqhost_ans_templ():
    file = open("reqhost.ans.tmpl", "w+")
    file.write('''

        placeholder.fqdn


        ''')
    file.close()

def print_templ():
    file = open("signing_policy_template", "w+")
    file.write('''
        # ca-signing-policy.conf, see ca-signing-policy.doc for more information
        #
        # This is the configuration file describing the policy for what CAs are
        # allowed to sign whoses certificates.
        #
        # This file is parsed from start to finish with a given CA and subject
        # name.
        # subject names may include the following wildcard characters:
        #    *    Matches any number of characters.
        #    ?    Matches any single character.
        #
        # CA names must be specified (no wildcards). Names containing whitespaces
        # must be included in single quotes, e.g. 'Certification Authority'. 
        # Names must not contain new line symbols. 
        # The value of condition attribute is represented as a set of regular 
        # expressions. Each regular expression must be included in double quotes.  
        #
        # This policy file dictates the following policy:
        #   -The Globus CA can sign Globus certificates
        #
        # Format:
        #------------------------------------------------------------------------
        #  token type  | def.authority |                value              
        #--------------|---------------|-----------------------------------------
        # EACL entry #1|

         access_id_CA      X509         '/O=ESGF/OU=ESGF.ORG/CN=placeholder'

         pos_rights        globus        CA:sign

         cond_subjects     globus       '"/O=ESGF/OU=ESGF.ORG/*"'

        # end of EACL

        ''')
    file.close()


def migrate_tomcat_credentials_to_esgf(keystore_password, esg_dist_url):
    '''
    Move selected config files into esgf tomcat's config dir (certificate et al)
    Ex: /esg/config/tomcat
    -rw-r--r-- 1 tomcat tomcat 181779 Apr 22 19:44 esg-truststore.ts
    -r-------- 1 tomcat tomcat    887 Apr 22 19:32 hostkey.pem
    -rw-r--r-- 1 tomcat tomcat   1276 Apr 22 19:32 keystore-tomcat
    -rw-r--r-- 1 tomcat tomcat    590 Apr 22 19:32 pcmdi11.llnl.gov-esg-node.csr
    -rw-r--r-- 1 tomcat tomcat    733 Apr 22 19:32 pcmdi11.llnl.gov-esg-node.pem
    -rw-r--r-- 1 tomcat tomcat    295 Apr 22 19:42 tomcat-users.xml

    Only called when migration conditions are present.    
    '''
    tomcat_install_conf = os.path.join(config.config_dictionary["tomcat_install_dir"], "conf") 

    if tomcat_install_conf != config.config_dictionary["tomcat_conf_dir"]:
        if not os.path.exists(config.config_dictionary["tomcat_conf_dir"]):
            try:
                os.makedirs(config.config_dictionary["tomcat_conf_dir"])
            except OSError, exception:
                if exception.errno != 17:
                    raise
                sleep(1)
                pass
        
        esg_functions.backup(tomcat_install_conf)
        
        logger.debug("Moving credential files into node's tomcat configuration dir: %s", config.config_dictionary["tomcat_conf_dir"])
        truststore_file_name = esg_functions.trim_string_from_head(config.config_dictionary["truststore_file"])
        # i.e. /usr/local/tomcat/conf/esg-truststore.ts
        if os.path.exists(os.path.join(tomcat_install_conf, truststore_file_name)) and not os.path.exists(config.config_dictionary["truststore_file"]):
            shutil.move(os.path.join(tomcat_install_conf, truststore_file_name), config.config_dictionary["truststore_file"])
            print "+"

        keystore_file_name = esg_functions.trim_string_from_head(config.config_dictionary["keystore_file"])
        if os.path.exists(os.path.join(tomcat_install_conf, keystore_file_name)) and not os.path.exists(config.config_dictionary["keystore_file"]):
            shutil.move(os.path.join(tomcat_install_conf, keystore_file_name), config.config_dictionary["keystore_file"])
            print "+"

        tomcat_users_file_name = esg_functions.trim_string_from_head(config.config_dictionary["tomcat_users_file"])
        if os.path.exists(os.path.join(tomcat_install_conf, tomcat_users_file_name)) and not os.path.exists(config.config_dictionary["tomcat_users_file"]):
            shutil.move(os.path.join(tomcat_install_conf, tomcat_users_file_name), config.config_dictionary["tomcat_users_file"])
            print "+"

        if os.path.exists(os.path.join(tomcat_install_conf, "hostkey.pem")) and not os.path.exists(os.path.join(config.config_dictionary["tomcat_conf_dir"], "hostkey.pem")):
            shutil.move(os.path.join(tomcat_install_conf, "hostkey.pem"), os.path.join(config.config_dictionary["tomcat_conf_dir"], "hostkey.pem"))
            print "+"

        try:
            if os.path.exists(os.path.join(tomcat_install_conf, config.config_dictionary["esgf_host"] +"-esg-node.csr")) and not os.path.exists(os.path.join(config.config_dictionary["tomcat_conf_dir"], config.config_dictionary["esgf_host"] +"-esg-node.csr")):
                shutil.move(os.path.join(tomcat_install_conf, config.config_dictionary["esgf_host"] +"-esg-node.csr"), os.path.join(config.config_dictionary["tomcat_conf_dir"], config.config_dictionary["esgf_host"] +"-esg-node.csr"))

            if os.path.exists(os.path.join(tomcat_install_conf, config.config_dictionary["esgf_host"] +"-esg-node.pem")) and not os.path.exists(os.path.join(config.config_dictionary["tomcat_conf_dir"], config.config_dictionary["esgf_host"] +"-esg-node.pem")):
                shutil.move(os.path.join(tomcat_install_conf, config.config_dictionary["esgf_host"] +"-esg-node.pem"), os.path.join(config.config_dictionary["tomcat_conf_dir"], config.config_dictionary["esgf_host"] +"-esg-node.pem"))
        except KeyError:
            if os.path.exists(os.path.join(tomcat_install_conf, socket.getfqdn() +"-esg-node.csr")) and not os.path.exists(os.path.join(config.config_dictionary["tomcat_conf_dir"], socket.getfqdn() +"-esg-node.csr")):
                shutil.move(os.path.join(tomcat_install_conf, socket.getfqdn() +"-esg-node.csr"), os.path.join(config.config_dictionary["tomcat_conf_dir"], socket.getfqdn() +"-esg-node.csr"))

            if os.path.exists(os.path.join(tomcat_install_conf, socket.getfqdn() +"-esg-node.pem")) and not os.path.exists(os.path.join(config.config_dictionary["tomcat_conf_dir"], socket.getfqdn() +"-esg-node.pem")):
                shutil.move(os.path.join(tomcat_install_conf, socket.getfqdn() +"-esg-node.pem"), os.path.join(config.config_dictionary["tomcat_conf_dir"], socket.getfqdn() +"-esg-node.pem"))
        
        os.chown(config.config_dictionary["tomcat_conf_dir"], pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_uid, grp.getgrnam(config.config_dictionary["tomcat_group"]).gr_gid)

        #Be sure that the server.xml file contains the explicit Realm specification needed.
        server_xml_object = untangle.parse(os.path.join(config.config_dictionary["tomcat_install_dir"], "conf", "server.xml"))
        if not server_xml_object.Realm:
            fetch_file_name = "server.xml"
            fetch_file_path = os.path.join(config.config_dictionary["tomcat_install_dir"], "conf", fetch_file_name)

            if esg_functions.checked_get(fetch_file_path, "{esg_dist_url}/externals/bootstrap/node.{fetch_file_name}-v{tomcat_version}".format(esg_dist_url = esg_dist_url, fetch_file_name = fetch_file_name, tomcat_version = esg_functions.trim_string_from_tail(config.config_dictionary["tomcat_version"]))) != 0:
                # os.chdir(starting_directory)
                esg_functions.checked_done(1)
            os.chmod(fetch_file_path, 0600)
            os.chown(fetch_file_path, pwd.getpwnam(config.config_dictionary["tomcat_user"]).pw_uid, grp.getgrnam(config.config_dictionary["tomcat_group"]).gr_gid)

        #SET the server.xml variables to contain proper values
        logger.debug("Editing %s/conf/server.xml accordingly...", config.config_dictionary["tomcat_install_dir"])
        edit_tomcat_server_xml(keystore_password)

def tomcat_port_check():
    ''' 
        Helper function to poke at tomcat ports...
        Port testing for http and https
    '''
    return_all = True
    protocol = "http"
    print "checking connection at all ports described in {tomcat_install_dir}/conf/server.xml".format(config.config_dictionary["tomcat_install_dir"])
    server_xml_object = untangle.parse(os.path.join(config.config_dictionary["tomcat_install_dir"], "conf", "server.xml"))
            # server_xml_object.Server.Connector[1]["keystorePass"] = local_keystore_password
    for connector in server_xml_object.Server.Connector:
        if connector["port"] == "8223":
            continue
        if connector["port"] == "8443":
            protocol="https"
        print "checking localhost port [${port}]"
        wait_time = 5
        return_code = None
        while wait_time > 0:
            return_code = subprocess.call("curl -k {protocol}://localhost:{port} >& /dev/null".format(protocol = protocol, port = connector["port"]))
            if return_code == 0:
                break
            sleep(1)
            wait_time -= 1
        if return_code == 0:
            logger.info("[OK]")
        else:
            logger.error("[FAIL]")

        #We only care about reporting a failure for ports below 1024
        #specifically 80 (http) and 443 (https)
        if connector.has_key("protocol") and "http" in connector["protocol"].lower():
            esgf_http_port = connector["port"]
        if connector.has_key("SSLEnabled"):
            esgf_https_port = connector["port"]

        if connector["port"] < 1024:
            return_all += return_code

    return return_all


def write_tomcat_env():
    pass

def write_tomcat_install_log():
    pass

def write_postgress_env():
    pass
def write_postgress_install_log():
    pass
     
def _choose_postgres_user_password():
    while True:
            postgres_user_password = raw_input("Enter password for postgres user $postgress_user: ")
            postgres_user_password_confirmation = raw_input("Re-enter password for postgres user $postgress_user: ")
            if postgres_user_password != postgres_user_password_confirmation:
                print "The passwords did not match. Enter same password twice."
                continue
            else:
                return postgres_user_password
def backup_db():
    pass
if __name__ == '__main__':
    main()
