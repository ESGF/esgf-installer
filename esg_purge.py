import os
import shutil
import glob
import datetime
import errno
import logging
import psutil
import yaml
from esgf_utilities import esg_functions
from esgf_utilities.esg_exceptions import SubprocessError
from base import esg_tomcat_manager
from index_node import solr


logger = logging.getLogger("esgf_logger" +"."+ __name__)
with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def purge_postgres():
    '''Removes postgres installation via yum'''
    print "\n*******************************"
    print "Purging Postgres"
    print "******************************* \n"

    try:
        esg_functions.stream_subprocess_output("service postgresql stop")
    except SubprocessError, error:
        pass

    try:
        esg_functions.stream_subprocess_output("yum remove -y postgresql-server.x86_64 postgresql.x86_64 postgresql-devel.x86_64")
    except SubprocessError:
        pass

    try:
        # shutil.rmtree("/usr/local/pgsql")
        shutil.rmtree("/var/lib/pgsql")
        os.remove(os.path.join(os.environ["HOME"], ".pgpass"))
    except OSError:
        pass

def purge_tomcat():
    print "\n*******************************"
    print "Purging Tomcat"
    print "******************************* \n"

    esg_tomcat_manager.stop_tomcat()

    try:
        shutil.rmtree("/etc/logrotate.d/esgf_tomcat")
    except OSError, error:
        pass

    tomcat_directories = glob.glob("/usr/local/tomcat*")
    tomcat_directories.extend(glob.glob("/usr/local/apache-tomcat*"))
    for directory in tomcat_directories:
        try:
            shutil.rmtree(directory)
        except OSError:
            pass

    try:
        os.unlink("/usr/local/tomcat")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass
        else:
            logger.exception("Could not delete symlink /usr/local/tomcat")

    try:
        os.remove("/tmp/catalina.pid")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass

    # Tomcat may leave stuck java processes.  Kill them with extreme prejudice
    try:
        esg_functions.stream_subprocess_output("pkill -9 -f 'java.*/usr/local/tomcat'")
    except SubprocessError:
        pass

def purge_java():
    print "\n*******************************"
    print "Purging Java"
    print "******************************* \n"

    try:
        shutil.rmtree("/usr/local/{}".format(config["java_version"]))
    except OSError:
        pass

    try:
        shutil.rmtree("/usr/local/java")
    except OSError:
        pass

    try:
        shutil.rmtree("/usr/bin/java")
    except OSError:
        pass

def purge_ant():
    print "\n*******************************"
    print "Purging Ant"
    print "******************************* \n"
    try:
        esg_functions.stream_subprocess_output("yum remove -y ant")
    except SubprocessError:
        pass

def purge_thredds():
    print "\n*******************************"
    print "Purging Thredds"
    print "******************************* \n"

    try:
        shutil.rmtree("/usr/local/tomcat/webapps/thredds")
    except OSError:
        pass

def purge_base():
    print "\n*******************************"
    print "Purging Base ESGF Directories"
    print "******************************* \n"

    directories_to_delete = ["/esg", "/etc/certs", "/etc/esgfcerts",
    "/etc/tempcerts", "/opt/esgf", "/tmp/inputpipe", "/tmp/outputpipe", "/usr/local/cog", "/var/www/.python-eggs"]

    files_to_delete = ["/etc/httpd/conf/esgf-httpd.conf", "/usr/local/bin/add_checksums_to_map.sh"]
    for directory in directories_to_delete:
        try:
            print "Deleting {directory}: ".format(directory=directory)
            shutil.rmtree(directory)
        except OSError, error:
            pass

    for file_name in files_to_delete:
        try:
            print "Deleting {file_name}: ".format(file_name=file_name)
            os.remove(file_name)
        except OSError, error:
            pass

    # We want to potentially preserve certificates, as they may be
    # annoying to recreate and sign.
    if os.path.isfile("/etc/hostcert.pem"):
        logger.warning("preserving /etc/hostcert.pem to /tmp/hostcert-%s.pem",str(datetime.date.today()))
        shutil.move("/etc/hostcert.pem", "/tmp/hostcert-{DATETIME}.pem".format(DATETIME=str(datetime.date.today())))

    if os.path.isfile("/etc/hostkey.pem"):
        logger.warning("preserving /etc/hostkey.pem to /tmp/hostkey-%s.pem",str(datetime.date.today()))
        shutil.move("/etc/hostkey.pem", "/tmp/hostkey-{DATETIME}.pem".format(DATETIME=str(datetime.date.today())))


    # We don't need to preserve the certificate signing request
    try:
        os.remove("/etc/hostcert_request.pem")
    except OSError, error:
        pass

    # WARNING: if $HOME has been reset from /root during an install
    # run, these directories could show up in a different place!
    root_dirs = ["/root/.cache", "/root/.python-eggs"]
    for directory in root_dirs:
        try:
            shutil.rmtree(directory)
        except OSError, error:
            pass

    for directory in  glob.glob("/usr/local/esgf*"):
        for directory in root_dirs:
            try:
                shutil.rmtree(directory)
            except OSError, error:
                pass


def purge_cdat():
    pass


def purge_cog():
    try:
        shutil.rmtree("/usr/local/cog")
    except OSError:
        pass
    try:
        os.remove("/usr/local/bin/wait_for_postgres.sh")
    except OSError, error:
        pass
    try:
        os.remove("/usr/local/bin/wait_for_postgres.sh")
    except OSError, error:
        pass

def purge_apache():
    try:
        esg_functions.stream_subprocess_output("yum remove -y httpd httpd-devel mod_ssl")
    except SubprocessError:
        pass

    try:
        shutil.rmtree("/etc/httpd")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass

def purge_conda():
    try:
        shutil.rmtree("/usr/local/conda")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass

def purge_solr():

    solr.stop_solr()

    for directory in glob.glob("/usr/local/esgf-solr-*"):
        try:
            shutil.rmtree(directory)
        except OSError:
            pass

    for directory in glob.glob("/usr/local/solr-*"):
        try:
            shutil.rmtree(directory)
        except OSError:
            pass

    # Solr may leave stuck java processes.  Kill them with extreme prejudice
    try:
        esg_functions.stream_subprocess_output("pkill -9 -f 'java.*/usr/local/tomcat'")
    except SubprocessError:
        pass

#TODO: define purge_dashboard()
def purge_dashboard():
    pass

def confirm_purge():
    purged_directories = ["/var/lib/pgsql", "/usr/local/java", "/usr/bin/java", "/usr/local/tomcat", "/esg", "/etc/certs", "/etc/esgfcerts",
    "/etc/tempcerts", "/opt/esgf", "/tmp/inputpipe", "/tmp/outputpipe", "/usr/local/cog", "/var/www/.python-eggs", "/usr/local/solr", "/usr/local/cog", "/usr/local/conda"]

    for directory in purged_directories:
        if os.path.exists(directory):
            print "Purge failed.  {} still exists and must be delete manually.".format(directory)
            return

    print "All ESGF components have been successfully deleted."



def main():
    purge_postgres()
    purge_tomcat()
    purge_thredds()
    purge_ant()
    purge_java()
    purge_base()
    purge_cdat()
    purge_apache()
    purge_cog()
    # purge_conda()
    confirm_purge()

if __name__ == '__main__':
    main()
