
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
        esg_functions.dowload_update(globus_file, globus_file_url)
        os.chmod(globus_file, 0755)

    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        directive = "notype"
        if installation_type == "DATA":
            logger.info("Globus Setup for Data-Node... (GridFTP server) ")
            directive = "datanode"
            setup_globus_services(directive)
            write_globus_env()
            esgbash2py.touch(os.path.join(globus_location,"esg_esg-node_installed"))

        if installation_type == "IDP":
            logger.info("Globus Setup for Index-Node... (MyProxy server)")
            directive = "gateway"
            setup_mode = "install"
            setup_globus_services(directive, setup_mode)
            write_globus_env()
            esgbash2py.touch(os.path.join(globus_location,"esg_esg-node_installed"))

def write_globus_env():
    # ((show_summary_latch++))
    # echo "export GLOBUS_LOCATION=$GLOBUS_LOCATION" >> ${envfile}
    # dedup ${envfile} && source ${envfile}
    # return 0
    pass


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



#Should have been "INHERITED" from calling esg-node or esg-gway scripts
install_prefix=${install_prefix:-"/usr/local"}
DEBUG=${DEBUG:-1}
force_install=${force_install:-0}
workdir=${workdir:-~/workbench/esg}
install_manifest=${install_manifest:-"${esg_root_dir}/esgf-install-manifest"}
globus_global_certs_dir=${globus_global_certs_dir:-/etc/grid-security/certificates}
esg_functions_file=${esg_functions_file:-${install_prefix}/bin/esg-functions}

#------------------------------------------------------------
# We want globus to fully behave as though it's home is /root
orig_user_home=${HOME}
HOME=/root
#------------------------------------------------------------

#--------------
# ID Setting
#--------------
# this should get exported from caller preferably
if [[ -z "$installer_uid" || -z "$installer_gid" ]]; then
    installer_user=${ESG_USER:-$(echo "$HOME" | sed 's#.*/\([^/]\+\)/\?$#\1#')}
    installer_uid=${ESG_USER_UID:-${SUDO_UID:-$(id -u $installer_user)}}
    installer_gid=${ESG_USER_GID:-${SUDO_GID:-$(id -g $installer_user)}}
    installer_home=${ESG_USER_HOME:-$(getent passwd ${installer_uid} | awk -F : '{print $6}')}

    #deprecate SUDO_?ID so we only use one variable for all this
    [[ $SUDO_UID ]] && ESG_USER_UID=${SUDO_UID} && unset SUDO_UID && echo "SUDO_UID is deprecated, use ESG_USER_UID instead"
    [[ $SUDO_GID ]] && ESG_USER_GID=${SUDO_GID} && unset SUDO_GID && echo "SUDO_GID is deprecated, use ESG_USER_GID instead"
fi

esg_root_dir=${esg_root_dir:-"/esg"}
esg_backup_dir=${esg_backup_dir:-"${esg_root_dir}/backups"}
esg_config_dir=${esg_config_dir:-"${esg_root_dir}/config"}
esg_log_dir=${esg_log_dir:-"${esg_root_dir}/log"}
esg_tools_dir=${esg_tools_dir:-"${esg_root_dir}/tools"}

esg_dist_url=${esg_dist_url_root}$( ((devel == 1)) && echo "/devel" || echo "")

compress_extensions=${compress_extensions:-".tar.gz|.tar.bz2|.tgz|.bz2"}
cdat_home=${cdat_home:-${install_prefix}/cdat}

#-----------
globus_version=${globus_version:-"6.0"}
usage_parser_version=${usage_parser_version:-"0.1.1"}

distro=$(perl -ple 's/^([^ ]*) .*$/$1/;' < /etc/redhat-release)
release=$(perl -ple 's/^.* (\d).\d .*$/$1/;' < /etc/redhat-release)

#-----------
globus_location=${GLOBUS_LOCATION:-${install_prefix}/globus}
# since script runs as root and simpleCA should be done as root, make it /root/.globus here
#NOTE-RedHat/CentOS specific...
globus_install_dir=$globus_location
globus_workdir=${workdir}/extra/globus
globus_sys_acct=${globus_sys_acct:-globus}
globus_sys_acct_group=${globus_sys_acct_group:-globus}
globus_sys_acct_passwd=${globus_sys_acct_passwd:-$(cat ${esgf_secret_file} 2> /dev/null)}
#-----------
gridftp_config=${gridftp_config:-""}
gridftp_dist_url_base=${esg_dist_url}/globus/gridftp
gridftp_chroot_jail=${esg_root_dir}/gridftp_root
#ports end-user configured:
gridftp_server_port=2811
gridftp_server_port_range=${gridftp_server_port_range:-50000,51000}
gridftp_server_source_range=${gridftp_server_source_range:-50000,51000}
gridftp_server_usage_log=${esg_log_dir}/esg-server-usage-gridftp.log
gridftp_server_usage_config=${esg_config_dir}/gridftp/esg-server-usage-gridftp.conf
esg_crontab=${esg_config_dir}/esg_crontab
#-----------
myproxy_config_args=${myproxy_config_args:-""}
myproxy_dist_url_base=${esg_dist_url}/globus/myproxy
myproxy_dist_url=http://downloads.sourceforge.net/project/cilogon/myproxy/myproxy-${myproxy_version}.tar.gz
myproxy_endpoint=${myproxy_endpoint}
myproxy_location=${globus_location}/bin/
#-----------
#esg_usage_parser_dist_url=http://www.mcs.anl.gov/~neillm/esg/esg_usage_parser-0.1.0.tar.gz
esg_usage_parser_dist_url=${esg_dist_url}/globus/gridftp/esg_usage_parser-${usage_parser_version}.tar.bz2
pam_pgsql_workdir=${workdir}/extra/pam_pgsql
pam_pgsql_install_dir=${install_prefix}/pam
postgress_jar=${postgress_jar:-postgresql-8.4-703.jdbc3.jar}

#-----------
#"PRIVATE" variables that are expected to be set and overridden by calling script!!
#-----------
openid_dirname=${openid_dirname:-"https://${esgf_host}/esgf-idp/openid/"}
esgf_db_name=${ESGF_DB_NAME:-${GATEWAY_DB_NAME:-esgcet}} #(originating instance of this var)
postgress_install_dir=${postgress_install_dir:-${install_prefix}/pgsql}
postgress_user=${postgress_user:-dbsuper}
postgress_host=${postgress_host:-localhost}
postgress_port=${postgress_port:-5432}
pg_sys_acct=${pg_sys_acct:-postgres}
#-----------

date_format=${date_format:-"+%Y_%m_%d_%H%M%S"}

export X509_CERT_DIR=${X509_CERT_DIR:-/etc/grid-security/certificates/}
export GLOBUS_SYS_ACCT=${globus_sys_acct}  #TODO: why is this an exported var?

#NOTE: This is just here as a note, should be set already by th
#      calling environment. Maybe refactor this out of esg-node and
#      pull test_publication into separate test publication script?
#      Hmmmm.... No harm in doubling up, but come back and make crispy
#      and clean later
prefix_to_path LD_LIBRARY_PATH $GLOBUS_LOCATION/lib >> ${envfile}
prefix_to_path PATH $GLOBUS_LOCATION/bin >> ${envfile}
dedup ${envfile} && source ${envfile}


#NTP is so important to distributed systems that it should be started on G.P.
/etc/init.d/ntpd start >& /dev/null

#--------------------------------------------------------------
# PROCEDURE
#--------------------------------------------------------------
def setup_globus_services(config_type):
    '''arg1 - config_type ("datanode" | "gateway"  ["install"|"update"])'''

    print "*******************************"
    print "Setting up Globus... (config type: $config_type)"
    print "*******************************"
    globus_version = "6.0"
    if os.access("/usr/bin/globus-version", os.X_OK):
        print "Detected an existing Globus installation"
        print "Checking for Globus {}".format(globus_version)
        installed_globus_version = esg_functions.call_subprocess("/usr/bin/globus-version")['stdout']
        if esg_version_manager.compare_versions(installed_globus_version, globus_version):
            print "Globus version appears sufficiently current"

    if esg_property_manager.get_property("install.globus"):
        setup_postgres_answer = esg_property_manager.get_property("install.globus")
    else:
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

        create_globus_account()
        install_globus(config_type)
        setup_gcs_io("firstrun")
        setup_gridftp_metrics_logging()

        config_gridftp_server()
        config_gridftp_metrics_logging("end-user")

        if os.path.exists("/usr/sbin/globus-gridftp-server"):
            esg_property_manager.set_property("gridftp_app_home", "/usr/sbin/globus-gridftp-server")
    elif config_type == "gateway":
        print "*******************************"
        print "Setting up The ESGF Globus MyProxy Services"
        print "*******************************"

        install_globus(config_type)
        setup_gcs_id("firstrun")
        config_myproxy_server()
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
    esg_bash2.py.mkdir_p(globus_workdir)
    # chmod a+rw $globus_workdir
    os.chmod(globus_workdir, current_mode.st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    with esg_bash2.py.pushd(globus_workdir):
        # Setup Globus RPM repo
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

    esg_usage_parser_dist_file = "esg_usage_parser-{}.tar.bz2".format(usage_parser_version)
    esg_usage_parser_dist_url= "https://aims1.llnl.gov/esgf/dist//globus/gridftp/esg_usage_parser-{}.tar.bz2".format(usage_parser_version)
    esg_usage_parser_dist_dir = os.path.join(globus_workdir, "esg_usage_parser-{}".format(usage_parser_version))
    esg_bash2py.mkdir_p(esg_usage_parser_dist_dir)
    # chmod a+rw $globus_workdir
    os.chmod(globus_workdir, current_mode.st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    with esg_bash2py.pushd(esg_usage_parser_dist_dir):
        print "Downloading Globus GridFTP Usage Parser from {}".format(esg_usage_parser_dist_url)
        esg_functions.dowload_update(esg_usage_parser_dist_file, esg_usage_parser_dist_url)

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
        config_file.write("USAGEFILE={}\n".format(gridftp_server_usage_log)
        config_file.write("TMPFILE={}\n".format(os.path.join(config["esg_log_dir"], "__up_tmpfile"))
        config_file.write("DEBUG=0\n")
        config_file.write("NODBWRITE=0\n")

    print 'Setting up a cron job, /etc/cron.d/esg_usage_parser ...'
    with open("/etc/cron.d/esg_usage_parser", "w") as cron_file:
        cron_file.write("5 0,12 * * * root ESG_USAGE_PARSER_CONF={gridftp_server_usage_config} {esg_tools_dir}/esg_usage_parser".format(gridftp_server_usage_config=gridftp_server_usage_config, esg_tools_dir=config["esg_tools_dir"]))

def setup_gridftp_jail(globus_sys_acct):

    print "*******************************"
    print "Setting up GridFTP... chroot jail"
    print "*******************************"

    gridftp_chroot_jail = "{esg_root_dir}/gridftp_root".format(config["esg_root_dir"])
    if not os.path.exists(gridftp_chroot_jail):
        print "{} does not exist, making it...".format(gridftp_chroot_jail)
        esg_bash2.py.mkdir_p(gridftp_chroot_jail)

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
            logger.debug("could not find property %s", property_name)
            raise
        except ConfigParser.NoOptionError:
            logger.debug("could not find property %s", property_name)
            raise

        for dataset in dataset_list:
            mount_name, mount_dir = dataset.split("|")
            print "mounting [{mount_dir}] into chroot jail [{gridftp_chroot_jail}/] as [{mount_name}]".format(mount_dir=mount_dir, mount_name=mount_name, gridftp_chroot_jail=gridftp_chroot_jail)
            real_mount_dir = esg_functions.readlink_f(mount_dir)
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
            sanitized_passwd.write("root:x:0:0:root:/root:/bin/bash\n")
            sanitized_passwd.write("bin:x:1:1:bin:/bin:/dev/null\n")
            sanitized_passwd.write("ftp:x:14:50:FTP User:/var/ftp:/dev/null\n")
            sanitized_passwd.write("globus:x:101:156:Globus System User:/home/globus:/bin/bash\n")

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

setup_gcs_io() {

    local input
    if [ $GLOBUS_SETUP = 'yes' ]; then


        local myproxy_hostname=${myproxy_endpoint:-${esgf_idp_peer:-%(HOSTNAME)s}}

        cat >/etc/globus-connect-server-esgf.conf <<EOF
[Globus]
User = %(GLOBUS_USER)s
Password = %(GLOBUS_PASSWORD)s
[Endpoint]
Name = %(SHORT_HOSTNAME)s
Public = True
[Security]
FetchCredentialFromRelay = True
CertificateFile = /etc/grid-security/hostcert.pem
KeyFile = /etc/grid-security/hostkey.pem
TrustedCertificateDirectory = /etc/grid-security/certificates/
IdentityMethod = MyProxy
AuthorizationMethod = Gridmap
[GridFTP]
Server = %(HOSTNAME)s
IncomingPortRange = ${gridftp_server_port_range}
OutgoingPortRange = ${gridftp_server_source_range}
RestrictPaths = R/,N/etc,N/tmp,N/dev
Sharing = False
SharingRestrictPaths = R/
SharingStateDir = ${gridftp_chroot_jail}/etc/grid-security/sharing/\$USER
[MyProxy]
Server = ${myproxy_hostname}
EOF

        globus-connect-server-io-setup -c /etc/globus-connect-server-esgf.conf -v
        return $?
    fi

    # Create a substitution of GCS configuration files for GridFTP server
    [ ! -d /etc/gridftp.d ] && mkdir /etc/gridftp.d
    cat >/etc/gridftp.d/globus-connect-esgf <<EOF
port_range 50000,51000
\$GLOBUS_TCP_SOURCE_RANGE 50000,51000
restrict_paths R/,N/etc,N/tmp,N/dev
\$GRIDMAP "/etc/grid-security/grid-mapfile"
\$X509_USER_CERT "/etc/grid-security/hostcert.pem"
\$X509_USER_KEY "/etc/grid-security/hostkey.pem"
log_single /var/log/gridftp.log
log_level ALL
\$X509_CERT_DIR "/etc/grid-security/certificates"
EOF

    return 0

}

# (OLD WAY) http://www.ci.uchicago.edu/wiki/bin/view/ESGProject/GridFTPServerWithTokenAuthorizationModuleConfig
# http://www.ci.uchicago.edu/wiki/bin/view/ESGProject/EnhancedEndUserDownloadGridFTPModule
config_gridftp_server() {

    echo "GridFTP - Configuration..."
    echo
    echo "*******************************"
    echo "Setting up GridFTP..."
    echo "*******************************"
    echo

    write_as_property gridftp_server_port

    #TODO: Decide how to maintain semantic integrity
    [ -z ${globus_sys_acct} ] && echo " ERROR: globus_sys_acct=[${globus_sys_acct}] must be set" && checked_done 1

    # generate ESG SAML Auth config file
    write_esgsaml_auth_conf

    dnode_root_dn_wildcard='^.*$'
    grid-mapfile-add-entry -dn ${dnode_root_dn_wildcard} -ln ${globus_sys_acct}

    echo "chroot_path ${gridftp_chroot_jail}" > /etc/gridftp.d/globus-esgf
    echo 'usage_stats_id 2811' >> /etc/gridftp.d/globus-esgf
    echo 'usage_stats_target localhost:0\!all' >> /etc/gridftp.d/globus-esgf
    echo 'acl customgsiauthzinterface' >> /etc/gridftp.d/globus-esgf
    echo "\$GLOBUS_USAGE_DEBUG \"MESSAGES,${gridftp_server_usage_log}\"" >> /etc/gridftp.d/globus-esgf
    echo '$GSI_AUTHZ_CONF "/etc/grid-security/authz_callouts_esgsaml.conf"' >> /etc/gridftp.d/globus-esgf
    echo '#$GLOBUS_GSI_AUTHZ_DEBUG_LEVEL "10"' >> /etc/gridftp.d/globus-esgf
    echo '#$GLOBUS_GSI_AUTHZ_DEBUG_FILE "/var/log/gridftp-debug.log"' >> /etc/gridftp.d/globus-esgf

    checked_done 0
}

#By making this a separate function it may be called directly in the
#event that the gateway_service_root needs to be repointed. (another Estani gem :-))
write_esgsaml_auth_conf() {
    get_property orp_security_authorization_service_endpoint
    echo "AUTHSERVICE=${orp_security_authorization_service_endpoint}" > /etc/grid-security/esgsaml_auth.conf
    echo
    echo "---------esgsaml_auth.conf---------"
    cat /etc/grid-security/esgsaml_auth.conf
    echo "---------------------------------"
    echo
    return 0
}

test_auth_service() {
    echo -n "Testing authorization service on ${esgf_host} ... "
    ! globus_adq_client https://${esgf_host}/esg-orp/saml/soap/secure/authorizationService.htm https://${esgf_host}/esgf-idp/openid/rootAdmin gsiftp://${esgf_host}:${gridftp_server_port}//esg_dataroot/test/sftlf.nc | grep -q 'NOT PERMIT' >& /dev/null
    local ret=$?
    [ ${ret} == 0 ] && [OK] || [FAIL]
    return ${ret}
}

test_gridftp_server() {
    local ret=0
    local tmpdestfile
    debug_print "test_gridftp_server: [$@]"

    local personal_credential_repo="$HOME/.globus"

    mkdir -p ${personal_credential_repo}
    chown -R ${installer_uid}:${installer_gid} ${personal_credential_repo}

    rm -rf ${personal_credential_repo}/esgf_credentials >& /dev/null
    local _X509_CERT_DIR=${personal_credential_repo}/esgf_credentials
    local _X509_USER_KEY=${personal_credential_repo}/esgf_credentials
    local _X509_USER_CERT=${personal_credential_repo}/esgf_credentials

    echo "myproxy-logon -s $myproxy_endpoint -l rootAdmin -p $myproxy_port -T"
    X509_CERT_DIR=${_X509_CERT_DIR} \
        X509_USER_KEY=${_X509_USER_KEY} \
        X509_USER_CERT=${_X509_USER_CERT} \
        myproxy-logon -s $myproxy_endpoint -l rootAdmin -p $myproxy_port -T
    [ $? != 0 ] && echo " ERROR: MyProxy not setup properly.  Unable to execute command." && return 1

    echo -n "GridFTP - End-User Test... [$1] "
    tmpdestfile=$(mktemp)
    X509_CERT_DIR=${_X509_CERT_DIR} \
        X509_USER_KEY=${_X509_USER_KEY} \
        X509_USER_CERT=${_X509_USER_CERT} \
        globus-url-copy gsiftp://${esgf_host:-localhost}:${gridftp_server_port}/esg_dataroot/test/sftlf.nc ${tmpdestfile} && \
        diff <(echo $(md5sum ${tmpdestfile} | awk '{print $1}')) <(echo $(md5sum /esg/gridftp_root/esg_dataroot/test/sftlf.nc | awk '{print $1}')) && \
        rm -f ${tmpdestfile} && [OK] || ( [FAIL] && ((ret++)) )
    return ${ret}
}

configure_esgf_publisher_for_gridftp() {
    echo -n " configuring publisher to use this GridFTP server... "
    if [ -e ${publisher_home}/${publisher_config} ]; then
        cp ${publisher_home}/${publisher_config}{,.bak}
        sed -i 's#\(gsiftp://\)\([^:]*\):\([^/].*\)/#\1'${esgf_gridftp_host:-${esgf_host}}':'${gridftp_server_port}'/#' ${publisher_home}/${publisher_config}
        echo "[OK]"
        return 0
    fi
    echo "[FAIL]"
    return 1
}

#see caller start_globus_services() above.
#returns true  (0) if this function actively started the process
#returns false (1) if this function did not have to start the process since already running
start_gridftp_server() {
    local global_x509_cert_dir=${global_x509_cert_dir:-${X509_CERT_DIR:-"/etc/grid-security/certificates"}}
    local ret=0
    echo " GridFTP - Starting server... $*"
    #TODO: Does it matter if root starts the server vs the globus_sys_acct ??? Neill?
    #      Is there a difference between who starts the server and who the server
    #      xfrs file as?
    write_esgsaml_auth_conf
    setup_gridftp_jail
    post_gridftp_jail_setup

    echo -n " syncing local certificates into chroot jail... "
    [ -n "${gridftp_chroot_jail}" ] && [ "${gridftp_chroot_jail}" != "/" ] && [ -e "${gridftp_chroot_jail}/etc/grid-security/certificates" ] && \
        rm -rf ${gridftp_chroot_jail}/etc/grid-security/certificates && \
        mkdir -p ${gridftp_chroot_jail}/etc/grid-security && \
        (cd /etc/grid-security; tar cpf - certificates) | tar xpf - -C ${gridftp_chroot_jail}/etc/grid-security
    [ $? == 0 ] && echo "[OK]" || echo "[FAIL]"

    configure_esgf_publisher_for_gridftp

    service globus-gridftp-server start

    return 0
}


stop_gridftp_server() {
    service globus-gridftp-server stop
    return 0
}


#This function "succeeds" (is true -> returns 0)  if there *are* running processes found
check_gridftp_process() {
    local port="$1"
    val=$(ps -elf | grep globus-gridftp-server | grep -v grep | grep "${port}" | awk ' END { print NR }')
    [ $(($val > 0 )) == 1 ] && echo " gridftp-server process is running on port [${port}]..." && return 0
    return 1
}


#--------------------------------------------------------------
# MY PROXY
#--------------------------------------------------------------

# This function bascially copies and renames the signed cert into the right place.
# It also does the bookkeeping needed in the overall property file to reflect the DN
# arg (optional) -> the signed certificate (.pem) file to be installed
install_globus_keypair() {
    #--------------------------------------------------
    #Install signed globus pem file
    #--------------------------------------------------
    local globus_grid_security_dir=${globus_global_certs_dir%/*}
    if [ -d  ${globus_grid_security_dir} ]; then
        local globus_signed_cert=${1:-${globus_grid_security_dir}/${esgf_host:-$(hostname --fqdn)}-esg-node-globus.pem}
        if [ -e "${globus_signed_cert}" ]; then
            [ -e ${globus_grid_security_dir}/hostcert.pem ] && mv ${globus_grid_security_dir}/hostcert.pem{,.bak}
            mv -v ${globus_signed_cert} ${globus_grid_security_dir}/hostcert.pem && \
                chmod 644 ${globus_grid_security_dir}/hostcert.pem && \
                openssl x509 -noout -text -in ${globus_grid_security_dir}/hostcert.pem
        else
            echo "ERROR: Could not find certificate ${globus_signed_cert}"
            exit 5
        fi
    else
        echo "ERROR: Could not locate target globus key location:[${globus_grid_security_dir}]"
        exit 6
    fi

    [ -e "${globus_grid_security_dir}/hostcert.pem" ] && \
        write_as_property node_dn $(extract_openssl_dn ${globus_grid_security_dir}/hostcert.pem) && echo "properly updated [OK]"
    echo
}

globus_check_certificates() {
    debug_print "globus_check_certificates..."
    local my_cert=/etc/grid-security/hostcert.pem
    #do this in a subshell
    (source ${esg_functions_file} && check_cert_expiry_for_files ${my_cert})
}


#--------------------
# Register with Globus Web Service and get a host certificate
#--------------------

setup_gcs_id() {


    if [ "x$1" = "xfirstrun" ]; then
        pushd /etc/tempcerts >& /dev/null
    else
        pushd /etc/esgfcerts >& /dev/null
    fi

    myproxyca_dir=/var/lib/globus-connect-server/myproxy-ca
    [ ! -d ${myproxyca_dir}/newcerts ] && mkdir -p ${myproxyca_dir}/newcerts && chmod 700 ${myproxyca_dir}
    [ ! -d ${myproxyca_dir}/private ] && mkdir -p ${myproxyca_dir}/private && chmod 700 ${myproxyca_dir}/private
    cp cacert.pem ${myproxyca_dir}
    cp cakey.pem ${myproxyca_dir}/private
    cp signing-policy ${myproxyca_dir}
    if [ -s hostkey.pem -a -s hostcert.pem ]; then
        cp host*.pem /etc/grid-security
    fi
    localhash=`openssl x509 -noout -hash -in cacert.pem`
    cp globus_simple_ca_${localhash}_setup-0.tar.gz ${myproxyca_dir}
    cp globus_simple_ca_${localhash}_setup-0.tar.gz /etc/grid-security/certificates
    popd >& /dev/null

    local myproxy_config_dir=${esg_config_dir}/myproxy
    mkdir -p ${myproxy_config_dir}

    local input

    echo '*******************************'
    echo ' Registering the IdP node with Globus Platform'
    echo '*******************************'
    echo
    echo 'The installer will create a Globus (www.globus.org) endpoint to allow users to'
    echo 'download data through Globus. This uses the GridFTP server on the data node.'
    echo 'The endpoint is named as <globus_username>#<host_name>, e.g. llnl#pcmdi9 where'
    echo 'llnl is Globus username and pcmdi9 is endpoint name. To create a Globus account,'
    echo 'go to www.globus.org/SignUp.'
    echo
    echo 'This step can be skipped, but users will not be able to download datasets'
    echo 'from the GridFTP server on the data node through the ESGF web interface.'
    echo

    while [ 1 ]; do
        read -e -p 'Do you want to register the MyProxy server with Globus? [Y/n]: ' input
        [ -z "${input}" -o "${input}" = 'Y' -o "${input}" = 'y' ] && export GLOBUS_SETUP='yes' && break
        [ "${input}" = 'N' -o "${input}" = 'n' ] && export GLOBUS_SETUP='no' && break
    done

    if [ $GLOBUS_SETUP = 'yes' ]; then

        if [ -z "$GLOBUS_USER" ]; then
            local input
            while [ 1 ]; do
                read -e -p "Please provide a Globus username [${globus_user}]: " input
                [ -n "${input}" ] && export GLOBUS_USER="${input}" && break
                [ -n "${globus_user}" ] && export GLOBUS_USER="${globus_user}" && break
            done
            unset input
        fi

        if [ -z "$GLOBUS_PASSWORD" ]; then
            local input
            while [ 1 ]; do
                read -es -p "Globus password [$([ -n "${globus_password}" ] && echo "*********")]: " input
                [ -n "${input}" ] && export GLOBUS_PASSWORD="${input}" && break
                [ -n "${globus_password}" ] && export GLOBUS_PASSWORD="${globus_password}" && break
            done
            unset input
        fi

        cat >${myproxy_config_dir}/globus-connect-server.conf <<EOF
[Globus]
User = %(GLOBUS_USER)s
Password = %(GLOBUS_PASSWORD)s
[Endpoint]
Name = %(SHORT_HOSTNAME)s
Public = True
[Security]
FetchCredentialFromRelay = True
CertificateFile = /etc/grid-security/hostcert.pem
KeyFile = /etc/grid-security/hostkey.pem
TrustedCertificateDirectory = /etc/grid-security/certificates/
IdentityMethod = MyProxy
[GridFTP]
Server = %(HOSTNAME)s
RestrictPaths = R/,N/etc,N/tmp,N/dev
Sharing = False
SharingRestrictPaths = R/
[MyProxy]
Server = %(HOSTNAME)s
EOF

        globus-connect-server-id-setup -c ${myproxy_config_dir}/globus-connect-server.conf -v
        return $?
    fi

    # Create a substitution of Globus generated confguration files for MyProxy server
    [ ! -d /etc/myproxy.d ] && mkdir /etc/myproxy.d
    cat >/etc/myproxy.d/globus-connect-esgf <<EOF
export MYPROXY_USER=root
export X509_CERT_DIR="/etc/grid-security/certificates"
export X509_USER_CERT="/etc/grid-security/hostcert.pem"
export X509_USER_KEY="/etc/grid-security/hostkey.pem"
export X509_USER_PROXY=""
export MYPROXY_OPTIONS="\${MYPROXY_OPTIONS:+\$MYPROXY_OPTIONS }-c /var/lib/globus-connect-server/myproxy-server.conf -s /var/lib/globus-connect-server/myproxy-ca/store"
EOF

    cat >/esg/config/myproxy/myproxy-server.config <<EOF
        authorized_retrievers      "*"
        default_retrievers         "*"
        authorized_renewers        "*"
        authorized_key_retrievers  "*"
        trusted_retrievers         "*"
        default_trusted_retrievers "none"
        max_cert_lifetime          "72"
        disable_usage_stats        "true"
        cert_dir                   "/etc/grid-security/certificates"

        pam_id "myproxy"
        pam "required"

        certificate_issuer_cert "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"
        certificate_issuer_key "/var/lib/globus-connect-server/myproxy-ca/private/cakey.pem"
        certificate_issuer_key_passphrase "globus"
        certificate_serialfile "/var/lib/globus-connect-server/myproxy-ca/serial"
        certificate_out_dir "/var/lib/globus-connect-server/myproxy-ca/newcerts"
        certificate_issuer_subca_certfile "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"
        certificate_mapapp /esg/config/myproxy/myproxy-certificate-mapapp
        certificate_extapp /esg/config/myproxy/esg_attribute_callout_app
EOF

    return 0
}


# Note: myproxy servers live on gateway machines
# see - http://www.ci.uchicago.edu/wiki/bin/view/ESGProject/MyProxyWithAttributeCalloutConfig
# arg = *"install" ------ run in install mode [install_mode=1]
#        "update" ------- update the simpleCA [install_mode=0]
config_myproxy_server() {

    echo "MyProxy - Configuration... [$@]"

    #toggle var install(1)/update(0)
    local install_mode=1

    for arg in $@
    do
        case $arg in
            "install")
                install_mode=1
                ;;
            "update")
                install_mode=0
                ;;
            *)
                printf "

    ERROR: You have entered an invalid argument: [$@]\n

    Usage:
    function - esg-globus:config_myproxy_server [install|update]
    (* indicates default values if no args are given)

    \n"
                return 1
                ;;
        esac
    done

    #--------------------
    # Compile Java Code Used by "callout" scripts in ${globus_location}/bin
    #--------------------
    if [ ! -e ESGOpenIDRetriever.class ] || [ ! -e ESGGroupRetriever ]; then
        pushd ${globus_location}/bin >& /dev/null
        echo "Download and building ESGOpenIDRetriever and ESGGroupRetriever..."
        wget -O ESGOpenIDRetriever.java ${myproxy_dist_url_base}/ESGOpenIDRetriever.java
        wget -O ESGGroupRetriever.java  ${myproxy_dist_url_base}/ESGGroupRetriever.java

        #NOTE: "gateway_app_home" is available if this file is sourced from esg-gway
        if [ -e ${gateway_app_home}/WEB-INF/lib/${postgress_jar} ]; then
            echo " Found postgres jar in gateway web application's lib"
            ln -s ${gateway_app_home}/WEB-INF/lib/${postgress_jar}
        else
            echo " Could not find postgresql jdbc jar in gateway web application's lib"
            echo " getting it..."
            wget -O ${postgress_jar} ${myproxy_dist_url_base}/${postgress_jar}
        fi

        local cp=.:`pwd`:$(find `pwd`| grep .jar | xargs | perl -pe 's/ /:/g')
        echo "javac -classpath ${cp} ESGOpenIDRetriever.java"
        javac -classpath ${cp} ESGOpenIDRetriever.java
        echo "javac -classpath ${cp} ESGGroupRetriever.java"
        javac -classpath ${cp} ESGGroupRetriever.java
        popd >& /dev/null
        unset cp
    fi
    #--------------------

    #--------------------
    # Get myproxy-certificate-mapapp file
    #--------------------
    fetch_myproxy_certificate_mapapp
    #--------------------

    #--------------------
    # Configure pam_sql.conf
    #--------------------
    edit_pam_pgsql_conf
    #--------------------

    #--------------------
    # Fetch -> pam resource file used for myproxy
    #--------------------
    fetch_etc_pam_d_myproxy
    #--------------------

    #--------------------
    # Get esg_attribute_callout_app file
    #--------------------
    fetch_esg_attribute_callout_app
    #--------------------

    #--------------------
    # Create /esg/config/myproxy/myproxy-server.config
    #--------------------
    edit_myproxy_server_config
    #--------------------

    #--------------------
    # Add /etc/myproxy.d/myproxy-esgf to force MyProxy server to use /esg/config/myproxy/myproxy-server.config
    #--------------------
    edit_etc_myproxyd
    #--------------------


    write_db_name_env

    popd >& /dev/null
    write_myproxy_install_log

    restart_myproxy_server

    checked_done 0
}

write_myproxy_install_log() {
    [ -e /usr/sbin/myproxy-server ] && \
        write_as_property myproxy_app_home /usr/sbin/myproxy-server || \
        echo "WARNING: Cannot find executable /usr/sbin/myproxy-server"
    ! grep myproxy.endpoint ${esg_config_dir}/esgf.properties && write_as_property myproxy_endpoint "${esgf_host:-$(hostname --fqdn)}"
    ! grep myproxy.port ${esg_config_dir}/esgf.properties && write_as_property myproxy_port
    write_as_property myproxy_dn "/$(openssl x509 -text -noout -in /etc/grid-security/hostcert.pem | sed -n 's#.*Subject: \(.*$\)#\1#p' | tr -s " " | sed -n 's#, #/#gp')"

    echo "$(date ${date_format}) globus:myproxy=${myproxy_version} ${myproxy_app_home}" >> ${install_manifest}
    dedup ${install_manifest}
    return 0

}

write_db_name_env() {
    ((show_summary_latch++))
    echo "export ESGF_DB_NAME=${esgf_db_name}" >> ${envfile}
    dedup ${envfile} && source ${envfile}
    return 0
}


test_myproxy_server() {
    echo "MyProxy - Test... (faux) [$@]"
    #TODO: Sanity check code...
    return 0
}

start_myproxy_server() {
    check_myproxy_process && return 0
    if [ -x /etc/init.d/myproxy-server ]; then
        /etc/init.d/myproxy-server start && return 0
    elif [ -x /etc/init.d/myproxy ]; then
        echo " MyProxy - Starting server..."
        /etc/init.d/myproxy start && return 0
    fi
    return 1
}

stop_myproxy_server() {
    if [ -x /etc/init.d/myproxy-server ]; then
        /etc/init.d/myproxy-server stop
    elif [ -x /etc/init.d/myproxy ]; then
        /etc/init.d/myproxy stop
    fi

    if check_myproxy_process; then
        echo "Detected Running myproxy-server..."
    else
        echo "No MyProxy Process Currently Running..." && return 1
    fi

    killall myproxy-server && echo " [OK] " || echo " [FAIL] "
    return $?
}

restart_myproxy_server() {
    stop_myproxy_server
    start_myproxy_server
}

#This function "succeeds" (is true -> returns 0)  if there *are* running processes found
check_myproxy_process() {
    val=$(ps -elf | grep myproxy-server* | grep -v grep | awk ' END { print NR }')
    [ $(($val > 0 )) == 1 ] && echo "myproxy-server process is running..." && return 0
    return 1
}

############################################
# Configuration File Editing Functions
############################################

edit_myproxy_server_config() {
    mkdir -p ${esg_config_dir}/myproxy
    pushd ${esg_config_dir}/myproxy >& /dev/null
    local tfile=myproxy-server.config
    echo "Creating/Modifying myproxy server configuration file: `pwd`/${tfile}"
    [ -e "${tfile}" ] && mv -v ${tfile}{,.bak}

    cat > ${tfile} <<EOF
        authorized_retrievers      "*"
        default_retrievers         "*"
        authorized_renewers        "*"
        authorized_key_retrievers  "*"
        trusted_retrievers         "*"
        default_trusted_retrievers "none"
        max_cert_lifetime          "72"
        disable_usage_stats        "true"
        cert_dir                   "/etc/grid-security/certificates"

        pam_id "myproxy"
        pam "required"

        certificate_issuer_cert "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"
        certificate_issuer_key "/var/lib/globus-connect-server/myproxy-ca/private/cakey.pem"
        certificate_issuer_key_passphrase "globus"
        certificate_serialfile "/var/lib/globus-connect-server/myproxy-ca/serial"
        certificate_out_dir "/var/lib/globus-connect-server/myproxy-ca/newcerts"
        certificate_issuer_subca_certfile "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"
        certificate_mapapp ${esg_config_dir}/myproxy/myproxy-certificate-mapapp
        certificate_extapp ${esg_config_dir}/myproxy/esg_attribute_callout_app
EOF

    chmod 600 ${tfile}
    ((DEBUG)) && cat ${tfile}
    popd >& /dev/null
    unset tfile
    return 0
}

edit_pam_pgsql_conf() {
    local _force_install=$((force_install + ${1:-0}))
    pushd /etc >& /dev/null
    local tfile=pam_pgsql.conf
    echo "Download and Modifying pam pgsql configuration file: `pwd`/${tfile}"
    checked_get ${tfile}.tmpl ${myproxy_dist_url_base}/etc_${tfile} $((_force_install))
    [ -e "${tfile}" ] && mv -v ${tfile}{,.bak}
    cp -vf ${tfile}{.tmpl,}
    [ -n "${tfile}" ] && chmod 600 ${tfile}* >& /dev/null
    [ $? != 0 ] && return 1
    eval "perl -p -i -e 's/\\@\\@postgress_host\\@\\@/${postgress_host}/g' ${tfile}"
    echo -n "*"
    eval "perl -p -i -e 's/\\@\\@postgress_port\\@\\@/${postgress_port}/g' ${tfile}"
    echo -n "*"
    eval "perl -p -i -e 's/\\@\\@postgress_user\\@\\@/${postgress_user}/g' ${tfile}"
    echo -n "*"
    eval "perl -p -i -e 's/\\@\\@pg_sys_acct_passwd\\@\\@/${pg_sys_acct_passwd}/g' ${tfile}"
    echo -n "*"
    eval "perl -p -i -e 's/\\@\\@esgf_db_name\\@\\@/${esgf_db_name}/g' ${tfile}"
    eval "perl -p -i -e 's/\\@\\@esgf_idp_peer\\@\\@/${esgf_idp_peer}/g' ${tfile}"
    echo -n "*"
    echo " [OK]"
    ((DEBUG)) && cat ${tfile}
    popd >& /dev/null
    unset tfile
    return 0
}

edit_etc_myproxyd() {
    echo "export MYPROXY_OPTIONS=\"-c ${esg_config_dir}/myproxy/myproxy-server.config -s /var/lib/globus-connect-server/myproxy-ca/store\""> /etc/myproxy.d/myproxy-esgf
    return 0
}

fetch_myproxy_certificate_mapapp() {
    local _force_install=$((force_install + ${1:-0}))
    local myproxy_config_dir=${esg_config_dir}/myproxy
    mkdir -p ${myproxy_config_dir}
    pushd ${myproxy_config_dir} >& /dev/null

    local tfile=myproxy-certificate-mapapp
    echo "Downloading configuration file: `pwd`/${tfile}"
    checked_get ${tfile}.tmpl ${myproxy_dist_url_base}/${tfile} $((_force_install))
    local ret=$?
#    (( ret >= 1 )) && return 0
    [ -e "${tfile}.tmpl" ] && chmod 640 ${tfile}.tmpl && cp -v ${tfile}{.tmpl,} && chmod 751 ${tfile} && \
        sed -i.bak 's#/root/\.globus/simpleCA/cacert\.pem#/var/lib/globus-connect-server/myproxy-ca/cacert\.pem#' ${tfile}
    ((DEBUG)) && cat ${tfile}
    popd >& /dev/null
    unset tfile
    return 0
}

fetch_etc_pam_d_myproxy() {
    local _force_install=$((force_install + ${1:-0}))
    pushd /etc/pam.d >& /dev/null
    local tfile=myproxy
    echo "Fetching pam's myproxy resource file: `pwd`/${tfile}"
    checked_get ${tfile} ${myproxy_dist_url_base}/etc_pam.d_${tfile} $((_force_install))
    ((DEBUG)) && cat ${tfile}
    popd >& /dev/null
    unset tfile
}

fetch_esg_attribute_callout_app() {
    local _force_install=$((force_install + ${1:-0}))
    #Configure External Attribute Callout with MyProxy
    local myproxy_config_dir=${esg_config_dir}/myproxy
    mkdir -p ${myproxy_config_dir}
    pushd ${myproxy_config_dir} >& /dev/null

    local tfile=esg_attribute_callout_app
    echo "Downloading configuration file: `pwd`/${tfile}"
    checked_get ${tfile} ${myproxy_dist_url_base}/${tfile} $((_force_install))
    [ -e "${tfile}" ] && chmod 751 ${tfile}
    ((DEBUG)) && cat ${tfile}
    popd >& /dev/null
    unset tfile
}

sanity_check_myproxy_configurations() {
    local _force_install=$((force_install + ${1:-0}))
    edit_myproxy_server_config $((_force_install))
    edit_pam_pgsql_conf $((_force_install))
    fetch_myproxy_certificate_mapapp $((_force_install))
    fetch_etc_pam_d_myproxy $((_force_install))
    fetch_esg_attribute_callout_app $((_force_install))
    edit_etc_myproxyd $((_force_install))
}

############################################
# Utility Functions
############################################

create_globus_account() {
    ########
    #Create the system account for globus to run as.
    ########
    [ -z "${globus_sys_acct}" ] && echo "no globus account specfied, must be specified to continue!" && checked_done
    echo -n "checking globus account \"${globus_sys_acct}\"... "

    id ${globus_sys_acct}
    if [ $? != 0 ]; then
        echo
	echo " Hmmm...: There is no globus system account user \"$globus_sys_acct\" present on system, making one... "
	#NOTE: "useradd/groupadd" are a RedHat/CentOS thing... to make this cross distro compatible clean this up.
	if [ ! $(getent group ${globus_sys_acct_group}) ]; then
	    /usr/sbin/groupadd -r ${globus_sys_acct_group}
	    [ $? != 0 ] && [ $? != 9 ] && echo "ERROR: Could not add globus system group: ${globus_sys_acct_group}" && checked_done 1
	fi

	if [ -z "${globus_sys_acct_passwd}" ]; then
	    #set the password for the system user...
	    while [ 1 ]; do
		local input
		read -s -p "Create password for globus system account: \"${globus_sys_acct}\" " input
		[ -n "${input}" ] && globus_sys_acct_passwd=${input}  && unset input && break
	    done
	fi
	echo -n "Creating account... "
	/usr/sbin/useradd -r -c"Globus System User" -g ${globus_sys_acct_group} -p ${globus_sys_acct_passwd} -s /bin/bash ${globus_sys_acct}
	[ $? != 0 ] && [ $? != 9 ] && echo "ERROR: Could not add globus system account user" && popd && checked_done 1
        echo "[OK]"
    else
        echo "[OK]"
    fi
}


############################################
# Globus Online Setup
############################################
setup_globus_online() {
    printf "
    Setting up Globus Online / ESGF integration...

    NOTE: You MUST have created a Globus Online account for
    this node: In order for oAuth to work correctly such that
    the user does not have to link their ESG credential with their
    Globus Online account, this node must have its own account.

        https://www.globusonline.org/SignUp

"
    local local=y
    read -e -p "Continue? [Y/n] " input
    [ "n" = "$(echo "${input}" | tr [A-Z] [a-z])" ] && return 1
    unset input

    (
        local config_file=${esg_config_dir}/globusonline.properties
        load_properties ${config_file}

        local input
        while [ 1 ]; do
            read -e -p "Please enter your Globus Online ID [${GOesgfPortalID}]: " input
            [ -n "${input}" ] && GOesgfPortalID=${input} && break
            [ -n "${GOesgfPortalID}" ] && break
        done
        unset input
        write_as_property GOesgfPortalID

        while [ 1 ]; do
            read -e -p "Please enter your Globus Online Password [$([ -n "${GOesgfPortalPassword}" ] && echo "*********")]: " input
            [ -n "${input}" ] && GOesgfPortalPassword=${input} && break
            [ -n "${GOesgfPortalPassword}" ] && break
        done
        unset input
        write_as_property GOesgfPortalPassword

        chmod 600 ${config_file}
        chown ${tomcat_user:-tomcat}.${tomcat_group:-tomcat} ${config_file}

        local mkproxy_dist_url="${esg_dist_url}/externals/bootstrap/mkproxy-10-15-2012.tar.gz"
        local mkproxy_dist_file=${mkproxy_dist_url##*/}
        pushd /tmp/
        checked_get ${mkproxy_dist_file} ${mkproxy_dist_url} $((force_install))
        (( $? > 1 )) && echo " ERROR: Could not download Globus Online install script" && popd >& /dev/null && checked_done 1
        tar xvzf ${mkproxy_dist_file}
        [ $? != 0 ] && echo " WARNING: Could not extract Globus Online install script (properly)" && popd >& /dev/null #&& checked_done 1
        cd /tmp/mkproxy
        [ $? != 0 ] && echo " ERROR: Could not Chang to mkproxy directory" && popd >& /dev/null && checked_done 1
        make
        [ $? != 0 ] && echo " ERROR: Could not build mkproxy program" && popd >& /dev/null && checked_done 1
        cp -v /tmp/mkproxy/mkproxy /usr/local/bin
        cd ../
        [ -e "/tmp/${mkproxy_dist_file}" ] && rm -rf mkproxy /tmp/${mkproxy_dist_file}
        popd >& /dev/null
        (config_file=${esg_config_dir}/searchconfig.properties write_as_property enableGlobusOnline true && chmod 600 ${config_file})
    )
    echo "<<<<$?>>>>"
}
