import os
import logging
import shutil
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from base import esg_postgres

logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def setup_security(node_type_list, esg_dist_url):
    #####
    # Install The ESGF Security Services
    #####
    # - Takes boolean arg: 0 = setup / install mode (default)
    #                      1 = updated mode
    #
    # In setup mode it is an idempotent install (default)
    # In update mode it will always pull down latest after archiving old
    #
    esgf_security_version = "1.2.8"
    currently_installed_version = esg_functions.get_version_from_manifest("esgf-security")
    if currently_installed_version:
        if esg_version_manager.compare_versions(currently_installed_version, esgf_security_version):
            print "A sufficient version of esgf-security is installed"
            return

    configure_postgress(node_type_list, esg_dist_url, esgf_security_version)
    fetch_user_migration_launcher(node_type_list, esg_dist_url)
    fetch_policy_check_launcher(node_type_list, esg_dist_url)
    clean_security_webapp_subsystem()


def write_security_db_install_log(db_dir, esgf_security_version):
    esg_functions.write_to_install_manifest("python:esgf_security", db_dir, esgf_security_version)

def configure_postgress(node_type_list, esg_dist_url, esgf_security_version):
    #--------------------------------------------------
    #NOTE: This must be run AFTER the esg node web app
    #      installation/configuration (setup_node_manager)
    #--------------------------------------------------
    if "IDP" in node_type_list:

        print "*******************************"
        print "Configuring Postgres... for ESGF Security"
        print "*******************************"

        node_db_name = "esgcet"
        node_db_security_schema_name = "esgf_security"
        if node_db_name not in esg_postgres.postgres_list_dbs():
            esg_postgres.create_database(node_db_name)

        if node_db_security_schema_name in esg_postgres.postgres_list_db_schemas():
            print "Detected an existing security schema installation..."
        else:
            esg_postgres.postgres_clean_schema_migration("ESGF Security")

        db_dir = os.path.join("{}/esgf-security-{}/db".format(config["workdir"], esgf_security_version))
        esg_bash2py.mkdir_p(db_dir)
        with esg_bash2py.pushd(db_dir):
            #------------------------------------------------------------------------
            #Based on the node type selection we build the appropriate database tables
            #------------------------------------------------------------------------
            esgf_security_db_version = "0.1.4"
            #TODO: bump this version to 2.7
            python_version = "2.6"
            esgf_security_egg_file = "esgf_security-{}-py{}.egg".format(esgf_security_db_version, python_version)
            esgf_security_egg_url = "{}/esgf-security/{}".format(esg_dist_url, esgf_security_egg_file)

            #download the egg file from the distribution server is necessary....
            esg_functions.download_update(esgf_security_egg_file, esgf_security_egg_url)

            #install the egg....
            # esg_functions.stream_subprocess_output("conda install -y postgresql")
            #TODO: update this to use setuptools
            esg_functions.stream_subprocess_output("easy_install {}".format(esgf_security_egg_file))

            node_db_name= "esgcet"
            node_db_security_schema_name="esgf_security"
            if node_db_security_schema_name in esg_postgres.postgres_list_db_schemas():
                schema_backup = raw_input("Do you want to make a back up of the existing database schema [{}:{}]? [Y/n]".format(node_db_name, node_db_security_schema_name)) or "y"
                if schema_backup.lower() in ["y", "yes"]:
                    print "Creating a backup archive of the database schema [{}:{}]".format(node_db_name, node_db_security_schema_name)
                    esg_postgres.backup_db(node_db_name, "dbsuper")

            #run the code to build the database and install sql migration...
            pg_sys_acct_passwd = esg_functions.get_postgres_password()
            esgf_security_initialize_command = "esgf_security_initialize --dburl {postgress_user}:{pg_sys_acct_passwd}@{postgress_host}:{postgress_port}/{node_db_name} -c".format(postgress_user=config["postgress_user"], pg_sys_acct_passwd=pg_sys_acct_passwd, postgress_host=config["postgress_host"], postgress_port=config["postgress_port"], node_db_name=node_db_name)
            esg_functions.stream_subprocess_output(esgf_security_initialize_command)

            write_security_db_install_log(db_dir, esgf_security_version)

    else:
        logger.debug("This function, configure_postgress(), is not applicable to current node type ({})".format(set(node_type_list)))


#******************************************************************
# SECURITY SETUP
#******************************************************************

def security_startup_hook(node_type_list, esgf_security_version):
    logger.info("Security Startup Hook: Setup policy and whitelists... ")
    _setup_policy_files(node_type_list, esgf_security_version)
    _setup_static_whitelists("ats", "idp")


def _setup_policy_files(node_type_list, esgf_security_version):
    if "DATA" in node_type_list and "INDEX" in node_type_list:
        logger.debug("setup_policy_files()... ")

        tmp_extract_dir = os.path.join("esg", "tmp")
        policy_file_name = "esgf_policies"
        internal_jar_path = "esg/security/config"
        full_extracted_jar_dir = os.path.join(tmp_extract_dir, internal_jar_path)

        if "DATA" in node_type_list:
            app_path = esg_property_manager.get_property("orp_security_authorization_service_app_home")
            security_jar_file = os.path.join(app_path, "WEB-INF", "lib", "esgf-security-{}.jar".format(esgf_security_version))
        elif "INDEX" in node_type_list:
            app_path = esg_property_manager.get_property("index_service_app_home")
            security_jar_file = os.path.join(app_path, "WEB-INF", "lib", "esgf-security-{}.jar".format(esgf_security_version))

        if not os.path.isfile(security_jar_file):
            esg_functions.exit_with_error("Could not determine location of security jar, exiting...")

        logger.debug("Using security jar file: %s", security_jar_file)

        #If old named file exists rename
        # esgf_polcies.xml -> esgf_policies_local.xml
        esgf_policy_file = os.path.join(config["esg_config_dir"], "esgf_policies.xml")
        if os.path.isfile(esgf_policy_file):
            shutil.move(esgf_policy_file, os.path.join(config["esg_config_dir"], "esgf_policies_local.xml"))

        esgf_policy_static_file = os.path.join(config["esg_config_dir"], "esgf_policies_static.xml")
        if os.path.isfile(esgf_policy_static_file):
            shutil.move(esgf_policy_static_file, os.path.join(config["esg_config_dir"], "esgf_policies_common.xml"))

        if not os.path.isfile(os.path.join(config["esg_config_dir"], "esgf_policies_local.xml")):
            tmp_extract_dir = os.path.join(config["esg_root_dir"], "tmp")
            esg_bash2py.mkdir_p(tmp_extract_dir)
            with esg_bash2py.pushd(tmp_extract_dir):
                esg_functions.stream_subprocess_output("/usr/local/java/bin/jar xvf {security_jar_file} {internal_jar_path}/{policy_file_name}_local.xml".format(security_jar_file=security_jar_file, internal_jar_path=internal_jar_path, policy_file_name=policy_file_name))
            shutil.copyfile(os.path.join(full_extracted_jar_dir, policy_file_name+"_common.xml"), config["esg_config_dir"])

            tomcat_user_id = esg_functions.get_user_id("tomcat")
            tomcat_group_id = esg_functions.get_group_id("tomcat")
            policy_file_common = os.path.join(config["esg_config_dir"], policy_file_name+"_common.xml")
            os.chown(policy_file_common, tomcat_user_id, tomcat_group_id)
            os.chmod(policy_file_common, 0640)


def _setup_static_whitelists(node_type_list, esgf_security_version):
    if "DATA" in node_type_list and "INDEX" in node_type_list and "IDP" in node_type_list:
        service_types = ["DATA", "INDEX", "IDP"]
        app_config_dir = "/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg/orp/orp/config"

        tmp_extract_dir = os.path.join("esg", "tmp")
        internal_jar_path = "esg/security/config"
        full_extracted_jar_dir = os.path.join(tmp_extract_dir, internal_jar_path)

        if "DATA" in node_type_list:
            app_path = esg_property_manager.get_property("orp_security_authorization_service_app_home")
            security_jar_file="{}/WEB-INF/lib/esgf-security-{}.jar".format(app_path, esgf_security_version)
        elif "INDEX" in node_type_list:
            app_path = esg_property_manager.get_property("index_service_app_home")
            security_jar_file="{}/WEB-INF/lib/esgf-security-{}.jar".format(app_path, esgf_security_version)
        elif "IDP" in node_type_list:
            app_path = esg_property_manager.get_property("idp_service_app_home")
            security_jar_file="{}/WEB-INF/lib/esgf-security-{}.jar".format(app_path, esgf_security_version)
        else:
            esg_functions.exit_with_error("Could not find security jar file: esgf-security-{}.jar".format(esgf_security_version))

        logger.debug("Using security jar file: %s", security_jar_file)

        for service_type in service_types:
            esg_config_xml = os.path.join(config["esg_config_dir"], "esgf_{}_static.xml".format(service_type))
            app_config_xml = os.path.join(app_config_dir, "esgf_{}_static.xml".format(service_type))
            if not os.path.isfile(esg_config_xml) and os.path.isfile(app_config_xml):
                esg_bash2py.mkdir_p(tmp_extract_dir)
                with esg_bash2py.pushd(tmp_extract_dir):
                    esg_functions.stream_subprocess_output("/usr/local/java/bin/jar xvf {security_jar_file} {internal_jar_path}/esgf_{service_type}_static.xml".format(security_jar_file=security_jar_file, internal_jar_path=internal_jar_path, service_type=service_type))
                    shutil.copyfile(os.path.join(full_extracted_jar_dir, "esgf_{}_static.xml".format(service_type)), config["esg_config_dir"])

                    tomcat_user_id = esg_functions.get_user_id("tomcat")
                    tomcat_group_id = esg_functions.get_group_id("tomcat")
                    service_type_static = os.path.join(config["esg_config_dir"], "esgf_{}_static.xml".format(service_type))
                    os.chown(service_type_static, tomcat_user_id, tomcat_group_id)
                    os.chmod(service_type_static, 0640)
    else:
        logger.debug("This function, _setup_static_whitelists(), is not applicable to current node type (%s)", node_type_list)

#******************************************************************
#******************************************************************


#--------------------------------------
# Clean / Uninstall this module...
#--------------------------------------
def clean_security_webapp_subsystem():
    '''Removes the deprecated esgf-security webapp if found on system'''
    #TODO: Look up removing property from esgf.properties and install_manifest
    # remove_property security_app_home

    security_webapp_path = "{}/webapps/esgf-security".format(config["tomcat_install_dir"])
    if os.path.isdir(security_webapp_path):
        logger.info("Removing deprecated esgf-security webapp")
        esg_functions.backup(security_webapp_path)
        shutil.rmtree(security_webapp_path)



def fetch_user_migration_launcher(node_type_list, esg_dist_url):
    if "IDP" in node_type_list:
        with esg_bash2py.pushd(config["scripts_dir"]):
            security_web_service_name = "esgf-security"
            esgf_user_migration_launcher = "esgf-user-migrate"
            esgf_user_migration_launcher_url = "{}/{}/{}".format(esg_dist_url, security_web_service_name, esgf_user_migration_launcher)
            esg_functions.download_update(esgf_user_migration_launcher, esgf_user_migration_launcher_url)
            os.chmod(esgf_user_migration_launcher, 0755)
    else:
        logger.debug("This function, fetch_user_migration_launcher(), is not applicable to current node type ({})".format(set(node_type_list)))

def fetch_policy_check_launcher(node_type_list, esg_dist_url):
    if "IDP" in node_type_list and "DATA" in node_type_list:
        with esg_bash2py.pushd(config["scripts_dir"]):
            security_web_service_name = "esgf-security"
            esgf_policy_check_launcher = "esgf-policy-check"
            esgf_user_migration_launcher = "esgf-user-migrate"
            esgf_policy_check_launcher_url = "{}/{}/{}".format(esg_dist_url, security_web_service_name, esgf_policy_check_launcher)
            esg_functions.download_update(esgf_policy_check_launcher, esgf_policy_check_launcher_url)
            os.chmod(esgf_user_migration_launcher, 0755)
    else:
        logger.debug("This function, fetch_policy_check_launcher(), is not applicable to current node type ({})".format(set(node_type_list)))
