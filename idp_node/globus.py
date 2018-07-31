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
from esgf_utilities import pybash
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from esgf_utilities import esg_cert_manager
from esgf_utilities.esg_exceptions import SubprocessError, InvalidNodeTypeError
from base import esg_tomcat_manager
from base import esg_postgres
from idp_node import gridftp
from idp_node import myproxy


logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def check_for_globus_installation(globus_version, installation_type):
    if os.access("/usr/bin/globus-version", os.X_OK):
        print "Detected an existing Globus installation"
        print "Checking for Globus {}".format(globus_version)
        installed_globus_version = esg_functions.call_subprocess("/usr/bin/globus-version")['stdout']
        if esg_version_manager.compare_versions(installed_globus_version, globus_version+".0"):
            if installation_type == "DATA" and os.path.exists("/usr/bin/globus-connect-server-io-setup"):
                print "GridFTP already installed"
                print "Globus version appears sufficiently current"
                return True
            if installation_type == "IDP" and os.path.exists("/usr/bin/globus-connect-server-id-setup"):
                print "MyProxy already installed"
                print "Globus version appears sufficiently current"
                return True

def setup_globus(installation_type):
    '''
    Globus Toolkit ->  MyProxy (client) & GridFTP (server)
    Takes arg <selection bit vector>
    The rest of the args are the following...
    for data-node configuration (GridFTP stuff): ["bdm"|"end-user"] see esg-globus script
    for idp configuration (MyProxy stuff): [gen-self-cert] <dir> | <regen-simpleca> [fetch-certs|gen-self-cert|keep-certs] | ["install"|"update"]'''
    logger.debug("setup_globus for installation type: %s", installation_type)

    globus_version = "6.0"

    if check_for_globus_installation(globus_version, installation_type):
        try:
            setup_globus_answer = esg_property_manager.get_property("update.globus")
            if not setup_globus_answer:
                raise ConfigParser.NoOptionError
        except ConfigParser.NoOptionError:
            setup_globus_answer = raw_input(
                "Do you want to continue with the Globus installation and setup? [y/N]: ") or "N"

        if setup_globus_answer.lower().strip() in ["no", 'n']:
            logger.info("Skipping Globus installation. Using existing Globus version")
            return

    globus_location = "/usr/local/globus"

    pybash.mkdir_p(config["workdir"])
    with pybash.pushd(config["workdir"]):
        directive = "notype"
        if installation_type == "DATA":
            logger.info("Globus Setup for Data-Node... (GridFTP server) ")
            directive = "datanode"
            setup_globus_services(directive)
            write_globus_env(globus_location)
            pybash.touch(os.path.join(globus_location,"esg_esg-node_installed"))

        if installation_type == "IDP":
            logger.info("Globus Setup for Index-Node... (MyProxy server)")
            directive = "gateway"
            setup_mode = "install"
            setup_globus_services(directive)
            write_globus_env(globus_location)
            pybash.touch(os.path.join(globus_location, "esg_esg-node_installed"))

def write_globus_env(globus_location):
    '''Write globus properties to /etc/esg.env'''
    esg_property_manager.set_property("GLOBUS_LOCATION", "export GLOBUS_LOCATION={}".format(globus_location), property_file=config["envfile"], section_name="esgf.env", separator="_")


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
    '''Stops the globus services'''

    if installation_type == "DATA":
        stop_globus_services("datanode")
    elif installation_type == "IDP":
        stop_globus_services("gateway")
    else:
        raise InvalidNodeTypeError("Globus is not installed on a {} node type".format(installation_type))

#--------------------------------------------------------------
# PROCEDURE
#--------------------------------------------------------------
def setup_globus_services(config_type):
    '''arg1 - config_type ("datanode" | "gateway"  ["install"|"update"])'''

    print "*******************************"
    print "Setting up Globus... (config type: {})".format(config_type)
    print "*******************************"

    globus_sys_acct = "globus"

    logger.debug("setup_globus_services for %s", config_type)

    globus_location = "/usr/local/globus"
    pybash.mkdir_p(os.path.join(globus_location, "bin"))

    if config_type == "datanode":
        print "*******************************"
        print "Setting up ESGF Globus GridFTP Service(s)"
        print "*******************************"

        create_globus_account(globus_sys_acct)
        _install_globus(config_type)
        gridftp.setup_gcs_io("firstrun")
        gridftp.setup_gridftp_metrics_logging()

        gridftp.config_gridftp_server(globus_sys_acct)
        gridftp.config_gridftp_metrics_logging()

        if os.path.exists("/usr/sbin/globus-gridftp-server"):
            esg_property_manager.set_property("gridftp_app_home", "/usr/sbin/globus-gridftp-server")

    elif config_type == "gateway":
        print "*******************************"
        print "Setting up The ESGF Globus MyProxy Services"
        print "*******************************"

        _install_globus(config_type)
        myproxy.setup_gcs_id("firstrun")
        myproxy.config_myproxy_server(globus_location)
    else:
        print "You must provide a configuration type arg [datanode | gateway]"
        return


def start_globus_services(config_type):
    print "Starting Globus services for {}".format(config_type)

    if config_type == "datanode":
        gridftp.start_gridftp_server()
        esg_property_manager.set_property("gridftp_endpoint", "gsiftp://{}".format(esg_functions.get_esgf_host()))
    elif config_type == "gateway":
        myproxy.start_myproxy_server()
    else:
        print "You must provide a configuration type arg [datanode | gateway]"
        return

def stop_globus_services(config_type):
    '''Stop globus'''
    print "stop_globus_services for {}".format(config_type)

    if config_type == "datanode":
        gridftp.stop_gridftp_server()
    elif config_type == "gateway":
        myproxy.stop_myproxy_server()
    else:
        print "You must provide a configuration type arg [datanode | gateway]"
        return

def check_for_existing_globus_rpm_packages():
    '''Check if globus rpm is already installed'''
    rpm_packages = esg_functions.call_subprocess("rpm -qa")["stdout"].split("\n")
    globus_packages = [package for package in rpm_packages if "globus" in package]
    logger.debug("globus_packages: %s", globus_packages)
    return globus_packages

#--------------------------------------------------------------
# GLOBUS INSTALL (subset)
#--------------------------------------------------------------
# All methods below this point should be considered "private" functions

def install_globus_rpm():
    '''Install globus rpm repo'''
    globus_connect_server_file = "globus-connect-server-repo-latest.noarch.rpm"
    globus_connect_server_url = "http://toolkit.globus.org/ftppub/globus-connect-server/globus-connect-server-repo-latest.noarch.rpm"
    esg_functions.download_update(globus_connect_server_file, globus_connect_server_url)
    esg_functions.stream_subprocess_output("rpm --import http://www.globus.org/ftppub/globus-connect-server/RPM-GPG-KEY-Globus")
    esg_functions.stream_subprocess_output("rpm -i globus-connect-server-repo-latest.noarch.rpm")

def _install_globus(config_type):
    if config_type == "datanode":
        globus_type = "globus-connect-server-io"
    elif config_type == "gateway":
        globus_type = "globus-connect-server-id"
    else:
        print "You must provide a configuration type arg [datanode | gateway]"
        return

    globus_workdir = os.path.join(config["workdir"], "extra", "globus")
    pybash.mkdir_p(globus_workdir)
    current_mode = os.stat(globus_workdir)
    # chmod a+rw $globus_workdir
    os.chmod(globus_workdir, current_mode.st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    with pybash.pushd(globus_workdir):
        # Setup Globus RPM repo
        if not check_for_existing_globus_rpm_packages():
            install_globus_rpm()
        # Install Globus and ESGF RPMs
        esg_functions.stream_subprocess_output("yum -y install {}".format(globus_type))
        esg_functions.stream_subprocess_output("yum -y update {}".format(globus_type))

        if globus_type == "globus-connect-server-io":
            try:
                esg_functions.stream_subprocess_output("yum -y install --nogpgcheck globus-authz-esgsaml-callout globus-gaa globus-adq customgsiauthzinterface")
                esg_functions.stream_subprocess_output("yum -y update --nogpgcheck globus-authz-esgsaml-callout globus-gaa globus-adq customgsiauthzinterface")
            except SubprocessError, error:
                logger.error(error)
                pass
        else:
            #TODO: remove --nogpgcheck check when packages are properly signed
            esg_functions.stream_subprocess_output("yum -y install --nogpgcheck mhash pam-pgsql")
            esg_functions.stream_subprocess_output("yum -y update --nogpgcheck mhash pam-pgsql")




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

def globus_check_certificates():
    '''Check if globus certificates are valid'''
    print "globus_check_certificates..."
    my_cert = "/etc/grid-security/hostcert.pem"
    esg_cert_manager.check_cert_expiry(my_cert)
