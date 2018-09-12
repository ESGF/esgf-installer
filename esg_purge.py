import os
import shutil
import glob
import datetime
import errno
import logging
import psutil
import yaml
from esgf_utilities import esg_functions, pybash
from esgf_utilities.esg_exceptions import SubprocessError
from base import esg_tomcat_manager
from index_node import solr
from plumbum.commands import ProcessExecutionError


logger = logging.getLogger("esgf_logger" +"."+ __name__)
with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def purge_postgres():
    '''Removes postgres installation via yum'''
    print "\n*******************************"
    print "Purging Postgres"
    print "******************************* \n"

    try:
        esg_functions.call_binary("service", ["postgresql", "stop"])
    except ProcessExecutionError:
        pass

    try:
        esg_functions.call_binary("yum", ["remove", "-y", "postgresql-server.x86_64", "postgresql.x86_64", "postgresql-devel.x86_64"])
    except ProcessExecutionError:
        pass

    try:
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
        os.remove("/etc/logrotate.d/esgf_tomcat")
    except OSError, error:
        pass

    tomcat_directories = glob.glob("/usr/local/tomcat*")
    tomcat_directories.extend(glob.glob("/usr/local/apache-tomcat*"))
    for directory in tomcat_directories:
        try:
            shutil.rmtree(directory)
        except OSError:
            if os.path.islink(directory):
                os.unlink(directory)
            pass

    # try:
    #     os.unlink("/usr/local/tomcat")
    # except OSError, error:
    #     if error.errno == errno.ENOENT:
    #         pass
    #     else:
    #         logger.exception("Could not delete symlink /usr/local/tomcat")

    try:
        os.remove("/tmp/catalina.pid")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass

    # Tomcat may leave stuck java processes.  Kill them with extreme prejudice
    try:
        esg_functions.call_binary("pkill", ["-9", "-f", "'java.*/usr/local/tomcat'"])
    except ProcessExecutionError:
        pass

def purge_java():
    print "\n*******************************"
    print "Purging Java"
    print "******************************* \n"

    java_tarfile = pybash.trim_string_from_head(config["java_dist_url"])
    try:
        os.remove("/usr/local/src/esgf/workbench/esg/{}".format(java_tarfile))
    except OSError:
        pass

    try:
        shutil.rmtree("/usr/local/jdk{}".format(config["java_version"]))
    except OSError:
        pass

    try:
        os.unlink("/usr/local/java")
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
        esg_functions.call_binary("yum", ["remove", "-y", "ant"])
    except ProcessExecutionError:
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
    try:
        esg_functions.call_binary("umount", ["/esg/gridftp_root/esg_dataroot"])
    except ProcessExecutionError:
        pass

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
        esg_functions.call_binary("yum", ["remove", "-y", "httpd", "httpd-devel", "mod_ssl"])
    except ProcessExecutionError:
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
    print "\n*******************************"
    print "Purging Solr"
    print "******************************* \n"

    try:
        solr.stop_solr()
    except SubprocessError:
        pass

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

    try:
        os.unlink("/usr/local/solr")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass
        else:
            logger.exception("Could not delete symlink /usr/local/tomcat")
    # Solr may leave stuck java processes.  Kill them with extreme prejudice
    try:
        esg_functions.call_binary("pkill", ["-9", "-f", "'java.*/usr/local/tomcat'"])
    except ProcessExecutionError:
        pass


def purge_globus():
    logger.info("Purging Globus")
    esg_functions.call_binary("yum", ["remove", "-y", "globus\* myproxy\*"])

    try:
        shutil.rmtree("/etc/esgfcerts")
    except OSError:
        pass

    try:
        os.remove("/etc/globus-host-ssl.conf")
    except OSError:
        pass
    try:
        os.remove("/etc/globus-user-ssl.conf")
    except OSError:
        pass
    try:
        os.remove("/etc/grid-security.conf")
    except OSError:
        pass

        globus_directories = glob.glob("/etc/globus*")
        for directory in globus_directories:
            try:
                shutil.rmtree(directory)
            except OSError, error:
                #if not a directory; use file delete method
                if error.errno == errno.ENOTDIR:
                    os.remove(directory)
    try:
        shutil.rmtree("/etc/grid-security")
    except OSError:
        pass

        gridftp_directories = glob.glob("/etc/gridftp*")
        for directory in gridftp_directories:
            try:
                shutil.rmtree(directory)
            except OSError, error:
                if error.errno == errno.ENOTDIR:
                    os.remove(directory)

    try:
        os.remove("/etc/logrotate.d/globus-connect-server")
    except OSError:
        pass

        myproxy_directories = glob.glob("/etc/myproxy*")
        for directory in myproxy_directories:
            try:
                shutil.rmtree(directory)
            except OSError, error:
                if error.errno == errno.ENOTDIR:
                    os.remove(directory)
    try:
        shutil.rmtree("/etc/pam.d/myproxy")
    except OSError:
        pass
    try:
        os.remove("/etc/pam_pgsql.conf")
    except OSError:
        pass
    try:
        os.remove("/etc/pam_pgsql.conf.tmpl.bak")
    except OSError:
        pass

        globus_gridftp_directories = glob.glob("/etc/rc.d/init.d/globus-gridftp-*")
        for directory in globus_gridftp_directories:
            try:
                shutil.rmtree(directory)
            except OSError, error:
                if error.errno == errno.ENOTDIR:
                    os.remove(directory)

    try:
        shutil.rmtree(os.path.join(os.environ["HOME"], ".globus"))
    except OSError:
        pass
    try:
        shutil.rmtree("/root/.globus")
    except OSError:
        pass
    try:
        shutil.rmtree("/usr/local/globus")
    except OSError:
        pass
    try:
        shutil.rmtree("/usr/local/gsoap")
    except OSError:
        pass
    try:
        shutil.rmtree("/usr/share/myproxy")
    except OSError:
        pass
    try:
        shutil.rmtree("/var/lib/globus")
    except OSError:
        pass
    try:
        shutil.rmtree("/var/lib/globus-connect-server")
    except OSError:
        pass
    try:
        shutil.rmtree("/var/lib/myproxy")
    except OSError:
        pass

    globus_modules = glob.glob("/usr/local/conda/envs/esgf-pub/lib/python2.7/site-packages/globus*")
    for module in globus_modules:
        try:
            shutil.rmtree(module)
        except OSError:
            pass

    try:
        os.remove("/usr/bin/globus-version")
    except OSError:
        pass


def purge_publisher():
    try:
        shutil.rmtree("/tmp/esg-publisher")
    except OSError:
        pass

    publisher_binaries = glob.glob("/usr/local/conda/envs/esgf-pub/bin/esg*")
    for binary in publisher_binaries:
        try:
            os.remove(binary)
        except OSError:
            pass

    publisher_modules = glob.glob("/usr/local/conda/envs/esgf-pub/lib/python2.7/site-packages/esg*")
    for module in publisher_modules:
        try:
            shutil.rmtree(module)
        except OSError:
            pass

#TODO: define purge_dashboard()
def purge_dashboard():
    pass

def confirm_purge():
    purged_directories = ["/var/lib/pgsql", "/usr/local/java", "/usr/bin/java", "/usr/local/tomcat", "/esg", "/etc/certs", "/etc/esgfcerts",
    "/etc/tempcerts", "/opt/esgf", "/tmp/inputpipe", "/tmp/outputpipe", "/usr/local/cog", "/var/www/.python-eggs", "/usr/local/solr"]

    for directory in purged_directories:
        if os.path.exists(directory):
            print "Purge failed.  {} still exists and must be delete manually.".format(directory)
            return

    print "All ESGF components have been successfully deleted."

def purge_slcs():
    try:
        shutil.rmtree("/usr/local/src/esgf-slcs-server-playbook")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass
    try:
        shutil.rmtree("/usr/local/esgf-slcs-server")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass

def main():
    purge_postgres()
    purge_tomcat()
    purge_thredds()
    purge_ant()
    purge_publisher()
    purge_solr()
    purge_java()
    purge_base()
    purge_cdat()
    purge_apache()
    purge_cog()
    purge_globus()
    purge_slcs()
    # purge_conda()
    confirm_purge()

if __name__ == '__main__':
    main()
