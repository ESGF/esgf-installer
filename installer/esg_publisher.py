'''
    ESGCET Package (Publisher) functions
'''
import esg_functions
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
import esg_bash2py
from time import sleep
from git import Repo
import esg_logging_manager
import esg_init
import yaml
import re
from pip.operations import freeze

logger = esg_logging_manager.create_rotating_log(__name__)

with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

esg_root_id = esg_functions.get_esg_root_id()

def check_publisher_version():
    '''Check if an existing version of the Publisher is found on the system'''
    module_list = list(freeze.freeze())
    matcher = re.compile("esgcet==.*")
    results_list = filter(matcher.match, module_list)
    if results_list:
        version = results_list[0].split("==")[1]
        print "Found existing esg-publisher installation (esg-publisher version {version})".format(version=version)
        return version
    else:
        print "esg-publisher not found on system."


def clone_publisher_repo(publisher_path):
    print "Fetching the cdat project from GIT Repo... %s" % (config["publisher_repo_https"])

    if not os.path.isdir(os.path.join(publisher_path, ".git")):
        Repo.clone_from(config[
                        "publisher_repo_https"], publisher_path)
    else:
        print "Publisher repo already exists {publisher_path}".format(publisher_path=publisher_path)

def checkout_publisher_branch(publisher_path, branch_name):
    publisher_repo_local = Repo(publisher_path)
    publisher_repo_local.git.checkout(branch_name)
    return publisher_repo_local

#TODO: Might belong in esg_postgres.py
def symlink_pg_binary():
    '''Creates a symlink to the /usr/bin directory so that the publisher setup.py script can find the postgres version'''
    esg_bash2py.symlink_force("/usr/pgsql-9.6/bin/pg_config", "/usr/bin/pg_config")

def install_publisher():
    # install publisher
    # from setuptools import sandbox
    symlink_pg_binary()
    esg_functions.stream_subprocess_output("python setup.py install")
    # from distutils.core import run_setup
    # run_setup('setup.py', ['install'])
    # sandbox.run_setup('setup.py', ['install'])


def generate_esgsetup_options(recommended_setup = 1):
    '''Generate the string that will pass arguments to esgsetup'''
    publisher_db_user = None
    try:
        publisher_db_user = config["publisher_db_user"]
    except KeyError:
        publisher_db_user = esg_property_manager.get_property("publisher_db_user")

    security_admin_password = esg_functions.get_security_admin_password()

    generate_esg_ini_command = "esgsetup --db".format(cdat_home=config["cdat_home"])
    if recommended_setup == 1:
        generate_esg_ini_command += " --minimal-setup"
    if config["db_database"]:
        generate_esg_ini_command += " --db-name %s" % (config["db_database"])
    if config["postgress_user"]:
        generate_esg_ini_command += " --db-admin %s" % (config["postgress_user"])

    if security_admin_password:
        generate_esg_ini_command += " --db-admin-password %s" % (security_admin_password)
    elif config["pg_sys_acct_passwd"]:
        generate_esg_ini_command += " --db-admin-password %s" % (config["pg_sys_acct_passwd"])

    if publisher_db_user:
        generate_esg_ini_command += " --db-user %s" % (publisher_db_user)
    if config["publisher_db_user_passwd"]:
        generate_esg_ini_command += " --db-user-password %s" % (config["publisher_db_user_passwd"])
    if config["postgress_host"]:
        generate_esg_ini_command += " --db-host %s" % (config["postgress_host"])
    if config["postgress_port"]:
        generate_esg_ini_command += " --db-port %s" % (config["postgress_port"])

    logger.info("generate_esg_ini_command in function: %s", generate_esg_ini_command)
    return generate_esg_ini_command

def run_esgsetup():
    '''generate esg.ini file using esgsetup script; #Makes call to esgsetup - > Setup the ESG publication configuration'''
    print "\n*******************************"
    print "Running esgsetup"
    print "******************************* \n"

    generate_esg_ini_command = '''esgsetup --config --minimal-setup --rootid {esg_root_id}'''.format(esg_root_id=esg_functions.get_esg_root_id())
    #"sed -i s/"host\.sample\.gov"/{esgf_host}/g {publisher_home}/{publisher_config}"
    #"sed -i s/"LASatYourHost"/LASat{node_short_name}/g {publisher_home}/{publisher_config}"
    try:
        esg_functions.stream_subprocess_output(generate_esg_ini_command)
    except Exception:
        logger.exception("Could not finish esgsetup")
        esg_functions.exit_with_error(1)

def run_esginitialize():
    '''Run the esginitialize script to initialize the ESG node database.'''
    print "\n*******************************"
    print "Running esginitialize"
    print "******************************* \n"

    esginitialize_process = esg_functions.call_subprocess("esginitialize -c")
    if esginitialize_process["returncode"] != 0:
        logger.exception("esginitialize failed")
        logger.error(esginitialize_process["stderr"])
        print esginitialize_process["stderr"]
        esg_functions.exit_with_error(1)
    else:
        print esginitialize_process["stdout"]
        print esginitialize_process["stderr"]

def setup_publisher():
    '''Install ESGF publisher'''

    print "\n*******************************"
    print "Setting up ESGCET Package...(%s)" %(config["esgcet_egg_file"])
    print "******************************* \n"
    ESG_PUBLISHER_VERSION= "v3.2.7"
    with esg_bash2py.pushd("/tmp"):
        clone_publisher_repo("/tmp/esg-publisher")
        with esg_bash2py.pushd("esg-publisher"):
            checkout_publisher_branch("/tmp/esg-publisher", "devel")
            with esg_bash2py.pushd("src/python/esgcet"):
                install_publisher()

# env needed by Python client to trust the data node server certicate
# ENV SSL_CERT_DIR /etc/grid-security/certificates
# ENV ESGINI /esg/config/esgcet/esg.ini
#
# # startup scripts
# COPY scripts/ /usr/local/bin/

def write_esgcet_install_log():
    """ Write the Publisher install properties to the install manifest"""
    with open(config["install_manifest"], "a+") as datafile:
        datafile.write(str(datetime.date.today()) + "python:esgcet=" +
                       config["esgcet_version"] + "\n")

    esg_property_manager.write_as_property(
        "publisher_config", config["publisher_config"])
    esg_property_manager.write_as_property(
        "publisher_home", config["publisher_home"])
    esg_property_manager.write_as_property("monitor.esg.ini", os.path.join(config[
                                    "publisher_home"], config["publisher_config"]))
    return 0

def main():
    setup_publisher()
    run_esgsetup()
    run_esginitialize()
    write_esgcet_install_log()

try:
    node_short_name = config["node_short_name"]
except:
    node_short_name = esg_property_manager.get_property("node_short_name")

def setup_esgcet(upgrade_mode=None, force_install = False, recommended_setup = 1, DEBUG = False):
    print "Checking for esgcet (publisher) %s " % (config["esgcet_version"])
    # TODO: come up with better name
    publisher_module_check = esg_version_manager.check_module_version(
        "esgcet", config["esgcet_version"])

    # TODO: implement this if block
    # if os.path.isfile(config["ESGINI"]):
    #   urls_mis_match=1
    #   # files= subprocess.Popen('ls -t | grep %s.\*.tgz | tail -n +$((%i+1)) | xargs' %(source_backup_name,int(num_of_backups)), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # esgini_dburl = files= subprocess.Popen("sed -n 's@^[^#]*[ ]*dburl[ ]*=[
    # ]*\(.*\)$@\1@p' %s | head -n1 | sed 's@\r@@'' "
    # %(config["ESGINI"]), shell=True,
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
     ''' % (config["esgcet_egg_file"], mode)

    if mode == "upgrade":
        if config["publisher_home"] == os.environ["HOME"] + "/.esgcet":
            print "user configuration", config["publisher_home"]
        else:
            print "system configuration", config["publisher_home"]

    default_upgrade_answer = None
    if force_install:
        default_upgrade_answer = "N"
    else:
        default_upgrade_answer = "Y"

    continue_installation_answer = None

    if os.path.isfile(os.path.join(config["publisher_home"], config["publisher_config"])):
        print "Detected an existing esgcet installation..."
        if default_upgrade_answer == "N":
            continue_installation_answer = raw_input(
                "Do you want to continue with esgcet installation and setup? [y/N]")
        else:
            continue_installation_answer = raw_input(
                "Do you want to continue with esgcet installation and setup? [Y/n]")

        if not continue_installation_answer.strip():
            continue_installation_answer = default_upgrade_answer

        if continue_installation_answer.lower() in ["y", "yes"]:
            print "Skipping esgcet installation and setup - will assume esgcet is setup properly"
            return 0

    starting_directory = os.getcwd()

    esg_bash2py.mkdir_p(config["workdir"])

    os.chdir(config["workdir"])

    pip_list = [{"package": "lxml", "version": "3.3.5"}, {"package": "requests", "version": "1.2.3"}, {"package": "SQLAlchemy", "version": "0.7.10"},
                {"package": "sqlalchemy-migrate", "version": "0.6"}, {"package": "psycopg2",
                                                                      "version": "2.5"}, {"package": "Tempita", "version": "0.5.1"},
                {"package": "decorator", "version": "3.4.0"}, {"package": "pysolr", "version": "3.3.0"}, {"package": "drslib", "version": "0.3.1p3"}]

    for _, value in enumerate(pip_list):
        print "installing %s-%s" % (value["package"], value["version"])
        pip.main(["install", value["package"] + "==" + value["version"]])

    # clone publisher
    publisher_git_protocol = "git://"

    workdir_esg_publisher_directory = os.path.join(config["workdir"], "esg-publisher")

    if force_install and os.path.isdir(workdir_esg_publisher_directory):
        try:
            shutil.rmtree(workdir_esg_publisher_directory)
        except:
            print "Could not delete directory: %s" % (workdir_esg_publisher_directory)

    if not os.path.isdir(workdir_esg_publisher_directory):

        print "Fetching the cdat project from GIT Repo... %s" % (config["publisher_repo"])
        Repo.clone_from(config[
                        "publisher_repo"], workdir_esg_publisher_directory)

        if not os.path.isdir(os.path.join(workdir_esg_publisher_directory, ".git")):

            publisher_git_protocol = "https://"
            print "Apparently was not able to fetch from GIT repo using git protocol... trying https protocol... %s" % (publisher_git_protocol)

            Repo.clone_from(config["publisher_repo_https"], workdir_esg_publisher_directory)

            if not os.path.isdir(os.path.join(config["workdir"], "esg-publisher", ".git")):
                print "Could not fetch from cdat's repo (with git nor https protocol)"
                esg_functions.exit_with_error(1)

    os.chdir(workdir_esg_publisher_directory)
    publisher_repo_local = Repo(workdir_esg_publisher_directory)
    publisher_repo_local.git.checkout("master")
    # pull from remote
    publisher_repo_local.remotes.origin.pull()
    # Checkout publisher tag
    try:
        publisher_repo_local.head.reference = publisher_repo_local.tags[
            config["publisher_tag"]]
        publisher_repo_local.head.reset(index=True, working_tree=True)
    except:
        print " WARNING: Problem with checking out publisher (esgcet) revision [%s] from repository :-(" % (config["esgcet_version"])

    # install publisher
    from setuptools import sandbox
    sandbox.run_setup('setup.py', ['install'])
    installation_command = "cd src/python/esgcet; %s/bin/python setup.py install" % (
        config["cdat_home"])
    try:
        output = subprocess.call(installation_command, shell=True)
        if output != 0:
            logger.error("Return code was %s for %s", output, installation_command)
            esg_functions.exit_with_error(1)
    except Exception, exception:
        logger.error(exception)
        esg_functions.exit_with_error(1)

    if mode == "install":
        choice = None

        config["ESGINI"] = os.path.join(config[
                                                          "publisher_home"], config["publisher_config"])
        print "Publisher configuration file -> [%s/%s]" % (config["publisher_home"], config["publisher_config"])

        esgf_host = None
        try:
            esgf_host = config["esgf_host"]
        except KeyError:
            esgf_host = esg_property_manager.get_property("esgf_host")

        org_id_input = raw_input(
            "What is your organization's id? [%s]: " % esg_root_id)
        if org_id_input:
            esg_root_id = org_id_input

        logger.info("%s/bin/esgsetup --config $( ((%s == 1 )) && echo '--minimal-setup' ) --rootid %s", config["cdat_home"], recommended_setup, esg_root_id)

        try:
            os.mkdir(config["publisher_home"])
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
            '''.format(publisher_home=config["publisher_home"], publisher_config=config["publisher_config"], cdat_home=config["cdat_home"],
                       recommended_setup=recommended_setup, esg_root_id=esg_root_id,
                       esgf_host=esgf_host, node_short_name=node_short_name)

        esg_ini_file_process = subprocess.Popen(generate_esg_ini_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout_data, stderr_data = esg_ini_file_process.communicate()
        if esg_ini_file_process.returncode != 0:
            logger.error("ESGINI.returncode did not equal 0: %s %s", esg_ini_file_process.returncode, generate_esg_ini_command)
            raise RuntimeError("%r failed, status code %s stdout %r stderr %r" % (
                       generate_esg_ini_command, esg_ini_file_process.returncode, stdout_data, stderr_data))
            os.chdir(starting_directory)
            esg_functions.exit_with_error(1)

    logger.info("chown -R %s:%s %s", config["installer_uid"], config["installer_gid"], config["publisher_home"])
    try:
        os.chown(config["publisher_home"], config[
                 "installer_uid"], config["installer_gid"])
    except:
        print "**WARNING**: Could not change owner successfully - this will lead to inability to use the publisher properly!"

    # Let's make sure the group is there before we attempt to assign a file to
    # it....
    try:
        tomcat_group_check = grp.getgrnam(
            config["tomcat_group"])
    except KeyError:
        groupadd_command = "/usr/sbin/groupadd -r %s" % (
            config["tomcat_group"])
        groupadd_output = subprocess.call(groupadd_command, shell=True)
        if groupadd_output != 0 or groupadd_output != 9:
            print "ERROR: *Could not add tomcat system group: %s" % (config["tomcat_group"])
            os.chdir(starting_directory)
            esg_functions.exit_with_error(1)

    try:
        tomcat_group_id = grp.getgrnam(
            config["tomcat_group"]).gr_gid
        os.chown(os.path.join(config[
                 "publisher_home"], config["publisher_config"]), -1, tomcat_group_id)
        os.chmod(os.path.join(config["publisher_home"], config["publisher_config"]), 0640)
    except:
        print "**WARNING**: Could not change group successfully - this will lead to inability to use the publisher properly!"

    esg_postgres.start_postgress()

    # security_admin_password=$(cat ${esgf_secret_file} 2> /dev/null)
    security_admin_password = esg_functions.get_security_admin_password()

    # get_property publisher_db_user ${publisher_db_user}
    publisher_db_user = None
    try:
        publisher_db_user = config["publisher_db_user"]
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
            '''.format(config["publisher_home"], config["publisher_config"], config["cdat_home"], recommended_setup,
            config["db_database"], config["db_database"],
            config["postgress_user"], config["postgress_user"],
            security_admin_password, config["pg_sys_acct_passwd"],
            publisher_db_user, publisher_db_user,
            config["publisher_db_user_passwd"], config["publisher_db_user_passwd"],
            config["postgress_host"], config["postgress_host"],
            config["postgress_port"], config["postgress_port"])
            logger.info("generate_esg_ini_command: %s", generate_esg_ini_command)

        else:
            esg_ini_command = generate_esgsetup_options()
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
        esg_functions.exit_with_error(1)

    try:
        #Call the esginitialize script -> Initialize the ESG node database.
        esginitialize_output = subprocess.call(
            "%s/bin/esginitialize -c" % (config["cdat_home"]), shell=True)
        if esginitialize_output != 0:
            logger.error("esginitialize_output: %s", esginitialize_output)
            os.chdir(starting_directory)
            esg_functions.exit_with_error(1)
    except Exception, exception:
        print "exception occurred with esginitialize_output: ", str(exception)

    os.chdir(starting_directory)
    write_esgcet_install_log()

    esg_functions.exit_with_error(0)

if __name__ == '__main__':
    main()
