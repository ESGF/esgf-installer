'''
    ESGCET Package (Publisher) functions
'''
import esg_functions
import logging
import os
import shutil
import pip
import subprocess
import grp
import datetime
import esg_postgres
import esg_functions
import esg_property_manager
import esg_version_manager
import esg_env_manager
from time import sleep
from git import Repo
from esg_init import EsgInit

logging.basicConfig(format = "%(levelname): %(lineno)s %(funcName)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = EsgInit()
esg_root_id = esg_functions.get_esg_root_id()

try:
    node_short_name = config.config_dictionary["node_short_name"]
except:
    node_short_name = esg_property_manager.get_property("node_short_name")

def setup_esgcet(upgrade_mode=None, force_install = False, recommended_setup = 1, DEBUG = False):
    print "Checking for esgcet (publisher) %s " % (config.config_dictionary["esgcet_version"])
    # TODO: come up with better name
    publisher_module_check = esg_version_manager.check_module_version(
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

    for _, value in enumerate(pip_list):
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
            esgf_host = esg_property_manager.get_property("esgf_host")

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

    esg_postgres.start_postgress()

    # security_admin_password=$(cat ${esgf_secret_file} 2> /dev/null)
    security_admin_password = esg_functions.get_security_admin_password()

    # get_property publisher_db_user ${publisher_db_user}
    publisher_db_user = None
    try:
        publisher_db_user = config.config_dictionary["publisher_db_user"]
    except KeyError:
        publisher_db_user = esg_property_manager.get_property("publisher_db_user")

    if mode == "install":
        #Makes call to esgsetup - > Setup the ESG publication configuration
        if not DEBUG:
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


def generate_esg_config_file(recommended_setup = 1):
    # get_property publisher_db_user ${publisher_db_user}
    publisher_db_user = None
    try:
        publisher_db_user = config.config_dictionary["publisher_db_user"]
    except KeyError:
        publisher_db_user = esg_functions.get_property("publisher_db_user")

    security_admin_password = esg_functions.get_security_admin_password()

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

def write_esgcet_env():
    # print
    datafile = open(config.envfile, "a+")
    try:
        datafile.write("export ESG_ROOT_ID=" + esg_root_id + "\n")
        esg_env_manager.deduplicate_settings_in_file(config.envfile)
    finally:
        datafile.close()


def write_esgcet_install_log():
    datafile = open(config.install_manifest, "a+")
    try:
        datafile.write(str(datetime.date.today()) + "python:esgcet=" +
                       config.config_dictionary["esgcet_version"] + "\n")
        esg_env_manager.deduplicate_settings_in_file(config.install_manifest)
    finally:
        datafile.close()

    esg_property_manager.write_as_property(
        "publisher_config", config.config_dictionary["publisher_config"])
    esg_property_manager.write_as_property(
        "publisher_home", config.config_dictionary["publisher_home"])
    esg_property_manager.write_as_property("monitor.esg.ini", os.path.join(config.config_dictionary[
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

    esg_postgres.start_postgress()

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