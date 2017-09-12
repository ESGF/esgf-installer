import os
import grp
import pwd
import shutil
import psycopg2
import esg_functions
import esg_version_manager
import esg_bash2py
from time import sleep
from distutils.spawn import find_executable
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import esg_logging_manager
import semver
import yaml

logger = esg_logging_manager.create_rotating_log(__name__)

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


def download_postgres():
    esg_functions.stream_subprocess_output("rpm -Uvh https://yum.postgresql.org/9.6/redhat/rhel-6-x86_64/pgdg-redhat96-9.6-3.noarch.rpm")
    esg_functions.stream_subprocess_output("yum -y install postgresql96-server postgresql96")

def initialize_postgres():
    if os.listdir("/var/lib/pgsql/9.6/data"):
        print "Data directory already exists. Skipping initialize_postgres()."
        return
    esg_functions.stream_subprocess_output("service postgresql-9.6 initdb")
    os.chmod(os.path.join(config["postgress_install_dir"], "9.6", "data"), 0700)

def check_for_postgres_sys_acct():
    postgres_user_id = pwd.getpwnam(config["pg_sys_acct"]).pw_uid
    if not postgres_user_id:
        print " Hmmm...: There is no postgres system account user \"{pg_sys_acct}\" present on system, making one...".format(pg_sys_acct = config["pg_sys_acct"])

def create_postgres_group():
    groupadd_command = "/usr/sbin/groupadd -r %s" % (
        config["pg_sys_acct_group"])
    groupadd_output = esg_functions.call_subprocess(groupadd_command)
    if groupadd_output["returncode"] != 0 or groupadd_output["returncode"] != 9:
        print "ERROR: *Could not add postgres system group: %s" % (config["pg_sys_acct_group"])
        esg_functions.exit_with_error(1)
    else:
        print "Created postgres group with group id: {postgres_group_id}".format(postgres_group_id=grp.getgrnam(config["pg_sys_acct_group"]).gr_gid)

def set_pg_sys_account_password():
    if not config["pg_sys_acct_passwd"]:
        while True:
            pg_sys_acct_passwd_input = raw_input("Create password for postgress system account: ")
            if not pg_sys_acct_passwd_input:
                print "Please enter a password: "
                continue
            else:
                config["pg_sys_acct_passwd"] = pg_sys_acct_passwd_input
                break
        with open(config["pg_secret_file"], "w") as secret_file:
            secret_file.write(config["pg_sys_acct_passwd"])

        #Change pg_secret_file permissions
        if os.path.isfile(config["pg_secret_file"]):
            os.chmod(config["pg_secret_file"], 0640)
            tomcat_group_id = grp.getgrnam(config["tomcat_group"]).gr_gid
            os.chown(config["pg_secret_file"], config["installer_uid"], tomcat_group_id)

        sleep(3)

def create_postgres_system_user(pg_sys_acct_homedir):
    print "Creating account..."
    useradd_command = '''/usr/sbin/useradd -r -c'PostgreSQL Service ESGF'
    -d {pg_sys_acct_homedir} -g {pg_sys_acct_group} -p
    {pg_sys_acct_passwd} -s /bin/bash {pg_sys_acct}'''.format(pg_sys_acct_homedir = pg_sys_acct_homedir,
       pg_sys_acct_group = config["pg_sys_acct_group"],
       pg_sys_acct_passwd = config["pg_sys_acct_passwd"],
       pg_sys_acct = config["pg_sys_acct"] )
    useradd_output = esg_functions.call_subprocess(useradd_command)

    postgres_user_id = pwd.getpwnam(config["pg_sys_acct"]).pw_uid

    if useradd_output["returncode"] != 0 or useradd_output["returncode"] != 9:
        print "ERROR: Could not add postgres system account user"
        esg_functions.exit_with_error(1)
    elif not postgres_user_id:
        print " ERROR: Problem with {pg_sys_acct} creation!!!".format(pg_sys_acct=config["pg_sys_acct"])
        esg_functions.exit_with_error(1)
    else:
        print "Created postgres user with group id: {postgres_user_id}".format(postgres_user_id=pwd.getpwnam(config["pg_sys_acct"]).pw_uid)


def get_postgres_user_shell():
    return pwd.getpwnam(config["pg_sys_acct"])[6]

def set_postgres_user_shell():
    print "Noticed that the existing postgres user [{pg_sys_acct}] does not have the bash shell... Hmmm... making it so ".format(pg_sys_acct = config["pg_sys_acct"])
    change_shell_command = "sed -i 's#\('{pg_sys_acct}'.*:\)\(.*\)$#\1/\bin/\bash#' /etc/passwd".format(pg_sys_acct = config["pg_sys_acct"])
    esg_functions.call_subprocess(change_shell_command)
    if get_postgres_user_shell() == "/bin/bash":
        print "[OK]"
        print "Postgres user shell is properly configured"
    else:
        print "[FAIL]"
        print "Postgres user shell is not properly configured. The shell is {postgres_shell}. It should be /bin/bash".format(postgres_shell=get_postgres_user_shell())

def change_pg_install_dir_ownership():
    postgres_user_id = pwd.getpwnam(config["pg_sys_acct"]).pw_uid
    postgres_group_id = grp.getgrnam(config["pg_sys_acct_group"]).gr_gid
    os.chown(config["postgress_install_dir"], postgres_user_id , postgres_group_id)

def create_postgres_log_dir():
    ''' Create log directory '''
    esg_bash2py.mkdir_p(os.path.join(config["postgress_install_dir"], "log"))
    postgres_user_id = pwd.getpwnam(config["pg_sys_acct"]).pw_uid
    try:
        os.chown(os.path.join(config["postgress_install_dir"], "log"), postgres_user_id, -1)
    except OSError, error:
        print " ERROR: Could not change ownership of postgres' log to \"{pg_sys_acct}\" user".format(pg_sys_acct = config["pg_sys_acct"])

def start_postgres():
    ''' Start db '''
    #if the data directory doesn't exist or is empty
    if not os.path.isdir("/var/lib/pgsql/9.6/data/") or not os.listdir("/var/lib/pgsql/9.6/data/"):
        initialize_postgres()
    esg_functions.stream_subprocess_output("service postgresql-9.6 start")
    esg_functions.stream_subprocess_output("chkconfig postgresql-9.6 on")

    sleep(3)
    if postgres_status():
        return True

def postgres_status():
    '''Checks the status of the postgres server'''
    status = esg_functions.call_subprocess("service postgresql-9.6 status")
    print "status:", status
    if "running" in status["stdout"]:
        return True
    else:
        return False

def restart_postgres():
    '''Restarts the postgres server'''
    esg_functions.call_subprocess("service postgresql-9.6 restart")

def build_connection_string(user,db_name=None, host=None, password=None):
    '''Creates the db connection string using the params as options '''
    db_connection_string = ["user={user}".format(user=user)]
    if db_name:
        db_connection_string.append("dbname={db_name}".format(db_name=db_name))
    if host:
        db_connection_string.append("host={host}".format(host=host))
    if password:
        db_connection_string.append("password={password}".format(password=password))

    return " ".join(db_connection_string)

def connect_to_db(user, db_name=None,  host=None, password=None):
    ''' Connect to database '''
    #Using password auth currently;
    #if the user is postgres, the effective user id (euid) needs to be postgres' user id.
    #Essentially change user from root to postgres
    #TODO: This was only working for ident identification
    #TODO: to connect initially, will have to remove host from connection string.  Add params for host and password
    #TODO: Create a helper function to build connection strings
    root_id = pwd.getpwnam("root").pw_uid
    if user == "postgres":
        postgres_id = pwd.getpwnam("postgres").pw_uid

        os.seteuid(postgres_id)
    db_connection_string = build_connection_string(user, db_name, host, password)
    print "db_connection_string: ", db_connection_string
    try:
        conn = psycopg2.connect(db_connection_string)
        print "Connected to {db_name} database as user '{user}'".format(db_name=db_name, user=user)

        #Set effective user id (euid) back to root
        if os.geteuid() != root_id:
            os.seteuid(root_id)

        return conn
    except Exception, error:
        logger.error(error)
        print "error: ", error
        print "I am unable to connect to the database."
        esg_functions.exit_with_error(1)

def check_for_postgres_db_user():
    ''' Need to be able to run psql as the postgres system user instead of root to avoid the peer authencation error '''
    check_for_pg_user_command = '''sudo -u postgres psql -U postgres -c "select count(*) from pg_roles where rolname='{postgress_user}'" postgres'''.format(postgress_user=config["postgress_user"])
    check_for_pg_user_output = esg_functions.call_subprocess(check_for_pg_user_command)
    print "check_for_postgres_db_user: ", check_for_pg_user_output
    count = int(check_for_pg_user_output["stdout"].strip().split("\n")[-2].strip())
    print "count: ", count
    print "count type: ", type(count)
    if count > 0:
        print "{postgress_user} user found".format(postgress_user=config["postgress_user"])
    else:
        create_postgres_db_user()

def create_postgres_db_user():
    postgres_db_user_password = _choose_postgres_user_password()
    create_pg_db_user_command = '''sudo -u postgres psql -c "create user {postgress_user} with superuser password '{postgres_db_user_password}';" '''.format(postgress_user=config["postgress_user"], postgres_db_user_password=postgres_db_user_password)
    create_pg_db_user_output = esg_functions.call_subprocess(create_pg_db_user_command)
    if create_pg_db_user_output["returncode"] == 0:
        print "Successfully created {postgress_user} db user".format(postgress_user=config["postgress_user"])

def download_config_files(force_install):
    ''' Download config files '''
    # #Get files
    esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
    hba_conf_file = "pg_hba.conf"
    if esg_functions.download_update(hba_conf_file, os.path.join(esg_dist_url,"externals", "bootstrap",hba_conf_file), force_install) > 1:
        esg_functions.exit_with_error(1)
    os.chmod(hba_conf_file, 0600)

    postgres_conf_file = "postgresql.conf"
    if esg_functions.download_update(postgres_conf_file, os.path.join(esg_dist_url,"externals", "bootstrap",postgres_conf_file), force_install) > 1:
        esg_functions.exit_with_error(1)
    os.chmod(postgres_conf_file, 0600)

def update_port_in_config_file():
    postgres_port_input = raw_input("Please Enter PostgreSQL port number [{postgress_port}]:> ".format(postgress_port = config["postgress_port"])) or  config["postgress_port"]
    print "\nSetting Postgress Port: {postgress_port} ".format(postgress_port = postgres_port_input)

    with open('postgresql.conf', 'r') as pg_conf_file :
        filedata = pg_conf_file.read()
    filedata = filedata.replace('@@postgress_port@@', config["postgress_port"])

    # Write the file out again
    with open('postgresql.conf', 'w') as pg_conf_file:
        pg_conf_file.write(filedata)

def update_log_dir_in_config_file():
    ''' Edit postgres config file '''
    print "Setting Postgress Log Dir in config_file: {postgress_install_dir} ".format(postgress_install_dir = config["postgress_install_dir"])

    with open('postgresql.conf', 'r') as pg_conf_file:
        filedata = pg_conf_file.read()
    filedata = filedata.replace('@@postgress_install_dir@@', config["postgress_install_dir"])

    # Write the file out again
    with open('postgresql.conf', 'w') as pg_conf_file:
        pg_conf_file.write(filedata)


    os.chown(config["postgress_install_dir"], pwd.getpwnam(config["pg_sys_acct"]).pw_uid,
        grp.getgrnam(config["pg_sys_acct_group"]).gr_gid)


def setup_postgres(force_install = False):
    print "\n*******************************"
    print "Setting up Postgres"
    print "******************************* \n"

    print "Checking for postgresql >= {postgress_min_version} ".format(postgress_min_version = config["postgress_min_version"])

    postgres_binary_path = find_executable("postgres")
    psql_path = find_executable("psql")

    if not psql_path:
        print "Postgres not found on system"
    else:
        try:
            postgres_version_found = esg_functions.call_subprocess("psql --version")["stdout"].split(" ")[-1]
            print "postgres version number: ", postgres_version_found
            if semver.compare(postgres_version_found, config["postgress_min_version"]) >= 1 and not force_install:
                # postgres_version_found = esg_functions.call_subprocess("psql --version")
                # print postgres_version_found["stdout"]
                default_continue_install = "N"
                continue_install = raw_input("Valid existing Postgres installation found. Do you want to continue with the setup [y/N]? ") or default_continue_install
                if continue_install.lower() in ["no", 'n']:
                    print "Skipping installation."
                    return True
            # elif
        except OSError, error:
            logger.error(error)

    backup_db_input = raw_input("Do you want to backup the current database? [Y/n]")
    if backup_db_input.lower() == "y" or backup_db_input.lower() == "yes":
        backup_db()

    download_postgres()

    '''Create system account (postgres) if it doesn't exist '''
    ########
    #Create the system account for postgress to run as.
    ########
    pg_sys_acct_homedir = psql_path
    pg_sys_acct_id = pwd.getpwnam(config["pg_sys_acct"]).pw_uid
    if not pg_sys_acct_id:
        print " Hmmm...: There is no postgres system account user \"{pg_sys_acct}\" present on system, making one...".format(pg_sys_acct = config["pg_sys_acct"])
        #NOTE: "useradd/groupadd" are a RedHat/CentOS thing... to make this cross distro compatible clean this up.
        create_postgres_group()
        set_pg_sys_account_password()
        create_postgres_system_user(pg_sys_acct_homedir)

    else:
        postgress_user_shell = get_postgres_user_shell()
        if postgress_user_shell != "/bin/bash":
            set_postgres_user_shell()
    change_pg_install_dir_ownership()


    initialize_postgres()

    #start the postgres server
    start_postgres()
    # check_for_postgres_db_user()
    # connect_to_db()
    with esg_bash2py.pushd(os.path.join(config["postgress_install_dir"], "9.6", "data")):
        # download_config_files(force_install)
        update_port_in_config_file()
        update_log_dir_in_config_file()
        restart_postgres()

    #TODO: Set password for postgres user
    setup_db_schemas(force_install)
    create_pg_pass_file()

    ''' function calls '''
    esg_functions.check_shmmax()
    write_postgress_env()
    write_postgress_install_log()
    esg_functions.exit_with_error(0)


'''Check if managed_db'''
# db_properties = esg_setup.get_db_properties()
# if esg_setup._is_managed_db(db_properties):
#     return True

'''Check if should perform upgrade'''
# upgrade  = None
# if not found_valid_version:
#     upgrade

def create_pg_pass_file():
    '''Creates the file to store login passwords for psql'''
    pg_pass_file_path = os.path.join(os.environ["HOME"], ".pgpass")
    with open(pg_pass_file_path, "w") as pg_pass_file:
        pg_pass_file.write('localhost:5432:cogdb:dbsuper:password')
        pg_pass_file.write('localhost:5432:esgcet:dbsuper:password')
    os.chmod(pg_pass_file_path, 0600)

def stop_postgress():
    '''Stops the postgres server'''
    esg_functions.stream_subprocess_output("service postgresql-9.6 stop")

def setup_db_schemas(force_install):
    '''Load ESGF schemas'''
    conn = connect_to_db("postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # create super user
    cur.execute("CREATE USER dbsuper with CREATEROLE superuser PASSWORD 'password';")
    # create 'esgcet' user
    cur.execute("CREATE USER esgcet PASSWORD 'password';")
    # create CoG database
    cur.execute("CREATE DATABASE cogdb;")
    # create ESGF database
    cur.execute("CREATE DATABASE esgcet;")

    #TODO: close connection here and connection to esgcet; or look up how to switch databases
    cur.close()
    conn.close()
    #TODO: move download_config_files() here
    shutil.copyfile("postgres_conf/postgresql.conf", "/var/lib/pgsql/9.6/data/postgresql.conf")
    postgres_user_id = pwd.getpwnam(config["pg_sys_acct"]).pw_uid
    postgres_group_id = grp.getgrnam(config["pg_sys_acct_group"]).gr_gid
    os.chown("/var/lib/pgsql/9.6/data/postgresql.conf", postgres_user_id, postgres_group_id)

    with open("/var/lib/pgsql/9.6/data/pg_hba.conf") as hba_conf_file:
        hba_conf_file.write("host    all             all             0.0.0.0/0               md5")
    # download_config_files(force_install)
    conn = connect_to_db("esgfcet", db_name='esgcet', host="localhost", password="password")
    cur = conn.cursor()
    # load ESGF schemas
    cur.execute(open("sqldata/esgf_esgcet.sql", "r").read())
    cur.execute(open("sqldata/esgf_node_manager.sql", "r").read())
    cur.execute(open("sqldata/esgf_security.sql", "r").read())
    cur.execute(open("sqldata/esgf_dashboard.sql", "r").read())

    # # list database users
    print list_users(conn=conn)

    load_esgf_data(cur)

    # IMPORTANT: change connections to require encrypted password
    esg_functions.replace_string_in_file("/var/lib/pgsql/9.6/data/pg_hba.conf", "ident", "md5")

def load_esgf_data(cur):
    # # load ESGF data
    # su --login - postgres --command "psql esgcet < /usr/local/bin/esgf_security_data.sql"
    cur.execute(open("sqldata/esgf_security_data.sql", "r").read())

    # # initialize migration table
    # su --login - postgres --command "psql esgcet < /usr/local/bin/esgf_migrate_version.sql"
    cur.execute(open("sqldata/esgf_migrate_version.sql", "r").read())

def backup_db():
    pass

def write_postgress_env():
    pass
def write_postgress_install_log():
    pass
def _choose_postgres_user_password():
    while True:
        postgres_user_password = raw_input("Enter password for postgres user {postgress_user}: ".format(postgress_user=config["postgress_user"]))
        postgres_user_password_confirmation = raw_input("Re-enter password for postgres user {postgress_user}: ".format(postgress_user=config["postgress_user"]))
        if postgres_user_password != postgres_user_password_confirmation:
            print "The passwords did not match. Enter same password twice."
            continue
        else:
            return postgres_user_password



#----------------------------------------------------------
# Postgresql informational functions
#
# These functions require that Postgresql be already installed and
# running correctly.
#----------------------------------------------------------


def postgres_create_db(db_name):
    esg_functions.stream_subprocess_output("createdb -U {postgress_user} {db_name}".format(postgress_user=config["postgress_user"], db_name=db_name))

def postgres_list_db_schemas(conn=None, db_name="postgres", user_name="postgres"):
    '''This prints a list of all schemas known to postgres.'''
    if not conn:
        conn = connect_to_db(db_name, user_name)
    cur = conn.cursor()
    try:
        cur.execute("select schema_name from information_schema.schemata;")
        schemas = cur.fetchall()
        # print "schemas: ", schemas
        schema_list = [schema[0] for schema in schemas]
        return schema_list
    except Exception, error:
        print "error:", error

def postgres_list_schemas_tables(conn=None, db_name="postgres", user_name="postgres"):
    '''List all Postgres tables in all schemas, in the schemaname.tablename format, in the ESGF database'''
    if not conn:
        conn = connect_to_db(db_name, user_name)
    cur = conn.cursor()
    try:
        cur.execute("SELECT schemaname,relname FROM pg_stat_user_tables;")
        schemas_tables = cur.fetchall()
        print "schemas_tables: ", schemas_tables
        return schemas_tables
    except Exception, error:
        print "error:", error

def postgres_list_dbs(conn=None, db_name="postgres", user_name="postgres"):
    '''This prints a list of all databases known to postgres.'''
    if not conn:
        conn = connect_to_db(db_name, user_name)
    # conn = connect_to_db("postgres", "dbsuper")
    cur = conn.cursor()
    try:
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        databases = cur.fetchall()
        database_list = [database[0] for database in databases]
        return database_list
    except Exception, error:
        print "error: ", error

def list_users(conn=None, db_name="postgres", user_name="postgres"):
    '''List all users in database'''
    if not conn:
        conn = connect_to_db(db_name, user_name)
    cur = conn.cursor()
    cur.execute("""SELECT usename FROM pg_user;""")
    users = cur.fetchall()
    user_list = [user[0] for user in users]
    # conn.close()
    return user_list

def list_roles(conn=None, db_name="postgres", user_name="postgres"):
    '''List all roles'''
    if not conn:
        conn = connect_to_db(db_name, user_name)
    cur = conn.cursor()
    cur.execute("""SELECT rolname FROM pg_roles;""")
    roles = cur.fetchall()
    roles_list = [role[0] for role in roles]
    return roles_list



def postgres_clean_schema_migration(repository_id):
    # Removes entries from the esgf_migrate_version table if any exist
    # where repository_id matches an SQL LIKE to the first argument
    #
    # The SQL LIKE strings are generally defined in
    # "src/python/esgf/<reponame>/schema_migration/migrate.cfg" in
    # each relevant repository.
    conn = connect_to_db(config["node_db_name"], config["postgress_user"])
    cur = conn.cursor()

    try:
        cur.execute("select count(*) from esgf_migrate_version where repository_id LIKE '%$%s%'", repository_id)
        results = cur.fetchall()

        if results > 0:
            print "cleaning out schema migration bookeeping for esgf_node_manager..."
            cur.execute("delete from esgf_migrate_version where repository_id LIKE '%$%s%'", repository_id)
    except Exception, error:
        print "error: ", error

def main():
    setup_postgres()

if __name__ == '__main__':
    main()
