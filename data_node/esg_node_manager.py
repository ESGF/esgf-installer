'''Installs the ESGF Node Manager webapp'''
import os
import shutil
import logging
import grp
import zipfile
import errno
import tarfile
import ConfigParser
import glob
import pwd
import yaml
from esgf_utilities import pybash
from esgf_utilities import esg_functions
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from base.esg_tomcat_manager import stop_tomcat
from base import esg_postgres

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

CURRENT_DIRECTORY = os.path.join(os.path.dirname(__file__))

def check_for_existing_node_manager():
    '''Check for existing node manager installation'''
    print "Checking for node manager {}".format(config["esgf_node_manager_version"])
    update_node_manager = esg_property_manager.get_property("update.node.manager")
    if esg_version_manager.check_webapp_version("esgf-node-manager", config["esgf_node_manager_version"]) and update_node_manager.lower() not in ["yes", "y"]:
        print "\n Found existing version of the node-manager [OK]"
        return True

    node_manager_service_app_home = esg_property_manager.get_property(
        "node_manager_service_app_home")
    if os.path.isdir(node_manager_service_app_home):
        print "Detected an existing node manager installation..."
        installation_answer = raw_input(
            "Do you want to continue with node manager installation and setup? [Y/n]") or "y"
        if installation_answer.lower() not in ["y", "yes"]:
            print "Skipping node manager installation and setup - will assume it's setup properly"
            return True

        backup_node_manager(node_manager_service_app_home, "esgcet")


def backup_node_manager(node_manager_service_app_home, node_db_name):
    backup_default_answer = "Y"
    backup_answer = raw_input("Do you want to make a back up of the existing distribution [esgf-node-manager]? [Y/n] ") or backup_default_answer
    if backup_answer.lower in ["yes", "y"]:
        print "Creating a backup archive of this web application [{}]".format(node_manager_service_app_home)
        esg_functions.backup(node_manager_service_app_home)

    backup_db_default_answer = "Y"
    backup_db_answer = raw_input("Do you want to make a back up of the existing database [{}:esgf_node_manager]?? [Y/n] ".format(
        config["node_db_name"])) or backup_db_default_answer

    if backup_db_answer.lower() in ["yes", "y"]:
        print "Creating a backup archive of the manager database schema [{}:esgf_node_manager]".format(config["node_db_name"])
        esg_postgres.backup_db(node_db_name)

def download_node_manager_tarball(node_dist_file, node_dist_url):
    '''Download node manager tarball from mirror'''
    esg_functions.download_update(node_dist_file, node_dist_url)

def delete_old_node_manager(node_dist_dir):
    '''Delete previously installed node manager'''
    # make room for new install
    print "Removing Previous Installation of the ESGF Node Manager... ({node_dist_dir})".format(node_dist_dir=node_dist_dir)
    try:
        shutil.rmtree(node_dist_dir)
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass
    else:
        logger.info("Deleted directory: %s", node_dist_dir)

    clean_node_manager_webapp_subsystem()

def untar_node_manager(node_dist_file):
    '''Extract node manager tarball'''
    print "unpacking {node_dist_file}...".format(node_dist_file=node_dist_file)
    try:
        tar = tarfile.open(node_dist_file)
        tar.extractall()
        tar.close()
    except Exception, error:
        logger.error(error)
        raise RuntimeError("Could not extract the ESG Node Manager file: {}".format(node_dist_file))

def setup_node_manager():
    '''Installs the ESGF Node Manager'''
    print "*******************************"
    print "Setting up The ESGF Node Manager..."
    print "*******************************"

    if check_for_existing_node_manager():
        return

    node_manager_service_app_home = esg_property_manager.get_property(
        "node_manager_service_app_home")


    pybash.mkdir_p(config["workdir"])
    with pybash.pushd(config["workdir"]):
        logger.debug("changed directory to : %s", os.getcwd())

        esg_dist_url = esg_property_manager.get_property("esg.dist.url")
        node_dist_url = "{}/esgf-node-manager/esgf-node-manager-{}.tar.gz".format(
            esg_dist_url, config["esgf_node_manager_version"])
        node_dist_file = pybash.trim_string_from_head(node_dist_url)
        node_dist_dir = "esgf-node-manager-{}".format(config["esgf_node_manager_version"])

        download_node_manager_tarball(node_dist_file, node_dist_url)

        delete_old_node_manager(node_dist_dir)

        untar_node_manager(node_dist_file)

        with pybash.pushd(node_dist_dir):
            logger.debug("changed directory to : %s", os.getcwd())
            stop_tomcat()

            #----------------------------
            pybash.mkdir_p(node_manager_service_app_home)
            node_manager_properties_file = "esgf-node-manager.properties"

            # NOTE: The saving of the last config file must be done *BEFORE* we untar the new distro!
            if os.path.isfile("/usr/local/tomcat/webapps/esgf-node-manager/WEB-INF/classes/{}".format(node_manager_properties_file)):
                esg_functions.create_backup_file("WEB-INF/classes/{}".format(node_manager_properties_file), ".saved")
                for file_name in glob.glob("WEB-INF/classes/{}*".format(node_manager_properties_file)):
                    try:
                        os.chmod(file_name, 0600)
                    except OSError, error:
                        logger.error(error)
            node_war_file = "esgf-node-manager.war"
            logger.info("Expanding war %s in %s", node_war_file, node_manager_service_app_home)
            with zipfile.ZipFile(node_war_file, 'r') as node_war:
                node_war.extractall(node_manager_service_app_home)


    write_node_manager_config()
    esgf_node_manager_egg_file = "esgf_node_manager-{}-py{}.egg".format(
        config["esgf_node_manager_db_version"], config["python_version"])
    node_db_node_manager_schema_name = "esgf_node_manager"
    node_db_name = "esgcet"
    configure_postgress(node_db_name, node_db_node_manager_schema_name, esgf_node_manager_egg_file, node_dist_dir)

    touch_generated_whitelist_files()
    write_node_manager_install_log()
    write_shell_contrib_command_file()

    fetch_shell_launcher()

    setup_nm_repo()



def setup_nm_repo():
    pass



def fetch_shell_launcher():
    '''Copies the shell launcher to the scripts directory'''
    shutil.copyfile(os.path.join(CURRENT_DIRECTORY, "node_manager_conf/esgf-sh"), "{}/esgf-sh".format(config["scripts_dir"]))
    os.chmod("{}/esgf-sh".format(config["scripts_dir"]), 0755)

def write_shell_contrib_command_file():
    '''Copies the contrib_command file'''
    shutil.copyfile(os.path.join(CURRENT_DIRECTORY, "node_manager_conf/esgf_contrib_commands"), "/esg/config/esgf_contrib_commands")

def write_node_manager_db_install_log(node_manager_app_context_root):
    '''Writes node manager database configuration to the install manifest'''
    esg_functions.write_to_install_manifest("python:esgf_node_manager", "{}/webapps/{}".format(config["tomcat_install_dir"], node_manager_app_context_root), config["esgf_node_manager_db_version"])

def write_node_manager_install_log():
    '''Writes node manager configuration to the install manifest'''
    node_manager_service_app_home = esg_property_manager.get_property("node_manager_service_app_home")
    esg_functions.write_to_install_manifest("webapp:esgf-node-manager", node_manager_service_app_home, config["esgf_node_manager_version"])


def touch_generated_whitelist_files():
    '''Create whitelist files'''
    logger.info("Generating whitelist files")
    whitelist_files = ["esgf_ats.xml", "esgf_azs.xml", "esgf_idp.xml", "esgf_shards.xml"]
    tomcat_user_id = pwd.getpwnam(config["tomcat_user"]).pw_uid
    tomcat_group_id = grp.getgrnam(config["tomcat_group"]).gr_gid
    for file_name in whitelist_files:
        file_path = os.path.join("/esg", file_name)
        pybash.touch(file_path)
        os.chown(file_path, tomcat_user_id, tomcat_group_id)
        os.chmod(file_path, 0644)

    if os.path.exists("/esg/content/las/conf/server"):
        pybash.touch("/esg/content/las/conf/server/las_servers.xml")
        os.chown("/esg/content/las/conf/server/las_servers.xml", tomcat_user_id, tomcat_group_id)
        os.chmod("/esg/content/las/conf/server/las_servers.xml", 0644)

#--------------------------------------------------
#NOTE: This must be run AFTER the esg node web app
#      installation/configuration (setup_node_manager)
#--------------------------------------------------
def configure_postgress(node_db_name, node_db_node_manager_schema_name, esgf_node_manager_egg_file, node_dist_dir):
    '''Configure the databsse for the Node Manager'''
    print "*******************************"
    print "Configuring Postgres... for ESGF Node Manager"
    print "*******************************"

    esg_postgres.start_postgres()

    if node_db_name not in esg_postgres.postgres_list_dbs():
        esg_postgres.create_database(node_db_name)
    else:
        if node_db_node_manager_schema_name in esg_postgres.postgres_list_db_schemas():
            logger.info("Detected an existing node manager schema installation...")
        else:
            esg_postgres.postgres_clean_schema_migration("ESGF Node Manager")

    with pybash.pushd(os.path.join(config["workdir"], node_dist_dir)):

        #------------------------------------------------------------------------
        #Based on the node type selection we build the appropriate database tables
        #------------------------------------------------------------------------
        esg_dist_url = esg_property_manager.get_property("esg.dist.url")
        esg_functions.download_update(esgf_node_manager_egg_file, "{}/esgf-node-manager/{}".format(esg_dist_url, esgf_node_manager_egg_file))


        #install the egg....
        esg_functions.call_binary("easy_install", [esgf_node_manager_egg_file])

        if node_db_node_manager_schema_name in esg_postgres.postgres_list_db_schemas():
            schema_backup = raw_input("Do you want to make a back up of the existing database schema [{}:{}]? [Y/n]".format(node_db_name, node_db_node_manager_schema_name)) or "y"
            if schema_backup.lower() in ["y", "yes"]:
                print "Creating a backup archive of the database schema [{}:{}]".format(node_db_name, node_db_node_manager_schema_name)
                esg_postgres.backup_db(node_db_name, "dbsuper")


        pg_sys_acct_passwd = esg_functions.get_postgres_password()
        initialize_options = ["--dburl", "{}:{}@{}:{}/{}".format(config["postgress_user"], pg_sys_acct_passwd, config["postgress_host"], config["postgress_port"], node_db_name), "-c"]
        esg_functions.call_binary("esgf_node_manager_initialize", initialize_options)

        node_manager_app_context_root = "esgf-node-manager"
        write_node_manager_db_install_log(node_manager_app_context_root)


def write_node_manager_config():
    '''Writes the node manager config out to the config file'''
    esg_property_manager.set_property("db.driver", config["postgress_driver"])
    esg_property_manager.set_property("db.protocol", config["postgress_protocol"])
    esg_property_manager.set_property("db.host", config["postgress_host"])
    esg_property_manager.set_property("db.port", config["postgress_port"])
    esg_property_manager.set_property("db.user", config["postgress_user"])
    esg_property_manager.set_property("mail.notification.messageTemplateFile", "notification.template")
    esg_property_manager.set_property("mail.notification.initialDelay", "10")
    esg_property_manager.set_property("mail.notification.period", "30")
    esg_property_manager.set_property("metrics.initialDelay", "10")
    esg_property_manager.set_property("metrics.period", "30")
    esg_property_manager.set_property("metrics.query.limit", "100")
    esg_property_manager.set_property("monitor.initialDelay", "10")
    esg_property_manager.set_property("monitor.period", "30")
    esg_property_manager.set_property("monitor.buffer.meminfo", "1058")
    esg_property_manager.set_property("monitor.buffer.cpuinfo", "1250")
    esg_property_manager.set_property("monitor.buffer.uptime", "23")
    esg_property_manager.set_property("monitor.buffer.loadavg", "27")
    esg_property_manager.set_property("monitor.query.limit", "100")
    esg_property_manager.set_property("registry.initialDelay", "10")
    esg_property_manager.set_property("registry.period", "600")
    esg_property_manager.set_property("conn.ping.initialDelay", "5")
    esg_property_manager.set_property("conn.ping.period", "30")
    esg_property_manager.set_property("conn.mgr.initialDelay", "10")
    esg_property_manager.set_property("conn.mgr.period", "30")

#--------------------------------------
# Clean / Uninstall this module...
#--------------------------------------


def clean_node_manager_webapp_subsystem():
    pass


def main():
    '''Main function'''
    esgf_host = esg_functions.get_esgf_host()
    node_manager_app_context_root = "esgf-node-manager"

    try:
        node_use_ssl = bool(esg_property_manager.get_property("node_use_ssl"))
    except ConfigParser.NoOptionError:
        esg_property_manager.set_property("node_use_ssl", "True")
        node_use_ssl = True

    if node_use_ssl:
        protocol = "https"
    else:
        protocol = "http"
    node_manager_service_endpoint = "{}://{}/{}/node".format(protocol, esgf_host, node_manager_app_context_root)
    esg_property_manager.set_property(
        "node_manager_service_endpoint", node_manager_service_endpoint)

    try:
        node_use_ips = bool(esg_property_manager.get_property("node_use_ips"))
    except ConfigParser.NoOptionError:
        esg_property_manager.set_property("node_use_ips", "True")
        node_use_ips = True

    try:
        node_poke_timeout = esg_property_manager.get_property("node_poke_timeout")
    except ConfigParser.NoOptionError:
        esg_property_manager.set_property("node_poke_timeout", 6000)

    esg_property_manager.set_property("node_manager_service_app_home", "{}/webapps/{}".format(config["tomcat_install_dir"], node_manager_app_context_root))
    esg_property_manager.set_property("node_manager_service_endpoint", "https://{}/esgf-nm/".format(esgf_host))

    #Database information....
    node_db_node_manager_schema_name = "esgf_node_manager"

    setup_node_manager()

if __name__ == '__main__':
    main()
