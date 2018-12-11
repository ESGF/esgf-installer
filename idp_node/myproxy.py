"""ESGF MyProxy Module."""
import os
import logging
import shutil
import ConfigParser
import OpenSSL
import psutil
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import pybash
from esgf_utilities import esg_property_manager
from esgf_utilities.esg_env_manager import EnvWriter
from plumbum.commands import ProcessExecutionError

logger = logging.getLogger("esgf_logger" + "." + __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def setup_gcs_id(first_run=None):
    """Register with Globus Web Service and get a host certificate."""
    """Runs the Globus Connect Server (gcs) ID setup script and gets a host certificate"""
    if first_run == "firstrun":
        cert_dir = "/etc/tempcerts"
    else:
        cert_dir = "/etc/esgfcerts"

    logger.debug("cert_dir: %s", cert_dir)

    with pybash.pushd(cert_dir):
        myproxyca_dir = "/var/lib/globus-connect-server/myproxy-ca"

        pybash.mkdir_p(os.path.join(myproxyca_dir, "newcerts"))
        os.chmod(myproxyca_dir, 0700)
        pybash.mkdir_p(os.path.join(myproxyca_dir, "private"))
        os.chmod(os.path.join(myproxyca_dir, "private"), 0700)

        shutil.copyfile("cacert.pem", os.path.join(myproxyca_dir, "cacert.pem"))
        shutil.copyfile("cakey.pem", os.path.join(myproxyca_dir, "private", "cakey.pem"))
        shutil.copyfile("signing-policy", os.path.join(myproxyca_dir, "signing-policy"))

        shutil.copyfile("hostcert.pem", "/etc/grid-security/hostcert.pem")
        shutil.copyfile("hostkey.pem", "/etc/grid-security/hostkey.pem")
        os.chmod("/etc/grid-security/hostkey.pem", 0600)

        try:
            cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open("cacert.pem").read())
        except OpenSSL.crypto.Error:
            logger.exception("Certificate is not correct.")
            raise

        cert_hash = esg_functions.convert_hash_to_hex(cert_obj.subject_name_hash())
        simpleCA_tar_file = "globus_simple_ca_{}_setup-0.tar.gz".format(cert_hash)
        shutil.copyfile(simpleCA_tar_file, os.path.join(myproxyca_dir, simpleCA_tar_file))
        shutil.copyfile(simpleCA_tar_file, os.path.join("/etc/grid-security/certificates", simpleCA_tar_file))

    print '*******************************'
    print ' Registering the IdP node with Globus Platform'
    print '*******************************'
    print 'The installer will create a Globus (www.globus.org) endpoint to allow users to'
    print 'download data through Globus. This uses the GridFTP server on the data node.'
    print 'The endpoint is named as <globus_username>#<host_name>, e.g. llnl#pcmdi9 where'
    print 'llnl is Globus username and pcmdi9 is endpoint name. To create a Globus account,'
    print 'go to www.globus.org/SignUp.'
    print 'This step can be skipped, but users will not be able to download datasets'
    print 'from the GridFTP server on the data node through the ESGF web interface.'

    try:
        register_myproxy_answer = esg_property_manager.get_property("register.myproxy")
    except ConfigParser.NoOptionError:
        register_myproxy_answer = raw_input(
            "Do you want to register the MyProxy server with Globus?: ") or "Y"

    globus_setup = register_myproxy_answer.lower() in ["y", "yes"]

    if globus_setup:
        myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
        pybash.mkdir_p(myproxy_config_dir)
        copy_gcs_conf()

        esg_functions.call_binary("globus-connect-server-id-setup", ["-c", "{}/globus-connect-server.conf".format(myproxy_config_dir), "-v"])

    # Create a substitution of Globus generated configuration files for MyProxy server
    copy_globus_connect_esgf()


def get_globus_username():
    """Get Globus username from properties file.  If not found, prompt user."""
    try:
        globus_user = esg_property_manager.get_property("globus.user")
    except ConfigParser.NoOptionError:
        while True:
            globus_user = raw_input("Please provide a Globus username: ")
            if not globus_user:
                print "Globus username cannot be blank."
            else:
                esg_property_manager.set_property("globus.user", globus_user)
                break
    return globus_user


def get_globus_password():
    """Get Globus password from properties file.  If not found, prompt user."""
    try:
        globus_password = esg_property_manager.get_property("globus.password")
    except ConfigParser.NoOptionError:
        while True:
            globus_password = raw_input("Please enter your Globus password: ")
            if not globus_password:
                print "The Globus password can not be blank"
                continue
            else:
                esg_property_manager.set_property("globus.password", globus_password)
                break

    return globus_password


def copy_gcs_conf(gcs_conf_path="/esg/config/myproxy/globus-connect-server.conf"):
    """Setups up the globus-connect-server.conf config file to be used with the globus-connect-server-id-setup binary."""
    shutil.copyfile(os.path.join(current_directory, "../config/globus-connect-server.conf"), gcs_conf_path)

    parser = ConfigParser.SafeConfigParser(allow_no_value=True)
    parser.read(gcs_conf_path)

    globus_user = get_globus_username()
    globus_password = get_globus_password()

    parser.set('Globus', "User", globus_user)
    parser.set('Globus', "Password", globus_password)
    parser.set('Endpoint', "Name", esg_property_manager.get_property("node.short.name"))
    parser.set('GridFTP', "Server", esg_functions.get_esgf_host())
    parser.set('MyProxy', "Server", esg_functions.get_esgf_host())

    with open(gcs_conf_path, "w") as conf_file:
        parser.write(conf_file)


def copy_globus_connect_esgf(config_path="/etc/myproxy.d/globus-connect-esgf"):
    """Copy custom Globus Connect configuration file."""
    pybash.mkdir_p("/etc/myproxy.d")
    logger.debug("Copying globus-connect-esgf file to /etc/myproxy.d")
    shutil.copyfile(os.path.join(current_directory, "../config/globus-connect-esgf"), config_path)


def config_myproxy_server(globus_location, install_mode="install"):
    """Configure MyProxy Server."""
    if install_mode not in ["install", "update"]:
        logger.error("You have entered an invalid argument: [%s]", install_mode)
        logger.error("The install mode must be either 'install' or 'update'")
        raise RuntimeError

    print "MyProxy - Configuration... [{}]".format(install_mode)

    copy_myproxy_certificate_apps()
    edit_pam_pgsql_conf()
    fetch_etc_pam_d_myproxy()
    copy_myproxy_server_config()
    edit_etc_myproxyd()
    write_db_name_env()

    restart_myproxy_server()


def start_myproxy_server():
    """Start MyProxy service."""
    if check_myproxy_process():
        return
    try:
        esg_functions.call_binary("service", ["myproxy-server", "start"])
    except ProcessExecutionError:
        raise


def stop_myproxy_server():
    """Stop MyProxy service."""
    try:
        esg_functions.call_binary("service", ["myproxy-server", "stop"])
    except ProcessExecutionError:
        raise

    if not check_myproxy_process():
        print "MyProxy Process is stopped..."


def restart_myproxy_server():
    """Restart MyProxy service."""
    try:
        esg_functions.call_binary("service", ["myproxy-server", "restart"])
    except ProcessExecutionError:
        raise


def myproxy_status():
    """Check the status of the myproxy server."""
    try:
        status = esg_functions.call_binary("service", ["myproxy-server", "status"])
    except ProcessExecutionError:
        pass
    else:
        return (True, status)


def check_myproxy_process():
    """Check the MyProxy process."""
    myproxy_processes = [proc for proc in psutil.process_iter(attrs=['pid', 'name', 'username']) if "myproxy-server" in proc.info["name"]]
    if myproxy_processes:
        print "myproxy-server process is running..."
        print myproxy_processes
        return myproxy_processes


def write_myproxy_install_log():
    """Write MyProxy install properties to logs."""
    if os.path.exists("/usr/sbin/myproxy-server"):
        esg_property_manager.set_property("myproxy_app_home", "/usr/sbin/myproxy-server")
        if not esg_property_manager.get_property("myproxy_endpoint"):
            esg_property_manager.set_property("myproxy_endpoint", esg_functions.get_esgf_host())
        if not esg_property_manager.get_property("myproxy_port"):
            default_myproxy_port = "7512"
            esg_property_manager.set_property("myproxy_port", default_myproxy_port)

        # TODO: get distinguished name for cert
        # esg_property_manager.set_property("myproxy_dn", default_myproxy_port)

        # TODO: Find myproxy_version
        # esg_functions.write_to_install_manifest("globus:myproxy", thredds_install_dir, thredds_version)


def copy_myproxy_server_config(config_path="/esg/config/myproxy/myproxy-server.config"):
    """Create /esg/config/myproxy/myproxy-server.config."""
    myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
    pybash.mkdir_p(myproxy_config_dir)
    if os.path.isfile(config_path):
        esg_functions.create_backup_file(config_path)
    logger.debug("Copying myproxy-server.config file to /esg/config/myproxy/")
    shutil.copyfile(os.path.join(current_directory, "../config/myproxy-server.config"), config_path)
    os.chmod(config_path, 0600)

############################################
# Configuration File Editing Functions
############################################


def copy_myproxy_certificate_apps():
    """Copy MyProxy certificate app into place."""
    myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
    pybash.mkdir_p(myproxy_config_dir)
    mapapp_file = os.path.join(os.path.dirname(__file__), "mapapp", "myproxy-certificate-mapapp")
    extapp_file = os.path.join(os.path.dirname(__file__), "mapapp", "esg_attribute_callout_app")
    retriever_file = os.path.join(os.path.dirname(__file__), "mapapp", "retriever.py")

    os.chmod(mapapp_file, 0751)
    os.chmod(extapp_file, 0751)

    shutil.copy2(mapapp_file, myproxy_config_dir)
    shutil.copy2(extapp_file, myproxy_config_dir)
    shutil.copy2(retriever_file, myproxy_config_dir)


def edit_pam_pgsql_conf():
    """Edit pam_pgsql configuration file with Postgres properties."""
    pgsql_conf_file = "/etc/pam_pgsql.conf"
    logger.info("Copy and Modifying pam pgsql configuration file: pam_pgsql.conf")
    shutil.copyfile(os.path.join(current_directory, "myproxy_conf_files/etc_pam_pgsql.conf"), pgsql_conf_file)
    os.chmod(pgsql_conf_file, 0600)

    # Replace placeholder values
    with open(pgsql_conf_file, 'r') as file_handle:
        filedata = file_handle.read()
    filedata = filedata.replace("@@esgf_db_name@@", esg_property_manager.get_property("db.database"))
    filedata = filedata.replace("@@postgress_host@@", esg_property_manager.get_property("db.host"))
    filedata = filedata.replace("@@postgress_port@@", esg_property_manager.get_property("db.port"))
    filedata = filedata.replace("@@postgress_user@@", esg_property_manager.get_property("db.user"))
    filedata = filedata.replace("@@esgf_idp_peer@@", esg_property_manager.get_property("esgf.index.peer"))
    filedata = filedata.replace("@@pg_sys_acct_passwd@@", esg_functions.get_postgres_password())

    # Write the file out again
    with open(pgsql_conf_file, 'w') as file_handle:
        file_handle.write(filedata)


def fetch_etc_pam_d_myproxy():
    """Fetch -> pam resource file used for myproxy."""
    myproxy_file = "/etc/pam.d/myproxy"
    logger.info("Copying pam's MyProxy resource file to %s", myproxy_file)
    shutil.copyfile(os.path.join(current_directory, "myproxy_conf_files/etc_pam.d_myproxy"), myproxy_file)


def edit_etc_myproxyd(myproxy_esgf_path="/etc/myproxy.d/myproxy-esgf"):
    """Add /etc/myproxy.d/myproxy-esgf to force MyProxy server to use /esg/config/myproxy/myproxy-server.config."""
    shutil.copyfile(os.path.join(current_directory, "../config/myproxy-esgf"), myproxy_esgf_path)


def write_db_name_env():
    """Write database name to environment configuration file."""
    EnvWriter.export("ESGF_DB_NAME", esg_property_manager.get_property("db.database"))
