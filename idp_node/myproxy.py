import os
import logging
import shutil
import ConfigParser
import OpenSSL
import stat
import glob
import psutil
import yaml
from requests.exceptions import HTTPError
from esgf_utilities import esg_functions
from esgf_utilities import pybash
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from esgf_utilities import esg_cert_manager
from esgf_utilities.esg_exceptions import SubprocessError
from base import esg_tomcat_manager
from base import esg_postgres
from esgf_utilities.esg_env_manager import EnvWriter

logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

#--------------------
# Register with Globus Web Service and get a host certificate
#--------------------
def setup_gcs_id(first_run=None):
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

    if register_myproxy_answer.lower() in ["y", "yes"]:
        GLOBUS_SETUP = True
    else:
        GLOBUS_SETUP = False

    if GLOBUS_SETUP:
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

        try:
            myproxy_hostname = esg_property_manager.get_property("myproxy_endpoint")
        except ConfigParser.NoOptionError:
            myproxy_hostname = esg_functions.get_esgf_host().upper()

        myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
        pybash.mkdir_p(myproxy_config_dir)
        globus_server_conf_file = os.path.join(myproxy_config_dir, "globus-connect-server.conf")

        parser = ConfigParser.SafeConfigParser(allow_no_value=True)
        parser.read(globus_server_conf_file)

        try:
            parser.add_section("Globus")
        except ConfigParser.DuplicateSectionError:
            logger.debug("section already exists")

        parser.set('Globus', "User", globus_user)
        parser.set('Globus', "Password", globus_password)

        try:
            parser.add_section("Endpoint")
        except ConfigParser.DuplicateSectionError:
            logger.debug("section already exists")

        parser.set('Endpoint', "Name", esg_property_manager.get_property("node.short.name"))
        parser.set('Endpoint', "Public", "True")

        try:
            parser.add_section("Security")
        except ConfigParser.DuplicateSectionError:
            logger.debug("section already exists")

        parser.set('Security', "FetchCredentialFromRelay", "False")
        parser.set('Security', "CertificateFile", "/etc/grid-security/hostcert.pem")
        parser.set('Security', "KeyFile", "/etc/grid-security/hostkey.pem")
        parser.set('Security', "TrustedCertificateDirectory", "/etc/grid-security/certificates/")
        parser.set('Security', "IdentityMethod", "MyProxy")
        parser.set('Security', "AuthorizationMethod", "Gridmap")

        try:
            parser.add_section("GridFTP")
        except ConfigParser.DuplicateSectionError:
            logger.debug("section already exists")

        parser.set('GridFTP', "Server", esg_functions.get_esgf_host())
        parser.set('GridFTP', "RestrictPaths", "R/,N/etc,N/tmp,N/dev")
        parser.set('GridFTP', "Sharing", "False")
        parser.set('GridFTP', "SharingRestrictPaths", "R/")

        try:
            parser.add_section("MyProxy")
        except ConfigParser.DuplicateSectionError:
            logger.debug("section already exists")

        parser.set('MyProxy', "Server", esg_functions.get_esgf_host())

        with open(globus_server_conf_file, "w") as config_file_object:
            parser.write(config_file_object)

        esg_functions.stream_subprocess_output("globus-connect-server-id-setup -c {}/globus-connect-server.conf -v".format(myproxy_config_dir))

    # Create a substitution of Globus generated confguration files for MyProxy server
    pybash.mkdir_p("/etc/myproxy.d")
    with open("/etc/myproxy.d/globus-connect-esgf", "w") as globus_connect_conf_file:
        globus_connect_conf_file.write("export MYPROXY_USER=root\n")
        globus_connect_conf_file.write('export X509_CERT_DIR="/etc/grid-security/certificates"\n')
        globus_connect_conf_file.write('export X509_USER_CERT="/etc/grid-security/hostcert.pem"\n')
        globus_connect_conf_file.write('export X509_USER_KEY="/etc/grid-security/hostkey.pem"\n')
        globus_connect_conf_file.write('export X509_USER_PROXY=""\n')
        globus_connect_conf_file.write('export MYPROXY_OPTIONS="-c /var/lib/globus-connect-server/myproxy-server.conf -s /var/lib/globus-connect-server/myproxy-ca/store"')

    with open("/esg/config/myproxy/myproxy-server.config", "w") as myproxy_server_file:
        myproxy_server_file.write('authorized_retrievers      "*"\n')
        myproxy_server_file.write('default_retrievers         "*"\n')
        myproxy_server_file.write('authorized_renewers        "*"\n')
        myproxy_server_file.write('authorized_key_retrievers  "*"\n')
        myproxy_server_file.write('trusted_retrievers         "*"\n')
        myproxy_server_file.write('default_trusted_retrievers "none"\n')
        myproxy_server_file.write('max_cert_lifetime          "72"\n')
        myproxy_server_file.write('disable_usage_stats        "true"\n')
        myproxy_server_file.write('cert_dir                   "/etc/grid-security/certificates"\n')

        myproxy_server_file.write('pam_id "myproxy"\n')
        myproxy_server_file.write('pam "required"\n')

        myproxy_server_file.write('certificate_issuer_cert "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"\n')
        myproxy_server_file.write('certificate_issuer_key "/var/lib/globus-connect-server/myproxy-ca/private/cakey.pem"\n')
        myproxy_server_file.write('certificate_issuer_key_passphrase "globus"\n')
        myproxy_server_file.write('certificate_serialfile "/var/lib/globus-connect-server/myproxy-ca/serial"\n')
        myproxy_server_file.write('certificate_out_dir "/var/lib/globus-connect-server/myproxy-ca/newcerts"\n')
        myproxy_server_file.write('certificate_issuer_subca_certfile "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"\n')
        myproxy_server_file.write('certificate_mapapp /esg/config/myproxy/myproxy-certificate-mapapp\n')
        myproxy_server_file.write('certificate_extapp /esg/config/myproxy/esg_attribute_callout_app\n')


def config_myproxy_server(globus_location, install_mode="install"):
    if install_mode not in ["install", "update"]:
        logger.error("You have entered an invalid argument: [%s]", install_mode)
        logger.error("The install mode must be either 'install' or 'update'")
        raise RuntimeError

    print "MyProxy - Configuration... [{}]".format(install_mode)


    #--------------------
    # Compile Java Code Used by "callout" scripts in ${globus_location}/bin
    #--------------------
    if not os.path.exists(os.path.join(globus_location, "bin", "ESGOpenIDRetriever.class")) or os.path.exists(os.path.join(globus_location, "bin", "ESGGroupRetriever")):
        with pybash.pushd("{}/bin".format(globus_location)):
            myproxy_dist_url_base = "{}/globus/myproxy".format(esg_property_manager.get_property("esg.root.url"))
            try:
                esg_functions.download_update("ESGOpenIDRetriever.java", "{}/ESGOpenIDRetriever.java".format(myproxy_dist_url_base))
            except HTTPError:
                raise
            try:
                esg_functions.download_update("ESGGroupRetriever.java", "{}/ESGGroupRetriever.java".format(myproxy_dist_url_base))
            except HTTPError:
                raise

            postgress_jar = "postgresql-8.4-703.jdbc3.jar"
            try:
                esg_functions.download_update(postgress_jar, "{}/{}".format(myproxy_dist_url_base, postgress_jar))
            except HTTPError:
                raise


            #Find all files with a .jar extension and concat file names separated by a colon.
            java_class_path = glob.glob("*.jar")
            java_class_path_string = ":".join(java_class_path)

            esg_functions.stream_subprocess_output("javac -classpath {} ESGOpenIDRetriever.java".format(java_class_path_string))
            esg_functions.stream_subprocess_output("javac -classpath {} ESGGroupRetriever.java".format(java_class_path_string))

        fetch_myproxy_certificate_mapapp()
        edit_pam_pgsql_conf()
        #--------------------
        # Fetch -> pam resource file used for myproxy
        #--------------------
        fetch_etc_pam_d_myproxy()
        fetch_esg_attribute_callout_app()
        #--------------------
        # Create /esg/config/myproxy/myproxy-server.config
        #--------------------
        edit_myproxy_server_config()
        #--------------------
        # Add /etc/myproxy.d/myproxy-esgf to force MyProxy server to use /esg/config/myproxy/myproxy-server.config
        #--------------------
        edit_etc_myproxyd()
        write_db_name_env()

        restart_myproxy_server()


def start_myproxy_server():
    if check_myproxy_process():
        return

    #TODO: this checks if a file has execute permissions; break into helper function
    if os.access("/etc/init.d/myproxy-server", os.X_OK):
        esg_functions.stream_subprocess_output("/etc/init.d/myproxy-server start")
    elif os.access("/etc/init.d/myproxy", os.X_OK):
        print " MyProxy - Starting server..."
        esg_functions.stream_subprocess_output("/etc/init.d/myproxy start")

def stop_myproxy_server():
    if os.access("/etc/init.d/myproxy-server", os.X_OK):
        esg_functions.stream_subprocess_output("/etc/init.d/myproxy-server stop")
    elif os.access("/etc/init.d/myproxy", os.X_OK):
        esg_functions.stream_subprocess_output("/etc/init.d/myproxy stop")

    if not check_myproxy_process():
        print "MyProxy Process is stopped..."

def restart_myproxy_server():
    stop_myproxy_server()
    start_myproxy_server()

def myproxy_status():
    '''Checks the status of the myproxy server'''
    if os.access("/etc/init.d/myproxy-server", os.X_OK):
        status = esg_functions.call_subprocess("/etc/init.d/myproxy-server status")
    print "myproxy server status:", status["stdout"]
    if "running" in status["stdout"]:
        return (True, status)
    else:
        return False

def check_myproxy_process():
    myproxy_processes = [proc for proc in psutil.process_iter(attrs=['pid', 'name', 'username']) if "myproxy-server" in proc.info["name"]]
    if myproxy_processes:
        print "myproxy-server process is running..."
        print myproxy_processes
        return myproxy_processes

def write_myproxy_install_log():
    if os.path.exists("/usr/sbin/myproxy-server"):
        esg_property_manager.set_property("myproxy_app_home", "/usr/sbin/myproxy-server")
        if not esg_property_manager.get_property("myproxy_endpoint"):
            esg_property_manager.set_property("myproxy_endpoint", esg_functions.get_esgf_host())
        if not esg_property_manager.get_property("myproxy_port"):
            default_myproxy_port = "7512"
            esg_property_manager.set_property("myproxy_port", default_myproxy_port)

        #TODO: get distinguished name for cert
        # esg_property_manager.set_property("myproxy_dn", default_myproxy_port)

        myproxy_app_home = "/usr/sbin/myproxy-server"
        #TODO: Find myproxy_version
        # esg_functions.write_to_install_manifest("globus:myproxy", thredds_install_dir, thredds_version)

def edit_myproxy_server_config():
    myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
    pybash.mkdir_p(myproxy_config_dir)
    with pybash.pushd(myproxy_config_dir):
        myproxy_config_file = "myproxy-server.config"
        "Creating/Modifying myproxy server configuration file: {}".format(myproxy_config_file)
        if os.path.isfile(myproxy_config_file):
            esg_functions.create_backup_file(myproxy_config_file)
        with open("/esg/config/myproxy/myproxy-server.config", "w") as myproxy_server_file:
            myproxy_server_file.write('authorized_retrievers      "*"\n')
            myproxy_server_file.write('default_retrievers         "*"\n')
            myproxy_server_file.write('authorized_renewers        "*"\n')
            myproxy_server_file.write('authorized_key_retrievers  "*"\n')
            myproxy_server_file.write('trusted_retrievers         "*"\n')
            myproxy_server_file.write('default_trusted_retrievers "none"\n')
            myproxy_server_file.write('max_cert_lifetime          "72"\n')
            myproxy_server_file.write('disable_usage_stats        "true"\n')
            myproxy_server_file.write('cert_dir                   "/etc/grid-security/certificates"\n')

            myproxy_server_file.write('pam_id "myproxy"\n')
            myproxy_server_file.write('pam "required"\n')

            myproxy_server_file.write('certificate_issuer_cert "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"\n')
            myproxy_server_file.write('certificate_issuer_key "/var/lib/globus-connect-server/myproxy-ca/private/cakey.pem"\n')
            myproxy_server_file.write('certificate_issuer_key_passphrase "globus"\n')
            myproxy_server_file.write('certificate_serialfile "/var/lib/globus-connect-server/myproxy-ca/serial"\n')
            myproxy_server_file.write('certificate_out_dir "/var/lib/globus-connect-server/myproxy-ca/newcerts"\n')
            myproxy_server_file.write('certificate_issuer_subca_certfile "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"\n')
            myproxy_server_file.write('certificate_mapapp /esg/config/myproxy/myproxy-certificate-mapapp\n')
            myproxy_server_file.write('certificate_extapp /esg/config/myproxy/esg_attribute_callout_app\n')

        os.chmod(myproxy_config_file, 0600)

############################################
# Configuration File Editing Functions
############################################

def fetch_myproxy_certificate_mapapp():
    myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
    pybash.mkdir_p(myproxy_config_dir)
    with pybash.pushd(myproxy_config_dir):
        mapapp_file = "myproxy-certificate-mapapp"
        print "Downloading configuration file: {}".format(mapapp_file)
        myproxy_dist_url_base = "{}/globus/myproxy".format(esg_property_manager.get_property("esg.root.url"))
        try:
            esg_functions.download_update(mapapp_file, myproxy_dist_url_base+"/{}".format(mapapp_file))
        except HTTPError:
            raise

        os.chmod(mapapp_file, 0751)
        esg_functions.replace_string_in_file(mapapp_file, "/root/.globus/simpleCA/cacert.pem", "/var/lib/globus-connect-server/myproxy-ca/cacert.pem")

def edit_pam_pgsql_conf():
    with pybash.pushd("/etc"):
        pgsql_conf_file = "pam_pgsql.conf"
        "Download and Modifying pam pgsql configuration file: {}".format(pgsql_conf_file)
        myproxy_dist_url_base = "{}/globus/myproxy".format(esg_property_manager.get_property("esg.root.url"))
        try:
            esg_functions.download_update(pgsql_conf_file, myproxy_dist_url_base+"/etc_{}".format(pgsql_conf_file))
        except HTTPError:
            raise

        os.chmod(pgsql_conf_file, 0600)

        #Replace placeholder values
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
    with pybash.pushd("/etc/pam.d"):
        myproxy_file = "myproxy"
        "Fetching pam's myproxy resource file: {}".format(myproxy_file)
        myproxy_dist_url_base = "{}/globus/myproxy".format(esg_property_manager.get_property("esg.root.url"))
        try:
            esg_functions.download_update(myproxy_file, myproxy_dist_url_base+"/etc_pam.d_{}".format(myproxy_file))
        except HTTPError:
            raise

def fetch_esg_attribute_callout_app():
    myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
    pybash.mkdir_p(myproxy_config_dir)
    with pybash.pushd(myproxy_config_dir):
        callout_app_file = "esg_attribute_callout_app"
        print "Downloading configuration file: {}".format(callout_app_file)
        myproxy_dist_url_base = "{}/globus/myproxy".format(esg_property_manager.get_property("esg.root.url"))
        try:
            esg_functions.download_update(callout_app_file, myproxy_dist_url_base+"/{}".format(callout_app_file))
        except HTTPError:
            raise
        os.chmod(callout_app_file, 0751)

def edit_etc_myproxyd():
    with open("/etc/myproxy.d/myproxy-esgf", "w") as myproxy_esgf_file:
        myproxy_esgf_file.write('''export MYPROXY_OPTIONS=\"-c {}/myproxy/myproxy-server.config -s /var/lib/globus-connect-server/myproxy-ca/store\"'''.format(config["esg_config_dir"]))

def write_db_name_env():
    EnvWriter.export("ESGF_DB_NAME", esg_property_manager.get_property("db.database"))
