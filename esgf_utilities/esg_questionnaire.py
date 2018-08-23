import os
import re
import socket
import logging
import ConfigParser
import getpass
import tld
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import esg_property_manager
from esgf_utilities import pybash

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def _prompt(key, msg, default=None, validate=None):
    '''
        A function for prompting the user for a property value if the value does not already exist
        in the property file.
    '''
    try:
        logger.info("%s = %s", key, esg_property_manager.get_property(key))
    except ConfigParser.NoOptionError:
        if validate is None:
            new_value = raw_input("{} [{}]".format(msg, default)) or default
        else:
            is_valid = False
            while not is_valid:
                new_value = raw_input("{} [{}]".format(msg, default)) or default
                is_valid = validate(new_value)
        esg_property_manager.set_property(key, new_value)
    except ConfigParser.NoSectionError:
        raise

def _choose_fqdn():

    default_host_name = socket.getfqdn()
    defaultdomain_regex = r"^\w+-*\w*\W*(.+)"
    defaultdomain = re.search(
        defaultdomain_regex, default_host_name).group(1)
    if not default_host_name:
        default_host_name = "localhost.localdomain"
    elif not defaultdomain:
        default_host_name = default_host_name + ".localdomain"

    msg = "What is the fully qualified domain name of this node?"
    key = "esgf.host"
    _prompt(key, msg, default=default_host_name)


def _choose_organization_name():
    '''Choose the organization name for the installation'''

    try:
        default_org_name = tld.get_tld("http://" + socket.gethostname(), as_object=True).domain
    except tld.exceptions.TldDomainNotFound:
        logger.exception("Could not find top level domain for %s.", socket.gethostname())
        default_org_name = "llnl"

    msg = "What is the name of your organization?"
    key = "esg.org.name"
    _prompt(key, msg, default=default_org_name)
    #NOTE Not sure what this is about, maybe meant to switch the arguments
    # Does not edit in place, returns a new string:
    #org_name_input.replace("", "_")
    # --> org_name_input = org_name_input.replace("_", "") ?
    # The same pattern occurs in the next two functions

def _choose_node_short_name():
    '''Choose the short name for the node installation'''

    msg = "Please give this node a \"short\" name"
    key = "node.short.name"
    _prompt(key, msg)

def _choose_node_long_name():

    msg = "Please give this node a \"long\" name"
    key = "node.long.name"
    _prompt(key, msg)

def _choose_node_namespace():

    try:
        top_level_domain = tld.get_tld("http://" + socket.gethostname(), as_object=True)
        domain = top_level_domain.domain
        suffix = top_level_domain.suffix
        default_node_namespace = suffix + "." + domain
    except tld.exceptions.TldDomainNotFound:
        top_level_domain = None
        default_node_namespace = None

    namespace_pattern_requirement = re.compile(r"(\w+.{1}\w+)$")
    def validate(node_namespace_input):
        ''' Validates node namespace input'''
        if not namespace_pattern_requirement.match(node_namespace_input):
            print "Namespace entered is not in a valid format. Valid format is [suffix].[domain]."
            return False
        return True

    msg = "What is the namespace for this node? (set to your reverse fqdn - Ex: \"gov.llnl\")"
    key = "node.namespace"
    _prompt(key, msg, default=default_node_namespace, validate=validate)


def _choose_node_peer_group():

    def validate(node_peer_group_input):
        ''' Validates node peer group input '''
        if node_peer_group_input.strip() not in ["esgf-test", "esgf-prod", "esgf-dev"]:
            print "Invalid Selection: {}".format(node_peer_group_input)
            print "Please choose either esgf-test, esgf-dev, or esgf-prod"
            return False
        return True
    #NOTE What is the exact meaning of the different options here?
    msg = "What peer group(s) will this node participate in?"
    msg += " Only choose esgf-test for test install or esgf-prod for production installation."
    msg += " Otherwise choose esgf-dev. (esgf-test|esgf-prod|esgf-dev)"
    key = "node.peer.group"
    _prompt(key, msg, default="esgf-dev", validate=validate)


def _choose_esgf_index_peer():

    default_esgf_index_peer = socket.getfqdn()
    msg = "What is the hostname of the node do you plan to publish to?"
    key = "esgf.index.peer"
    _prompt(key, msg, default=default_esgf_index_peer)


def _choose_mail_admin_address():

    msg = "What email address should notifications be sent as?"
    msg += " (The notification system will not be enabled without an email address)"
    key = "mail.admin.address"
    _prompt(key, msg)


def _choose_publisher_db_user(force_install=False):
    '''Sets the name of the database user for the Publisher'''

    msg = "What is the (low privilege) db account for publisher?"
    key = "publisher.db.user"
    _prompt(key, msg, default="esgcet")


def _choose_publisher_db_user_passwd(force_install=False):
    '''Choose the password for the publisher (esgcet) database user'''
    if esg_functions.get_publisher_password() and not force_install:
        if esg_functions.is_valid_password(esg_functions.get_publisher_password()):
            print "Using previously configured publisher DB password"
            return
        else:
            print "The current password is invalid.  Please set a new password"

    publisher_db_user = esg_property_manager.get_property("publisher.db.user") or "esgcet"

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

def initial_setup_questionnaire(force_install=False):
    print "-------------------------------------------------------"
    print 'Welcome to the ESGF Node installation program! :-)'
    print "-------------------------------------------------------"

    pybash.mkdir_p(config['esg_config_dir'])

    with pybash.pushd(config['esg_config_dir']):

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
