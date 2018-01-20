import os
import re
import socket
import tld
import urlparse
import logging
import getpass
from esg_exceptions import UnverifiedScriptError
from distutils.spawn import find_executable
import esg_functions
import esg_property_manager
import esg_version_manager
import logging
import esg_bash2py
import esg_init
import yaml
import semver
import readline

# logger = logging.getLogger("esgf_logger" +"."+ __name__)
logger = logging.getLogger(__name__)

with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def _choose_fqdn(force_install=False):
    if esg_property_manager.get_property("esgf_host") and not force_install:
        logger.info("esgf_host = [%s]", esg_property_manager.get_property("esgf_host"))
        return
    else:
        default_host_name = socket.getfqdn()
        defaultdomain_regex = r"^\w+-*\w*\W*(.+)"
        defaultdomain = re.search(
            defaultdomain_regex, default_host_name).group(1)
        if not default_host_name:
            default_host_name = "localhost.localdomain"
        elif not defaultdomain:
            default_host_name = default_host_name + ".localdomain"

        default_host_name = raw_input("What is the fully qualified domain name of this node? [{default_host_name}]: ".format(
            default_host_name=default_host_name)) or default_host_name
        esgf_host = default_host_name
        logger.info("esgf_host = [%s]", esgf_host)
        esg_property_manager.write_as_property("esgf_host", esgf_host)

def _choose_admin_password(password_file=config["esgf_secret_file"]):
    '''Sets the ESGF password that is stored in /esg/config/.esgf_pass'''
    if esg_functions.get_security_admin_password():
        return

    while True:
        password_input = getpass.getpass(
            "What is the admin password to use for this installation? (alpha-numeric only): ")
        if not esg_functions.is_valid_password(password_input):
            continue

        password_input_confirmation = getpass.getpass(
            "Please re-enter password to confirm: ")

        if esg_functions.confirm_password(password_input, password_input_confirmation):
            esg_functions.set_security_admin_password(password_input)
            esg_functions.set_java_keystore_password(password_input)
            break

def _choose_organization_name(force_install=False):
    '''Choose the organization name for the installation'''
    if esg_property_manager.get_property("esg_root_id") and not force_install:
        logger.info("esg_root_id = [%s]", esg_property_manager.get_property("esg_root_id"))
        return

    elif force_install:
        try:
            default_org_name = tld.get_tld(
                "http://" + socket.gethostname(), as_object=True).domain
        except tld.exceptions.TldDomainNotFound, error:
            logger.exception("Could not find top level domain for %s.", socket.gethostname())
            default_org_name = "llnl"
        while True:
            org_name_input = raw_input("What is the name of your organization? [{default_org_name}]: ".format(default_org_name=default_org_name)) or default_org_name
            org_name_input.replace("", "_")
            esg_property_manager.write_as_property("esg_root_id", org_name_input)
            break

def _choose_node_short_name(force_install=False):
    '''Choose the short name for the node installation'''
    if esg_property_manager.get_property("node_short_name") and not force_install:
        logger.info("node_short_name = [%s]", esg_property_manager.get_property("node_short_name"))
        return
    else:
        node_short_name_input = raw_input("Please give this node a \"short\" name [{node_short_name}]: ".format(node_short_name=None)) or None
        node_short_name_input.replace("", "_")
        esg_property_manager.write_as_property(
            "node_short_name", node_short_name_input)


def _choose_node_long_name(force_install=False):
    if esg_property_manager.get_property("node_long_name") and not force_install:
        logger.info("node_long_name = [%s]", esg_property_manager.get_property("node_long_name"))
        return

    else:
        node_long_name_input = raw_input("Please give this node a more descriptive \"long\" name [{node_long_name}]: ".format(
            node_long_name=None)) or None
        esg_property_manager.write_as_property(
            "node_long_name", node_long_name_input)

def _choose_node_namespace(force_install=False):
    if esg_property_manager.get_property("node_namespace") and not force_install:
        logger.info("node_namespace = [%s]", esg_property_manager.get_property("node_namespace"))
        return
    else:
        try:
            top_level_domain = tld.get_tld(
                "http://" + socket.gethostname(), as_object=True)
            domain = top_level_domain.domain
            suffix = top_level_domain.suffix
            default_node_namespace = suffix + "." + domain
        except tld.exceptions.TldDomainNotFound:
            top_level_domain = None
            default_node_namespace = None
        while True:
            node_namespace_input = raw_input("What is the namespace to use for this node? (set to your reverse fqdn - Ex: \"gov.llnl\") [{default_node_namespace}]: ".format(
                default_node_namespace=default_node_namespace)) or default_node_namespace
            namespace_pattern_requirement = re.compile("(\w+.{1}\w+)$")
            if not namespace_pattern_requirement.match(node_namespace_input):
                print "Namespace entered is not in a valid format.  Valid format is [suffix].[domain].  Example: gov.llnl"
                continue
            else:
                esg_property_manager.write_as_property(
                    "node_namespace", node_namespace_input)
                break

def _choose_node_peer_group(force_install=False):
    if esg_property_manager.get_property("node_peer_group") and not force_install:
        logger.info("node_peer_group = [%s]", esg_property_manager.get_property("node_peer_group"))
        return
    else:
        while True:
            node_peer_group_input = raw_input(
                "What peer group(s) will this node participate in? (esgf-test|esgf-prod|esgf-dev)[{node_peer_group}]: \nOnly choose esgf-test for test federation install or esgf-prod for production installation.  Otherwise choose esgf-dev.".format(node_peer_group="esgf-dev"))\
                or "esgf-dev"
            if node_peer_group_input.strip() not in ["esgf-test", "esgf-prod", "esgf-dev"]:
                print "Invalid Selection: {node_peer_group_input}".format(node_peer_group_input=node_peer_group_input)
                print "Please choose either esgf-test, esgf-dev, or esgf-prod"
                continue
            else:
                esg_property_manager.write_as_property(
                    "node_peer_group", node_peer_group_input)
                break

def _choose_esgf_index_peer(force_install=False):
    if esg_property_manager.get_property("esgf_index_peer") and not force_install:
        logger.info("esgf_index_peer = [%s]", esg_property_manager.get_property("esgf_index_peer"))
        return
    else:
        default_esgf_index_peer = socket.getfqdn()
        esgf_index_peer_input = raw_input("What is the hostname of the node do you plan to publish to? [{default_esgf_index_peer}]: ".format(
            default_esgf_index_peer=default_esgf_index_peer)) or default_esgf_index_peer
        esg_property_manager.write_as_property(
            "esgf_index_peer", esgf_index_peer_input)


def _choose_mail_admin_address(force_install=False):
    if esg_property_manager.get_property("mail_admin_address") and not force_install:
        logger.info("mail_admin_address = [%s]", esg_property_manager.get_property("mail_admin_address"))
        return
    else:
        mail_admin_address_input = raw_input(
            "What email address should notifications be sent as? [{mail_admin_address}]: ".format(mail_admin_address=esg_property_manager.get_property("mail_admin_address")))
        if mail_admin_address_input:
            esg_property_manager.write_as_property(
                "mail_admin_address", mail_admin_address_input)
        else:
            print " (The notification system will not be enabled without an email address)"

def _choose_publisher_db_user(force_install=False):
    '''Sets the name of the database user for the Publisher'''
    publisher_db_user = esg_property_manager.get_property("publisher_db_user")
    if publisher_db_user and not force_install:
        print "Found existing value for property publisher_db_user: {publisher_db_user}".format(publisher_db_user=publisher_db_user)
        logger.info("publisher_db_user: %s", publisher_db_user)
        return

    else:
        default_publisher_db_user = "esgcet"
        publisher_db_user_input = raw_input(
            "What is the (low privilege) db account for publisher? [{default_publisher_db_user}]: ".format(default_publisher_db_user=default_publisher_db_user)) or default_publisher_db_user
        esg_property_manager.write_as_property(
            "publisher_db_user", publisher_db_user_input)

def _choose_publisher_db_user_passwd(force_install=False):
    '''Choose the password for the publisher (esgcet) database user'''
    if esg_functions.get_publisher_password() and not force_install:
        if esg_functions.is_valid_password(esg_functions.get_publisher_password()):
            print "Using previously configured publisher DB password"
            return
        else:
            print "The current password is invalid.  Please set a new password"

    publisher_db_user = esg_property_manager.get_property("publisher_db_user") or "esgcet"

    while True:
        publisher_db_user_passwd_input = getpass.getpass(
            "What is the db password for publisher user ({publisher_db_user})?: ".format(publisher_db_user=publisher_db_user))
        if not esg_functions.is_valid_password(publisher_db_user_passwd_input):
            print "The password that was entered is invalid.  Please enter a different password."
            continue

        password_input_confirmation = getpass.getpass(
            "Please re-enter password to confirm: ")

        if esg_functions.confirm_password(publisher_db_user_passwd_input, password_input_confirmation):
            esg_functions.set_publisher_password(publisher_db_user_passwd_input)
            break

def initial_setup_questionnaire(force_install=False):
    print "-------------------------------------------------------"
    print 'Welcome to the ESGF Node installation program! :-)'
    print "-------------------------------------------------------"

    esg_bash2py.mkdir_p(config['esg_config_dir'])

    with esg_bash2py.pushd(config['esg_config_dir']):

        _choose_fqdn()

        _choose_admin_password()

        _choose_organization_name()
        _choose_node_short_name()
        _choose_node_long_name()
        _choose_node_namespace()
        _choose_node_peer_group()
        _choose_esgf_index_peer()
        _choose_mail_admin_address()

        _choose_publisher_db_user()
        _choose_publisher_db_user_passwd()

        os.chmod(config['pub_secret_file'], 0640)
        if "tomcat" not in esg_functions.get_group_list():
            esg_functions.add_unix_group(config["tomcat_group"])
        os.chown(config['esgf_secret_file'], config[
                 "installer_uid"], esg_functions.get_tomcat_group_id())

    return True
