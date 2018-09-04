import os
import grp
import pwd
import shutil
import sys
import re
import datetime
import ConfigParser
import logging
import getpass
from time import sleep
from distutils.spawn import find_executable
import yaml
import semver
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from esgf_utilities import esg_functions
from esgf_utilities import esg_property_manager
from esgf_utilities import pybash

logger = logging.getLogger("esgf_logger" + "." + __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def download_postgres():
    '''Download postgres from yum'''
    print "\n*******************************"
    print "Downloading Postgres"
    print "******************************* \n"

    esg_functions.stream_subprocess_output(
        "yum -y install postgresql-server.x86_64 postgresql.x86_64 postgresql-devel.x86_64")


def initialize_postgres():
    '''Sets up postgres data directory'''
    try:
        if os.listdir("/var/lib/pgsql/data"):
            logger.info("Data directory already exists. Skipping initialize_postgres().")
            return
    except OSError, error:
        logger.error(error)

    esg_functions.stream_subprocess_output("service postgresql initdb")
    os.chmod(os.path.join(config["postgress_install_dir"], "data"), 0700)


def check_existing_pg_version(psql_path, force_install=False):
    '''Gets the version number if a previous Postgres installation is detected'''
    print "Checking for postgresql >= {postgress_min_version} ".format(postgress_min_version=config["postgress_min_version"])

    if not psql_path:
        print "Postgres not found on system"
    else:
        try:
            postgres_version_found = esg_functions.call_subprocess("psql --version")["stdout"]
            postgres_version_number = re.search("\d.*", postgres_version_found).group()
            if semver.compare(postgres_version_number, config["postgress_min_version"]) >= 0 and not force_install:
                logger.info("Found acceptible Postgres version")
                return True
            else:
                logger.info("The Postgres version on the system does not meet the minimum requirements")
                return False
        except OSError:
            logger.exception("Unable to check existing Postgres version \n")


def setup_postgres(force_install=False, default_continue_install="N"):
    '''Installs postgres'''
    print "\n*******************************"
    print "Setting up Postgres"
    print "******************************* \n"

    psql_path = find_executable("psql")

    if check_existing_pg_version(psql_path):
        try:
            setup_postgres_answer = esg_property_manager.get_property("update.postgres")
        except ConfigParser.NoOptionError:
            setup_postgres_answer = raw_input(
                "Valid existing Postgres installation found. Do you want to continue with the setup [y/N]: ") or default_continue_install

        if setup_postgres_answer.lower().strip() in ["no", 'n']:
            logger.info("Skipping Postgres installation. Using existing Postgres version")
            return True
        else:
            force_install = True
            backup_db("postgres", "postgres")

    download_postgres()

    #Create system account (postgres) if it doesn't exist
    ########
    # Create the system account for postgress to run as.
    ########
    pg_sys_acct_homedir = psql_path
    if not check_for_postgres_sys_acct():
        # NOTE: "useradd/groupadd" are a RedHat/CentOS thing... to make this cross distro compatible clean this up.
        create_postgres_group()
        set_pg_sys_account_password()
        create_postgres_system_user(pg_sys_acct_homedir)

    else:
        postgress_user_shell = get_postgres_user_shell()
        if postgress_user_shell != "/bin/bash":
            set_postgres_user_shell()
    change_pg_install_dir_ownership()

    initialize_postgres()

    # start the postgres server
    start_postgres()
    setup_postgres_conf_file()

    restart_postgres()

    setup_db_schemas()
    create_pg_pass_file()

    esg_functions.check_shmmax()
    write_postgress_env()
    write_postgress_install_log()
    log_postgres_properties()

    # NOTE: The default pg_hba.conf starts with ident for auth, which means system accounts are used
    # This is so the postgres account can be initialized, ie have a password setup
    # After that is done it needs to be switched to md5. This command will also replace the idents
    # in the comments of the file.
    esg_functions.replace_string_in_file("/var/lib/pgsql/data/pg_hba.conf", "ident", "md5")

def create_pg_super_user(psycopg2_cursor, db_user_password):
    '''Create postgres super user'''
    print "Create {db_user} user: ".format(db_user=config["postgress_user"]), psycopg2_cursor.mogrify("CREATE USER {db_user} with CREATEROLE superuser PASSWORD \'{db_user_password}\';".format(db_user=config["postgress_user"], db_user_password=db_user_password))
    try:
        psycopg2_cursor.execute("CREATE USER {db_user} with CREATEROLE superuser PASSWORD \'{db_user_password}\';".format(
            db_user=config["postgress_user"], db_user_password=db_user_password))
    except psycopg2.ProgrammingError, error:
        # Error code reference: https://www.postgresql.org/docs/current/static/errcodes-appendix.html#ERRCODES-TABLE
        if error.pgcode == "42710":
            print "{db_user} role already exists. Skipping creation".format(db_user=config["postgress_user"])


def create_pg_publisher_user(cursor, db_user_password):
    '''Creates postgres user for the ESGF Publisher (esgcet by default)'''
    publisher_db_user = esg_property_manager.get_property("publisher.db.user")
    if not publisher_db_user:
        publisher_db_user = raw_input(
            "What is the (low privilege) db account for publisher? [esgcet]: ") or "esgcet"
    print "Create {publisher_db_user} user:".format(publisher_db_user=publisher_db_user), cursor.mogrify("CREATE USER {publisher_db_user} PASSWORD \'{db_user_password}\';".format(publisher_db_user=publisher_db_user, db_user_password=db_user_password))
    try:
        cursor.execute("CREATE USER {publisher_db_user} PASSWORD \'{db_user_password}\';".format(
            publisher_db_user=publisher_db_user, db_user_password=db_user_password))
    except psycopg2.ProgrammingError, error:
        # Error code reference: https://www.postgresql.org/docs/current/static/errcodes-appendix.html#ERRCODES-TABLE
        if error.pgcode == "42710":
            print "{publisher_db_user} role already exists. Skipping creation".format(publisher_db_user=publisher_db_user)

def setup_db_schemas(publisher_password=None):
    '''Load ESGF schemas'''
    conn = connect_to_db("postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    try:
        db_user_password = esg_functions.get_publisher_password()
    except IOError, error:
        logger.debug(error)
        esg_functions.set_publisher_password(publisher_password)
        db_user_password = esg_functions.get_publisher_password()

    create_pg_super_user(cur, db_user_password)

    # create 'esgcet' user
    create_pg_publisher_user(cur, db_user_password)

    # create CoG and publisher databases
    # create_database("cogdb", cur)
    create_database("esgcet", cur)
    cur.close()
    conn.close()

    # TODO: move download_config_files() here

    load_esgf_schemas(db_user_password)

def load_esgf_schemas(db_user_password):
    '''Loads ESGF schemas from SQL scripts'''
    conn = connect_to_db("dbsuper", db_name='esgcet', password=db_user_password)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    # load ESGF schemas
    cur.execute(open(os.path.join(os.path.dirname(__file__), "sqldata/esgf_esgcet.sql"), "r").read())
    cur.execute(open(os.path.join(os.path.dirname(__file__), "sqldata/esgf_node_manager.sql"), "r").read())
    cur.execute(open(os.path.join(os.path.dirname(__file__), "sqldata/esgf_dashboard.sql"), "r").read())

    #TODO: A bit of a hack; the CoG setup in an index node has a dependency on the esgf_security schema;
    # thus the index node has a dependency on the IDP node.  First attempt to decouple
    #Will eventually be handled in the ClI enforcing valid node types (i.e. index+idp)
    # node_type = esg_functions.get_node_type()
    # if "INDEX" in node_type:
    #     cur.execute(open(os.path.join(os.path.dirname(__file__), "sqldata/esgf_security.sql"), "r").read())


    load_esgf_data(cur)
    cur.close()
    conn.close()

def load_esgf_data(cur):
    '''# load ESGF data
    su --login - postgres --command "psql esgcet < /usr/local/bin/esgf_security_data.sql"
    cur.execute(open(os.path.join(os.path.dirname(__file__), "sqldata/esgf_security_data.sql"), "r").read())

    # initialize migration table
    su --login - postgres --command "psql esgcet < /usr/local/bin/esgf_migrate_version.sql"'''
    cur.execute(open(os.path.join(os.path.dirname(__file__), "sqldata/esgf_migrate_version.sql"), "r").read())


def backup_db(db_name, user_name, backup_dir="/etc/esgf_db_backup"):
    '''Backup database to directory specified by backup_dir'''
    backup_existing_db = esg_property_manager.get_property("backup.database")
    if not backup_existing_db or backup_existing_db.lower() not in ["yes", "y", "n", "no"]:
        backup_db_input = raw_input("Do you want to backup the current database? [Y/n]: ")
        if backup_db_input.lower() in ["n", "no"]:
            logger.info("Skipping backup database.")
            return

    pybash.mkdir_p(backup_dir)
    try:
        conn = connect_to_db(db_name, user_name)
        cur = conn.cursor()
        tables = list_tables(conn)
        for table in tables:
            # cur.execute('SELECT x FROM t')
            backup_file = os.path.join(backup_dir, '{table}_backup_{date}.sql'.format(
                table=table, date=str(datetime.date.today())))
            cur.execute("SELECT * FROM %s" % (table))
            backup_file_object = open(backup_file, 'w')
            for row in cur:
                backup_file_object.write("insert into t values (" + str(row) + ");")
            backup_file_object.close()
    except psycopg2.DatabaseError, error:
        print 'Error %s' % error
        sys.exit(1)
    finally:
        if conn:
            conn.close()

#----------------------------------------------------------
# Postgresql connections functions
#----------------------------------------------------------

def build_connection_string(user, db_name=None, host=None, password=None):
    '''Creates the db connection string using the params as options '''
    db_connection_string = ["user={user}".format(user=user)]
    if db_name:
        db_connection_string.append("dbname={db_name}".format(db_name=db_name))
    if host:
        db_connection_string.append("host={host}".format(host=host))
    if password:
        db_connection_string.append("password={password}".format(password=password))

    return " ".join(db_connection_string)


def connect_to_db(user, db_name=None, host="/tmp", password=None):
    ''' Connect to database '''
    # Using password auth currently;
    # if the user is postgres, the effective user id (euid) needs to be postgres' user id.
    # Essentially change user from root to postgres
    root_id = pwd.getpwnam("root").pw_uid
    if user == "postgres":
        postgres_id = pwd.getpwnam("postgres").pw_uid

        os.seteuid(postgres_id)
    db_connection_string = build_connection_string(user, db_name, host, password)
    try:
        conn = psycopg2.connect(db_connection_string)
        logger.debug("Connected to %s database as user '%s'", db_name, user)
        if not conn:
            print "Failed to connect to {db_name}".format(db_name=db_name)
            raise Exception

        # Set effective user id (euid) back to root
        if os.geteuid() != root_id:
            os.seteuid(root_id)

        return conn
    except Exception:
        logger.exception("Unable to connect to the database.")
        raise

#----------------------------------------------------------
# Postgresql user/group management functions
#----------------------------------------------------------
def create_pg_pass_file():
    '''Creates the file to store login passwords for psql'''
    pg_pass_file_path = os.path.join(os.environ["HOME"], ".pgpass")
    with open(pg_pass_file_path, "w") as pg_pass_file:
        pg_pass_file.write('localhost:5432:cogdb:dbsuper:password')
        pg_pass_file.write('localhost:5432:esgcet:dbsuper:password')
    os.chmod(pg_pass_file_path, 0600)


def check_for_postgres_sys_acct():
    '''Check if the postgres user account exists on the server'''
    try:
        pwd.getpwnam(config["pg_sys_acct"]).pw_uid
    except KeyError:
        print " Hmmm...: There is no postgres system account user \"{pg_sys_acct}\" present on system, making one...".format(pg_sys_acct=config["pg_sys_acct"])
    else:
        return True


def create_postgres_group():
    '''Creates postgres Unix group'''
    groupadd_command = "/usr/sbin/groupadd -r %s" % (
        config["pg_sys_acct_group"])
    try:
        groupadd_output = esg_functions.call_subprocess(groupadd_command)
    except SubprocessError, error:
        raise
    else:
        if groupadd_output["returncode"] != 0 or groupadd_output["returncode"] != 9:
            logger.error("Could not add postgres system group: %s", config["pg_sys_acct_group"])
            raise RuntimeError
        else:
            print "Created postgres group with group id: {postgres_group_id}".format(postgres_group_id=grp.getgrnam(config["pg_sys_acct_group"]).gr_gid)


def set_pg_sys_account_password():
    '''Sets postgres user account password'''
    if esg_functions.get_postgres_password():
        logger.info("Postgres password already set")
        return
    else:
        while True:
            pg_sys_acct_passwd_input = getpass.getpass(
                "Create password for postgress system account: ")
            if not pg_sys_acct_passwd_input:
                print "Please enter a password: "
                continue
            else:
                config["pg_sys_acct_passwd"] = pg_sys_acct_passwd_input
                break
        esg_functions.set_postgres_password(pg_sys_acct_passwd_input)


def create_postgres_system_user(pg_sys_acct_homedir):
    '''Create Postgres Unix user'''
    print "Creating Postgres user account..."
    useradd_command = '''/usr/sbin/useradd -r -c'PostgreSQL Service ESGF'
    -d {pg_sys_acct_homedir} -g {pg_sys_acct_group} -p
    {pg_sys_acct_passwd} -s /bin/bash {pg_sys_acct}'''.format(pg_sys_acct_homedir=pg_sys_acct_homedir,
                                                              pg_sys_acct_group=config["pg_sys_acct_group"],
                                                              pg_sys_acct_passwd=config["pg_sys_acct_passwd"],
                                                              pg_sys_acct=config["pg_sys_acct"])


    try:
        useradd_output = esg_functions.call_subprocess(useradd_command)
    except SubprocessError:
        logger.error("Could not create postgres user")
        raise
    else:
        if useradd_output["returncode"] != 0 or useradd_output["returncode"] != 9:
            raise RuntimeError("Could not add postgres system account user")


    postgres_user_id = pwd.getpwnam(config["pg_sys_acct"]).pw_uid

    if not postgres_user_id:
        raise RuntimeError("Problem with {} creation!!!".format(config["pg_sys_acct"]))
    else:
        postgres_group_id = grp.getgrnam("postgres").gr_gid
        print "Created postgres user with group id: {}".format(postgres_group_id)


def get_postgres_user_shell():
    '''Returns the shell for the postgres user'''
    return pwd.getpwnam(config["pg_sys_acct"])[6]


def set_postgres_user_shell():
    '''Sets the postgres user shell to /bin/bash'''
    print "Noticed that the existing postgres user [{pg_sys_acct}] does not have the bash shell... Hmmm... making it so ".format(pg_sys_acct=config["pg_sys_acct"])
    change_shell_command = "sed -i 's#\('{pg_sys_acct}'.*:\)\(.*\)$#\1/\bin/\bash#' /etc/passwd".format(
        pg_sys_acct=config["pg_sys_acct"])
    esg_functions.call_subprocess(change_shell_command)
    if get_postgres_user_shell() == "/bin/bash":
        print "[OK]"
        print "Postgres user shell is properly configured"
    else:
        print "[FAIL]"
        print "Postgres user shell is not properly configured. The shell is {postgres_shell}. It should be /bin/bash".format(postgres_shell=get_postgres_user_shell())


def change_pg_install_dir_ownership():
    '''Change permissions on postgress_install_dir'''
    postgres_user_id = pwd.getpwnam(config["pg_sys_acct"]).pw_uid
    postgres_group_id = grp.getgrnam(config["pg_sys_acct_group"]).gr_gid
    os.chown(config["postgress_install_dir"], postgres_user_id, postgres_group_id)



#----------------------------------------------------------
# Postgresql process management functions
#----------------------------------------------------------

def start_postgres():
    ''' Start db '''
    # if the data directory doesn't exist or is empty
    if not os.path.isdir("/var/lib/pgsql/data/") or not os.listdir("/var/lib/pgsql/data/"):
        initialize_postgres()
    esg_functions.stream_subprocess_output("service postgresql start")
    esg_functions.stream_subprocess_output("chkconfig postgresql on")

    sleep(3)
    if postgres_status():
        return True


def stop_postgres():
    '''Stops the postgres server'''
    esg_functions.stream_subprocess_output("service postgresql stop")


def postgres_status():
    '''Checks the status of the postgres server'''
    status = esg_functions.call_subprocess("service postgresql status")
    print "Postgres server status:", status["stdout"]
    if "running" in status["stdout"]:
        return (True, status)
    else:
        return False


def restart_postgres():
    '''Restarts the postgres server'''
    print "Restarting postgres server"
    restart_process = esg_functions.call_subprocess("service postgresql restart")
    if restart_process["returncode"] != 0:
        print "Restart failed."
        print "Error:", restart_process["stderr"]
        sys.exit(1)
    else:
        print restart_process["stdout"]
    sleep(7)
    postgres_status()


#----------------------------------------------------------
# Postgresql configuration management functions
#----------------------------------------------------------

def setup_postgres_conf_file():
    '''Copies postgres.conf file to proper location'''
    pg_conf = "/var/lib/pgsql/data/postgresql.conf"
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "postgres_conf/postgresql.conf"), pg_conf)
    postgres_user_id = esg_functions.get_user_id("postgres")
    postgres_group_id = esg_functions.get_group_id("postgres")
    os.chown(pg_conf, postgres_user_id, postgres_group_id)
    os.chmod(pg_conf, 0600)

def download_config_files(force_install):
    ''' Download config files '''
    # #Get files
    esg_dist_url = esg_property_manager.get_property("esg.dist.url")
    hba_conf_file = "pg_hba.conf"
    if not esg_functions.download_update(hba_conf_file, os.path.join(esg_dist_url, "externals", "bootstrap", hba_conf_file), force_install):
        raise RuntimeError("Could not download pg_hba.conf from distribution mirror")
    os.chmod(hba_conf_file, 0600)

    postgres_conf_file = "postgresql.conf"
    if not esg_functions.download_update(postgres_conf_file, os.path.join(esg_dist_url, "externals", "bootstrap", postgres_conf_file), force_install):
        raise RuntimeError("Could not download postgresql.conf from distribution mirror")
    os.chmod(postgres_conf_file, 0600)


def update_port_in_config_file():
    '''Updates the postgres port number in postgresql.conf'''
    postgres_port_input = raw_input("Please Enter PostgreSQL port number [{postgress_port}]:> ".format(
        postgress_port=config["postgress_port"])) or config["postgress_port"]
    print "\nSetting Postgress Port: {postgress_port} ".format(postgress_port=postgres_port_input)

    with open('postgresql.conf', 'r') as pg_conf_file:
        filedata = pg_conf_file.read()
    filedata = filedata.replace('@@postgress_port@@', config["postgress_port"])

    # Write the file out again
    with open('postgresql.conf', 'w') as pg_conf_file:
        pg_conf_file.write(filedata)


def update_log_dir_in_config_file():
    ''' Edit postgres config file '''
    print "Setting Postgress Log Dir in config_file: {postgress_install_dir} ".format(postgress_install_dir=config["postgress_install_dir"])

    with open('postgresql.conf', 'r') as pg_conf_file:
        filedata = pg_conf_file.read()
    filedata = filedata.replace('@@postgress_install_dir@@', config["postgress_install_dir"])

    # Write the file out again
    with open('postgresql.conf', 'w') as pg_conf_file:
        pg_conf_file.write(filedata)

    os.chown(config["postgress_install_dir"], pwd.getpwnam(config["pg_sys_acct"]).pw_uid,
             grp.getgrnam(config["pg_sys_acct_group"]).gr_gid)


#----------------------------------------------------------
# Postgresql logging functions
#----------------------------------------------------------
def log_postgres_properties():
    '''Write postgres properties to /esg/config/esgf.properties'''
    esg_property_manager.set_property("db.user", config["postgress_user"])
    esg_property_manager.set_property("db.host", config["postgress_host"])
    esg_property_manager.set_property("db.port", config["postgress_port"])
    esg_property_manager.set_property("db.database", "esgcet")

def write_postgress_env():
    '''Write postgres environment properties to /etc/esg.env'''
    esg_property_manager.set_property("PGHOME", "export PGHOME=/usr/bin/postgres", property_file=config["envfile"], section_name="esgf.env", separator="_")
    esg_property_manager.set_property("PGUSER", "export PGUSER={}".format(config["postgress_user"]), property_file=config["envfile"], section_name="esgf.env", separator="_")
    esg_property_manager.set_property("PGPORT", "export PGPORT={}".format(config["postgress_port"]), property_file=config["envfile"], section_name="esgf.env", separator="_")
    esg_property_manager.set_property("PGBINDIR", "export PGBINDIR={}".format(config["postgress_bin_dir"]), property_file=config["envfile"], section_name="esgf.env", separator="_")
    esg_property_manager.set_property("PGLIBDIR", "export PGLIBDIR={}".format(config["postgress_lib_dir"]), property_file=config["envfile"], section_name="esgf.env", separator="_")
    esg_property_manager.set_property("PATH", config["myPATH"], property_file=config["envfile"], section_name="esgf.env", separator="_")
    esg_property_manager.set_property("LD_LIBRARY_PATH", config["myLD_LIBRARY_PATH"], property_file=config["envfile"], section_name="esgf.env", separator="_")

def write_postgress_install_log():
    '''Write postgres version to install manifest'''
    postgres_version_found = esg_functions.call_subprocess("psql --version")["stdout"]
    postgres_version_number = re.search("\d.*", postgres_version_found).group()
    esg_functions.write_to_install_manifest("postgres", config["postgress_install_dir"], postgres_version_number)

#----------------------------------------------------------
# Postgresql informational functions
#
# These functions require that Postgresql be already installed and
# running correctly.
#----------------------------------------------------------


def create_database(database_name, cursor=None):
    '''Create database in postgres'''
    if not cursor:
        conn = connect_to_db("postgres")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
    try:
        cursor.execute("CREATE DATABASE {};".format(database_name))
    except psycopg2.ProgrammingError, error:
        # Error code reference: https://www.postgresql.org/docs/current/static/errcodes-appendix.html#ERRCODES-TABLE
        if error.pgcode == "42P04":
            logger.info("%s database already exists.  Skipping creation.", database_name)


def postgres_list_db_schemas(conn=None, user_name="postgres", db_name="postgres", password=None):
    '''This prints a list of all schemas known to postgres.'''
    if not conn:
        conn = connect_to_db(user_name, db_name, password=password)
    cur = conn.cursor()
    try:
        cur.execute("select schema_name from information_schema.schemata;")
        schemas = cur.fetchall()
        schema_list = [schema[0] for schema in schemas]
        return schema_list
    except Exception:
        logger.exception("Could not list database schemas")


def postgres_list_schemas_tables(conn=None, user_name="postgres", db_name="postgres"):
    '''List all Postgres tables in all schemas, in the schemaname.tablename format, in the ESGF database'''
    if not conn:
        conn = connect_to_db(user_name, db_name)
    cur = conn.cursor()
    try:
        cur.execute("SELECT schemaname,relname FROM pg_stat_user_tables;")
        schemas_tables = cur.fetchall()
        logger.debug("schemas_tables: %s", schemas_tables)
        return schemas_tables
    except Exception:
        logger.exception("Could not list schema tables")


def postgres_list_dbs(conn=None, user_name="postgres", db_name="postgres"):
    '''This prints a list of all databases known to postgres.'''
    if not conn:
        conn = connect_to_db(user_name, db_name)
    cur = conn.cursor()
    try:
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        databases = cur.fetchall()
        database_list = [database[0] for database in databases]
        return database_list
    except Exception:
        logger.exception("Could not list databases")


def list_users(conn=None, user_name="postgres", db_name="postgres"):
    '''List all users in database'''
    if not conn:
        conn = connect_to_db(user_name, db_name)
    cur = conn.cursor()
    try:
        cur.execute("""SELECT usename FROM pg_user;""")
        users = cur.fetchall()
        user_list = [user[0] for user in users]
        return user_list
    except Exception:
        logger.exception("Could not list users")


def list_roles(conn=None, user_name="postgres", db_name="postgres"):
    '''List all roles'''
    if not conn:
        conn = connect_to_db(user_name, db_name)
    cur = conn.cursor()
    cur.execute("""SELECT rolname FROM pg_roles;""")
    roles = cur.fetchall()
    roles_list = [role[0] for role in roles]
    return roles_list


def list_tables(conn=None, user_name="postgres", db_name="postgres"):
    '''List all tables in current database'''
    if not conn:
        conn = connect_to_db(user_name, db_name)
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';""")
    tables = cur.fetchall()
    tables_list = [{"schema_name": table[0], "table_name":table[1], "owner": table[2]}
                   for table in tables]
    return tables_list


def postgres_clean_schema_migration(repository_id):
    '''Removes entries from the esgf_migrate_version table if any exist
    where repository_id matches an SQL LIKE to the first argument

    The SQL LIKE strings are generally defined in
    "src/python/esgf/<reponame>/schema_migration/migrate.cfg" in
    each relevant repository.'''
    db_user_password = esg_functions.get_publisher_password()
    conn = connect_to_db(config["postgress_user"], config["node_db_name"], password=db_user_password)
    cur = conn.cursor()

    try:
        cur.execute(
            "select count(*) from esgf_migrate_version where repository_id LIKE '%$%s%'", repository_id)
        results = cur.fetchall()

        if results > 0:
            print "cleaning out schema migration bookeeping for esgf_node_manager..."
            cur.execute(
                "delete from esgf_migrate_version where repository_id LIKE '%$%s%'", repository_id)
    except Exception, error:
        print "error: ", error


def main():
    '''Main function'''
    setup_postgres()


if __name__ == '__main__':
    main()
