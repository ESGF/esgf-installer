import os
import shutil
import glob
import subprocess
import esg_functions

def purge_postgres():
    esg_functions.stream_subprocess_output("yum remove -y postgresql postgresql-libs postgresql-server")
    try:
        # shutil.rmtree("/usr/local/pgsql")
        shutil.rmtree("/var/lib/pgsql")
        os.remove(os.path.join(os.environ["HOME"], ".pgpass"))
    except OSError, error:
        print "error:", error

def purge_tomcat():
    # esg-node --stop may not actually cause Tomcat to exit properly,
    # so force-kill all remaining instances
    esg_functions.call_subprocess("pkill -9 -u tomcat")
    try:
        shutil.rmtree("/etc/logrotate.d/esgf_tomcat")
    except OSError, error:
        print "error deleting directory -> /etc/logrotate.d/esgf_tomcat:", error

    tomcat_directories = glob.glob("/usr/local/tomcat*")
    tomcat_directories.extend(glob.glob("/usr/local/apache-tomcat*"))
    for directory in tomcat_directories:
        try:
            shutil.rmtree(directory)
        except OSError, error:
            print "error deleting directory -> {directory}:".format(directory=directory), error
    os.unlink("/usr/local/tomcat")

    # Tomcat may leave stuck java processes.  Kill them with extreme prejudice
    esg_functions.call_subprocess("pkill -9 -f 'java.*/usr/local/tomcat'")

def purge_java():
    try:
        shutil.rmtree("/usr/local/java")
    except OSError, error:
        print "error: No Java installation found to delete"

def main():
    purge_postgres()
    purge_tomcat()
    purge_java()

if __name__ == '__main__':
    main()
