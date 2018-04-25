'''
Tomcat Management Functions
'''
import os
import shutil
import grp
import pwd
import errno
import logging
import sys
import signal
from time import sleep
import yaml
import requests
import psutil
from lxml import etree
from clint.textui import progress
from esgf_utilities.esg_exceptions import SubprocessError
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_cert_manager

logger = logging.getLogger("esgf_logger" + "." + __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

TOMCAT_VERSION = "8.5.20"
CATALINA_HOME = "/usr/local/tomcat"


def check_tomcat_version():
    esg_functions.stream_subprocess_output("/usr/local/tomcat/bin/version.sh")


def download_tomcat():
    if os.path.isdir("/usr/local/tomcat"):
        print "Tomcat directory found."
        check_tomcat_version()
        if esg_property_manager.get_property("update.tomcat"):
            setup_tomcat_answer = esg_property_manager.get_property("update.tomcat")
        else:
            setup_tomcat_answer = raw_input(
                "Do you want to contine the Tomcat installation [y/N]: ") or "no"
        if setup_tomcat_answer.lower() in ["no", "n"]:
            return False

    tomcat_download_url = "http://archive.apache.org/dist/tomcat/tomcat-8/v8.5.20/bin/apache-tomcat-8.5.20.tar.gz"
    print "downloading Tomcat"
    r = requests.get(tomcat_download_url)
    tomcat_download_path = "/tmp/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(
        TOMCAT_VERSION=TOMCAT_VERSION)
    with open(tomcat_download_path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

    return True


def extract_tomcat_tarball(dest_dir="/usr/local"):
    with esg_bash2py.pushd(dest_dir):
        esg_functions.extract_tarball(
            "/tmp/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(TOMCAT_VERSION=TOMCAT_VERSION))

        # Create symlink
        create_symlink(TOMCAT_VERSION)
        try:
            os.remove(
                "/tmp/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(TOMCAT_VERSION=TOMCAT_VERSION))
        except OSError, error:
            print "error:", error
            pass


def create_symlink(TOMCAT_VERSION):
    esg_bash2py.symlink_force(
        "/usr/local/apache-tomcat-{TOMCAT_VERSION}".format(TOMCAT_VERSION=TOMCAT_VERSION), "/usr/local/tomcat")


def remove_example_webapps():
    '''remove Tomcat example applications'''
    with esg_bash2py.pushd("/usr/local/tomcat/webapps"):
        try:
            shutil.rmtree("docs")
            shutil.rmtree("examples")
            shutil.rmtree("host-manager")
            shutil.rmtree("manager")
        except OSError, error:
            if error.errno == errno.ENOENT:
                pass
            else:
                logger.exception()

def setup_root_app():
    try:
        if "REFRESH" in open("/usr/local/tomcat/webapps/ROOT/index.html").read():
            print "ROOT app in place.."
            return
    except IOError:
        print "Don't see ESGF ROOT web application"

    esg_functions.backup("/usr/local/tomcat/webapps/ROOT")


    print "*******************************"
    print "Setting up Apache Tomcat...(v{}) ROOT webapp".format(config["tomcat_version"])
    print "*******************************"

    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        esg_dist_url = esg_property_manager.get_property("esg.dist.url")
        root_app_dist_url = "{}/ROOT.tgz".format(esg_dist_url)
        esg_functions.download_update("ROOT.tgz", root_app_dist_url)

        esg_functions.extract_tarball("ROOT.tgz", "/usr/local/webapps")

        if os.path.exists("/usr/local/tomcat/webapps/esgf-node-manager"):
            shutil.copyfile("/usr/local/tomcat/webapps/ROOT/index.html", "/usr/local/tomcat/webapps/ROOT/index.html.nm")
        if os.path.exists("/usr/local/tomcat/webapps/esgf-web-fe"):
            shutil.copyfile("/usr/local/tomcat/webapps/ROOT/index.html", "/usr/local/tomcat/webapps/ROOT/index.html.fe")

        esg_functions.change_ownership_recursive("/usr/local/tomcat/webapps/ROOT", esg_functions.get_user_id("tomcat"), esg_functions.get_group_id("tomcat"))
        print "ROOT application \"installed\""


def copy_config_files():
    '''copy custom configuration'''
    '''server.xml: includes references to keystore, truststore in /esg/config/tomcat'''
    '''context.xml: increases the Tomcat cache to avoid flood of warning messages'''

    print "\n*******************************"
    print "Copying custom Tomcat config files"
    print "******************************* \n"
    try:
        # shutil.copyfile(os.path.join(current_directory, "tomcat_conf/server.xml"), "/usr/local/tomcat/conf/server.xml")
        shutil.copyfile(os.path.join(current_directory, "tomcat_conf/context.xml"), "/usr/local/tomcat/conf/context.xml")
        esg_bash2py.mkdir_p("/esg/config/tomcat")

        shutil.copyfile(os.path.join(current_directory, "certs/tomcat-users.xml"), "/esg/config/tomcat/tomcat-users.xml")
        tomcat_user_id = pwd.getpwnam("tomcat").pw_uid
        tomcat_group_id = grp.getgrnam("tomcat").gr_gid
        os.chown("/esg/config/tomcat/tomcat-users.xml", tomcat_user_id, tomcat_group_id)

        shutil.copy(os.path.join(current_directory, "tomcat_conf/setenv.sh"), os.path.join(CATALINA_HOME, "bin"))
    except OSError, error:
        print "Could not copy tomcat certs.", error
        logger.exception()
        sys.exit()

    # esg_cert_manager.main()


def create_tomcat_user():
    '''Create the Tomcat system user and user group'''
    print "\n*******************************"
    print "Creating Tomcat User"
    print "******************************* \n"

    if "tomcat" in esg_functions.get_user_list():
        logger.info("Tomcat user already exists")
        return

    if not "tomcat" in esg_functions.get_group_list():
        esg_functions.call_subprocess("groupadd tomcat")

    esg_functions.call_subprocess("useradd -s /sbin/nologin -g tomcat -d /usr/local/tomcat tomcat")
    tomcat_directory = "/usr/local/apache-tomcat-{TOMCAT_VERSION}".format(
        TOMCAT_VERSION=TOMCAT_VERSION)
    tomcat_user_id = pwd.getpwnam("tomcat").pw_uid
    tomcat_group_id = grp.getgrnam("tomcat").gr_gid
    esg_functions.change_ownership_recursive(tomcat_directory, tomcat_user_id, tomcat_group_id)

    os.chmod("/usr/local/tomcat/webapps", 0775)


def start_tomcat():
    print "\n*******************************"
    print "Attempting to start Tomcat"
    print "******************************* \n"
    start_process = esg_functions.call_subprocess("/usr/local/tomcat/bin/catalina.sh start")
    if start_process["returncode"] != 0:
        esg_functions.exit_with_error(start_process["stderr"])

    check_tomcat_status()


def stop_tomcat():
    try:
        tomcat_pid = open("/usr/local/tomcat/logs/catalina.pid", "r").read()
    except IOError:
        print "PID file not found.  Tomcat not running"
        return
    if psutil.pid_exists(int(tomcat_pid)):
        try:
            esg_functions.stream_subprocess_output("/usr/local/tomcat/bin/catalina.sh stop")
        except SubprocessError, error:
            logger.exception(error)
            logger.info("Stopping Tomcat with catalina.sh script failed. Attempting to kill process...")
            try:
                os.kill(int(tomcat_pid), signal.SIGKILL)
            except OSError, error:
                print "Could not kill process"
                esg_functions.exit_with_error(error)

    check_tomcat_status()


def restart_tomcat():
    print "\n*******************************"
    print "Restarting Tomcat"
    print "******************************* \n"
    stop_tomcat()
    print "Sleeping for 7 seconds to allow shutdown"
    sleep(7)
    start_tomcat()
    print "Sleeping for 25 seconds to allow Tomcat restart"
    sleep(25)


def check_tomcat_status():
    try:
        tomcat_pid = open("/usr/local/tomcat/logs/catalina.pid", "r").read()
        if psutil.pid_exists(int(tomcat_pid)):
            print "Tomcat is running"
            return tomcat_pid
        else:
            print "Tomcat stopped."
            return False
    except IOError:
        print "PID file not found.  Tomcat not running"


def run_tomcat_config_test():
    esg_functions.stream_subprocess_output("/usr/local/tomcat/bin/catalina.sh configtest")


def copy_credential_files(tomcat_install_config_dir):
    '''Copy Tomcat config files'''
    logger.debug("Moving credential files into node's tomcat configuration dir: %s",
                 config["tomcat_conf_dir"])
    tomcat_credential_files = [config["truststore_file"], config["keystore_file"], config["tomcat_users_file"],
                               os.path.join(tomcat_install_config_dir, "hostkey.pem")]

    for file_path in tomcat_credential_files:
        credential_file_name = esg_bash2py.trim_string_from_head(file_path)
        if os.path.exists(os.path.join(tomcat_install_config_dir, credential_file_name)) and not os.path.exists(file_path):
            try:
                shutil.move(os.path.join(tomcat_install_config_dir,
                                         credential_file_name), file_path)
            except OSError:
                logger.exception("Could not move file %s", credential_file_name)

    esgf_host = esg_functions.get_esgf_host()
    if os.path.exists(os.path.join(tomcat_install_config_dir, esgf_host + "-esg-node.csr")) and not os.path.exists(os.path.join(config["tomcat_conf_dir"], esgf_host + "-esg-node.csr")):
        shutil.move(os.path.join(tomcat_install_config_dir, esgf_host + "-esg-node.csr"),
                    os.path.join(config["tomcat_conf_dir"], esgf_host + "-esg-node.csr"))

    if os.path.exists(os.path.join(tomcat_install_config_dir, esgf_host + "-esg-node.pem")) and not os.path.exists(os.path.join(config["tomcat_conf_dir"], esgf_host + "-esg-node.pem")):
        shutil.move(os.path.join(tomcat_install_config_dir, esgf_host + "-esg-node.pem"),
                    os.path.join(config["tomcat_conf_dir"], esgf_host + "-esg-node.pem"))


def check_server_xml():
    '''Check the Tomcat server.xml file for the explicit Realm specification needed.'''
    # Be sure that the server.xml file contains the explicit Realm specification needed.
    server_xml_path = os.path.join(config["tomcat_install_dir"], "conf", "server.xml")
    tree = etree.parse(server_xml_path)
    root = tree.getroot()
    realm_element = root.find(".//Realm")
    if realm_element:
        return True


def download_server_config_file(esg_dist_url):
    server_xml_url = "{esg_dist_url}/externals/bootstrap/node.server.xml-v{tomcat_major_version}".format(
        esg_dist_url=esg_dist_url, tomcat_major_version=config['tomcat_major_version'].strip("''"))
    esg_functions.download_update(os.path.join(
        config["tomcat_install_dir"], "conf", "server.xml"), server_xml_url)


def migrate_tomcat_credentials_to_esgf():
    '''
    Move selected config files into esgf tomcat's config dir (certificate et al)
    Ex: /esg/config/tomcat
    -rw-r--r-- 1 tomcat tomcat 181779 Apr 22 19:44 esg-truststore.ts
    -r-------- 1 tomcat tomcat    887 Apr 22 19:32 hostkey.pem
    -rw-r--r-- 1 tomcat tomcat   1276 Apr 22 19:32 keystore-tomcat
    -rw-r--r-- 1 tomcat tomcat    590 Apr 22 19:32 pcmdi11.llnl.gov-esg-node.csr
    -rw-r--r-- 1 tomcat tomcat    733 Apr 22 19:32 pcmdi11.llnl.gov-esg-node.pem
    -rw-r--r-- 1 tomcat tomcat    295 Apr 22 19:42 tomcat-users.xml
    Only called when migration conditions are present.
    '''
    tomcat_install_config_dir = os.path.join(config["tomcat_install_dir"], "conf")

    if tomcat_install_config_dir != config["tomcat_conf_dir"]:
        if not os.path.exists(config["tomcat_conf_dir"]):
            esg_bash2py.mkdir_p(config["tomcat_conf_dir"])

        esg_functions.backup(tomcat_install_config_dir)

        copy_credential_files(tomcat_install_config_dir)

        os.chown(config["tomcat_conf_dir"], esg_functions.get_user_id(
            "tomcat"), esg_functions.get_group_id("tomcat"))

        if not check_server_xml():
            esg_dist_url = esg_property_manager.get_property("esg.dist.url")
            download_server_config_file(esg_dist_url)

        # SET the server.xml variables to contain proper values
        edit_server_xml()


def edit_server_xml():
    '''Edit the placeholder values in the Tomcat server.xml configuration file'''

    logger.debug("Editing %s/conf/server.xml accordingly...", config["tomcat_install_dir"])
    keystore_password = esg_functions.get_java_keystore_password()

    xml_file = os.path.join(config["tomcat_install_dir"], "conf", "server.xml")
    xml_file_output = '{}_out.xml'.format(os.path.splitext(xml_file)[0])

    parser = etree.XMLParser(remove_comments=False)
    tree = etree.parse(xml_file, parser)
    root = tree.getroot()

    for param in root.iter():
        if param.tag == "Resource" or param.tag == "Realm":
            replaced_pathname = param.get("pathname").replace(
                "@@tomcat_users_file@@", config["tomcat_users_file"])
            param.set("pathname", replaced_pathname)
        if param.tag == "Connector":
            replaced_fqdn = param.get("proxyName").replace(
                "placeholder.fqdn", esg_functions.get_esgf_host())
            param.set("proxyName", replaced_fqdn)

            replaced_truststore_file = param.get("truststoreFile").replace(
                "@@truststore_file@@", config["truststore_file"])
            param.set("truststoreFile", replaced_truststore_file)

            replaced_truststore_pass = param.get("truststorePass").replace(
                "@@truststore_password@@", config["truststore_password"])
            param.set("truststorePass", replaced_truststore_pass)

            replaced_key_alias = param.get("keyAlias").replace(
                "@@keystore_alias@@", config["keystore_alias"])
            param.set("keyAlias", replaced_key_alias)

            replaced_keystore_file = param.get("keystoreFile").replace(
                "@@keystore_file@@", config["keystore_file"])
            param.set("keystoreFile", replaced_keystore_file)

            replaced_keystore_pass = param.get("keystorePass").replace(
                "@@keystore_password@@", keystore_password)
            param.set("keystorePass", replaced_keystore_pass)

    tree.write(xml_file_output)


def write_tomcat_env():
    esg_property_manager.set_property("CATALINA_HOME", "export CATALINA_HOME={}".format(config["tomcat_install_dir"]), config_file=config["envfile"], section_name="esgf.env")
    esg_property_manager.set_property("PATH_with_tomcat", os.environ["PATH"]+":/usr/local/tomcat/bin")

def write_tomcat_install_log():
    esg_functions.write_to_install_manifest("tomcat", config["tomcat_install_dir"], TOMCAT_VERSION)
    esg_property_manager.set_property("tomcat.install.dir", config["tomcat_install_dir"])
    esg_property_manager.set_property("esgf.http.port", "80")
    esg_property_manager.set_property("esgf.https.port", "443")

def get_tomcat_ports():
    parser = etree.XMLParser(remove_comments=False)
    tree = etree.parse(base/tomcat_conf/server.xml, parser)
    root = tree.getroot()
    ports = []

    for param in root.iter():
        if param.tag == "Connector":
            ports.append(param.get("port"))
    return ports


def tomcat_port_check():
    '''Test accessibility of tomcat ports listed in the server.xml config file'''
    tomcat_ports = get_tomcat_ports()

    failed_connections = []
    for port in tomcat_ports:
        if port == "8223":
            continue

        if port == "8443":
            protocol = "https"
        else:
            protocol = "http"

        status_code = requests.get("{}://localhost:{}".format(protocol, port)).status_code
        if status_code != "200":
            #We only care about reporting a failure for ports below 1024
            #specifically 80 (http) and 443 (https)
            if int(port) < 1024:
                failed_connections.append(port)

    if failed_connections:
        print "Connections failed on the following ports: {}".format(", ".join(failed_connections))
        return False

    print "Passed Tomcat port check"
    return True



def setup_tomcat_logrotate():
    '''If there is no logrotate file ${tomcat_logrotate_file} then create one
    default is to cut files after 512M up to 20 times (10G of logs)
    No file older than year should be kept.'''
    if not os.path.exists("/usr/sbin/logrotate"):
        print "Not able to find logrotate here [/usr/local/logrotate]"
        return False

    log_rot_size = "512M"
    log_rot_num_files = "20"
    tomcat_logrotate_file = "/etc/logrotate.d/esgf_tomcat"

    if not os.path.exists("/usr/local/tomcat/logs"):
        print "Sorry, could not find tomcat log dir"
        return False

    if not os.path.exists(tomcat_logrotate_file):
        print "Installing tomcat log rotation... [{}]".format(tomcat_logrotate_file)
        with open(tomcat_logrotate_file, "w") as logrotate_file:
            logrotate_file.write('"/usr/local/tomcat/logs/catalina.out" /usr/local/tomcat/logs/catalina.err {\n')
            logrotate_file.write('copytruncate\n')
            logrotate_file.write('size {log_rot_size}\n'.format(log_rot_size=log_rot_size))
            logrotate_file.write('rotate {log_rot_num_files}\n'.format(log_rot_num_files=log_rot_num_files))
            logrotate_file.write('maxage 365\n')
            logrotate_file.write('compress\n')
            logrotate_file.write('missingok\n')
            logrotate_file.write('create 0644 tomcat tomcat\n')

        os.chmod(tomcat_logrotate_file, 0644)

    tomcat_user = esg_functions.get_user_id("tomcat")
    tomcat_group = esg_functions.get_group_id("tomcat")

    if not os.path.exists("/usr/local/tomcat/logs/catalina.out"):
        print "Creating /usr/local/tomcat/logs/catalina.out"
        esg_bash2py.touch("/usr/local/tomcat/logs/catalina.out")
        os.chmod("/usr/local/tomcat/logs/catalina.out", 0644)
        os.chown("/usr/local/tomcat/logs/catalina.out", tomcat_user, tomcat_group)


    if not os.path.exists("/usr/local/tomcat/logs/catalina.err"):
        print "Creating /usr/local/tomcat/logs/catalina.err"
        esg_bash2py.touch("/usr/local/tomcat/logs/catalina.err")
        os.chmod("/usr/local/tomcat/logs/catalina.err", 0644)
        os.chown("/usr/local/tomcat/logs/catalina.err", tomcat_user, tomcat_group)

    if not os.path.exists("/etc/cron.daily/logrotate"):
        print "WARNING: Not able to find script [/etc/cron.daily/logrotate]"
        return False


def configure_tomcat():
    print "*******************************"
    print "Configuring Tomcat... (for Node Manager)"
    print "*******************************"

    setup_tomcat_logrotate()

    with esg_bash2py.pushd("/usr/local/tomcat/conf"):
        # Get server.xml
        if not os.path.exists("server.xml"):
            shutil.copyfile(os.path.join(current_directory, "tomcat_conf/server.xml"), "/usr/local/tomcat/conf/server.xml")
            tomcat_user = esg_functions.get_user_id("tomcat")
            tomcat_group = esg_functions.get_group_id("tomcat")
            os.chmod("/usr/local/tomcat/conf/server.xml", 0600)
            os.chown("/usr/local/tomcat/conf/server.xml", tomcat_user, tomcat_group)

        #Find or create keystore file
        if os.path.exists(config["keystore_file"]):
            print "Found existing keystore file {}".format(config["keystore_file"])
        else:
            print "creating keystore... "
            #create a keystore with a self-signed cert
            distinguished_name = "CN={esgf_host}".format(esgf_host=esg_functions.get_esgf_host())

            #if previous keystore is found; backup
            esg_cert_manager.backup_previous_keystore(config["keystore_file"])

            #-------------
            #Make empty keystore...
            #-------------
            keystore_password = esg_functions.get_java_keystore_password()
            esg_cert_manager.create_empty_java_keystore(config["keystore_file"], config["keystore_alias"], keystore_password, distinguished_name)


            #Setup temp CA
            esg_cert_manager.setup_temp_ca()

            #Fetch/Copy truststore to $tomcat_conf_dir
            if not os.path.exists(config["truststore_file"]):
                shutil.copyfile(os.path.join(os.path.dirname(__file__), "tomcat_certs/esg-truststore.ts"), config["truststore_file"])

            edit_server_xml()

            esg_cert_manager.add_my_cert_to_truststore()

            esg_functions.change_ownership_recursive(config["tomcat_install_dir"], "tomcat", "tomcat")
            esg_functions.change_ownership_recursive(config["tomcat_conf_dir"], "tomcat", "tomcat")



def main():
    print "\n*******************************"
    print "Setting up Tomcat {TOMCAT_VERSION}".format(TOMCAT_VERSION=TOMCAT_VERSION)
    print "******************************* \n"
    if download_tomcat():
        extract_tomcat_tarball()
        create_tomcat_user()
        os.environ["CATALINA_PID"] = "/tmp/catalina.pid"
        copy_config_files()
        configure_tomcat()
        remove_example_webapps()
        setup_root_app()
        migrate_tomcat_credentials_to_esgf()
        start_tomcat()
        tomcat_port_check()
        write_tomcat_install_log()
        esg_cert_manager.check_for_commercial_ca()


if __name__ == '__main__':
    main()
