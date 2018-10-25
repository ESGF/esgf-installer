import sys, getopt
import datetime
from esgf_utilities import esg_functions, pybash
from base import esg_postgres

def main(argv):
    #TODO: make default backup_directory
    migration_backup_dir = "/tmp/esg_installer_backup_{}".format(str(datetime.date.today()))
    pybash.mkdir_p(migration_backup_dir)
    directories_to_backup = ["/esg/config", "/esg/data", "/usr/local/cog_config", "/var/lib/pgsql/data"]
    for directory in directories_to_backup:
        esg_functions.backup(directory, migration_backup_dir)




if __name__ == "__main__":
   main(sys.argv)
