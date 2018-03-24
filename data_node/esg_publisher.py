'''
    ESGCET Package (Publisher) functions
'''
import os
import datetime
import logging
from git import Repo
import yaml
import re
from pip.operations import freeze
from esgf_utilities import esg_functions
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_bash2py


logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

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
    symlink_pg_binary()
    esg_functions.stream_subprocess_output("python setup.py install")


def generate_esgsetup_options(recommended_setup = 1):
    '''Generate the string that will pass arguments to esgsetup to initialize the database'''
    publisher_db_user = None
    try:
        publisher_db_user = config["publisher_db_user"]
    except KeyError:
        publisher_db_user = esg_property_manager.get_property("publisher_db_user")

    security_admin_password = esg_functions.get_security_admin_password()

    generate_esg_ini_command = "esgsetup --db"
    if recommended_setup == 1:
        generate_esg_ini_command += " --minimal-setup"
    if config["db_database"]:
        generate_esg_ini_command += " --db-name %s" % (config["db_database"])
    if config["postgress_user"]:
        generate_esg_ini_command += " --db-admin %s" % (config["postgress_user"])

    if security_admin_password:
        generate_esg_ini_command += " --db-admin-password %s" % (security_admin_password)

    if publisher_db_user:
        generate_esg_ini_command += " --db-user %s" % (publisher_db_user)

    publisher_password = esg_functions.get_publisher_password()
    if publisher_password:
        generate_esg_ini_command += " --db-user-password %s" % (publisher_password)
    if config["postgress_host"]:
        generate_esg_ini_command += " --db-host %s" % (config["postgress_host"])
    if config["postgress_port"]:
        generate_esg_ini_command += " --db-port %s" % (config["postgress_port"])

    logger.info("generate_esg_ini_command in function: %s", generate_esg_ini_command)
    # print "generate_esg_ini_command in function: %s" % generate_esg_ini_command
    return generate_esg_ini_command

def edit_esg_ini(node_short_name="test_node"):
    '''Edit placeholder values in the generated esg.ini file'''
    esg_ini_path = os.path.join(config["publisher_home"], config["publisher_config"])
    print "esg_ini_path:", esg_ini_path
    esg_functions.call_subprocess('sed -i s/esgcetpass/password/g {esg_ini_path}'.format(esg_ini_path=esg_ini_path))
    esg_functions.call_subprocess('sed -i s/"host\.sample\.gov"/{esgf_host}/g {esg_ini_path}'.format(esg_ini_path=esg_ini_path, esgf_host=esg_functions.get_esgf_host()))
    esg_functions.call_subprocess('sed -i s/"LASatYourHost"/LASat{node_short_name}/g {esg_ini_path}'.format(esg_ini_path=esg_ini_path,  node_short_name=node_short_name))

def run_esgsetup():
    '''generate esg.ini file using esgsetup script; #Makes call to esgsetup - > Setup the ESG publication configuration'''
    print "\n*******************************"
    print "Creating config file (esg.ini) with esgsetup"
    print "******************************* \n"

    os.environ["UVCDAT_ANONYMOUS_LOG"] = "no"
    #Create an initial ESG configuration file (esg.ini); TODO: make break into separate function
    esg_org_name = esg_property_manager.get_property("esg.org.name")
    generate_esg_ini_command = '''esgsetup --config --minimal-setup --rootid {esg_org_name} --db-admin-password password'''.format(esg_org_name=esg_functions.get_esg_org_name())

    try:
        esg_functions.stream_subprocess_output(generate_esg_ini_command)
        edit_esg_ini()
    except Exception:
        logger.exception("Could not finish esgsetup")
        esg_functions.exit_with_error(1)

    print "\n*******************************"
    print "Initializing database with esgsetup"
    print "******************************* \n"

    #Initialize the database
    db_setup_command = generate_esgsetup_options()
    print "db_setup_command:", db_setup_command

    try:
        esg_functions.stream_subprocess_output(db_setup_command)
    except Exception:
        logger.exception("Could not initialize database.")
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

    if os.path.isfile(os.path.join(config["publisher_home"], config["publisher_config"])):
        publisher_install = raw_input("Detected an existing esgcet installation. Do you want to continue with the Publisher installation [y/N]: ") or "no"
        if publisher_install.lower() in ["no", "n"]:
            return

    print "\n*******************************"
    print "Setting up ESGCET Package...(%s)" %(config["esgcet_egg_file"])
    print "******************************* \n"
    ESG_PUBLISHER_VERSION= "3.4.0a1"
    with esg_bash2py.pushd("/tmp"):
        clone_publisher_repo("/tmp/esg-publisher")
        with esg_bash2py.pushd("esg-publisher"):
            checkout_publisher_branch("/tmp/esg-publisher", ESG_PUBLISHER_VERSION)
            with esg_bash2py.pushd("src/python/esgcet"):
                install_publisher()


def write_esgcet_env():
    esg_property_manager.set_property("ESG_ROOT_ID", "export ESG_ROOT_ID={}".format(esg_property_manager.get_property("esg.org.name")), config_file=config["envfile"], section_name="esgf.env")

# env needed by Python client to trust the data node server certicate
# ENV SSL_CERT_DIR /etc/grid-security/certificates
# ENV ESGINI /esg/config/esgcet/esg.ini

def write_esgcet_install_log():
    """ Write the Publisher install properties to the install manifest"""
    with open(config["install_manifest"], "a+") as datafile:
        datafile.write(str(datetime.date.today()) + "python:esgcet=" +
                       config["esgcet_version"] + "\n")

    esg_property_manager.set_property(
        "publisher_config", config["publisher_config"])
    esg_property_manager.set_property(
        "publisher_home", config["publisher_home"])
    esg_property_manager.set_property("monitor.esg.ini", os.path.join(config[
                                    "publisher_home"], config["publisher_config"]))
    return 0

def main():
    setup_publisher()
    run_esgsetup()
    run_esginitialize()
    write_esgcet_install_log()
    write_esgcet_env()

if __name__ == '__main__':
    main()
