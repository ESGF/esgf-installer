"""ESG Security Module."""
import os
import logging
import shutil
import stat
import sys
import zipfile
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import pybash
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from base import esg_postgres

logger = logging.getLogger("esgf_logger" + "." + __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def setup_security(node_type_list, esg_dist_url):
    """Install The ESGF Security Services.

    - Takes boolean arg: 0 = setup / install mode (default)
                         1 = updated mode

    In setup mode it is an idempotent install (default)
    In update mode it will always pull down latest after archiving old
    """
    print "*******************************"
    print "Setting up ESGF Security Services"
    print "*******************************"
    currently_installed_version = esg_functions.get_version_from_install_manifest("esgf-security")
    if currently_installed_version:
        if esg_version_manager.compare_versions(currently_installed_version, config["esgf_security_version"]):
            print "A sufficient version of esgf-security is installed"
            return

    configure_postgress(node_type_list, esg_dist_url, config["esgf_security_version"])
    clean_security_webapp_subsystem()


def write_security_db_install_log(db_dir, esgf_security_version):
    """Write esgf-security settings to install manifest."""
    esg_functions.write_to_install_manifest("python:esgf_security", db_dir, esgf_security_version)


def configure_postgress(node_type_list, esg_dist_url, esgf_security_version=config["esgf_security_version"]):
    """Install the esgf_security schema."""
    # --------------------------------------------------
    # NOTE: This must be run AFTER the esg node web app
    #      installation/configuration (setup_node_manager)
    # --------------------------------------------------
    if "IDP" in node_type_list:

        print "*******************************"
        print "Configuring Postgres... for ESGF Security"
        print "*******************************"

        node_db_name = "esgcet"
        node_db_security_schema_name = "esgf_security"
        pg_sys_acct_passwd = esg_functions.get_postgres_password()
        if node_db_name not in esg_postgres.postgres_list_dbs(user_name="dbsuper", password=pg_sys_acct_passwd):
            esg_postgres.create_database(node_db_name)

        schema_list = esg_postgres.postgres_list_db_schemas(user_name="dbsuper", password=pg_sys_acct_passwd)
        logger.debug("schema list: %s", schema_list)
        if node_db_security_schema_name in schema_list:
            print "Detected an existing security schema installation..."
        else:
            esg_postgres.postgres_clean_schema_migration("ESGF Security")

        db_dir = os.path.join("{}/esgf-security-{}/db".format(config["workdir"], esgf_security_version))
        pybash.mkdir_p(db_dir)
        with pybash.pushd(db_dir):
            # ------------------------------------------------------------------------
            # Based on the node type selection we build the appropriate database tables
            # ------------------------------------------------------------------------
            esg_root_url = esg_property_manager.get_property("esg.root.url")
            python_version = "2.7"
            # https://aims1.llnl.gov/esgf/dist/devel/3.0/a/esgf-security/esgf_security-0.1.5-py2.7.egg
            esgf_security_egg_file = "esgf_security-{}-py{}.egg".format(config["esgf_security_db_version"], python_version)
            esgf_security_egg_url = "{}/devel/3.0/a/esgf-security/{}".format(esg_root_url, esgf_security_egg_file)

            # download the egg file from the distribution server is necessary....
            esg_functions.download_update(esgf_security_egg_file, esgf_security_egg_url)

            # install the egg....
            esg_functions.call_binary("easy_install", [esgf_security_egg_file])

            node_db_name = "esgcet"
            node_db_security_schema_name = "esgf_security"
            if node_db_security_schema_name in esg_postgres.postgres_list_db_schemas(user_name="dbsuper", password=pg_sys_acct_passwd):
                schema_backup = raw_input("Do you want to make a back up of the existing database schema [{}:{}]? [Y/n]".format(node_db_name, node_db_security_schema_name)) or "y"
                if schema_backup.lower() in ["y", "yes"]:
                    print "Creating a backup archive of the database schema [{}:{}]".format(node_db_name, node_db_security_schema_name)
                    esg_postgres.backup_db(node_db_name, "dbsuper")

            # run the code to build the database and install sql migration...
            pg_sys_acct_passwd = esg_functions.get_postgres_password()
            esgf_security_initialize_options = ["--dburl", "{}:{}@{}:{}/{}".format(config["postgress_user"], pg_sys_acct_passwd, config["postgress_host"], config["postgress_port"], node_db_name), "-c"]
            esg_functions.call_binary("esgf_security_initialize", esgf_security_initialize_options)
            write_security_db_install_log(db_dir, esgf_security_version)

    else:
        logger.debug("This function, configure_postgress(), is not applicable to current node type (%s)", set(node_type_list))


# ******************************************************************
# SECURITY SETUP
# ******************************************************************

def security_startup_hook(node_type_list):
    """Prepare esgf-security to start."""
    logger.info("Security Startup Hook: Setup policy and whitelists... ")
    _setup_policy_files(node_type_list)
    _setup_static_whitelists("ats", "idp")


def create_policy_files(policy_type, security_jar_file):
    """Create the policy files depending on the type argument (either local or common).

    :param type: The type of policy file to be created. Must either be 'local' or 'common'
    :returns: None
    :raises TypeError: raises an exception
    """
    policy_file_name = "esgf_policies"
    tmp_extract_dir = os.path.join("/esg", "tmp")
    internal_jar_path = "esg/security/config"
    full_extracted_jar_dir = os.path.join(tmp_extract_dir, internal_jar_path)
    logger.debug("full_extracted_jar_dir: %s", full_extracted_jar_dir)

    logger.debug("Creating %s policy files", type)
    if not os.path.isfile(os.path.join(config["esg_config_dir"], "esgf_policies_{}.xml".format(policy_type))):
        tmp_extract_dir = os.path.join(config["esg_root_dir"], "tmp")
        pybash.mkdir_p(tmp_extract_dir)
        with pybash.pushd(tmp_extract_dir):
            with zipfile.ZipFile(security_jar_file, 'r') as security_jar_zip:
                policy_name = "{policy_file_name}_{policy_type}.xml".format(policy_file_name=policy_file_name, policy_type=policy_type)
                policy_file_extraction_path = "{internal_jar_path}/{policy_name}".format(internal_jar_path=internal_jar_path, policy_name=policy_name)
                logger.info("Extracting %s from %s", policy_file_extraction_path, security_jar_file)
                security_jar_zip.extract(policy_file_extraction_path)
        shutil.copyfile(os.path.join(full_extracted_jar_dir, policy_name), os.path.join(config["esg_config_dir"], policy_name))

        tomcat_user_id = esg_functions.get_user_id("tomcat")
        tomcat_group_id = esg_functions.get_group_id("tomcat")
        policy_file_path = os.path.join(config["esg_config_dir"], policy_name)
        os.chown(policy_file_path, tomcat_user_id, tomcat_group_id)
        os.chmod(policy_file_path, 0640)


def _setup_policy_files(node_type_list):
    if "DATA" in node_type_list and "INDEX" in node_type_list:
        logger.debug("setup_policy_files()... ")

        if "DATA" in node_type_list:
            app_path = esg_property_manager.get_property("orp_security_authorization_service_app_home")
            security_jar_file = os.path.join(app_path, "WEB-INF", "lib", "esgf-security-{}.jar".format(config["esgf_security_version"]))
        elif "INDEX" in node_type_list:
            app_path = esg_property_manager.get_property("index_service_app_home")
            security_jar_file = os.path.join(app_path, "WEB-INF", "lib", "esgf-security-{}.jar".format(config["esgf_security_version"]))

        if not os.path.isfile(security_jar_file):
            logger.error("%s not found", security_jar_file)
            raise OSError

        logger.debug("Using security jar file: %s", security_jar_file)
        print "security_jar_file:", security_jar_file

        # If old named file exists rename
        # esgf_policies.xml -> esgf_policies_local.xml
        esgf_policy_file = os.path.join(config["esg_config_dir"], "esgf_policies.xml")
        if os.path.isfile(esgf_policy_file):
            shutil.move(esgf_policy_file, os.path.join(config["esg_config_dir"], "esgf_policies_local.xml"))
        # esgf_policies_static.xml -> esgf_policies_common.xml
        esgf_policy_static_file = os.path.join(config["esg_config_dir"], "esgf_policies_static.xml")
        if os.path.isfile(esgf_policy_static_file):
            shutil.move(esgf_policy_static_file, os.path.join(config["esg_config_dir"], "esgf_policies_common.xml"))

        create_policy_files("local", security_jar_file)
        create_policy_files("common", security_jar_file)


def update_idp_static_xml_permissions(whitelist_file_dir=config["esg_config_dir"]):
    """Update xml file permissions."""
    xml_file_path = os.path.join(whitelist_file_dir, "esgf_idp_static.xml")
    current_mode = os.stat(xml_file_path)
    try:
        os.chmod(xml_file_path, current_mode.st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    except OSError:
        raise


def _setup_static_whitelists(node_type_list, esgf_security_version):
    if "DATA" in node_type_list and "INDEX" in node_type_list and "IDP" in node_type_list:
        service_types = ["DATA", "INDEX", "IDP"]
        app_config_dir = "/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg/orp/orp/config"

        tmp_extract_dir = os.path.join("/esg", "tmp")
        internal_jar_path = "esg/security/config"
        full_extracted_jar_dir = os.path.join(tmp_extract_dir, internal_jar_path)

        # TODO: review and fix; poor design, security_jar_file would get overwritten if there are multiple node types
        if "DATA" in node_type_list:
            app_path = esg_property_manager.get_property("orp_security_authorization_service_app_home")
            security_jar_file = "{}/WEB-INF/lib/esgf-security-{}.jar".format(app_path, esgf_security_version)
        elif "INDEX" in node_type_list:
            app_path = esg_property_manager.get_property("index_service_app_home")
            security_jar_file = "{}/WEB-INF/lib/esgf-security-{}.jar".format(app_path, esgf_security_version)
        elif "IDP" in node_type_list:
            app_path = esg_property_manager.get_property("idp_service_app_home")
            security_jar_file = "{}/WEB-INF/lib/esgf-security-{}.jar".format(app_path, esgf_security_version)

        if not os.path.exists(security_jar_file):
            logger.error("Could not find security jar file %s", security_jar_file)
            sys.exit()

        logger.debug("Using security jar file: %s", security_jar_file)

        for service_type in service_types:
            esg_config_xml = os.path.join(config["esg_config_dir"], "esgf_{}_static.xml".format(service_type))
            app_config_xml = os.path.join(app_config_dir, "esgf_{}_static.xml".format(service_type))
            if not os.path.isfile(esg_config_xml) and os.path.isfile(app_config_xml):
                pybash.mkdir_p(tmp_extract_dir)
                with pybash.pushd(tmp_extract_dir):
                    with zipfile.ZipFile(security_jar_file, 'r') as security_jar_zip:
                        static_file_path = "{}/esgf_{}_static.xml".format(internal_jar_path, service_type)
                        logger.info("Extracting %s from %s", static_file_path, security_jar_file)
                        security_jar_zip.extract(static_file_path)
                    shutil.copyfile(os.path.join(full_extracted_jar_dir, "esgf_{}_static.xml".format(service_type)), config["esg_config_dir"])

                    tomcat_user_id = esg_functions.get_user_id("tomcat")
                    tomcat_group_id = esg_functions.get_group_id("tomcat")
                    service_type_static = os.path.join(config["esg_config_dir"], "esgf_{}_static.xml".format(service_type))
                    os.chown(service_type_static, tomcat_user_id, tomcat_group_id)
                    os.chmod(service_type_static, 0640)
    else:
        logger.debug("This function, _setup_static_whitelists(), is not applicable to current node type (%s)", node_type_list)


# --------------------------------------
# Clean / Uninstall this module...
# --------------------------------------
def clean_security_webapp_subsystem():
    """Remove the deprecated esgf-security webapp if found on system."""
    # TODO: Look up removing property from esgf.properties and install_manifest
    # remove_property security_app_home

    security_webapp_path = "{}/webapps/esgf-security".format(config["tomcat_install_dir"])
    if os.path.isdir(security_webapp_path):
        logger.info("Removing deprecated esgf-security webapp")
        esg_functions.backup(security_webapp_path)
        shutil.rmtree(security_webapp_path)
