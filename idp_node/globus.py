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
from esgf_utilities.esg_exceptions import SubprocessError
from base import esg_tomcat_manager
from base import esg_postgres


logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def setup_globus(installation_type):
    '''
    Globus Toolkit ->  MyProxy (client) & GridFTP (server)
    Takes arg <selection bit vector>
    The rest of the args are the following...
    for data-node configuration (GridFTP stuff): ["bdm"|"end-user"] see esg-globus script
    for idp configuration (MyProxy stuff): [gen-self-cert] <dir> | <regen-simpleca> [fetch-certs|gen-self-cert|keep-certs] | ["install"|"update"]'''
    logger.debug("setup_globus for installation type: %s", installation_type)

    globus_location = "/usr/local/globus"
    with esg_bash2py.pushd(config["scripts_dir"]):
        globus_file = "esg-globus"
        globus_file_url = "https://aims1.llnl.gov/esgf/dist/devel/externals/bootstrap/esg-globus"
        esg_functions.download_update(globus_file, globus_file_url)
        os.chmod(globus_file, 0755)

    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        directive = "notype"
        if installation_type == "DATA":
            logger.info("Globus Setup for Data-Node... (GridFTP server) ")
            directive = "datanode"
            setup_globus_services(directive)
            write_globus_env(globus_location)
            esg_bash2py.touch(os.path.join(globus_location,"esg_esg-node_installed"))

        if installation_type == "IDP":
            logger.info("Globus Setup for Index-Node... (MyProxy server)")
            directive = "gateway"
            setup_mode = "install"
            setup_globus_services(directive)
            write_globus_env(globus_location)
            esg_bash2py.touch(os.path.join(globus_location,"esg_esg-node_installed"))

def write_globus_env(globus_location):
    esg_property_manager.set_property("GLOBUS_LOCATION", "export GLOBUS_LOCATION={}".format(globus_location), config_file=config["envfile"], section_name="esgf.env")


def start_globus(installation_type):
    '''Starts the globus services by delegating out to esg-globus script
    arg1 selection bit vector ($sel)
    args* (in the context of "data" node ->  ["bdm"|"end-user"])'''
    if installation_type == "DATA":
        directive = "datanode"
        start_globus_services(directive)
    if installation_type == "IDP":
        directive = "gateway"
        start_globus_services(directive)

def stop_globus(installation_type):
    '''Stops the globus services by delegating out to esg-globus script
    arg1 selection bit vector ($sel)'''

    if installation_type == "DATA":
        directive = "datanode"
        stop_globus_services(directive)
    if installation_type == "IDP":
        stop_globus_services(directive)

#--------------------------------------------------------------
# PROCEDURE
#--------------------------------------------------------------
def setup_globus_services(config_type):
    '''arg1 - config_type ("datanode" | "gateway"  ["install"|"update"])'''

    print "*******************************"
    print "Setting up Globus... (config type: {})".format(config_type)
    print "*******************************"
    globus_version = "6.0"
    globus_sys_acct = "globus"

    if os.access("/usr/bin/globus-version", os.X_OK):
        print "Detected an existing Globus installation"
        print "Checking for Globus {}".format(globus_version)
        installed_globus_version = esg_functions.call_subprocess("/usr/bin/globus-version")['stdout']
        if esg_version_manager.compare_versions(installed_globus_version, globus_version+".0"):
            print "Globus version appears sufficiently current"

    try:
        setup_postgres_answer = esg_property_manager.get_property("install.globus")
        if not setup_postgres_answer:
            raise ConfigParser.NoOptionError
    except ConfigParser.NoOptionError:
        setup_postgres_answer = raw_input(
            "Do you want to continue with the Globus installation and setup? [y/N]: ") or "N"

    if setup_postgres_answer.lower().strip() in ["no", 'n']:
        logger.info("Skipping Globus installation. Using existing Globus version")
        return

    logger.debug("setup_globus_services for %s", config_type)

    globus_location = "/usr/local/globus"
    esg_bash2py.mkdir_p(os.path.join(globus_location, "bin"))

    if config_type == "datanode":
        print "*******************************"
        print "Setting up ESGF Globus GridFTP Service(s)"
        print "*******************************"

        create_globus_account(globus_sys_acct)
        _install_globus(config_type)
        setup_gcs_io("firstrun")
        setup_gridftp_metrics_logging()

        config_gridftp_server(globus_sys_acct)
        config_gridftp_metrics_logging()

        if os.path.exists("/usr/sbin/globus-gridftp-server"):
            esg_property_manager.set_property("gridftp_app_home", "/usr/sbin/globus-gridftp-server")
    elif config_type == "gateway":
        print "*******************************"
        print "Setting up The ESGF Globus MyProxy Services"
        print "*******************************"

        _install_globus(config_type)
        setup_gcs_id("firstrun")
        config_myproxy_server(globus_location)
    else:
        print "You must provide a configuration type arg [datanode | gateway]"
        return


def start_globus_services(config_type):
    print "Starting Globus services for {}".format(config_type)

    if config_type == "datanode":
        start_gridftp_server()
        esg_property_manager.set_property("gridftp_endpoint", "gsiftp://{}".format(esg_functions.get_esgf_host()))
    elif config_type == "gateway":
        start_myproxy_server()
    else:
        print "You must provide a configuration type arg [datanode | gateway]"
        return

def stop_globus_services(config_type):
    print "stop_globus_services for {}".format(config_type)

    if config_type == "datanode":
        stop_gridftp_server()
    elif config_type == "gateway":
        stop_myproxy_server()
    else:
        print "You must provide a configuration type arg [datanode | gateway]"
        return

def check_for_existing_globus_rpm_packages():
    rpm_packages = esg_functions.call_subprocess("rpm -qa")["stdout"].split("\n")
    globus_packages = [package for package in rpm_packages if "globus" in package]
    return globus_packages

#--------------------------------------------------------------
# GLOBUS INSTALL (subset)
#--------------------------------------------------------------
# All methods below this point should be considered "private" functions

def _install_globus(config_type):
    if config_type == "datanode":
        globus_type = "globus-connect-server-io"
    elif config_type == "gateway":
        globus_type = "globus-connect-server-id"
    else:
        print "You must provide a configuration type arg [datanode | gateway]"
        return

    globus_workdir= os.path.join(config["workdir"],"extra", "globus")
    esg_bash2py.mkdir_p(globus_workdir)
    current_mode = os.stat(globus_workdir)
    # chmod a+rw $globus_workdir
    os.chmod(globus_workdir, current_mode.st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    with esg_bash2py.pushd(globus_workdir):
        # Setup Globus RPM repo
        if not check_for_existing_globus_rpm_packages():
            globus_connect_server_file = "globus-connect-server-repo-latest.noarch.rpm"
            globus_connect_server_url = "http://toolkit.globus.org/ftppub/globus-connect-server/globus-connect-server-repo-latest.noarch.rpm"
            esg_functions.download_update(globus_connect_server_file, globus_connect_server_url)
            esg_functions.stream_subprocess_output("rpm --import http://www.globus.org/ftppub/globus-connect-server/RPM-GPG-KEY-Globus")
            esg_functions.stream_subprocess_output("rpm -i globus-connect-server-repo-latest.noarch.rpm")

        # Install Globus and ESGF RPMs
        esg_functions.stream_subprocess_output("yum -y install {}".format(globus_type))
        esg_functions.stream_subprocess_output("yum -y update {}".format(globus_type))

        if globus_type == "globus-connect-server-io":
            esg_functions.stream_subprocess_output("yum -y install globus-authz-esgsaml-callout globus-gaa globus-adq customgsiauthzinterface")
            esg_functions.stream_subprocess_output("yum -y update globus-authz-esgsaml-callout globus-gaa globus-adq customgsiauthzinterface")
        else:
            esg_functions.stream_subprocess_output("yum -y install mhash pam-pgsql")
            esg_functions.stream_subprocess_output("yum -y update mhash pam-pgsql")


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

    esg_usage_parser_dist_file = "esg_usage_parser-{}.tar.bz2".format(usage_parser_version)
    esg_usage_parser_dist_url= "https://aims1.llnl.gov/esgf/dist//globus/gridftp/esg_usage_parser-{}.tar.bz2".format(usage_parser_version)
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
    gridftp_server_usage_config= "{esg_config_dir}/gridftp/esg-server-usage-gridftp.conf".format(config["esg_config_dir"])
    gridftp_server_usage_config_dir = os.path.join(config["esg_config_dir"], "gridftp", "esg-server-usage-gridftp")
    esg_bash2py.mkdir_p(gridftp_server_usage_config_dir)

    with open(gridftp_server_usage_config, "w") as config_file:
        config_file.write("DBNAME={}\n".format(esg_property_manager.get_property("db.database")))
        config_file.write("DBHOST={}\n".format(esg_property_manager.get_property("db.host")))
        config_file.write("DBPORT={}\n".format(esg_property_manager.get_property("db.port")))
        config_file.write("DBUSER={}\n".format(esg_property_manager.get_property("db.user")))
        config_file.write("DBPASS={}\n".format(esg_functions.get_postgres_password()))
        gridftp_server_usage_log = "{esg_log_dir}/esg-server-usage-gridftp.log".format(config["esg_log_dir"])
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

    gridftp_chroot_jail = "{esg_root_dir}/gridftp_root".format(config["esg_root_dir"])
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

        print "Reading ESGINI=[${}] for thredds_dataset_roots to mount....".format("/esg/config/esgcet/esg.ini")

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
    gridftp_chroot_jail = "{esg_root_dir}/gridftp_root".format(config["esg_root_dir"])
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


def setup_gcs_io(first_run=None):
    if first_run == "firstrun":
        cert_dir = "/etc/tempcerts"
    else:
        cert_dir = "/etc/esgfcerts"

    with esg_bash2py.pushd(cert_dir):
        if os.path.isfile("hostkey.pem"):
            shutil.copyfile("hostkey.pem", "/etc/grid-security/hostkey.pem")
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

    if esg_property_manager.get_property("register.gridftp"):
        register_gridftp_answer = esg_property_manager.get_property("register.gridftp")
    else:
        register_gridftp_answer = raw_input(
        "Do you want to register the GridFTP server with Globus?: ") or "Y"

    if register_gridftp_answer.lower() in ["y", "yes"]:
        GLOBUS_SETUP = True
    else:
        GLOBUS_SETUP = False

    if GLOBUS_SETUP:
        if esg_property_manager.get_property("globus.user"):
            globus_user= esg_property_manager.get_property("globus.user")
        else:
            while True:
                globus_user = raw_input("Please provide a Globus username: ")
                if not globus_user:
                    print "Globus username cannot be blank."
                else:
                    break

        if esg_property_manager.get_property("globus.password"):
            globus_password = esg_property_manager.get_property("globus.password")
        else:
            while True:
                globus_password = raw_input("Please enter your Globus password: ")
                if not globus_password:
                    print "The Globus password can not be blank"
                    continue
                else:
                    esg_property_manager.set_property("globus.password", globus_password)
                    break

        if esg_property_manager.get_property("myproxy.endpoint"):
            myproxy_hostname = esg_property_manager.get_property("myproxy.endpoint")
        else:
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

        parser.set('Security', "FetchCredentialFromRelay", "True")
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
        gridftp_chroot_jail = "{esg_root_dir}/gridftp_root".format(config["esg_root_dir"])
        parser.set('GridFTP', "SharingStateDir", os.path.join(gridftp_chroot_jail, "etc", "grid-security", "sharing", globus_user))

        try:
            parser.add_section("MyProxy")
        except ConfigParser.DuplicateSectionError:
            logger.debug("section already exists")

        parser.set('MyProxy', "Server", myproxy_hostname)

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
    orp_security_authorization_service_endpoint = esg_property_manager.get_property("orp_security_authorization_service_endpoint")
    with open("/etc/grid-security/esgsaml_auth.conf", "w") as esgsaml_conf_file:
        logger.info("---------esgsaml_auth.conf---------")
        logger.info("AUTHSERVICE=%s", orp_security_authorization_service_endpoint)
        logger.info("---------------------------------")
        esgsaml_conf_file.write("AUTHSERVICE={}".format(orp_security_authorization_service_endpoint))


def configure_esgf_publisher_for_gridftp():
    print " configuring publisher to use this GridFTP server... "
    publisher_path = os.path.join(config["publisher_home"], config["publisher_config"])
    if os.path.exists(publisher_path):
        shutil.copyfile(publisher_path, publisher_path+".bak")
        esg_functions.stream_subprocess_output('''sed -i 's#\(gsiftp://\)\([^:]*\):\([^/].*\)/#\1'${esgf_gridftp_host:-${esgf_host}}':'${gridftp_server_port}'/#' ${publisher_home}/${publisher_config}''')


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

def check_gridftp_process(port_number):
    gridftp_processes = [proc for proc in psutil.process_iter(attrs=['pid', 'name', 'username', 'port']) if "globus-gridftp-server" in proc.info["name"]]
    # print " gridftp-server process is running on port [${port}]..."


#--------------------
# Register with Globus Web Service and get a host certificate
#--------------------
def setup_gcs_id(first_run=None):
    if first_run == "firstrun":
        cert_dir = "/etc/tempcerts"
    else:
        cert_dir = "/etc/esgfcerts"

    logger.debug("cert_dir: %s", cert_dir)

    with esg_bash2py.pushd(cert_dir):
        myproxyca_dir = "/var/lib/globus-connect-server/myproxy-ca"

        esg_bash2py.mkdir_p(os.path.join(myproxyca_dir, "newcerts"))
        os.chmod(myproxyca_dir, 0700)
        esg_bash2py.mkdir_p(os.path.join(myproxyca_dir, "private"))
        os.chmod(os.path.join(myproxyca_dir, "private"), 0700)

        shutil.copyfile("cacert.pem", os.path.join(myproxyca_dir, "cacert.pem"))
        shutil.copyfile("cakey.pem", os.path.join(myproxyca_dir, "private", "cakey.pem"))
        shutil.copyfile("signing-policy", os.path.join(myproxyca_dir, "signing-policy"))

        shutil.copyfile("hostcert.pem", "/etc/grid-security/hostcert.pem")
        shutil.copyfile("hostkey.pem", "/etc/grid-security/hostkey.pem")

        try:
            cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open("cacert.pem").read())
        except OpenSSL.crypto.Error:
            logger.exception("Certificate is not correct.")

        cert_hash = str(cert_obj.subject_name_hash())
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


    if esg_property_manager.get_property("register.myproxy"):
        register_myproxy_answer = esg_property_manager.get_property("register.myproxy")
    else:
        register_myproxy_answer = raw_input(
        "Do you want to register the MyProxy server with Globus?: ") or "Y"

    if register_myproxy_answer.lower() in ["y", "yes"]:
        GLOBUS_SETUP = True
    else:
        GLOBUS_SETUP = False

    if GLOBUS_SETUP:
        if esg_property_manager.get_property("globus.user"):
            globus_user = esg_property_manager.get_property("globus.user")
        else:
            while True:
                globus_user = raw_input("Please provide a Globus username: ")
                if not globus_user:
                    print "Globus username cannot be blank."
                else:
                    break

        if esg_property_manager.get_property("globus.password"):
            globus_password = esg_property_manager.get_property("globus.password")
        else:
            while True:
                globus_password = raw_input("Please enter your Globus password: ")
                if not globus_password:
                    print "The Globus password can not be blank"
                    continue
                else:
                    esg_property_manager.set_property("globus.password", globus_password)
                    break

        if esg_property_manager.get_property("myproxy_endpoint"):
            myproxy_hostname = esg_property_manager.get_property("myproxy_endpoint")
        else:
            myproxy_hostname = esg_functions.get_esgf_host().upper()

        myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
        esg_bash2py.mkdir_p(myproxy_config_dir)
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

        parser.set('Security', "FetchCredentialFromRelay", "True")
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
    esg_bash2py.mkdir_p("/etc/myproxy.d")
    with open("/etc/myproxy.d/globus-connect-esgf", "w") as globus_connect_conf_file:
        globus_connect_conf_file.write("export MYPROXY_USER=root")
        globus_connect_conf_file.write('export X509_CERT_DIR="/etc/grid-security/certificates"')
        globus_connect_conf_file.write('export X509_USER_CERT="/etc/grid-security/hostcert.pem"')
        globus_connect_conf_file.write('export X509_USER_KEY="/etc/grid-security/hostkey.pem"')
        globus_connect_conf_file.write('export X509_USER_PROXY=""')
        globus_connect_conf_file.write('export MYPROXY_OPTIONS="\${MYPROXY_OPTIONS:+\$MYPROXY_OPTIONS }-c /var/lib/globus-connect-server/myproxy-server.conf -s /var/lib/globus-connect-server/myproxy-ca/store"')

    with open("/esg/config/myproxy/myproxy-server.config", "w") as myproxy_server_file:
        myproxy_server_file.write('authorized_retrievers      "*"')
        myproxy_server_file.write('default_retrievers         "*"')
        myproxy_server_file.write('authorized_renewers        "*"')
        myproxy_server_file.write('authorized_key_retrievers  "*"')
        myproxy_server_file.write('trusted_retrievers         "*"')
        myproxy_server_file.write('default_trusted_retrievers "none"')
        myproxy_server_file.write('max_cert_lifetime          "72"')
        myproxy_server_file.write('disable_usage_stats        "true"')
        myproxy_server_file.write('cert_dir                   "/etc/grid-security/certificates"')

        myproxy_server_file.write('pam_id "myproxy"')
        myproxy_server_file.write('pam "required"')

        myproxy_server_file.write('certificate_issuer_cert "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"')
        myproxy_server_file.write('certificate_issuer_key "/var/lib/globus-connect-server/myproxy-ca/private/cakey.pem"')
        myproxy_server_file.write('certificate_issuer_key_passphrase "globus"')
        myproxy_server_file.write('certificate_serialfile "/var/lib/globus-connect-server/myproxy-ca/serial"')
        myproxy_server_file.write('certificate_out_dir "/var/lib/globus-connect-server/myproxy-ca/newcerts"')
        myproxy_server_file.write('certificate_issuer_subca_certfile "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"')
        myproxy_server_file.write('certificate_mapapp /esg/config/myproxy/myproxy-certificate-mapapp')
        myproxy_server_file.write('certificate_extapp /esg/config/myproxy/esg_attribute_callout_app')



def config_myproxy_server(globus_location, install_mode="install"):
    if install_mode not in ["install", "update"]:
        print "The install mode must be either 'install' or 'update'"
        esg_functions.exit_with_error("ERROR: You have entered an invalid argument: [{}]".format(install_mode))

    print "MyProxy - Configuration... [{}]".format(install_mode)


    #--------------------
    # Compile Java Code Used by "callout" scripts in ${globus_location}/bin
    #--------------------
    if not os.path.exists(os.path.join(globus_location, "bin", "ESGOpenIDRetriever.class")) or os.path.exists(os.path.join(globus_location, "bin", "ESGGroupRetriever")):
        with esg_bash2py.pushd("{}/bin".format(globus_location)):
            myproxy_dist_url_base = "{}/globus/myproxy".format(config["esg_dist_url_root"])
            esg_functions.download_update("ESGOpenIDRetriever.java", "{}/ESGOpenIDRetriever.java".format(myproxy_dist_url_base))
            esg_functions.download_update("ESGGroupRetriever.java", "{}/ESGGroupRetriever.java".format(myproxy_dist_url_base))

            postgress_jar = "postgresql-8.4-703.jdbc3.jar"
            esg_functions.download_update(postgress_jar, "{}/{}".format(myproxy_dist_url_base, postgress_jar))

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

def write_db_name_env():
    esgf_db_name = esg_property_manager.get_property("db.database")
    esg_property_manager.set_property("ESGF_DB_NAME", "export ESGF_DB_NAME={}".format(esgf_db_name), config_file=config["envfile"], section_name="esgf.env")

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

def check_myproxy_process():
    myproxy_processes = [proc for proc in psutil.process_iter(attrs=['pid', 'name', 'username', 'port']) if "myproxy-server" in proc.info["name"]]
    if myproxy_processes:
        print "myproxy-server process is running..."
        print myproxy_processes
        return myproxy_processes


############################################
# Configuration File Editing Functions
############################################

def edit_myproxy_server_config():
    myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
    esg_bash2py.mkdir_p(myproxy_config_dir)
    with esg_bash2py.pushd(myproxy_config_dir):
        myproxy_config_file = "myproxy-server.config"
        "Creating/Modifying myproxy server configuration file: {}".format(myproxy_config_file)
        if os.path.isfile(myproxy_config_file):
            esg_functions.create_backup_file(myproxy_config_file)
        with open("/esg/config/myproxy/myproxy-server.config", "w") as myproxy_server_file:
            myproxy_server_file.write('authorized_retrievers      "*"')
            myproxy_server_file.write('default_retrievers         "*"')
            myproxy_server_file.write('authorized_renewers        "*"')
            myproxy_server_file.write('authorized_key_retrievers  "*"')
            myproxy_server_file.write('trusted_retrievers         "*"')
            myproxy_server_file.write('default_trusted_retrievers "none"')
            myproxy_server_file.write('max_cert_lifetime          "72"')
            myproxy_server_file.write('disable_usage_stats        "true"')
            myproxy_server_file.write('cert_dir                   "/etc/grid-security/certificates"')

            myproxy_server_file.write('pam_id "myproxy"')
            myproxy_server_file.write('pam "required"')

            myproxy_server_file.write('certificate_issuer_cert "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"')
            myproxy_server_file.write('certificate_issuer_key "/var/lib/globus-connect-server/myproxy-ca/private/cakey.pem"')
            myproxy_server_file.write('certificate_issuer_key_passphrase "globus"')
            myproxy_server_file.write('certificate_serialfile "/var/lib/globus-connect-server/myproxy-ca/serial"')
            myproxy_server_file.write('certificate_out_dir "/var/lib/globus-connect-server/myproxy-ca/newcerts"')
            myproxy_server_file.write('certificate_issuer_subca_certfile "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"')
            myproxy_server_file.write('certificate_mapapp /esg/config/myproxy/myproxy-certificate-mapapp')
            myproxy_server_file.write('certificate_extapp /esg/config/myproxy/esg_attribute_callout_app')

        os.chmod(myproxy_config_file, 0600)

def edit_pam_pgsql_conf():
    with esg_bash2py.pushd("/etc"):
        pgsql_conf_file = "pam_pgsql.conf"
        "Download and Modifying pam pgsql configuration file: {}".format(pgsql_conf_file)
        myproxy_dist_url_base = "{}/globus/myproxy".format(config["esg_dist_url"])
        esg_functions.download_update(pgsql_conf_file, myproxy_dist_url_base+"/etc_{}".format(pgsql_conf_file))

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

def edit_etc_myproxyd():
    with open("/etc/myproxy.d/myproxy-esgf", "w") as myproxy_esgf_file:
        myproxy_esgf_file.write('''"export MYPROXY_OPTIONS=\"-c {}/myproxy/myproxy-server.config -s /var/lib/globus-connect-server/myproxy-ca/store\""'''.format(config["esg_config_dir"]))


def fetch_myproxy_certificate_mapapp():
    myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
    esg_bash2py.mkdir_p(myproxy_config_dir)
    with esg_bash2py.pushd(myproxy_config_dir):
        mapapp_file = "myproxy-certificate-mapapp"
        print "Downloading configuration file: {}".format(mapapp_file)
        myproxy_dist_url_base = "{}/globus/myproxy".format(config["esg_dist_url"])
        esg_functions.download_update(mapapp_file, myproxy_dist_url_base+"/{}".format(mapapp_file))

        os.chmod(mapapp_file, 0751)
        esg_functions.replace_string_in_file(mapapp_file, "/root/.globus/simpleCA/cacert.pem", "var/lib/globus-connect-server/myproxy-ca/cacert.pem")

def fetch_etc_pam_d_myproxy():
    with esg_bash2py.pushd("/etc/pam.d"):
        myproxy_file = "myproxy"
        "Fetching pam's myproxy resource file: {}".format(myproxy_file)
        myproxy_dist_url_base = "{}/globus/myproxy".format(config["esg_dist_url"])
        esg_functions.download_update(myproxy_file, myproxy_dist_url_base+"/etc_pam.d_{}".format(myproxy_file))

def fetch_esg_attribute_callout_app():
    myproxy_config_dir = os.path.join(config["esg_config_dir"], "myproxy")
    esg_bash2py.mkdir_p(myproxy_config_dir)
    with esg_bash2py.pushd(myproxy_config_dir):
        callout_app_file = "esg_attribute_callout_app"
        print "Downloading configuration file: {}".format(callout_app_file)
        myproxy_dist_url_base = "{}/globus/myproxy".format(config["esg_dist_url"])
        esg_functions.download_update(callout_app_file, myproxy_dist_url_base+"/{}".format(callout_app_file))
        os.chmod(callout_app_file, 0751)


############################################
# Utility Functions
############################################

def create_globus_account(globus_sys_acct):
    '''Create the system account for globus to run as.'''

    try:
        esg_functions.stream_subprocess_output("groupadd -r {}".format(globus_sys_acct))
    except SubprocessError, error:
        logger.debug(error[0]["returncode"])
        if error[0]["returncode"] == 9:
            pass

    globus_sys_acct_passwd = esg_functions.get_security_admin_password()
    try:
        esg_functions.stream_subprocess_output('''/usr/sbin/useradd -r -c"Globus System User" -g {globus_sys_acct_group} -p {globus_sys_acct_passwd} -s /bin/bash {globus_sys_acct}'''.format(globus_sys_acct_group="globus", globus_sys_acct_passwd=globus_sys_acct_passwd, globus_sys_acct=globus_sys_acct))
    except SubprocessError, error:
        logger.debug(error[0]["returncode"])
        if error[0]["returncode"] == 9:
            pass


############################################
# Globus Online Setup
############################################
# setup_globus_online() {
#     printf "
#     Setting up Globus Online / ESGF integration...
#
#     NOTE: You MUST have created a Globus Online account for
#     this node: In order for oAuth to work correctly such that
#     the user does not have to link their ESG credential with their
#     Globus Online account, this node must have its own account.
#
#         https://www.globusonline.org/SignUp
#
# "
#     local local=y
#     read -e -p "Continue? [Y/n] " input
#     [ "n" = "$(echo "${input}" | tr [A-Z] [a-z])" ] && return 1
#     unset input
#
#     (
#         local config_file=${esg_config_dir}/globusonline.properties
#         load_properties ${config_file}
#
#         local input
#         while [ 1 ]; do
#             read -e -p "Please enter your Globus Online ID [${GOesgfPortalID}]: " input
#             [ -n "${input}" ] && GOesgfPortalID=${input} && break
#             [ -n "${GOesgfPortalID}" ] && break
#         done
#         unset input
#         write_as_property GOesgfPortalID
#
#         while [ 1 ]; do
#             read -e -p "Please enter your Globus Online Password [$([ -n "${GOesgfPortalPassword}" ] && echo "*********")]: " input
#             [ -n "${input}" ] && GOesgfPortalPassword=${input} && break
#             [ -n "${GOesgfPortalPassword}" ] && break
#         done
#         unset input
#         write_as_property GOesgfPortalPassword
#
#         chmod 600 ${config_file}
#         chown ${tomcat_user:-tomcat}.${tomcat_group:-tomcat} ${config_file}
#
#         local mkproxy_dist_url="${esg_dist_url}/externals/bootstrap/mkproxy-10-15-2012.tar.gz"
#         local mkproxy_dist_file=${mkproxy_dist_url##*/}
#         pushd /tmp/
#         checked_get ${mkproxy_dist_file} ${mkproxy_dist_url} $((force_install))
#         (( $? > 1 )) && echo " ERROR: Could not download Globus Online install script" && popd >& /dev/null && checked_done 1
#         tar xvzf ${mkproxy_dist_file}
#         [ $? != 0 ] && echo " WARNING: Could not extract Globus Online install script (properly)" && popd >& /dev/null #&& checked_done 1
#         cd /tmp/mkproxy
#         [ $? != 0 ] && echo " ERROR: Could not Chang to mkproxy directory" && popd >& /dev/null && checked_done 1
#         make
#         [ $? != 0 ] && echo " ERROR: Could not build mkproxy program" && popd >& /dev/null && checked_done 1
#         cp -v /tmp/mkproxy/mkproxy /usr/local/bin
#         cd ../
#         [ -e "/tmp/${mkproxy_dist_file}" ] && rm -rf mkproxy /tmp/${mkproxy_dist_file}
#         popd >& /dev/null
#         (config_file=${esg_config_dir}/searchconfig.properties write_as_property enableGlobusOnline true && chmod 600 ${config_file})
#     )
#     echo "<<<<$?>>>>"
# }
