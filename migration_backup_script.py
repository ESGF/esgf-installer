import sys, getopt, os
import datetime
import StringIO
import ConfigParser
from backports import configparser
from esgf_utilities import esg_functions, pybash
from base import esg_postgres

def check_previous_install():
    return os.path.exists("/usr/local/bin/esg-node")


#TODO: Create a function to port values from old config files to new esgf.properties file

def add_config_file_section_header(config_file_name, section_header):
    '''INI-style config files in 2.x typically do not have section headers that are required to be parsed by ConfigParser. This function will add the required section headers'''

    config = StringIO.StringIO()
    config.write('[{}]\n'.format(section_header))
    config.write(open(config_file_name).read())
    config.seek(0, os.SEEK_SET)

    parser = configparser.ConfigParser()
    parser.read(config)

    with open(config_file_name, "w") as file_object:
        parser.write(file_object, space_around_delimiters=False)


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
    directories_to_backup = ["/usr/local/tomcat", "/usr/local/solr", "/etc/grid-security", "/esg/config", "/usr/local/cog/cog_config", "/etc/esgfcerts", "/etc/certs"]
    for directory in directories_to_backup:
        esg_functions.backup(directory, migration_backup_dir)

    files_to_backup = ["/esg/content/thredds/catalog.xml", "/esg/config/esgf.properties", "/esg/esgf-install-manifest", "/etc/esg.env", "/esg/config/config_type"]
    for file_name in files_to_backup:
        esg_functions.create_backup_file(file_name, backup_dir=migration_backup_dir)

    add_config_file_section_header(os.path.join(migration_backup_dir, "esgf.properties-{}.bak".format(str(datetime.date.today()))), "installer.properties")
    add_config_file_section_header(os.path.join(migration_backup_dir, "esgf-install-manifest-{}.bak".format(str(datetime.date.today()))), "install_manifest")


def main(argv):
    if check_previous_install():
        backup_esg_installation()


if __name__ == "__main__":
   main(sys.argv)
