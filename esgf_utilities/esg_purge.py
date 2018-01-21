import os
import shutil
import glob
import datetime
import errno
import logging
from esgf_utilities import esg_functions
from esgf_utilities.esg_exceptions import SubprocessError

logger = logging.getLogger("esgf_logger" +"."+ __name__)

def purge_postgres():
    '''Removes postgres installation via yum'''
    print "\n*******************************"
    print "Purging Postgres"
    print "******************************* \n"

    try:
        esg_functions.stream_subprocess_output("service postgresql stop")
    except SubprocessError, error:
        print "Error stopping Postgres", error
    esg_functions.stream_subprocess_output("yum remove -y postgresql-server.x86_64 postgresql.x86_64 postgresql-devel.x86_64")
    try:
        # shutil.rmtree("/usr/local/pgsql")
        shutil.rmtree("/var/lib/pgsql")
        os.remove(os.path.join(os.environ["HOME"], ".pgpass"))
    except OSError, error:
        logger.exception("Could not delete /var/lib/pgsql")

def purge_tomcat():
    print "\n*******************************"
    print "Purging Tomcat"
    print "******************************* \n"

    # esg-node --stop may not actually cause Tomcat to exit properly,
    # so force-kill all remaining instances
    try:
        esg_functions.call_subprocess("pkill -9 -u tomcat")
    except SubprocessError, error:
        print "Error killing tomcat:", error
    try:
        shutil.rmtree("/etc/logrotate.d/esgf_tomcat")
    except OSError, error:
        logger.exception("Couldn't delete %s", "/etc/logrotate.d/esgf_tomcat")

    tomcat_directories = glob.glob("/usr/local/tomcat*")
    tomcat_directories.extend(glob.glob("/usr/local/apache-tomcat*"))
    for directory in tomcat_directories:
        try:
            shutil.rmtree(directory)
        except OSError:
            logger.exception("Couldn't delete %s", directory)
    try:
        os.unlink("/usr/local/tomcat")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass
        else:
            logger.exception("Could not delete symlink /usr/local/tomcat")

    # Tomcat may leave stuck java processes.  Kill them with extreme prejudice
    esg_functions.call_subprocess("pkill -9 -f 'java.*/usr/local/tomcat'")

def purge_java():
    print "\n*******************************"
    print "Purging Java"
    print "******************************* \n"

    try:
        shutil.rmtree("/usr/local/java")
    except OSError:
        logger.exception("No Java installation found to delete at /usr/local/java")

    try:
        shutil.rmtree("/usr/bin/java")
    except OSError:
        logger.exception("No Java installation found to delete at /usr/bin/java")

def purge_ant():
    print "\n*******************************"
    print "Purging Ant"
    print "******************************* \n"
    esg_functions.stream_subprocess_output("yum remove -y ant")

def purge_thredds():
    print "\n*******************************"
    print "Purging Thredds"
    print "******************************* \n"

    try:
        shutil.rmtree("/usr/local/tomcat/webapps/thredds")
    except OSError:
        logger.exception("Couldn't delete thredds")

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
            logger.exception("Couldn't delete %s", directory)

    for file_name in files_to_delete:
        try:
            print "Deleting {file_name}: ".format(file_name=file_name)
            os.remove(file_name)
        except OSError, error:
            logger.exception("Couldn't delete %s", directory)

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
        logger.exception("Could not delete /etc/hostcert_request.pem")

    # WARNING: if $HOME has been reset from /root during an install
    # run, these directories could show up in a different place!
    root_dirs = ["/root/.cache", "/root/.python-eggs"]
    for directory in root_dirs:
        try:
            shutil.rmtree(directory)
        except OSError, error:
            logger.exception("Couldn't delete %s", directory)

    for directory in  glob.glob("/usr/local/esgf*"):
        for directory in root_dirs:
            try:
                shutil.rmtree(directory)
            except OSError, error:
                logger.exception("Couldn't delete %s", directory)

    for directory in  glob.glob("/usr/local/esgf-solr-*"):
        for directory in root_dirs:
            try:
                shutil.rmtree(directory)
            except OSError, error:
                logger.exception("Couldn't delete %s", directory)

    for directory in  glob.glob("/usr/local/solr*"):
        for directory in root_dirs:
            try:
                shutil.rmtree(directory)
            except OSError, error:
                logger.exception("Couldn't delete %s", directory)

    # Solr may leave stuck java processes.  Kill them with extreme prejudice
    esg_functions.call_subprocess("pkill -9 -f 'java.*/usr/local/tomcat'")

def purge_cdat():
    pass


def purge_cog():
    try:
        shutil.rmtree("/usr/local/cog")
    except OSError, error:
        logger.exception("Couldn't delete /usr/local/cog")
    try:
        os.remove("/usr/local/bin/wait_for_postgres.sh")
    except OSError, error:
        logger.exception("Couldn't delete /usr/local/bin/wait_for_postgres.sh")
    try:
        os.remove("/usr/local/bin/wait_for_postgres.sh")
    except OSError, error:
        logger.exception("Couldn't delete /usr/local/bin/process_esgf_config_archive.sh")

def purge_apache():
    esg_functions.stream_subprocess_output("yum remove -y httpd httpd-devel mod_ssl")
    try:
        shutil.rmtree("/etc/httpd")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass

#TODO: define purge_conda()
def purge_conda():
    pass

#TODO: define purge_solr
def purge_solr():
    pass
#TODO: define purge_dashboard()
def purge_dashboard():
    pass

def main():
    from esgf_utilities import esg_logging_manager

    esg_logging_manager.main()
    logger = logging.getLogger("esgf_logger" + "." + __name__)

    purge_postgres()
    purge_tomcat()
    purge_thredds()
    purge_ant()
    purge_java()
    purge_base()
    purge_cdat()
    purge_apache()
    purge_cog()

if __name__ == '__main__':
    main()
