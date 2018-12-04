import sys
import getopt
import re
import os
import shutil
import errno
import datetime
import StringIO
import ConfigParser
import yaml
from backports import configparser
from esgf_utilities import esg_functions, pybash
from base import esg_postgres


def copy_tomcat_env_file():
    '''Copies the setenv.sh Tomcat file'''
    CATALINA_HOME = "/usr/local/tomcat"
    shutil.copy("base/tomcat_conf/setenv.sh", os.path.join(CATALINA_HOME, "bin"))

def copy_previous_component_versions():
    print "\n*******************************"
    print "Copying settings from 2.x esg-init to 3.0 esg_config.yaml file"
    print "******************************* \n"
    previous_versions = {}
    with open("/usr/local/bin/esg-init") as init_file:
        for line in init_file:
            try:
                key, val = line.split("=")
                if "version" in key:
                    version_number = re.search(r"\d.*", val).group().strip('"}')
                    previous_versions[key.strip()] = version_number
            except ValueError:
                pass
    print "previous_versions:", previous_versions
    yaml_config = os.path.join(os.path.dirname(__file__), "esg_config.yaml")
    with open(yaml_config) as yaml_file:
        config_settings = yaml.load(yaml_file)

    print "config_settings:", config_settings
    for key, version in previous_versions.iteritems():
        print "key:", key
        print "version:", version
        config_settings[key] = version

    with open(yaml_config, "w") as yaml_file:
        yaml.dump(config_settings, yaml_file)


def check_previous_install():
    return os.path.exists("/usr/local/bin/esg-node")


def copy_previous_settings(old_config_file, new_config_file):
    print "\n*******************************"
    print "Copying settings from 2.x esgf.properties to 3.0 esgf.properties file"
    print "******************************* \n"
    old_parser = configparser.ConfigParser()
    try:
        old_parser.read(old_config_file)
    except configparser.DuplicateSectionError:
        pass

    previous_values = dict(old_parser.items('installer.properties'))

    new_parser = configparser.ConfigParser()
    new_parser.read(new_config_file)

    for key, value in previous_values.iteritems():
        new_parser["installer.properties"][key] = str(value)

    with open(new_config_file, "w") as file_object:
        new_parser.write(file_object, space_around_delimiters=False)

#TODO: Create a function to port values from old config files to new esgf.properties file
def copy_config_settings(old_config_file, new_config_file):
    '''Copy settings from existing config file to ESGF 3.0 config file'''
    parser = configparser.ConfigParser()
    parser.read(old_config_file)

    old_values = dict(parser.items('Section'))
    logger.debug("old config values: %s", old_values)

    new_parser = configparser.ConfigParser()
    new_parser.read(new_config_file)

    for key, value in old_values.iteritems():
        parser["installer.properties"][key] = str(value)

    with open(property_file, "w") as file_object:
        parser.write(file_object, space_around_delimiters=False)


def add_config_file_section_header(config_file_name, section_header):
    '''INI-style config files in 2.x typically do not have section headers that are required to be parsed by ConfigParser. This function will add the required section headers'''
    print "\n*******************************"
    print "Adding section header to {}".format(config_file_name)
    print "******************************* \n"
    config = StringIO.StringIO()
    config.write('[{}]\n'.format(section_header))
    config.write(open(config_file_name).read())
    config.seek(0, os.SEEK_SET)

    with open(config_file_name, "w") as file_object:
        shutil.copyfileobj(config, file_object)


def migrate_solr_shards_config_file(config_file_path):
    '''Copy over settings from the esgf_shards.config file and format it so it can be parsed by ConfigParser'''
    parser = configparser.ConfigParser()
    parser.add_section("esgf_solr_shards")

    with open(config_file_path) as shard_config:
        for line in shard_config:
            if "[esgf_solr_shards]" in line:
                return
            line = line.strip()
            if line:
                key, val = line.split(":")
                print "key:", key
                print "value:", val
                parser["esgf_solr_shards"][key] = str(val)

    with open("/esg/config/esgf_shards.config", "w") as shard_config:
        parser.write(shard_config, space_around_delimiters=False)


def backup_esg_installation():
    '''From https://github.com/ESGF/esgf-installer/wiki/ESGF-Pre-Installation-Backup

         /usr/local/tomcat (contains Tomcat configuration and web applications)
         /usr/local/esgf-solr-5.2.1 (contains the Solr configuration for the local and remote shards)
         /esg/config (contains ESGF configuration for various applications)
         /esg/solr-index (contains the Solr indexes for the local and remote shards)
         /etc/grid-security (contains trusted X509 certificates)
         /esg/content/thredds/catalog.xml (Thredds Master Catalog XML File)
         /usr/local/cog/cog_config (Local CoG configuration not in the pg database)
         /etc/esgfcerts - (copy of the certificates used to setup globus)
         /etc/certs - (copy of certificates set up with Apache)

    '''
    #TODO: make default backup_directory
    print "\n*******************************"
    print "Backing up ESGF Installation"
    print "******************************* \n"
    migration_backup_dir = "/etc/esg_installer_backup_{}".format(str(datetime.date.today()))
    pybash.mkdir_p(migration_backup_dir)

    files_to_backup = ["/esg/content/thredds/catalog.xml", "/esg/config/esgf.properties", "/esg/esgf-install-manifest", "/etc/esg.env", "/esg/config/config_type", "/esg/config/esgf_shards.config"]
    for file_name in files_to_backup:
        try:
            esg_functions.create_backup_file(file_name, backup_dir=migration_backup_dir)
        except IOError, error:
            if error.errno == errno.ENOENT:
                pass

    # Remove old install manifest
    try:
        os.remove("/esg/esgf-install-manifest")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass

    properties_backup_path = os.path.join(migration_backup_dir, "esgf.properties-{}.bak".format(str(datetime.date.today())))
    try:
        add_config_file_section_header(properties_backup_path, "installer.properties")
    except IOError, error:
        if error.errno == errno.ENOENT:
            pass
    install_manifest_backup_path = os.path.join(migration_backup_dir, "esgf-install-manifest-{}.bak".format(str(datetime.date.today())))
    try:
        add_config_file_section_header(install_manifest_backup_path, "install_manifest")
    except IOError, error:
        if error.errno == errno.ENOENT:
            pass
    shards_config_backup_path = os.path.join(migration_backup_dir, "esgf_shards.config-{}.bak".format(str(datetime.date.today())))
    migrate_solr_shards_config_file(shards_config_backup_path)

    directories_to_backup = ["/usr/local/tomcat", "/usr/local/solr", "/etc/grid-security", "/esg/config", "/usr/local/cog/cog_config", "/etc/esgfcerts", "/etc/certs"]
    for directory in directories_to_backup:
        esg_functions.backup(directory, migration_backup_dir)

    current_directory = os.path.join(os.path.dirname(__file__))
    copy_previous_settings(properties_backup_path, os.path.join(current_directory, "esgf.properties.template"))
    copy_previous_component_versions()



def main(argv):
    if check_previous_install():
        backup_esg_installation()
        copy_tomcat_env_file()


if __name__ == "__main__":
   main(sys.argv)
