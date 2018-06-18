import os
import logging
import shutil
import ConfigParser
import OpenSSL
import stat
import glob
import psutil
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from esgf_utilities import esg_cert_manager
from esgf_utilities.esg_exceptions import SubprocessError
from base import esg_tomcat_manager
from base import esg_postgres

logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

#--------------------------------------------------------------
# GRID FTP
#--------------------------------------------------------------
#http://www.ci.uchicago.edu/wiki/bin/view/ESGProject/ESGUsageParser
def setup_gridftp_metrics_logging():
    usage_parser_version = "0.1.1"
    print "Checking for esg_usage_parser >= {} ".format(usage_parser_version)
    # TODO: check version at os.path.join(config["esg_tools_dir"], "esg_usage_parser")

    print "GridFTP Usage - Configuration..."
    print "*******************************"
    print "Setting up GridFTP Usage..."
    print "*******************************"

    directory_list = [config["esg_backup_dir"], config["esg_tools_dir"], config["esg_log_dir"], config["esg_config_dir"]]
    for directory in directory_list:
        esg_bash2py.mkdir_p(directory)

    esg_functions.stream_subprocess_output("yum -y install perl-DBD-Pg")

    globus_workdir= os.path.join(config["workdir"],"extra", "globus")
    esg_bash2py.mkdir_p(globus_workdir)

    esg_dist_url = esg_property_manager.get_property("esg.dist.url")
    esg_usage_parser_dist_file = "esg_usage_parser-{}.tar.bz2".format(usage_parser_version)
    esg_usage_parser_dist_url= "{}/globus/gridftp/esg_usage_parser-{}.tar.bz2".format(esg_dist_url, usage_parser_version)
    esg_usage_parser_dist_dir = os.path.join(globus_workdir, "esg_usage_parser-{}".format(usage_parser_version))
    esg_bash2py.mkdir_p(esg_usage_parser_dist_dir)

    current_mode = os.stat(globus_workdir)
    # chmod a+rw $globus_workdir
    os.chmod(globus_workdir, current_mode.st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    with esg_bash2py.pushd(esg_usage_parser_dist_dir):
        print "Downloading Globus GridFTP Usage Parser from {}".format(esg_usage_parser_dist_url)
        esg_functions.download_update(esg_usage_parser_dist_file, esg_usage_parser_dist_url)

        esg_functions.extract_tarball(esg_usage_parser_dist_file)

        shutil.copyfile("esg_usage_parser", os.path.join(config["esg_tools_dir"], "esg_usage_parser"))
        os.chmod(os.path.join(config["esg_tools_dir"], "esg_usage_parser"), 0755)


def config_gridftp_metrics_logging():
    '''generate config file for gridftp server'''
    print 'Configuring gridftp metrics collection ...'
    gridftp_server_usage_config= "{}/gridftp/esg-server-usage-gridftp.conf".format(config["esg_config_dir"])
    gridftp_server_usage_config_dir = os.path.join(config["esg_config_dir"], "gridftp", "esg-server-usage-gridftp")
    esg_bash2py.mkdir_p(gridftp_server_usage_config_dir)

    with open(gridftp_server_usage_config, "w") as config_file:
        config_file.write("DBNAME={}\n".format(esg_property_manager.get_property("db.database")))
        config_file.write("DBHOST={}\n".format(esg_property_manager.get_property("db.host")))
        config_file.write("DBPORT={}\n".format(esg_property_manager.get_property("db.port")))
        config_file.write("DBUSER={}\n".format(esg_property_manager.get_property("db.user")))
        config_file.write("DBPASS={}\n".format(esg_functions.get_postgres_password()))
        gridftp_server_usage_log = "{}/esg-server-usage-gridftp.log".format(config["esg_log_dir"])
        config_file.write("USAGEFILE={}\n".format(gridftp_server_usage_log))
        config_file.write("TMPFILE={}\n".format(os.path.join(config["esg_log_dir"], "__up_tmpfile")))
        config_file.write("DEBUG=0\n")
        config_file.write("NODBWRITE=0\n")

    print 'Setting up a cron job, /etc/cron.d/esg_usage_parser ...'
    with open("/etc/cron.d/esg_usage_parser", "w") as cron_file:
        cron_file.write("5 0,12 * * * root ESG_USAGE_PARSER_CONF={gridftp_server_usage_config} {esg_tools_dir}/esg_usage_parser".format(gridftp_server_usage_config=gridftp_server_usage_config, esg_tools_dir=config["esg_tools_dir"]))

def setup_gridftp_jail(globus_sys_acct="globus"):

    print "*******************************"
    print "Setting up GridFTP... chroot jail"
    print "*******************************"

    gridftp_chroot_jail = "{}/gridftp_root".format(config["esg_root_dir"])
    if not os.path.exists(gridftp_chroot_jail):
        print "{} does not exist, making it...".format(gridftp_chroot_jail)
        esg_bash2py.mkdir_p(gridftp_chroot_jail)

        print "Creating chroot jail @ {}".format(gridftp_chroot_jail)
        esg_functions.stream_subprocess_output("globus-gridftp-server-setup-chroot -r {}".format(gridftp_chroot_jail))

        globus_jail_path = os.path.join(gridftp_chroot_jail, "etc", "grid-security", "sharing", globus_sys_acct)
        esg_bash2py.mkdir_p(globus_jail_path)
        globus_id = esg_functions.get_user_id("globus")
        globus_group = esg_functions.get_group_id("globus")
        esg_functions.change_ownership_recursive(globus_jail_path, globus_id, globus_group)
        esg_functions.change_permissions_recursive(globus_jail_path, 0700)

        if not os.path.exists("/esg/config/esgcet/esg.ini"):
            print "Cannot find ESGINI=[{}] file that describes data dir location".format("/esg/config/esgcet/esg.ini")
            return

        print "Reading ESGINI=[{}] for thredds_dataset_roots to mount....".format("/esg/config/esgcet/esg.ini")

        parser = ConfigParser.SafeConfigParser(allow_no_value=True)
        parser.read("/esg/config/esgcet/esg.ini")

        try:
            dataset_list = parser.get("DEFAULT", "thredds_dataset_roots").strip().split("\n")
        except ConfigParser.NoSectionError:
            logger.debug("could not find property %s", "thredds_dataset_roots")
            raise
        except ConfigParser.NoOptionError:
            logger.debug("could not find property %s", "thredds_dataset_roots")
            raise

        for dataset in dataset_list:
            mount_name, mount_dir = dataset.split("|")
            print "mounting [{mount_dir}] into chroot jail [{gridftp_chroot_jail}/] as [{mount_name}]".format(mount_dir=mount_dir, mount_name=mount_name, gridftp_chroot_jail=gridftp_chroot_jail)
            real_mount_dir = esg_functions.readlinkf(mount_dir)
            gridftp_mount_dir = os.path.join(gridftp_chroot_jail, mount_name)
            esg_bash2py.mkdir_p(gridftp_mount_dir)
            esg_functions.stream_subprocess_output("mount --bind {} {}".format(real_mount_dir, gridftp_mount_dir))

def post_gridftp_jail_setup():
    '''Write our trimmed version of /etc/password in the chroot location'''
    gridftp_chroot_jail = "{}/gridftp_root".format(config["esg_root_dir"])
    if not os.path.exists(gridftp_chroot_jail):
        logger.error("%s does not exist. Exiting.", gridftp_chroot_jail)
        return

    # Add a test data file if already not added
    test_data_file = os.path.join(gridftp_chroot_jail, "esg_dataroot", "test", "sftlf.nc")
    if not os.path.isfile(test_data_file):
        esg_bash2py.mkdir_p(os.path.join(gridftp_chroot_jail, "esg_dataroot", "test"))
        with open(test_data_file, "w") as test_file:
            test_file.write("test")

    print "writing sanitized passwd file to [{}/etc/passwd]".format(gridftp_chroot_jail)
    esg_bash2py.mkdir_p(os.path.join(gridftp_chroot_jail, "etc"))
    sanitized_passwd = os.path.join(gridftp_chroot_jail, "etc", "passwd")
    if not os.path.exists(sanitized_passwd):
        with open(sanitized_passwd, "w") as sanitized_passwd_file:
            sanitized_passwd_file.write("root:x:0:0:root:/root:/bin/bash\n")
            sanitized_passwd_file.write("bin:x:1:1:bin:/bin:/dev/null\n")
            sanitized_passwd_file.write("ftp:x:14:50:FTP User:/var/ftp:/dev/null\n")
            sanitized_passwd_file.write("globus:x:101:156:Globus System User:/home/globus:/bin/bash\n")

    #Write our trimmed version of /etc/group in the chroot location
    print "writing sanitized group file to [{}/etc/group]".format(gridftp_chroot_jail)
    sanitized_group = os.path.join(gridftp_chroot_jail, "etc", "group")
    if not os.path.exists(sanitized_group):
        with open(sanitized_group, "w") as santized_group_file:
            santized_group_file.write("root:x:0:root\n")
            santized_group_file.write("bin:x:1:root,bin,daemon\n")
            santized_group_file.write("ftp:x:50:\n")
            santized_group_file.write("globus:x:156:\n")


def config_gridftp_server(globus_sys_acct, gridftp_chroot_jail="{}/gridftp_root".format(config["esg_root_dir"])):
    print "GridFTP - Configuration..."
    print "*******************************"
    print "Setting up GridFTP..."
    print "*******************************"

    gridftp_server_port = "2811"
    esg_property_manager.set_property("gridftp_server_port", gridftp_server_port)

    # generate ESG SAML Auth config file
    write_esgsaml_auth_conf()

    dnode_root_dn_wildcard = '^.*$'
    esg_functions.stream_subprocess_output("grid-mapfile-add-entry -dn {} -ln {}".format(dnode_root_dn_wildcard, globus_sys_acct))

    with open("/etc/gridftp.d/globus-esgf", "w") as globus_esgf_file:
        globus_esgf_file.write("chroot_path {}\n".format(gridftp_chroot_jail))
        globus_esgf_file.write("usage_stats_id 2811\n")
        globus_esgf_file.write("usage_stats_target localhost:0\!all\n")
        globus_esgf_file.write("acl customgsiauthzinterface\n")
        gridftp_server_usage_log = "{}/esg-server-usage-gridftp.log".format(config["esg_log_dir"])
        globus_esgf_file.write("GLOBUS_USAGE_DEBUG \"MESSAGES,{}\n".format(gridftp_server_usage_log))
        globus_esgf_file.write("GSI_AUTHZ_CONF '/etc/grid-security/authz_callouts_esgsaml.conf'\n")
        globus_esgf_file.write("GLOBUS_GSI_AUTHZ_DEBUG_FILE '/var/log/gridftp-debug.log'\n")

def write_esgsaml_auth_conf():
    '''By making this a separate function it may be called directly in the
    event that the gateway_service_root needs to be repointed. (another Estani gem :-))'''
    try:
        orp_security_authorization_service_endpoint = esg_property_manager.get_property("orp_security_authorization_service_endpoint")
    except ConfigParser.NoOptionError:
        print "orp_security_authorization_service_endpoint property not found"
        return
    with open("/etc/grid-security/esgsaml_auth.conf", "w") as esgsaml_conf_file:
        logger.info("---------esgsaml_auth.conf---------")
        logger.info("AUTHSERVICE=%s", orp_security_authorization_service_endpoint)
        logger.info("---------------------------------")
        esgsaml_conf_file.write("AUTHSERVICE={}".format(orp_security_authorization_service_endpoint))


def configure_esgf_publisher_for_gridftp():
    print " configuring publisher to use this GridFTP server... "
    publisher_config_path = os.path.join(config["publisher_home"], config["publisher_config"])
    if os.path.exists(publisher_config_path):
        shutil.copyfile(publisher_config_path, publisher_config_path+".bak")
        #replace gsiftp://host.sample.gov:2811/ with esgf_host and gridftp_server_port in esg.ini
        parser = ConfigParser.SafeConfigParser(allow_no_value=True)
        parser.read(publisher_config_path)
        thredds_file_services = parser.get("DEFAULT", "thredds_file_services")
        thredds_file_services = thredds_file_services.replace("host.sample.gov:2811", "{}".format(esg_functions.get_esgf_host()))


def start_gridftp_server(gridftp_chroot_jail="{}/gridftp_root".format(config["esg_root_dir"])):
    global_x509_cert_dir = "/etc/grid-security/certificates"
    print " GridFTP - Starting server... $*"
    write_esgsaml_auth_conf()
    setup_gridftp_jail()
    post_gridftp_jail_setup()

    print " syncing local certificates into chroot jail... "
    if os.path.exists(gridftp_chroot_jail) and gridftp_chroot_jail != "/" and os.path.exists(os.path.join(gridftp_chroot_jail, "etc", "grid-security", "certificates")):
        shutil.rmtree(os.path.join(gridftp_chroot_jail, "etc", "grid-security", "certificates"))
        esg_bash2py.mkdir_p(os.path.join(gridftp_chroot_jail, "etc", "grid-security"))
        shutil.copytree("/etc/grid-security/certificates", os.path.join(gridftp_chroot_jail, "etc", "grid-security", "certificates"))

    configure_esgf_publisher_for_gridftp()

    esg_functions.stream_subprocess_output("service globus-gridftp-server start")


def stop_gridftp_server():
    esg_functions.stream_subprocess_output("service globus-gridftp-server stop")

def gridftp_server_status():
    '''Checks the status of the gridftp server'''
    status = esg_functions.call_subprocess("service globus-gridftp-server status")
    print "Gridftp server status:", status["stdout"]
    if "running" in status["stdout"]:
        return (True, status)
    else:
        return False

def check_gridftp_process(port_number):
    gridftp_processes = [proc for proc in psutil.process_iter(attrs=['pid', 'name', 'username', 'port']) if "globus-gridftp-server" in proc.info["name"]]
    # print " gridftp-server process is running on port [${port}]..."


def setup_gcs_io(first_run=None):
    if first_run == "firstrun":
        cert_dir = "/etc/tempcerts"
    else:
        cert_dir = "/etc/esgfcerts"

    with esg_bash2py.pushd(cert_dir):
        if os.path.isfile("hostkey.pem"):
            shutil.copyfile("hostkey.pem", "/etc/grid-security/hostkey.pem")
            os.chmod("/etc/grid-security/hostkey.pem", 0600)
        if os.path.isfile("hostcert.pem"):
            shutil.copyfile("hostcert.pem", "/etc/grid-security/hostcert.pem")

    print '*******************************'
    print ' Registering the Data node with Globus Platform'
    print '*******************************'
    print 'The installer will create a Globus (www.globus.org) endpoint to allow users to'
    print 'download data through Globus. This uses the GridFTP server on the data node.'
    print 'The endpoint is named as <globus_username>#<host_name>, e.g. llnl#pcmdi9 where'
    print 'llnl is Globus username and pcmdi9 is endpoint name. To create a Globus account,'
    print 'go to www.globus.org/SignUp.'
    print 'This step can be skipped, but users will not be able to download datasets'
    print 'from the GridFTP server on the data node through the ESGF web interface.'

    try:
        register_gridftp_answer = esg_property_manager.get_property("register.gridftp")
    except ConfigParser.NoOptionError:
        register_gridftp_answer = raw_input(
        "Do you want to register the GridFTP server with Globus?: ") or "Y"

    if register_gridftp_answer.lower() in ["y", "yes"]:
        GLOBUS_SETUP = True
    else:
        GLOBUS_SETUP = False

    if GLOBUS_SETUP:
        try:
            globus_user= esg_property_manager.get_property("globus.user")
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
            myproxy_hostname = esg_property_manager.get_property("myproxy.endpoint")
        except ConfigParser.NoOptionError:
            myproxy_hostname = esg_functions.get_esgf_host().upper()

        parser = ConfigParser.SafeConfigParser(allow_no_value=True)
        parser.read("/etc/globus-connect-server-esgf.conf")

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
        gridftp_server_port_range = "50000,51000"
        parser.set('GridFTP', "IncomingPortRange", gridftp_server_port_range)
        gridftp_server_source_range = "50000,51000"
        parser.set('GridFTP', "OutgoingPortRange", gridftp_server_source_range)
        parser.set('GridFTP', "RestrictPaths", "R/,N/etc,N/tmp,N/dev")
        parser.set('GridFTP', "Sharing", "False")
        parser.set('GridFTP', "SharingRestrictPaths", "R/")
        gridftp_chroot_jail = "{}/gridftp_root".format(config["esg_root_dir"])
        parser.set('GridFTP', "SharingStateDir", os.path.join(gridftp_chroot_jail, "etc", "grid-security", "sharing", globus_user))

        with open("/etc/globus-connect-server-esgf.conf", "w") as config_file_object:
            parser.write(config_file_object)


        esg_functions.stream_subprocess_output("globus-connect-server-io-setup -c /etc/globus-connect-server-esgf.conf -v")

    # Create a substitution of GCS configuration files for GridFTP server
    esg_bash2py.mkdir_p("/etc/gridftp.d")

    with open("/etc/gridftp.d/globus-connect-esgf", "w") as globus_connect_file:
        globus_connect_file.write("port_range 50000,51000\n")
        globus_connect_file.write("GLOBUS_TCP_SOURCE_RANGE 50000,51000\n")
        globus_connect_file.write("restrict_paths R/,N/etc,N/tmp,N/dev\n")
        globus_connect_file.write("GRIDMAP '/etc/grid-security/grid-mapfile'\n")
        globus_connect_file.write("X509_USER_CERT '/etc/grid-security/hostcert.pem'\n")
        globus_connect_file.write("X509_USER_KEY '/etc/grid-security/hostkey.pem'\n")
        globus_connect_file.write("log_single /var/log/gridftp.log\n")
        globus_connect_file.write("log_level ALL\n")
        globus_connect_file.write("X509_CERT_DIR '/etc/grid-security/certificates'\n")
