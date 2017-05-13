import os
import subprocess
import logging
import grp
import pwd
import psycopg2
import esg_functions
import esg_setup
import shlex
from esg_init import EsgInit
from time import sleep

logging.basicConfig(format = "%(levelname): %(lineno)s %(funcName)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = EsgInit()

def setup_postgres(force_install = False):
    print '''
    *******************************
    Setting up Postgres
    ******************************* '''
    if esg_setup._is_managed_db():
        return True

    print "Checking for postgresql >= {postgress_min_version} ".format(postgress_min_version = config.config_dictionary["postgress_min_version"])
    postgres_binary_path = os.path.join(config.config_dictionary["postgress_bin_dir"], "postgres")
    logger.debug("postgres_binary_path: %s", postgres_binary_path)
    try:
        found_valid_version = esg_functions.check_for_acceptible_version(postgres_binary_path, config.config_dictionary["postgress_min_version"], version_command = "-V")
        if found_valid_version and not force_install:
            print "Valid existing Postgres installation found"
            print "[OK]"
            return True
    except OSError, error:
        logger.error(error)

    # upgrade  = None
    # if not found_valid_version:
    #     upgrade 

    #---------------------------------------
    #Setup PostgreSQL RPM repository
    #---------------------------------------

    backup_db_input = raw_input("Do you want to backup the curent database? [Y/n]") 
    if backup_db_input.lower() == "y" or backup_db_input.lower() == "yes":
        backup_db()


    yum_install_postgres = subprocess.Popen(["yum", "-y", "install", "postgresql", "postgresql-server", "postgresql-devel"], stdout=subprocess.PIPE)
    print "yum_install_postgres: ", yum_install_postgres.communicate()[0]
    print "yum_install_postgres return code: ", yum_install_postgres.returncode

    print "Restarting Database..."
    stop_postgress()
    esg_functions.checked_done(start_postgress())

    ########
    #Create the system account for postgress to run as.
    ########
    pg_sys_acct_homedir="/var/lib/pgsql"
    if not pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid:
        print " Hmmm...: There is no postgres system account user \"{pg_sys_acct}\" present on system, making one...".format(pg_sys_acct = config.config_dictionary["pg_sys_acct"])
        #NOTE: "useradd/groupadd" are a RedHat/CentOS thing... to make this cross distro compatible clean this up.
        groupadd_command = "/usr/sbin/groupadd -r %s" % (
            config.config_dictionary["pg_sys_acct_group"])
        groupadd_output = subprocess.call(groupadd_command, shell=True)
        if groupadd_output != 0 or groupadd_output != 9:
            print "ERROR: *Could not add postgres system group: %s" % (config.config_dictionary["pg_sys_acct_group"])
            esg_functions.checked_done(1)
        if not config.config_dictionary["pg_sys_acct_passwd"]:
            while True:
                pg_sys_acct_passwd_input = raw_input("Create password for postgress system account: ")
                if not pg_sys_acct_passwd_input:
                    print "Please enter a password: "
                    continue
                else:
                    config.config_dictionary["pg_sys_acct_passwd"] = pg_sys_acct_passwd_input
                    break
        print "Creating account..."
        useradd_command = '''/usr/sbin/useradd -r -c'PostgreSQL Service ESGF' 
        -d $pg_sys_acct_homedir -g $pg_sys_acct_group -p 
        $pg_sys_acct_passwd -s /bin/bash $pg_sys_acct'''.format(pg_sys_acct_homedir = pg_sys_acct_homedir,
           pg_sys_acct_group = config.config_dictionary["pg_sys_acct_group"], 
           pg_sys_acct_passwd = config.config_dictionary["pg_sys_acct_passwd"],
           pg_sys_acct = config.config_dictionary["pg_sys_acct"] )
        useradd_output = subprocess.call(useradd_command, shell=True)
        if useradd_output != 0 or useradd_output != 9:
            print "ERROR: Could not add postgres system account user"
            esg_functions.checked_done(1)
        with open(config.pg_secret_file, "w") as secret_file:
            secret_file.write(config.config_dictionary["pg_sys_acct_passwd"])

    else:
        postgress_user_shell = pwd.getpwnam(config.config_dictionary["pg_sys_acct"])[6]
        if postgress_user_shell != "/bin/bash":
            print "Noticed that the existing postgres user [{pg_sys_acct}] does not have the bash shell... Hmmm... making it so ".format(pg_sys_acct = config.config_dictionary["pg_sys_acct"])
            change_shell_command = "sed -i 's#\('{pg_sys_acct}'.*:\)\(.*\)$#\1/\bin/\bash#' /etc/passwd".format(pg_sys_acct = config.config_dictionary["pg_sys_acct"])
            subprocess.call(change_shell_command, shell=True)
            if pwd.getpwnam(config.config_dictionary["pg_sys_acct"])[6] == "/bin/bash":
                print "[OK]"
            else:
                print "[FAIL]"

    if os.path.isfile(config.pg_secret_file):
        os.chmod(config.pg_secret_file, 0640)
        os.chown(config.pg_secret_file, config.config_dictionary[
                 "installer_uid"], grp.getgrnam(
            config.config_dictionary["tomcat_group"]).gr_gid)

    sleep(3)
    #double check that the account is really there!
    if not pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid:
        print " ERROR: Problem with $pg_sys_acct creation!!!"
        esg_functions.checked_done(1) 

    os.chown(config.config_dictionary["postgress_install_dir"], pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid, 
        grp.getgrnam(config.config_dictionary["pg_sys_acct_group"]).gr_gid)


    #Create the database:
    try:
        os.mkdir(os.path.join(config.config_dictionary["postgress_install_dir"], "data"))
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass
    
    try:
        os.chown(os.path.join(config.config_dictionary["postgress_install_dir"], "data"), pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid, -1)
    except:
        print " ERROR: Could not change ownership of postgres' data to \"$pg_sys_acct\" user".format(pg_sys_acct = config.config_dictionary["pg_sys_acct"])
        esg_functions.checked_done(1)

    os.chmod(os.path.join(config.config_dictionary["postgress_install_dir"], "data"), 0700)
    initialize_db_command = 'su $pg_sys_acct -c "$postgress_bin_dir/initdb -D $postgress_install_dir/data"'
    subprocess.call(initialize_db_command, shell = True)
    try:
        os.mkdir(os.path.join(config.config_dictionary["postgress_install_dir"], "log"))
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass
    
    try:
        os.chown(os.path.join(config.config_dictionary["postgress_install_dir"], "log"), pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid, -1)
    except:
        print " ERROR: Could not change ownership of postgres' log to \"$pg_sys_acct\" user".format(pg_sys_acct = config.config_dictionary["pg_sys_acct"])

    #Start the database
    start_postgress()

    if not os.access(os.path.join(config.config_dictionary["postgress_bin_dir"], "psql"), os.X_OK):
        print " ERROR: psql not found after install!"
        esg_functions.checked_done(1) 

    #Check to see if there is a ${postgress_user} already on the system if not, make one
    try:
        conn=psycopg2.connect("dbname='postgres' user='postgres' password={pg_sys_acct_passwd}".format(pg_sys_acct_passwd = config.config_dictionary["pg_sys_acct_passwd"])) 
    except Exception, error:
        logger.error(error)
        print "I am unable to connect to the database."
        esg_functions.checked_done(1)

    cur = conn.cursor()
    cur.execute("select count(*) from pg_roles where rolname={postgress_user}".format(postgress_user = config.config_dictionary["postgress_user"]))
    rows = cur.fetchall()
    if rows[0][0] > 0:
        print "${postgress_user} exists!! :-)".format(config.config_dictionary["postgress_user"])
    else:
        while True:
            postgres_user_password = _choose_postgres_user_password()
            try:
                cur.execute("create user {postgress_user} with superuser password '{postgres_user_password}';".format(postgress_user = config.config_dictionary["postgress_user"], 
                    postgres_user_password = postgres_user_password))
                break
            except:
                print "Could not create {postgress_user} account in database".format(postgress_user = config.config_dictionary["postgress_user"])
                continue

    starting_directory = os.getcwd()
    os.chdir(os.path.join(config.config_dictionary["postgress_install_dir"], "data"))
    
    #Get files
    esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
    hba_conf_file = "pg_hba.conf"
    if esg_functions.checked_get(hba_conf_file, os.path.join(esg_dist_url,"externals", "bootstrap",hba_conf_file), force_install) > 1:
        os.chdir(starting_directory)
        esg_functions.checked_done(1)
    os.chmod(hba_conf_file, 0600)

    postgres_conf_file = "postgresql.conf"
    if esg_functions.checked_get(postgres_conf_file, os.path.join(esg_dist_url,"externals", "bootstrap",postgres_conf_file), force_install) > 1:
        os.chdir(starting_directory)
        esg_functions.checked_done(1)
    os.chmod(postgres_conf_file, 0600)


    #-----
    #NOTE: This database is an internal database to this esg
    #application stack... I don't think it would even be prudent to
    #offer then opportunity for someone to bind to the public
    #interface.  If they choose to do so after the fact, then they are
    #making that conscious decision, but I won't make it a part of
    #this process.

    #@@postgress_host@@ #Token in file...

    #local input
    #read -e -p "Please Enter the IP address or name of this host [${postgress_host}]:> " input
    #[ ! -z "${input}" ] && postgress_host=${input}
    #printf "\nUsing IP: ${postgress_host}\n"
    #eval "perl -p -i -e 's/\\@\\@postgress_host\\@\\@/${postgress_host}/g' ${fetch_file}"
    #-----

    #@@postgress_port@@ #Token in file...

    postgres_port_input = raw_input("Please Enter PostgreSQL port number [{postgress_port}]:> ".format(postgress_port = config.config_dictionary["postgress_port"])) or  config.config_dictionary["postgress_port"]
    print "\nSetting Postgress Port: {postgress_port} ".format(postgress_port = postgres_port_input)
    postgres_port_returncode = subprocess.call('''eval "perl -p -i -e 's/\\@\\@postgress_port\\@\\@/{postgress_port}/g' ${postgres_conf_file}" '''.format(postgress_port = config.config_dictionary["postgress_port"], postgres_conf_file = postgres_conf_file)) 
    if postgres_port_returncode == 0:
        print "Postgres port set: [OK]"
    else:
        print "Postgres port set: [FAIL]"

    print "Setting Postgress Log Dir: {postgress_install_dir} ".format(postgress_install_dir = config.config_dictionary["postgress_install_dir"])    
    postgres_log_dir_returncode = subprocess.call('''eval "perl -p -i -e 's/\\@\\@postgress_install_dir\\@\\@/{postgress_install_dir}/g' ${postgres_conf_file}" '''.format(postgress_install_dir = config.config_dictionary["postgress_install_dir"], postgres_conf_file = postgres_conf_file)) 
    if postgres_log_dir_returncode == 0:
        print "Postgres Log Dir set: [OK]"
    else:
        print "Postgres Log Dir set: [FAIL]"

    os.chown(config.config_dictionary["postgress_install_dir"], pwd.getpwnam(config.config_dictionary["pg_sys_acct"]).pw_uid, 
        grp.getgrnam(config.config_dictionary["pg_sys_acct_group"]).gr_gid)

    os.chdir(starting_directory)

    esg_functions.check_shmmax()
    write_postgress_env()
    write_postgress_install_log()
    esg_functions.checked_done(0)

# returns 1 if it is already running (if check_postgress_process returns 0
# - true)
def start_postgress():
    if esg_functions.check_postgress_process() == 0:
        print "Postgres is already running"
        return True
    print "Starting Postgress..."
    for file in os.listdir("/etc/init.d/"):
        if "postgresql" in file:
            postgresql_executable_name = file
            logger.info("postgresql_executable_name: %s", postgresql_executable_name)
    postgres_start_command = shlex.split("/etc/init.d/{postgresql_executable_name} start".format(postgresql_executable_name = postgresql_executable_name))
    status = subprocess.Popen(postgres_start_command)
    status_output, err = status.communicate()
    # print "status_output: ", status_output
    logger.info("status_output: %s", status_output)
    logger.error("err: %s ", err)
    sleep(3)
    progress_process_status = subprocess.Popen(
        "/bin/ps -elf | grep postgres | grep -v grep", shell=True)
    progress_process_status_tuple = progress_process_status.communicate()
    logger.info("progress_process_status_tuple: %s", progress_process_status_tuple)
    esg_functions.checked_done(0)
    return True

def stop_postgress():
    if esg_setup._is_managed_db:
        print "Please be sure external database is NOT running at this point..."
        return True
    if esg_functions.check_postgress_process() == 1:
        print "Postgres already stopped"
        return True
    print "Stopping Postgres...."
    status = subprocess.Popen("/etc/init.d/postgresql stop",
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    status_output, err = status.communicate()
    print "status_output: ", status_output
    sleep(3)
    esg_functions.check_shmmax()
    progress_process_status = subprocess.Popen(
        "/bin/ps -elf | grep postgres | grep -v grep", shell=True)
    progress_process_status_tuple = progress_process_status.communicate()
    esg_functions.checked_done(0)


def backup_db():
    pass

def write_postgress_env():
    pass
def write_postgress_install_log():
    pass
def _choose_postgres_user_password():
    while True:
            postgres_user_password = raw_input("Enter password for postgres user $postgress_user: ")
            postgres_user_password_confirmation = raw_input("Re-enter password for postgres user $postgress_user: ")
            if postgres_user_password != postgres_user_password_confirmation:
                print "The passwords did not match. Enter same password twice."
                continue
            else:
                return postgres_user_password

