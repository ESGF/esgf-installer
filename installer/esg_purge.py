import os
import shutil
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


def main():
    purge_postgres()
    pass

if __name__ == '__main__':
    main()
