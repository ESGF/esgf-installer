'''
    ESGCET Package (Publisher) functions
'''
import os
import datetime
import logging
import ConfigParser
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import esg_property_manager
from esgf_utilities import pybash
from esgf_utilities.esg_env_manager import EnvWriter
from plumbum.commands import ProcessExecutionError


logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def check_publisher_version():
    '''Check if an existing version of the Publisher is found on the system'''
    return esg_functions.pip_version("esgcet")

def edit_esg_ini(node_short_name="test_node"):
    '''Edit placeholder values in the generated esg.ini file'''
    esg_ini_path = "/esg/config/esgcet/esg.ini"
    esg_functions.replace_string_in_file(esg_ini_path, "esgcetpass", esg_functions.get_publisher_password())
    esg_functions.replace_string_in_file(esg_ini_path, "host.sample.gov", esg_functions.get_esgf_host())
    esg_functions.replace_string_in_file(esg_ini_path, "LASatYourHost", "LASat{}".format(node_short_name))

def generate_esgsetup_options():
    '''Generate the string that will pass arguments to esgsetup to initialize the database'''
    try:
        publisher_db_user = config["publisher_db_user"]
    except KeyError:
        publisher_db_user = esg_property_manager.get_property("publisher_db_user")

    security_admin_password = esg_functions.get_security_admin_password()
    publisher_password = esg_functions.get_publisher_password()

    esgsetup_options = ["--db", "--minimal-setup", "--db-name", config["db_database"], "--db-admin", config["postgress_user"], "--db-admin-password", security_admin_password, "--db-user", publisher_db_user, "--db-user-password", publisher_password, "--db-host", config["postgress_host"], "--db-port", config["postgress_port"]]

    logger.info("esgsetup_options: %s", " ".join(esgsetup_options))
    return esgsetup_options

def run_esgsetup():
    '''generate esg.ini file using esgsetup script; #Makes call to esgsetup - > Setup the ESG publication configuration'''
    print "\n*******************************"
    print "Creating config file (esg.ini) with esgsetup"
    print "******************************* \n"

    os.environ["UVCDAT_ANONYMOUS_LOG"] = "no"
    #Create an initial ESG configuration file (esg.ini); TODO: make break into separate function
    try:
        esg_org_name = esg_property_manager.get_property("esg.org.name")
    except ConfigParser.NoOptionError:
        raise

    #TODO: password should be replaced with esg_functions.get_publisher_password(); or not there at all like classic esg-node
    esg_setup_options = ["--config", "--minimal-setup", "--rootid", esg_org_name]

    try:
        esg_functions.call_binary("esgsetup", esg_setup_options)
    except ProcessExecutionError, err:
        logger.error("esgsetup failed")
        logger.error(err)
        raise

    edit_esg_ini()

    print "\n*******************************"
    print "Initializing database with esgsetup"
    print "******************************* \n"

    #TODO:break this into esgsetup_database()
    #Initialize the database
    esgsetup_options = generate_esgsetup_options()

    try:
        esg_functions.call_binary("esgsetup", esgsetup_options)
    except ProcessExecutionError, err:
        logger.error("esginitialize failed")
        logger.error(err)
        raise

def run_esginitialize():
    '''Run the esginitialize script to initialize the ESG node database.'''
    print "\n*******************************"
    print "Running esginitialize"
    print "******************************* \n"

    try:
        esg_functions.call_binary("esginitialize", ["-c"])
    except ProcessExecutionError, err:
        logger.error("esginitialize failed")
        logger.error(err)
        raise

def setup_publisher(tag=config["publisher_tag"]):
    '''Install ESGF publisher'''

    print "\n*******************************"
    print "Setting up ESGCET Package"
    print "******************************* \n"

    subdir = "src/python/esgcet"
    pkg_name = "esgcet"
    repo = "https://github.com/ESGF/esg-publisher.git"
    esg_functions.pip_install_git(repo, pkg_name, tag, subdir)
    pybash.mkdir_p("/esg/data/test")


def write_esgcet_env():
    '''Write Publisher environment properties to /etc/esg.env'''
    EnvWriter.export("ESG_ROOT_ID", esg_property_manager.get_property("esg.org.name"))

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

def esgcet_startup_hook():
    '''Prepares the Publisher for startup'''
    print "ESGCET (Publisher) Startup Hook: Setting perms... "
    esg_ini_path = os.path.join(config["publisher_home"], config["publisher_config"])
    if not os.path.exists(esg_ini_path):
        raise OSError("{} does not exists".format(esg_ini_path))
    os.chown(esg_ini_path, -1, esg_functions.get_group_id("tomcat"))
    os.chmod(esg_ini_path, 0644)


def set_index_peer(host=None, index_type="p2p"):
    '''Setting the (index peer) node to which we will publish
       This is how we make sure that the publisher is pointing to the correct publishing service.
       We edit the esg.ini file with the information in the esgf.properties file, specifically the hessian_service_url value in esg.ini
    '''
    if not host:
        try:
            index_peer = esg_property_manager.get_property("esgf_index_peer")
        except ConfigParser.NoOptionError:
            print "Could not find esgf_index_peer"
            return
    if host == "localhost" or host == "self":
        index_peer = esg_functions.get_esgf_host()

    print "Setting Index Peer... to => [{}] (endpoint type = {})".format(index_peer, index_type)

    #Fetch and Insert the Certificate for Index Peer (to let in index peer's publishingService callback)
    register(index_peer)

    try:
        publishing_service_endpoint = esg_property_manager.get_property("publishing_service_endpoint")
    except ConfigParser.NoOptionError:
        print "publishing_service_endpoint property hasn't been set in esgf.properties"

    if index_type == "gateway":
        publishing_service_endpoint = "https://{}/remote/secure/client-cert/hessian/publishingService".format(index_peer)
    else:
        publishing_service_endpoint = "https://{}/esg-search/remote/secure/client-cert/hessian/publishingService".format(index_peer)

    publisher_config_path = os.path.join(config["publisher_home"], config["publisher_config"])
    esg_property_manager.set_property("hessian_service_url", publishing_service_endpoint, property_file=publisher_config_path, section_name="DEFAULT")

    esg_property_manager.set_property("esgf_index_peer", index_peer.rsplit("/", 1)[0])
    esg_property_manager.set_property("publishing_service_endpoint", publishing_service_endpoint)



def main():
    '''Main function'''
    if os.path.isfile(os.path.join(config["publisher_home"], config["publisher_config"])):
        try:
            publisher_install = esg_property_manager.get_property("update.publisher")
        except ConfigParser.NoOptionError:
            publisher_install = raw_input("Detected an existing esgcet installation. Do you want to continue with the Publisher installation [y/N]: ") or "no"

        if publisher_install.lower() in ["no", "n"]:
            print "Using existing Publisher installation.  Skipping setup."
            return
    setup_publisher()
    run_esgsetup()
    run_esginitialize()
    write_esgcet_install_log()
    write_esgcet_env()

if __name__ == '__main__':
    main()
