import sys
import os
import subprocess
import re
import shutil
from OpenSSL import crypto
import logging
import requests
import socket
import platform
import netifaces
import tld
import grp
import shlex
import hashlib
from time import sleep
from esg_init import EsgInit
from esg_exceptions import UnprivilegedUserError, WrongOSError, UnverifiedScriptError
import esg_bash2py
import esg_functions
import esg_bootstrap
import esg_env_manager
import esg_property_manager
import esg_version_manager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = EsgInit()
use_local_files = 0
force_install = False


esg_functions_file = "/Users/hill119/Development/esgf-installer/esg-functions"
esg_init_file = "/Users/hill119/Development/esgf-installer/esg-init"


if os.path.isfile(esg_functions_file):
    esg_bash2py.source(esg_init_file)
    esg_bash2py.source(esg_functions_file)
else:
    print "file not found"


def check_prerequisites():
    '''
        Checking for what we expect to be on the system a-priori that we are not going to install or be responsible for
    '''
    print '''
        \033[01;31m
      EEEEEEEEEEEEEEEEEEEEEE   SSSSSSSSSSSSSSS         GGGGGGGGGGGGGFFFFFFFFFFFFFFFFFFFFFF
      E::::::::::::::::::::E SS:::::::::::::::S     GGG::::::::::::GF::::::::::::::::::::F
      E::::::::::::::::::::ES:::::SSSSSS::::::S   GG:::::::::::::::GF::::::::::::::::::::F
      EE::::::EEEEEEEEE::::ES:::::S     SSSSSSS  G:::::GGGGGGGG::::GFF::::::FFFFFFFFF::::F
        E:::::E       EEEEEES:::::S             G:::::G       GGGGGG  F:::::F       FFFFFF\033[0m
    \033[01;33m    E:::::E             S:::::S            G:::::G                F:::::F
        E::::::EEEEEEEEEE    S::::SSSS         G:::::G                F::::::FFFFFFFFFF
        E:::::::::::::::E     SS::::::SSSSS    G:::::G    GGGGGGGGGG  F:::::::::::::::F
        E:::::::::::::::E       SSS::::::::SS  G:::::G    G::::::::G  F:::::::::::::::F
        E::::::EEEEEEEEEE          SSSSSS::::S G:::::G    GGGGG::::G  F::::::FFFFFFFFFF\033[0m
    \033[01;32m    E:::::E                         S:::::SG:::::G        G::::G  F:::::F
        E:::::E       EEEEEE            S:::::S G:::::G       G::::G  F:::::F
      EE::::::EEEEEEEE:::::ESSSSSSS     S:::::S  G:::::GGGGGGGG::::GFF:::::::FF
      E::::::::::::::::::::ES::::::SSSSSS:::::S   GG:::::::::::::::GF::::::::FF
      E::::::::::::::::::::ES:::::::::::::::SS      GGG::::::GGG:::GF::::::::FF
      EEEEEEEEEEEEEEEEEEEEEE SSSSSSSSSSSSSSS           GGGGGG   GGGGFFFFFFFFFFF.llnl.gov
    \033[0m
    '''

    print "Checking that you have root privileges on %s... " % (socket.gethostname())
    root_check = os.geteuid()
    if root_check != 0:
        raise UnprivilegedUserError
    print "[OK]"

    #----------------------------------------
    print "Checking requisites... "

    # checking for OS, architecture, distribution and version

    print "Checking operating system....."
    release_version = re.search(
        "(centos|redhat)-(\S*)-", platform.platform()).groups()
    logger.debug("Release Version: %s", release_version)
    if "6" not in release_version[1]:
        raise WrongOSError
    else:
        print "Operating System = {OS} {version}".format(OS=release_version[0], version=release_version[1])
        print "[OK]"


def init_structure():

    if not os.path.isfile(config.config_dictionary["config_file"]):
        esg_bash2py.touch(config.config_dictionary["config_file"])

    config_check = 7
    directories_to_check = [config.config_dictionary["scripts_dir"], config.config_dictionary["esg_backup_dir"], config.config_dictionary["esg_tools_dir"],
                            config.config_dictionary[
                                "esg_log_dir"], config.esg_config_dir, config.config_dictionary["esg_etc_dir"],
                            config.config_dictionary["tomcat_conf_dir"]]
    for directory in directories_to_check:
        if not os.path.isdir(directory):
            try:
                os.makedirs(directory)
                config_check -= 1
            except OSError, e:
                if e.errno != 17:
                    raise
                sleep(1)
                pass
        else:
            config_check -= 1
    if config_check != 0:
        print "ERROR: checklist incomplete $([FAIL])"
        esg_functions.checked_done(1)
    else:
        print "checklist $([OK])"

    os.chmod(config.config_dictionary["esg_etc_dir"], 0777)

    if os.access(config.envfile, os.W_OK):
        write_paths()

    #--------------
    # Setup variables....
    #--------------

    check_for_my_ip()

    try:
        esgf_host = config.config_dictionary["esgf_host"]
    except KeyError:
        esgf_host = esg_property_manager.get_property("esgf_host")

    try:
        esgf_default_peer = config.config_dictionary["esgf_default_peer"]
    except KeyError:
        esgf_default_peer = esg_property_manager.get_property("esgf_default_peer")

    try:
        esgf_idp_peer_name = config.config_dictionary["esgf_idp_peer_name"]
    except KeyError:
        esgf_idp_peer_name = esg_property_manager.get_property("esgf_idp_peer_name")

    try:
        esgf_idp_peer = config.config_dictionary["esgf_idp_peer"]
    except KeyError:
        esgf_idp_peer = esg_property_manager.get_property("esgf_idp_peer")

    # logger.debug("trim_string_from_tail(esgf_idp_peer_name): %s",  esg_functions.trim_string_from_tail(esgf_idp_peer))
    if not esgf_idp_peer:
        myproxy_endpoint = None
    else:
        myproxy_endpoint = esg_bash2py.trim_string_from_tail(esgf_idp_peer)
    # re.search("/\w+", source)

    try:
        config.config_dictionary["myproxy_port"]
    except KeyError:
        myproxy_port = esg_bash2py.Expand.colonMinus(
            esg_property_manager.get_property("myproxy_port"), "7512")

    try:
        esg_root_id = config.config_dictionary["esg_root_id"]
    except KeyError:
        esg_root_id = esg_property_manager.get_property("esg_root_id")

    try:
        node_peer_group = config.config_dictionary["node_peer_group"]
    except KeyError:
        node_peer_group = esg_property_manager.get_property("node_peer_group")

    try:
        config.config_dictionary["node_short_name"]
    except KeyError:
        node_short_name = esg_property_manager.get_property("node_short_name")

    # NOTE: Calls to get_property must be made AFTER we touch the file ${config_file} to make sure it exists
    # this is actually an issue with dedup_properties that gets called in the
    # get_property function

    # Get the distinguished name from environment... if not, then esgf.properties... and finally this can be overwritten by the --dname option
    # Here node_dn is written in the /XX=yy/AAA=bb (macro->micro) scheme.
    # We transform it to dname which is written in the java style AAA=bb,
    # XX=yy (micro->macro) scheme using "standard2java_dn" function

    try:
        dname = config.config_dictionary["dname"]
    except KeyError:
        dname = esg_property_manager.get_property("dname")

    try:
        gridftp_config = config.config_dictionary["gridftp_config"]
    except KeyError:
        gridftp_config = esg_property_manager.get_property(
            "gridftp_config", "bdm end-user")

    try:
        publisher_config = config.config_dictionary["publisher_config"]
    except KeyError:
        publisher_config = esg_property_manager.get_property(
            "publisher_config", "esg.ini")

    try:
        publisher_home = config.config_dictionary["publisher_home"]
    except KeyError:
        publisher_home = esg_property_manager.get_property(
            "publisher_home", config.esg_config_dir + "/esgcet")

    # Sites can override default keystore_alias in esgf.properties (keystore.alias=)
    # config.config_dictionary["keystore_alias"] = esg_functions.get_property("keystore_alias")
    # logger.debug("keystore_alias in esg_setup: %s", config.config_dictionary["keystore_alias"])

    config.config_dictionary["ESGINI"] = os.path.join(
        publisher_home, publisher_config)

    return 0


def write_paths():
    config.config_dictionary["show_summary_latch"] += 1

    datafile = open(config.envfile, "a+")
    datafile.write("export ESGF_HOME=" + config.esg_root_dir + "\n")
    datafile.write("export ESG_USER_HOME=" +
                   config.config_dictionary["installer_home"] + "\n")
    datafile.write("export ESGF_INSTALL_WORKDIR=" +
                   config.config_dictionary["workdir"] + "\n")
    datafile.write("export ESGF_INSTALL_PREFIX=" +
                   config.install_prefix + "\n")
    datafile.write("export PATH=" + config.myPATH +
                   ":" + os.environ["PATH"] + "\n")
    datafile.write("export LD_LIBRARY_PATH=" + config.myLD_LIBRARY_PATH +
                   ":" + os.environ["LD_LIBRARY_PATH"] + "\n")
    datafile.truncate()
    datafile.close()

    esg_env_manager.deduplicate_settings_in_file(config.envfile)


def _select_ip_address():
    choice = int(raw_input(""))
    return choice


def _render_ip_address_menu(ip_addresses):
    print "Detected multiple IP addresses bound to this host...\n"
    print "Please select the IP address to use for this installation\n"
    print "\t-------------------------------------------\n"
    for index, ip in enumerate(ip_addresses.iteritems(), 1):
        print "\t %i) %s" % (index, ip)
    print "\t-------------------------------------------\n"


def check_for_my_ip(force_install=False):
    logger.debug("Checking for IP address(es)...")
    matched = 0
    my_ip_address = None
    eth0 = netifaces.ifaddresses(netifaces.interfaces()[1])
    ip_addresses = [ip["addr"] for ip in eth0[netifaces.AF_INET]]

    try:
        esgf_host_ip
    except NameError:
        esgf_host_ip = esg_property_manager.get_property("esgf_host_ip")

    if esgf_host_ip and not force_install:
        logger.info("Using IP: %s", esgf_host_ip)
        return 0

    # We want to make sure that the IP address we have in our config
    # matches one of the IPs that are associated with this host
    for ip in ip_addresses:
        if ip == esgf_host_ip:
            matched += 1

    if matched == 0:
        logger.info(
            "Configured host IP address does not match available IPs...")

    if not esgf_host_ip or force_install or matched == 0:
        if len(ip_addresses) > 1:
            # ask the user to choose...
            while True:
                _render_ip_address_menu(ip_addresses)
                default = 0
                choice = _select_ip_address() or default
                my_ip_address = ip_addresses[choice]
                logger.info("selected address -> %s", my_ip_address)
                break
        else:
            my_ip_address = ip_addresses[0]

    esg_property_manager.write_as_property("esgf_host_ip", my_ip_address)
    esgf_host_ip = esg_property_manager.get_property("esgf_host_ip")
    return esgf_host_ip


def _choose_fqdn(esgf_host):
    if not esgf_host or force_install:
        default_host_name = esgf_host or socket.getfqdn()
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
    else:
        logger.info("esgf_host = [%s]", esgf_host)
        esg_property_manager.write_as_property("esgf_host", esgf_host)


def _is_valid_password(password_input):
    if not password_input or not str.isalnum(password_input):
        print "Invalid password... "
        return False
    if not password_input or len(password_input) < 6:
        print "Sorry password must be at least six characters :-( "
        return False


def _confirm_password(password_input, password_confirmation):
    if password_confirmation == password_input:
        return True
    else:
        print "Sorry, values did not match"
        return False


def _update_admin_password_file(updated_password):
    try:
        security_admin_password_file = open(config.esgf_secret_file, 'w+')
        security_admin_password_file.write(updated_password)
    except IOError, error:
        logger.error(error)
    finally:
        security_admin_password_file.close()

    # Use the same password when creating the postgress account
    config.config_dictionary["pg_sys_acct_passwd"] = updated_password

# TODO: move this function to esg_functions


def _add_user_group(group_name):
    # TODO: Refactor by modifying the /etc/group and /etc/gshadow files; use
    # [max_list.gr_gid for max_list in group_list] to find max group id and
    # increment
    groupadd_command = ["/usr/sbin/groupadd", "-r", group_name]
    # groupadd_command = "/usr/sbin/groupadd -r {group_name}".format(group_name = group_name)
    try:
        groupadd_output = subprocess.check_output(groupadd_command, shell=True)
    except subprocess.CalledProcessError as error:
        logger.error(error)
        print "ERROR: *Could not add tomcat system group: %s" % (config.config_dictionary["tomcat_group"])
        # os.chdir(starting_directory)
        esg_functions.checked_done(1)


def _update_password_files_permissions():
    os.chmod(config.esgf_secret_file, 0640)

    try:
        tomcat_group_info = grp.getgrnam(
            config.config_dictionary["tomcat_group"])
    except KeyError:
        _add_user_group(config.config_dictionary["tomcat_group"])

    tomcat_group_id = tomcat_group_info.gr_id

    try:
        os.chown(config.esgf_secret_file, config.config_dictionary[
                 "installer_uid"], tomcat_group_id)
    except OSError, error:
        logger.error(error)

    if os.path.isfile(config.esgf_secret_file):
        os.chmod(config.esgf_secret_file, 0640)
        try:
            os.chown(config.esgf_secret_file, config.config_dictionary[
                     "installer_uid"], tomcat_group_id)
        except OSError, error:
            logger.error(error)

    if not os.path.isfile(config.pg_secret_file):
        esg_bash2py.touch(config.pg_secret_file)
        try:
            with open(config.pg_secret_file, "w") as secret_file:
                secret_file.write(config.config_dictionary[
                                  "pg_sys_acct_passwd"])
        except IOError, error:
            logger.error(error)
    else:
        os.chmod(config.pg_secret_file, 0640)
        try:
            os.chown(config.pg_secret_file, config.config_dictionary[
                     "installer_uid"], tomcat_group_id)
        except OSError, error:
            logger.error(error)


def _choose_admin_password():
    while True:
        password_input = raw_input(
            "What is the admin password to use for this installation? (alpha-numeric only)")

        security_admin_password = esg_functions.get_security_admin_password()
        if force_install and len(password_input) == 0 and len(security_admin_password) > 0:
            changed = False
            break
        if not _is_valid_password(password_input):
            continue
        if password_input:
            security_admin_password = password_input

        security_admin_password_confirmation = raw_input(
            "Please re-enter password to confirm: ")
        if _confirm_password(security_admin_password, security_admin_password_confirmation):
            changed = True
            break

    if changed is True:
        _update_admin_password_file(password_input)

    _update_password_files_permissions()


def _choose_organization_name():
    esg_root_id = esg_property_manager.get_property("esg_root_id")
    if not esg_root_id or force_install:
        while True:
            default_org_name = tld.get_tld(
                "http://" + socket.gethostname(), as_object=True).domain
            org_name_input = raw_input("What is the name of your organization? [{default_org_name}]: ", format(
                default_org_name=default_org_name)) or default_org_name
            org_name_input.replace("", "_")
            esg_property_manager.write_as_property("esg_root_id", esg_root_id)
            break
    else:
        logger.info("esg_root_id = [%s]", esg_root_id)


def _choose_node_short_name():
    node_short_name = esg_property_manager.get_property("node_short_name")
    if not node_short_name or force_install:
        while True:
            node_short_name_input = raw_input("Please give this node a \"short\" name [{node_short_name}]: ".format(
                node_short_name=node_short_name)) or node_short_name
            node_short_name_input.replace("", "_")
            esg_property_manager.write_as_property(
                "node_short_name", node_short_name_input)
            break
    else:
        logger.info("node_short_name = [%s]", node_short_name)


def _choose_node_long_name():
    node_long_name = esg_property_manager.get_property("node_long_name")
    if not node_long_name or force_install:
        while True:
            node_long_name_input = raw_input("Please give this node a more descriptive \"long\" name [{node_long_name}]: ".format(
                node_long_name=node_long_name)) or node_long_name
            esg_property_manager.write_as_property(
                "node_long_name", node_long_name_input)
            break
    else:
        logger.info("node_long_name = [%s]", node_long_name)


def _choose_node_namespace():
    node_namespace = esg_property_manager.get_property("node_namespace")
    if not node_namespace or force_install:
        top_level_domain = tld.get_tld(
            "http://" + socket.gethostname(), as_object=True)
        domain = top_level_domain.domain
        suffix = top_level_domain.suffix
        default_node_namespace = suffix + "." + domain
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
    else:
        logger.info("node_namespace = [%s]", node_namespace)


def _choose_node_peer_group():
    node_peer_group = esg_property_manager.get_property("node_peer_group")
    if not node_peer_group or force_install:
        try:
            node_peer_group
        except NameError:
            node_peer_group = "esgf-test"
        while True:
            node_peer_group_input = raw_input(
                "What peer group(s) will this node participate in? (esgf-test|esgf-prod) [{node_peer_group}]: ".format(node_peer_group=node_peer_group)) or node_peer_group
            if node_peer_group_input != "esgf-test" or node_peer_group_input != "esgf-prod":
                print "Invalid Selection: {node_peer_group_input}".format(node_peer_group_input=node_peer_group_input)
                print "Please choose either esgf-test or esgf-prod"
                continue
            else:
                esg_property_manager.write_as_property(
                    "node_peer_group", node_peer_group_input)
                break
    else:
        logger.info("node_peer_group = [%s]", node_peer_group)


def _choose_esgf_default_peer():
    esgf_default_peer = esg_property_manager.get_property("esgf_default_peer")
    if not esgf_default_peer or force_install:
        try:
            default_esgf_default_peer = esgf_host
        except NameError:
            default_esgf_default_peer = socket.getfqdn()

        esgf_default_peer_input = raw_input("What is the default peer to this node? [{default_esgf_default_peer}]: ".format(
            default_esgf_default_peer=default_esgf_default_peer)) or default_esgf_default_peer
        esg_property_manager.write_as_property(
            "esgf_default_peer", esgf_default_peer_input)
    else:
        logger.info("esgf_default_peer = [%s]", esgf_default_peer)


def _choose_esgf_index_peer():
    esgf_index_peer = esg_property_manager.get_property("esgf_index_peer")
    if not esgf_index_peer or force_install:
        default_esgf_index_peer = esgf_default_peer or esgf_host or socket.getfqdn()
        esgf_index_peer_input = raw_input("What is the hostname of the node do you plan to publish to? [{default_esgf_index_peer}]: ".format(
            default_esgf_index_peer=default_esgf_index_peer)) or default_esgf_index_peer
        esg_property_manager.write_as_property(
            "esgf_index_peer", esgf_index_peer_input)
    else:
        logger.info("esgf_index_peer = [%s]", esgf_index_peer)


def _choose_mail_admin_address():
    mail_admin_address = esg_property_manager.get_property("mail_admin_address")
    if not mail_admin_address or force_install:
        mail_admin_address_input = raw_input(
            "What email address should notifications be sent as? [{mail_admin_address}]: ".format(mail_admin_address=mail_admin_address))
        if mail_admin_address_input:
            esg_property_manager.write_as_property(
                "mail_admin_address", mail_admin_address_input)
        else:
            print " (The notification system will not be enabled without an email address)"
    else:
        logger.info("mail_admin_address = [%s]", mail_admin_address)


def _choose_publisher_db_user():
    default_publisher_db_user = None
    publisher_db_user = esg_property_manager.get_property("publisher_db_user")
    if not publisher_db_user or force_install:
        default_publisher_db_user = publisher_db_user or "esgcet"
        publisher_db_user_input = raw_input(
            "What is the (low priv) db account for publisher? [${default}]: ") or default_publisher_db_user
        esg_property_manager.write_as_property(
            "publisher_db_user", publisher_db_user_input)
    else:
        logger.info("publisher_db_user: %s", publisher_db_user)


def _choose_publisher_db_user_passwd():
    if not config.config_dictionary["publisher_db_user_passwd"] or force_install:
        publisher_db_user_passwd_input = raw_input(
            "What is the db password for publisher user ({publisher_db_user})?: ".format(publisher_db_user=publisher_db_user))
        if publisher_db_user_passwd_input:
            with open(config.pub_secret_file, "w") as secret_file:
                secret_file.write(publisher_db_user_passwd_input)

    if not os.path.isfile(config.pub_secret_file):
        esg_bash2py.touch(config.pub_secret_file)
        with open(config.pub_secret_file, "w") as secret_file:
            secret_file.write(config.config_dictionary[
                              "publisher_db_user_passwd"])


def initial_setup_questionnaire():
    print "-------------------------------------------------------"
    print 'Welcome to the ESGF Node installation program! :-)'

    esg_bash2py.mkdir_p(config.esg_config_dir)

    starting_directory = os.getcwd()

    os.chdir(config.esg_config_dir)

    esgf_host = esg_property_manager.get_property("esgf_host")
    _choose_fqdn(esgf_host)

    try:
        security_admin_password_file = open(config.esgf_secret_file, 'r')
        security_admin_password = security_admin_password_file.read()
    except IOError, error:
        logger.error(error)

    finally:
        security_admin_password_file.close()

    if not security_admin_password or force_install:
        _choose_admin_password()

    _choose_organization_name()
    _choose_node_short_name()
    _choose_node_long_name()
    _choose_node_namespace()
    _choose_node_peer_group()
    _choose_esgf_default_peer()
    _choose_esgf_index_peer()
    _choose_mail_admin_address()

    db_properties_dict = {"db_user": None, "db_host": None,
                          "db_port": None, "db_database": None, "db_managed": None}
    for key, value in db_properties_dict.items():
        db_properties_dict[key] = esg_property_manager.get_property(key)

    if not all(db_properties_dict) or force_install:
        _is_managed_db()
        _get_db_conn_str_questionnaire()
    else:
        if db_properties_dict["db_host"] == esgf_host or db_properties_dict["db_host"] == "localhost":
            print "db_connection_string = {db_user}@localhost".format(db_user=db_properties_dict["db_user"])
        else:
            connstring_ = "{db_user}@{db_host}:{db_port}/{db_database} [external = ${db_managed}]".format(db_user=db_properties_dict["db_user"],
                                                                                                          db_host=db_properties_dict[
                                                                                                              "db_host"],
                                                                                                          db_port=db_properties_dict[
                                                                                                              "db_port"],
                                                                                                          db_database=db_properties_dict[
                                                                                                              "db_database"],
                                                                                                          db_managed=db_properties_dict["db_managed"])

    _choose_publisher_db_user()
    _choose_publisher_db_user_passwd()

    os.chmod(config.pub_secret_file, 0640)
    tomcat_group_info = grp.getgrnam(
        config.config_dictionary["tomcat_group"])
    tomcat_group_id = tomcat_group_info[2]
    os.chown(config.esgf_secret_file, config.config_dictionary[
             "installer_uid"], tomcat_group_id)

    if db_properties_dict["db_host"] == db_properties_dict["db_host"] or db_host == "localhost":
        logger.info("db publisher connection string %s@localhost",
                    db_properties_dict["db_user"])
    else:
        logger.info("db publisher connection string %s@%s:%s/%s",
                    db_properties_dict["db_user"], db_host, db_port, db_database)

    esg_env_manager.deduplicate_properties(
        config.config_dictionary["config_file"])

    os.chdir(starting_directory)

    return True


def _get_db_conn_str_questionnaire():
    # postgresql://esgcet@localhost:5432/esgcet
    user_ = None
    host_ = None
    port_ = None
    dbname_ = None
    connstring_ = None
    valid_connection_string = None

    # Note the values referenced here should have been set by prior get_property *** calls
    # that sets these values in the script scope. (see the call in
    # questionnaire function - above)
    if not db_user or not db_host or not db_port or not db_database:
        if not db_host:
            if db_host == esgf_host or db_host == "localhost":
                connstring_ = "{db_user}@localhost"
            else:
                connstring_ = "{db_user}@{db_host}:{db_port}/{db_database}"
    while True:
        print "Please enter the database connection string..."
        print " (form: postgresql://[username]@[host]:[port]/esgcet)"
        db_managed = esg_property_manager.get_property("db_managed")
        #(if it is a not a force install and we are using a LOCAL (NOT MANAGED) database then db_managed == "no")
        if not connstring_ and db_managed != "yes" and not force_install:
            connstring_ = "dbsuper@localhost:5432/esgcet"
        db_connection_input = raw_input(
            "What is the database connection string? [postgresql://${connstring_}]: postgresql://".format(connstring_=connstring_)) or connstring_
        parsed_db_conn_string = urlparse.urlparse(db_connection_input)
        # result.path[1:] is database name
        if not parsed_db_conn_string.username or not parsed_db_conn_string.hostname or parsed_db_conn_string.port or parsed_db_conn_string.result.path[1:]:
            logger.error("ERROR: Incorrect connection string syntax or values")
            valid_connection_string = False
        else:
            valid_connection_string = True
            break
    logger.debug("user = %s", user_)
    logger.debug("host = %s", host_)
    logger.debug("port = %s", port_)
    logger.debug("database = %s", dbname_)

    # write vars to property file
    esg_functions.write_as_property("db_user", user_)
    esg_functions.write_as_property("db_host", host_)
    esg_functions.write_as_property("db_port", port_)
    esg_functions.write_as_property("db_database", dbname_)

    logger.debug("valid_connection_string: %s",  valid_connection_string)
    return valid_connection_string


def _is_managed_db():
    '''
        responds true (returns 0) if this IS intended to be a managed database
        is expecting the vars:
        ---- "db_host"
        ---- "esgf_host"
        to be set
        Define: managed - (true|0) this means NOT manipulated by this script but done by external means
        (hint prepend "externally" before managed to get the meaning - yes I find it confusing but Stephen likes this term :-))
        db_managed=no means that it is a LOCAL database. (I have to change this damn verbiage... what I get for following pasco-speak ;-).
    '''
    db_managed_default = None
    default_selection_output = None
    db_managed = esg_property_manager.get_property("db_managed")
    if not force_install:
        if db_managed == "yes":
            return True
        else:
            return False

    if not db_managed:
        logger.debug("esgf_host = %s", esgf_host)
        logger.debug("db_host = %s", db_host)

        # Try to come up with some "sensible" default value for the user...
        if db_host == esgf_host or db_host == "localhost" or not db_host:
            db_managed_default = "no"
            default_selection_output = "[y/N]:"
        else:
            db_managed_default = "yes"
            default_selection_output = "[Y/n]:"

        external_db_input = raw_input(
            "Is the database external to this node? " + default_selection_output)
        if not external_db_input:
            db_managed = db_managed_default
            esg_property_manager.write_as_property("db_managed", db_managed)
        else:
            if external_db_input.lower() == "y" or external_db_input.lower() == "yes":
                db_managed == "yes"
            else:
                db_managed == "no"
            esg_property_manager.write_as_property("db_managed", db_managed)
    else:
        logger.info("db_managed = [%s]", db_managed)

    if db_managed == "yes":
        print "Set to use externally \"managed\" database on host: {db_host}".format(db_host=db_host)
        return True
    else:
        logger.debug("(hmm... setting db_host to localhost)")
        # Note: if not managed and on the local machine... always use
        # "localhost"
        db_host = "localhost"
        return False


def install_prerequisites():
    '''
        Install prerequisite modules via yum
    '''
    print '''
    *******************************
    Installing prerequisites
    ******************************* 
    '''
    yum_remove_rpm_forge = subprocess.Popen(
        ["yum", "-y", "remove", "rpmforge-release"], stdout=subprocess.PIPE)
    esg_functions.stream_subprocess_output(yum_remove_rpm_forge)

    yum_install_epel = subprocess.Popen(
        ["yum", "-y", "install", "epel-release"], stdout=subprocess.PIPE)
    esg_functions.stream_subprocess_output(yum_install_epel)

    yum_install_list = ["yum", "-y", "install", "yum-plugin-priorities", "sqlite-devel", "freetype-devel", "git", "curl-devel",
                        "autoconf", "automake", "bison", "file", "flex", "gcc", "gcc-c++",
                        "gettext-devel", "libtool", "uuid-devel", "libuuid-devel", "libxml2",
                        "libxml2-devel", "libxslt", "libxslt-devel", "lsof", "make",
                        "openssl-devel", "pam-devel", "pax", "readline-devel", "tk-devel",
                        "wget", "zlib-devel", "perl-Archive-Tar", "perl-XML-Parser",
                        "libX11-devel", "libtool-ltdl-devel", "e2fsprogs-devel", "gcc-gfortran",
                        "libicu-devel", "libgtextutils-devel", "httpd,"" httpd-devel",
                        "mod_ssl", "libjpeg-turbo-devel", "myproxy", '*ExtUtils*']

    yum_install_prerequisites = subprocess.Popen(
        yum_install_list, stdout=subprocess.PIPE)
    esg_functions.stream_subprocess_output(yum_install_prerequisites)


def setup_java():
    '''
        Installs Oracle Java from rpm using yum localinstall.  Does nothing if an acceptible Java install is found.
    '''
    print '''
    *******************************
    Setting up Java {java_version}
    ******************************* '''.format(java_version=config.config_dictionary["java_version"])
    if os.path.exists(os.path.join("/usr", "java", "jdk{java_version}".format(java_version=config.config_dictionary["java_version"]))):
        logger.info("Found existing Java installation.  Skipping set up.")
        return
    java_major_version = config.config_dictionary["java_version"].split(".")[1]
    java_minor_version = config.config_dictionary["java_version"].split("_")[1]
    # wget --no-check-certificate --no-cookies --header "Cookie:
    # oraclelicense=accept-securebackup-cookie"
    # http://download.oracle.com/otn-pub/java/jdk/8u112-b15/jdk-8u112-linux-x64.rpm
    download_oracle_java_string = 'wget --no-check-certificate --no-cookies --header "Cookie: oraclelicense=accept-securebackup-cookie" http://download.oracle.com/otn-pub/java/jdk/{java_major_version}u{java_minor_version}-b15/jdk-{java_major_version}u{java_minor_version}-linux-x64.rpm'.format(
        java_major_version=java_major_version, java_minor_version=java_minor_version)
    subprocess.call(shlex.split(download_oracle_java_string))

    command_list = ["yum", "-y", "localinstall", "jdk-{java_major_version}u{java_minor_version}-linux-x64.rpm".format(
        java_major_version=java_major_version, java_minor_version=java_minor_version)]
    yum_install_java = subprocess.Popen(
        command_list, stdout=subprocess.PIPE, universal_newlines=True, bufsize=1)
    esg_functions.stream_subprocess_output(yum_install_java)

    logger.debug("Creating symlink /usr/java/jdk{java_version}/ -> {java_install_dir}".format(
        java_version=config.config_dictionary["java_version"], java_install_dir=config.config_dictionary["java_install_dir"]))
    esg_bash2py.symlink_force("/usr/java/jdk{java_version}/".format(
        java_version=config.config_dictionary["java_version"]), config.config_dictionary["java_install_dir"])


def write_java_env():
    config.config_dictionary["show_summary_latch"] += 1
    target = open(config.config_dictionary['envfile'], 'w')
    target.write("export JAVA_HOME=" +
                 config.config_dictionary["java_install_dir"])


def setup_ant():
    '''
        Install ant via yum. Does nothing if a version of Ant is already installed.
    '''
    print '''
    *******************************
    Setting up Ant
    ******************************* '''
    if os.path.exists(os.path.join("/usr", "bin", "ant")):
        logger.info("Found existing Ant installation.  Skipping set up.")
        return

    command_list = ["yum", "-y", "install", "ant"]
    yum_install_ant = subprocess.Popen(command_list, stdout=subprocess.PIPE)
    esg_functions.stream_subprocess_output(yum_install_ant)


def setup_cdat():
    print "Checking for *UV* CDAT (Python+CDMS) {cdat_version} ".format(cdat_version=config.config_dictionary["cdat_version"])
    try:
        sys.path.insert(0, os.path.join(
            config.config_dictionary["cdat_home"], "bin", "python"))
        import cdat_info
        if esg_version_manager.check_version_atleast(cdat_info.Version, config.config_dictionary["cdat_version"]) == 0 and not force_install:
            print "CDAT already installed [OK]"
            return True
    except ImportError, error:
        logger.error(error)

    print '''
    *******************************
    Setting up CDAT - (Python + CDMS)... {cdat_version}
    ******************************* '''.format(cdat_version=config.config_dictionary["cdat_version"])

    if os.access(os.path.join(config.config_dictionary["cdat_home"], "bin", "uvcdat"), os.X_OK):
        print "Detected an existing CDAT installation..."
        cdat_setup_choice = raw_input(
            "Do you want to continue with CDAT installation and setup? [y/N] ")
        if cdat_setup_choice.lower() != "y" or cdat_setup_choice.lower() != "yes":
            print "Skipping CDAT installation and setup - will assume CDAT is setup properly"
            return True

    try:
        os.makedirs(config.config_dictionary["workdir"])
    except OSError, exception:
        if exception.errno != 17:
            raise
        sleep(1)
        pass

    starting_directory = os.getcwd()
    os.chdir(config.config_dictionary["workdir"])

    yum_install_uvcdat = subprocess.Popen(
        ["yum", "-y", "install", "uvcdat"], stdout=subprocess.PIPE)
    print "yum_install_uvcdat_output: ", yum_install_uvcdat.communicate()[0]
    print "yum_install_return_code: ", yum_install_uvcdat.returncode
    if yum_install_uvcdat.returncode != 0:
        print "[FAIL] \n\tCould not install or update uvcdat\n\n"
        return False

    curl_output = subprocess.call(
        "curl -k -O https://bootstrap.pypa.io/ez_setup.py", shell=True)
    setup_tools_output = subprocess.call("{cdat_home}/bin/python ez_setup.py".format(
        cdat_home=config.config_dictionary["cdat_home"]), shell=True)
    pip_setup_output = subprocess.call("{cdat_home}/bin/easy_install pip".format(
        cdat_home=config.config_dictionary["cdat_home"]), shell=True)

    os.chdir(starting_directory)

    return True
