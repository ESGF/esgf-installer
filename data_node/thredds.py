"""Thredds Module."""
import os
import shutil
import logging
import getpass
import ConfigParser
import zipfile
import re
from distutils.dir_util import copy_tree
import requests
import yaml
from lxml import etree
from clint.textui import progress
from esgf_utilities import esg_functions
from esgf_utilities import pybash
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_truststore_manager
from base import esg_tomcat_manager, esg_postgres
from esgf_utilities.esg_env_manager import EnvWriter
from plumbum.commands import ProcessExecutionError


logger = logging.getLogger("esgf_logger" + "." + __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def check_thredds_version():
    """Check the MANIFEST.MF file for the Thredds version."""
    with open("/usr/local/tomcat/webapps/thredds/META-INF/MANIFEST.MF", "r") as manifest_file:
        contents = manifest_file.readlines()
        matcher = re.compile("Implementation-Version.*")
        results_list = filter(matcher.match, contents)
        if results_list:
            version_number = results_list[0].split(":")[1].strip().split("-")[0]
            logger.debug("(Thredds version %s)", version_number)
            return version_number
        else:
            print "Thredds not found on system."


def download_thredds_war(thredds_url):
    """Download thredds war file from thredds_url."""
    print "\n*******************************"
    print "Downloading Thredds war file"
    print "******************************* \n"

    response = requests.get(thredds_url, stream=True)
    path = '/usr/local/tomcat/webapps/thredds/thredds.war'
    with open(path, 'wb') as thredds_war:
        total_length = int(response.headers.get('content-length'))
        for chunk in progress.bar(response.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                thredds_war.write(chunk)
                thredds_war.flush()


def create_password_hash(tomcat_user_password):
    """Create a hash for a Tomcat user's password using Tomcat's digest.sh script."""
    password_hash = esg_functions.call_subprocess("/usr/local/tomcat/bin/digest.sh -a SHA {tomcat_user_password}".format(tomcat_user_password=tomcat_user_password))
    return password_hash["stdout"].split(":")[1].strip()


def update_tomcat_users_file(tomcat_username, password_hash, tomcat_users_file=config["tomcat_users_file"]):
    """Add a new user to the tomcat-users.xml file."""
    tree = etree.parse(tomcat_users_file)
    root = tree.getroot()
    updated_dnode_user = False
    for param in root.iter():
        if param == "user" and param.get("username") == "dnode_user":
            param.set("password", password_hash)
            param.set("roles", "tdrAdmin,tdsConfig")
            updated_dnode_user = True

    if not updated_dnode_user:
        new_user = etree.SubElement(root, "user")
        new_user.set("username", tomcat_username)
        new_user.set("password", password_hash)
        new_user.set("roles", "tdrAdmin,tdsConfig")

    tree.write(open(tomcat_users_file, "w"), pretty_print=True, encoding='utf-8', xml_declaration=True)


def add_tomcat_user():
    """Add a user to the default Tomcat user database (tomcat-users.xml) for container-managed authentication."""
    print "Create user credentials\n"
    try:
        tomcat_username = esg_property_manager.get_property("tomcat.user")
    except ConfigParser.NoOptionError:
        default_user = "dnode_user"
        tomcat_username = raw_input("Please enter username for tomcat [{default_user}]:  ".format(default_user=default_user)) or default_user

    valid_password = False
    while not valid_password:
        tomcat_user_password = esg_functions.get_security_admin_password()
        if not tomcat_user_password:
            tomcat_user_password = getpass.getpass("Please enter password for user, \"{tomcat_username}\" [********]:   ".format(tomcat_username=tomcat_username))

        if esg_functions.is_valid_password(tomcat_user_password):
            valid_password = True

    password_hash = create_password_hash(tomcat_user_password)

    update_tomcat_users_file(tomcat_username, password_hash)


def get_idp_peer_from_config():
    """Parse the config file to get the IDP peer."""
    try:
        esgf_idp_peer = esg_property_manager.get_property("esgf.idp.peer")
    except ConfigParser.NoOptionError:
        default_idp_peer = esg_functions.get_esgf_host()
        esgf_idp_peer = raw_input("Please specify your IDP peer node's FQDN [{}]: ".format(default_idp_peer)) or default_idp_peer

    return esgf_idp_peer


def select_idp_peer(esgf_idp_peer=None):
    """Set the node's IDP peerself.

    Called during setup_tds or directly by --set-idp-peer | --set-admin-peer flags
    """
    if not esgf_idp_peer:
        esgf_idp_peer = get_idp_peer_from_config()

    esgf_idp_peer_name = esgf_idp_peer.upper()

    myproxy_endpoint = esgf_idp_peer

    # If issues arise where sites are not using commercial certs from
    # trusted root certificate authorities, uncomment this and fix it
    # if esg_functions.get_esgf_host() != myproxy_endpoint:
    #    esg_truststore_manager.install_peer_node_cert(myproxy_endpoint)

    esg_property_manager.set_property("esgf_idp_peer_name", esgf_idp_peer_name)
    esg_property_manager.set_property("esgf_idp_peer", esgf_idp_peer)

    esg_property_manager.set_property("myproxy_endpoint", myproxy_endpoint)
    default_myproxy_port = 7512
    esg_property_manager.set_property("myproxy_port", default_myproxy_port)

    write_tds_env()


def write_tds_env():
    """Write thredds info to /etc/esg.env."""
    EnvWriter.export("ESGF_IDP_PEER_NAME", esg_property_manager.get_property("esgf_idp_peer_name"))
    EnvWriter.export("ESGF_IDP_PEER", esg_property_manager.get_property("esgf_idp_peer"))


def update_mail_admin_address():
    """Update mail_admin_address in threddsConfig.xml."""
    try:
        mail_admin_address = esg_property_manager.get_property("mail.admin.address")
    except ConfigParser.NoOptionError:
        return
    else:
        esg_functions.replace_string_in_file('/esg/content/thredds/threddsConfig.xml', "support@my.group", mail_admin_address)


def esgsetup_thredds():
    """Configure Thredds with esgsetup."""
    os.environ["UVCDAT_ANONYMOUS_LOG"] = "no"
    try:
        index_peer = esg_property_manager.get_property("esgf.index.peer")
    except ConfigParser.NoOptionError:
        # default peer is yourself
        default_peer = esg_functions.get_esgf_host()
        index_peer = raw_input("Enter the name of the Index Peer Node: [{}]".format(default_peer)) or default_peer

    security_admin_password = esg_functions.get_security_admin_password()
    esgsetup_options = ["--config", "--minimal-setup", "--thredds", "--publish", "--gateway", index_peer, "--thredds-password", security_admin_password]
    try:
        esg_functions.call_binary("esgsetup", esgsetup_options)
    except ProcessExecutionError, err:
        logger.error("esgsetup_thredds failed")
        logger.error(err)
        raise


def copy_public_directory():
    """HACK ALERT!! For some reason the public directory does not respect thredds' tds.context.root.path property.

    So have to manually move over this directory to avert server not starting! -gavin
    """
    content_dir = os.path.join("{thredds_content_dir}".format(thredds_content_dir=config["thredds_content_dir"]), "thredds")
    if not os.path.isdir(content_dir):
        pybash.mkdir_p(content_dir)
        public_dir = "{}/webapps/thredds/WEB-INF/altContent/startup/public".format(config["tomcat_install_dir"])
        try:
            copy_tree(public_dir, content_dir)
        except OSError:
            raise

        tomcat_user = esg_functions.get_user_id("tomcat")
        tomcat_group = esg_functions.get_group_id("tomcat")
        esg_functions.change_ownership_recursive(config["thredds_content_dir"], tomcat_user, tomcat_group)


def verify_thredds_credentials(thredds_ini_file="/esg/config/esgcet/esg.ini", tomcat_users_file=config["tomcat_users_file"]):
    """Verify that Thredds credentials in /esg/config/esgcet/esg.ini matches /esg/config/tomcat/tomcat-users.xml."""
    print "Inspecting tomcat... "
    tree = etree.parse(tomcat_users_file)
    root = tree.getroot()
    user_element = root.find("user")
    tomcat_username = user_element.get("username")
    tomcat_password_hash = user_element.get("password")

    print "Inspecting publisher... "
    thredds_username = esg_property_manager.get_property("thredds.username", property_file=thredds_ini_file, section_name="DEFAULT")
    thredds_password = esg_property_manager.get_property("thredds.password", property_file=thredds_ini_file, section_name="DEFAULT")
    thredds_password_hash = create_password_hash(thredds_password)

    print "Checking username... "
    logger.debug("tomcat_username: %s", tomcat_username)
    logger.debug("thredds_username: %s", thredds_username)
    if tomcat_username != thredds_username:
        print "The user_name property in {tomcat_users_file} doesn't match the user_name in {thredds_ini_file}".format(tomcat_users_file=tomcat_users_file, thredds_ini_file=thredds_ini_file)
        raise Exception

    print "Checking password... "
    logger.debug("tomcat_password_hash: %s", tomcat_password_hash)
    logger.debug("thredds_password_hash: %s", thredds_password_hash)
    if tomcat_password_hash != thredds_password_hash:
        print "The password property in {tomcat_users_file} doesn't match the password in {thredds_ini_file}".format(tomcat_users_file=tomcat_users_file, thredds_ini_file=thredds_ini_file)
        raise Exception

    print "Verified Thredds crendentials"
    return True


def copy_jar_files(esg_dist_url):
    """Copy jar files to Thredds.

    TDS jars necessary to support ESGF security filters
    some jars are retrieved from the ESGF repository
    other jars are copied from the unpacked ORP or NM distributions
    """
    esg_functions.download_update("/usr/local/tomcat/webapps/thredds/WEB-INF/lib/jdom-legacy-1.1.3.jar", "{esg_dist_url}/filters/jdom-legacy-1.1.3.jar".format(esg_dist_url=esg_dist_url))
    esg_functions.download_update("/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-httpclient-3.1.jar", "{esg_dist_url}/filters/commons-httpclient-3.1.jar".format(esg_dist_url=esg_dist_url))
    esg_functions.download_update("/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-lang-2.6.jar", "{esg_dist_url}/filters/commons-lang-2.6.jar".format(esg_dist_url=esg_dist_url))


def copy_xml_files():
    """Copy Thredds configuration xmls files into proper location on server."""
    shutil.copyfile(os.path.join(current_directory, "thredds_conf/tomcat-users.xml"), "{}/tomcat-users.xml".format(config["tomcat_conf_dir"]))

    pybash.mkdir_p("{tomcat_conf_dir}/Catalina/localhost".format(tomcat_conf_dir=config["tomcat_conf_dir"]))
    shutil.copyfile(os.path.join(current_directory, "thredds_conf/tomcat-thredds.xml"), "{}/Catalina/localhost/thredds.xml".format(config["tomcat_conf_dir"]))

    # TDS configuration root
    pybash.mkdir_p(os.path.join(config["thredds_content_dir"], "thredds"))
    # TDS memory configuration
    shutil.copyfile(os.path.join(current_directory, "thredds_conf/threddsConfig.xml"), "/esg/content/thredds/threddsConfig.xml")

    # ESGF root catalog
    shutil.copyfile(os.path.join(current_directory, "thredds_conf/catalog.xml"), "/esg/content/thredds/catalog.xml-esgcet")

    tomcat_user_id = esg_functions.get_user_id("tomcat")
    tomcat_group_id = esg_functions.get_group_id("tomcat")
    shutil.copyfile(os.path.join(current_directory, "thredds_conf/thredds.web.xml"), "/usr/local/tomcat/webapps/thredds/WEB-INF/web.xml")
    os.chown("/usr/local/tomcat/webapps/thredds/WEB-INF/web.xml", tomcat_user_id, tomcat_group_id)

    pybash.mkdir_p("/esg/content/thredds/esgcet")
    # TDS customized applicationContext.xml file with ESGF authorizer
    shutil.copyfile(os.path.join(current_directory, "thredds_conf/applicationContext.xml"), "/usr/local/tomcat/webapps/thredds/WEB-INF/applicationContext.xml")

    os.chown("{}/tomcat-users.xml".format(config["tomcat_conf_dir"]), tomcat_user_id, tomcat_group_id)

    # TDS customized logging (uses DEBUG)
    shutil.copyfile(os.path.join(current_directory, "thredds_conf/log4j2.xml"), "/usr/local/tomcat/webapps/thredds/WEB-INF/classes/log4j2.xml")


def write_tds_install_log():
    """Write thredds info to install manifest."""
    thredds_version = check_thredds_version()
    thredds_install_dir = os.path.join("{}".format(config["tomcat_install_dir"]), "webapps", "thredds")
    esg_functions.write_to_install_manifest("webapp:thredds", thredds_install_dir, thredds_version)

    esgf_host = esg_functions.get_esgf_host()
    esg_property_manager.set_property("thredds_service_endpoint", "http://{}/thredds".format(esgf_host))
    esg_property_manager.set_property("thredds_service_app_home", "{}/webapps/thredds".format(config["tomcat_install_dir"]))


def setup_thredds():
    """Install Thredds."""
    print "\n*******************************"
    print "Setting up Thredds"
    print "******************************* \n"

    if os.path.isdir("/usr/local/tomcat/webapps/thredds"):
        try:
            thredds_install = esg_property_manager.get_property("update.thredds")
        except ConfigParser.NoOptionError:
            thredds_install = raw_input("Existing Thredds installation found.  Do you want to continue with the Thredds installation [y/N]: ") or "no"

        if thredds_install.lower() in ["no", "n"]:
            print "Using existing Thredds installation.  Skipping setup."
            return

    esg_tomcat_manager.stop_tomcat()

    pybash.mkdir_p("/usr/local/tomcat/webapps/thredds")
    esg_dist_url = esg_property_manager.get_property("esg.dist.url")

    thredds_url = "{}/thredds/5.0/{}/thredds.war".format(esg_dist_url, config["tds_version"])
    download_thredds_war(thredds_url)

    with pybash.pushd("/usr/local/tomcat/webapps/thredds"):
        with zipfile.ZipFile("/usr/local/tomcat/webapps/thredds/thredds.war", 'r') as thredds_war_file:
            thredds_war_file.extractall()
        os.remove("thredds.war")
        tomcat_user_id = esg_functions.get_tomcat_user_id()
        tomcat_group_id = esg_functions.get_tomcat_group_id()
        esg_functions.change_ownership_recursive("/usr/local/tomcat/webapps/thredds", tomcat_user_id, tomcat_group_id)

    copy_xml_files()
    add_tomcat_user()

    select_idp_peer()
    copy_public_directory()
    update_mail_admin_address()

    copy_jar_files(esg_dist_url)

    # change ownership of content directory
    tomcat_user_id = esg_functions.get_tomcat_user_id()
    tomcat_group_id = esg_functions.get_tomcat_group_id()
    esg_functions.change_ownership_recursive("/esg/content/thredds/", tomcat_user_id, tomcat_group_id)

    # change ownership of source directory
    esg_functions.change_ownership_recursive("/usr/local/webapps/thredds", tomcat_user_id, tomcat_group_id)

    # restart tomcat to put modifications in effect.
    esg_tomcat_manager.stop_tomcat()
    esg_tomcat_manager.start_tomcat()
    esg_postgres.start_postgres()

    esgsetup_thredds()

    write_tds_install_log()

    # verify_thredds_credentials()

    # cleanup
    # shutil.rmtree("/usr/local/tomcat/webapps/esgf-node-manager/")


def tds_startup_hook():
    """Prepare thredds to start."""
    print "TDS (THREDDS) Startup Hook: Setting permissions... "
    esg_functions.change_ownership_recursive(config["thredds_content_dir"], uid=esg_functions.get_user_id("tomcat"))


def main():
    """Run Main function."""
    setup_thredds()


if __name__ == '__main__':
    main()
