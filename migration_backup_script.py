import sys, getopt, os, shutil
import datetime
import StringIO
import ConfigParser
from backports import configparser
from esgf_utilities import esg_functions, pybash
from base import esg_postgres

def check_previous_install():
    return os.path.exists("/usr/local/bin/esg-node")

def copy_previous_settings(old_config_file, new_config_file):
    print "\n*******************************"
    print "Copying settings from 2.x esgf.properties to 3.0 esgf.properties file"
    print "******************************* \n"
    old_parser = configparser.ConfigParser()
    old_parser.read(old_config_file)

    previous_values = dict(old_parser.items('installer.properties'))

    new_parser = configparser.ConfigParser()
    new_parser.read(new_config_file)

    for key, value in previous_values.iteritems():
        new_parser["installer.properties"][key] = str(value)

    with open(new_config_file, "w") as file_object:
        new_parser.write(file_object, space_around_delimiters=False)


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

    files_to_backup = ["/esg/content/thredds/catalog.xml", "/esg/config/esgf.properties", "/esg/esgf-install-manifest", "/etc/esg.env", "/esg/config/config_type"]
    for file_name in files_to_backup:
        esg_functions.create_backup_file(file_name, backup_dir=migration_backup_dir)

    #Remove old install manifest
    os.remove("/esg/esgf-install-manifest")

    properties_backup_path = os.path.join(migration_backup_dir, "esgf.properties-{}.bak".format(str(datetime.date.today())))
    add_config_file_section_header(properties_backup_path, "installer.properties")
    install_manifest_backup_path = os.path.join(migration_backup_dir, "esgf-install-manifest-{}.bak".format(str(datetime.date.today())))
    add_config_file_section_header(install_manifest_backup_path, "install_manifest")

    directories_to_backup = ["/usr/local/tomcat", "/usr/local/solr", "/etc/grid-security", "/esg/config", "/usr/local/cog/cog_config", "/etc/esgfcerts", "/etc/certs"]
    for directory in directories_to_backup:
        esg_functions.backup(directory, migration_backup_dir)

    current_directory = os.path.join(os.path.dirname(__file__))
    copy_previous_settings(properties_backup_path, os.path.join(current_directory, "esgf.properties.template"))



def main(argv):
    if check_previous_install():
        backup_esg_installation()


if __name__ == "__main__":
   main(sys.argv)
