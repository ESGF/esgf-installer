#!/usr/bin/python2.6

import sys
import os
import subprocess
import pwd
import re
# import math
# import pylint
import mmap
import shutil
from OpenSSL import crypto
import datetime
import tarfile
import logging
import requests
import stat
import socket
import platform
import netifaces
import tld
import grp
# import yum
from time import sleep
from esg_init import EsgInit
import esg_bash2py
import esg_functions
import esg_bootstrap

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = EsgInit()
use_local_files=0
force_install = False

def source(script, update=1):
    pipe = subprocess.Popen(". %s; env" % script, stdout=subprocess.PIPE, shell=True)
    data = pipe.communicate()[0]

    env = dict((line.split("=", 1) for line in data.splitlines()))
    if update:
        os.environ.update(env)

    return env


# esg_functions_file = "/usr/local/bin/esg-functions"
esg_functions_file = "/Users/hill119/Development/esgf-installer/esg-functions"
esg_init_file="/Users/hill119/Development/esgf-installer/esg-init"

def print_hello():
    print "hello world"


# subprocess.call(['ls', '-1'], shell=True)
# subprocess.call('echo $HOME', shell=True)
# subprocess.check_call('echo $PATH', shell=True)


output = subprocess.check_output(['ls', '-1'])
print 'Have %d bytes in output' % len(output)
print output

if os.path.isfile(esg_functions_file):
    print "found file: ", esg_functions_file
    # subprocess.call('source ${esg_functions_file}', shell=True)
    source(esg_init_file)
    source(esg_functions_file)
    print "sourcing from:", esg_functions_file
    print "Checking for java >= ${java_min_version} and valid JAVA_HOME... "
else:
    print "file not found"


def init_structure():

    # print "init_structure: esg_dist_url =",  config.config_dictionary["esg_dist_url"]

    if not os.path.isfile(config.config_dictionary["config_file"]):
        esg_functions.touch(config.config_dictionary["config_file"])

    config_check = 7
    directories_to_check = [config.config_dictionary["scripts_dir"], config.config_dictionary["esg_backup_dir"], config.config_dictionary["esg_tools_dir"], 
        config.config_dictionary["esg_log_dir"], config.esg_config_dir, config.config_dictionary["esg_etc_dir"], 
        config.config_dictionary["tomcat_conf_dir"]  ]
    for directory in directories_to_check:
        if not os.path.isdir(directory): 
            try:
                os.makedirs(directory)
                config_check-=1
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
    #Setup variables....
    #--------------

    check_for_my_ip()

    try:
        esgf_host = config.config_dictionary["esgf_host"]
    except KeyError:
        esgf_host = esg_functions.get_property("esgf_host")
        
    try:
        esgf_default_peer = config.config_dictionary["esgf_default_peer"]
    except KeyError:
        esgf_default_peer = esg_functions.get_property("esgf_default_peer")
        
    try:
        esgf_idp_peer_name = config.config_dictionary["esgf_idp_peer_name"]
    except KeyError:
        esgf_idp_peer_name = esg_functions.get_property("esgf_idp_peer_name")

    try:
        esgf_idp_peer = config.config_dictionary["esgf_idp_peer"]
    except KeyError:
        esgf_idp_peer = esg_functions.get_property("esgf_idp_peer")

    
    # logger.debug("trim_string_from_tail(esgf_idp_peer_name): %s",  esg_functions.trim_string_from_tail(esgf_idp_peer))
    if not esgf_idp_peer:
        myproxy_endpoint = None
    else:
        myproxy_endpoint = esg_functions.trim_string_from_tail(esgf_idp_peer)
    # re.search("/\w+", source)

    try:
        config.config_dictionary["myproxy_port"]
    except KeyError:
        myproxy_port =  esg_bash2py.Expand.colonMinus(esg_functions.get_property("myproxy_port"), "7512")

    try:
        esg_root_id = config.config_dictionary["esg_root_id"]
    except KeyError:
        esg_root_id = esg_functions.get_property("esg_root_id")

    try:
        node_peer_group = config.config_dictionary["node_peer_group"]
    except KeyError:
        node_peer_group = esg_functions.get_property("node_peer_group")

    try:
        config.config_dictionary["node_short_name"]
    except KeyError:
        node_short_name = esg_functions.get_property("node_short_name")
        

    #NOTE: Calls to get_property must be made AFTER we touch the file ${config_file} to make sure it exists
    #this is actually an issue with dedup_properties that gets called in the get_property function

    #Get the distinguished name from environment... if not, then esgf.properties... and finally this can be overwritten by the --dname option
    #Here node_dn is written in the /XX=yy/AAA=bb (macro->micro) scheme.
    #We transform it to dname which is written in the java style AAA=bb, XX=yy (micro->macro) scheme using "standard2java_dn" function

    try:
        dname = config.config_dictionary["dname"]
    except KeyError:
        dname = esg_functions.get_property("dname")
            
    try:
        gridftp_config = config.config_dictionary["gridftp_config"]
    except KeyError:
        gridftp_config = esg_functions.get_property("gridftp_config", "bdm end-user")
            
    try:
        publisher_config = config.config_dictionary["publisher_config"]
    except KeyError:
        publisher_config = esg_functions.get_property("publisher_config", "esg.ini")
            
    try:
        publisher_home = config.config_dictionary["publisher_home"]
    except KeyError:
        publisher_home = esg_functions.get_property("publisher_home", config.esg_config_dir+"/esgcet")
            

    # Sites can override default keystore_alias in esgf.properties (keystore.alias=)
    config.config_dictionary["keystore_alias"] = esg_functions.get_property("keystore_alias")

    config.config_dictionary["ESGINI"] = os.path.join(publisher_home, publisher_config)

    return 0


def write_paths():
    config.config_dictionary["show_summary_latch"]+=1

    datafile = open(config.envfile, "a+")
    datafile.write("export ESGF_HOME="+config.esg_root_dir+"\n")
    datafile.write("export ESG_USER_HOME="+config.config_dictionary["installer_home"]+"\n")
    datafile.write("export ESGF_INSTALL_WORKDIR="+config.config_dictionary["workdir"]+"\n")
    datafile.write("export ESGF_INSTALL_PREFIX="+config.install_prefix+"\n")
    datafile.write("export PATH="+config.myPATH+":"+os.environ["PATH"]+"\n")
    datafile.write("export LD_LIBRARY_PATH="+config.myLD_LIBRARY_PATH+":"+os.environ["LD_LIBRARY_PATH"]+"\n")
    datafile.truncate()
    datafile.close()

    esg_functions.deduplicate_settings_in_file(config.envfile)

def _select_ip_address():
    choice = int(raw_input(""))
    return choice

def _render_ip_address_menu(ip_addresses):
        print "Detected multiple IP addresses bound to this host...\n"
        print "Please select the IP address to use for this installation\n"
        print "\t-------------------------------------------\n"
        for index, ip in enumerate(ip_addresses.iteritems(),1):
            print "\t %i) %s" % (index, ip)
        print "\t-------------------------------------------\n"

def check_for_my_ip(force_install=False):
    logger.debug("Checking for IP address(es)...")
    matched = 0
    my_ip_address = None
    eth0 = netifaces.ifaddresses(netifaces.interfaces()[1])
    ip_addresses = [ ip["addr"] for ip in eth0[netifaces.AF_INET] ]

    try:
        esgf_host_ip
    except NameError:            
        esgf_host_ip = esg_functions.get_property("esgf_host_ip")

    if esgf_host_ip and not force_install:
        logger.info("Using IP: %s", esgf_host_ip)
        return 0

    #We want to make sure that the IP address we have in our config
    #matches one of the IPs that are associated with this host
    for ip in ip_addresses:
        if ip == esgf_host_ip:
            matched +=1

    if matched == 0:
        logger.info("Configured host IP address does not match available IPs...")

    if not esgf_host_ip or force_install or matched == 0:
        if len(ip_addresses) > 1:
            #ask the user to choose...
            while True:
                _render_ip_address_menu()
                default = 0
                choice = _select_ip_address() or default
                my_ip_address = ip_addresses[choice]
                logger.info("selected address -> %s", my_ip_address)
                break
        else:
            my_ip_address = ip_addresses[0]

    esg_functions.write_as_property("esgf_host_ip", my_ip_address)
    esgf_host_ip = esg_functions.get_property("esgf_host_ip")
    return esgf_host_ip

#checking for what we expect to be on the system a-priori
#that we are not going to install or be responsible for
def check_prerequisites():
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

    print "Checking that you have root privs on %s... " % (socket.gethostname())
    root_check = os.geteuid()
    if root_check != 0:
        print "$([FAIL]) \n\tMust run this program with root's effective UID\n\n"
        return 1
    print "[OK]"

    #----------------------------------------
    print "Checking requisites... "

     # checking for OS, architecture, distribution and version

    OS = platform.system()
    MACHINE = platform.machine()
    RELEASE_VERSION = re.search("(centos|redhat)-(\S*)-", platform.platform()).groups()[2]

    if RELEASE_VERSION[0] != "6":
        print "ESGF can only be installed on versions 6 of Red Hat, CentOS or Scientific Linux x86_64 systems" 
        return 1

def _choose_fqdn(esgf_host):
    if not esgf_host or force_install:
        default_host_name = esgf_host or socket.getfqdn()
        defaultdomain_regex =  r"^\w+-*\w*\W*(.+)"
        defaultdomain = re.search(defaultdomain_regex, default_host_name).group(1)
        if not default_host_name:
            default_host_name = "localhost.localdomain"
        elif not defaultdomain:
            default_host_name = default_host_name + ".localdomain"

        default_host_name = raw_input("What is the fully qualified domain name of this node? [{default_host_name}]: ".format(default_host_name = default_host_name)) or default_host_name
        esgf_host = default_host_name
        logger.info("esgf_host = [%s]", esgf_host)
        esg_functions.write_as_property("esgf_host", esgf_host)
    else:
        logger.info("esgf_host = [%s]", esgf_host)
        esg_functions.write_as_property("esgf_host", esgf_host)

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

    #Use the same password when creating the postgress account
    config.config_dictionary["pg_sys_acct_passwd"] = updated_password

#TODO: move this function to esg_functions
def _add_user_group(group_name):
    #TODO: Refactor by modifying the /etc/group and /etc/gshadow files; use [max_list.gr_gid for max_list in group_list] to find max group id and increment
    groupadd_command = ["/usr/sbin/groupadd", "-r", group_name]
    # groupadd_command = "/usr/sbin/groupadd -r {group_name}".format(group_name = group_name)
    try:
        groupadd_output = subprocess.check_output(groupadd_command, shell=True)
    except subprocess.CalledProcessError as error:
        logger.error(error)
        print "ERROR: *Could not add tomcat system group: %s" % (config.config_dictionary["tomcat_group"])
        os.chdir(starting_directory)
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
        os.chown(config.esgf_secret_file, config.config_dictionary["installer_uid"], tomcat_group_id)
    except OSError, error:
        logger.error(error)

    if os.path.isfile(config.esgf_secret_file):
        os.chmod(config.esgf_secret_file, 0640)
        try:
            os.chown(config.esgf_secret_file, config.config_dictionary["installer_uid"], tomcat_group_id)
        except OSError, error:
            logger.error(error)

    if not os.path.isfile(config.pg_secret_file):
        esg_functions.touch(config.pg_secret_file)
        try:
            with open(config.pg_secret_file, "w") as secret_file:
                secret_file.write(config.config_dictionary["pg_sys_acct_passwd"])
        except IOError, error:
            logger.error(error)
    else:
        os.chmod(config.pg_secret_file, 0640)
        try:
            os.chown(config.pg_secret_file, config.config_dictionary["installer_uid"], tomcat_group_id)
        except OSError, error:
            logger.error(error)

def _choose_admin_password():
    while True:
        password_input = raw_input("What is the admin password to use for this installation? (alpha-numeric only)")

        if force_install and len(password_input) == 0 and len(security_admin_password) > 0:
            changed = False
            break
        if not _is_valid_password(password_input):
            continue
        if password_input:
            security_admin_password = password_input

        security_admin_password_confirmation = raw_input("Please re-enter password to confirm: ")
        if _confirm_password(security_admin_password,security_admin_password_confirmation):
            changed = True
            break

    if changed is True:
        _update_admin_password_file()

    _update_password_files_permissions()

def _choose_organization_name():
    esg_root_id = esg_functions.get_property("esg_root_id")
    if not esg_root_id or force_install:
        while True:
            default_org_name = tld.get_tld("http://"+socket.gethostname(), as_object=True).domain
            org_name_input = raw_input("What is the name of your organization? [{default_org_name}]: ", format(default_org_name = default_org_name)) or default_org_name
            org_name_input.replace("", "_")
            esg_functions.write_as_property("esg_root_id", esg_root_id)
            break
    else:
        logger.info("esg_root_id = [%s]", esg_root_id)

def _choose_node_short_name():
    node_short_name = esg_functions.get_property("node_short_name")
    if not node_short_name or force_install:
        while True:
            node_short_name_input = raw_input("Please give this node a \"short\" name [{node_short_name}]: ".format(node_short_name = node_short_name)) or node_short_name
            node_short_name_input.replace("", "_")
            esg_functions.write_as_property("node_short_name", node_short_name_input)
            break
    else:
        logger.info("node_short_name = [%s]", node_short_name)

def _choose_node_long_name():
    node_long_name = esg_functions.get_property("node_long_name")
    if not node_long_name or force_install:
        while True:
            node_long_name_input = raw_input("Please give this node a more descriptive \"long\" name [{node_long_name}]: ".format(node_long_name = node_long_name)) or node_long_name
            esg_functions.write_as_property("node_long_name", node_long_name_input)
            break
    else:
        logger.info("node_long_name = [%s]", node_long_name)

def _choose_node_namespace():
    node_namespace = esg_functions.get_property("node_namespace")
    if not node_namespace or force_install:
        top_level_domain =  tld.get_tld("http://"+socket.gethostname(), as_object=True)
        domain = top_level_domain.domain
        suffix = top_level_domain.suffix
        default_node_namespace = suffix+"."+domain
        while True:
            node_namespace_input = raw_input("What is the namespace to use for this node? (set to your reverse fqdn - Ex: \"gov.llnl\") [{default_node_namespace}]: ".format(default_node_namespace = default_node_namespace)) or default_node_namespace
            namespace_pattern_requirement = re.compile("(\w+.{1}\w+)$")
            if not namespace_pattern_requirement.match(node_namespace_input):
                print "Namespace entered is not in a valid format.  Valid format is [suffix].[domain].  Example: gov.llnl"
                continue
            else:
                esg_functions.write_as_property("node_namespace", node_namespace_input)
                break
    else:
        logger.info("node_namespace = [%s]", node_namespace)

def _choose_node_peer_group():
    node_peer_group = esg_functions.get_property("node_peer_group")
    if not node_peer_group or force_install:
        try:
            node_peer_group
        except NameError:
            node_peer_group = "esgf-test"
        while True:
            node_peer_group_input = raw_input("What peer group(s) will this node participate in? (esgf-test|esgf-prod) [{node_peer_group}]: ".format(node_peer_group = node_peer_group)) or node_peer_group
            if node_peer_group_input != "esgf-test" or node_peer_group_input != "esgf-prod":
                print "Invalid Selection: {node_peer_group_input}".format(node_peer_group_input = node_peer_group_input)
                print "Please choose either esgf-test or esgf-prod"
                continue
            else:
                esg_functions.write_as_property("node_peer_group", node_peer_group_input)
                break
    else:
       logger.info("node_peer_group = [%s]", node_peer_group)

def _choose_esgf_default_peer():
    esgf_default_peer = esg_functions.get_property("esgf_default_peer")
    if not esgf_default_peer or force_install:
        try:
            default_esgf_default_peer = esgf_host
        except NameError:
            default_esgf_default_peer = socket.getfqdn()

        esgf_default_peer_input = raw_input("What is the default peer to this node? [{default_esgf_default_peer}]: ".format(default_esgf_default_peer = default_esgf_default_peer)) or default_esgf_default_peer
        esg_functions.write_as_property("esgf_default_peer", esgf_default_peer_input)
    else:
        logger.info("esgf_default_peer = [%s]", esgf_default_peer)

def _choose_esgf_index_peer():
    esgf_index_peer = esg_functions.get_property("esgf_index_peer")
    if not esgf_index_peer or force_install:
        default_esgf_index_peer = esgf_default_peer or esgf_host or socket.getfqdn()
        esgf_index_peer_input = raw_input("What is the hostname of the node do you plan to publish to? [{default_esgf_index_peer}]: ".format(default_esgf_index_peer = default_esgf_index_peer)) or default_esgf_index_peer
        esg_functions.write_as_property("esgf_index_peer", esgf_index_peer_input)
    else:
        logger.info("esgf_index_peer = [%s]", esgf_index_peer)

def _choose_mail_admin_address():
    mail_admin_address = esg_functions.get_property("mail_admin_address")
    if not mail_admin_address or force_install:
        mail_admin_address_input = raw_input("What email address should notifications be sent as? [{mail_admin_address}]: ".format(mail_admin_address =  mail_admin_address)) 
        if mail_admin_address_input:
             esg_functions.write_as_property("mail_admin_address", mail_admin_address_input)
        else:
            print " (The notification system will not be enabled without an email address)"
    else:
        logger.info("mail_admin_address = [%s]", mail_admin_address)

def _choose_publisher_db_user():
    default_publisher_db_user = None        
    publisher_db_user = esg_functions.get_property("publisher_db_user")
    if not publisher_db_user or force_install:
        default_publisher_db_user = publisher_db_user or "esgcet"
        publisher_db_user_input = raw_input("What is the (low priv) db account for publisher? [${default}]: ") or default_publisher_db_user
        esg_functions.write_as_property("publisher_db_user", publisher_db_user_input)
    else:
        logger.info("publisher_db_user: %s", publisher_db_user)

def initial_setup_questionnaire():
    print "-------------------------------------------------------"
    print 'Welcome to the ESGF Node installation program! :-)'

    try:
        os.makedirs(config.esg_config_dir)
    except OSError, e:
        if e.errno != 17:
            raise
        sleep(1)
        pass

    starting_directory = os.getcwd()

    os.chdir(config.esg_config_dir)

    esgf_host = esg_functions.get_property("esgf_host")
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

    db_properties_dict = {"db_user": None,"db_host": None, "db_port": None, "db_database": None, "db_managed": None}
    for key, value in db_properties_dict.items():
        db_properties_dict[key] = esg_functions.get_property(key)

    # db_user = esg_functions.get_property("db_user")
    # db_host = esg_functions.get_property("db_host")
    # db_port = esg_functions.get_property("db_port")
    # db_database = esg_functions.get_property("db_database")
    # db_managed = esg_functions.get_property("db_managed")

    if not all(db_properties_dict) or force_install:
        _is_managed_db()
        _get_db_conn_str_questionnaire()
    else:
        if db_properties_dict["db_host"] == esgf_host or db_properties_dict["db_host"] == "localhost":
            print "db_connection_string = {db_user}@localhost".format(db_user = db_properties_dict["db_user"])
        else:
            connstring_ = "{db_user}@{db_host}:{db_port}/{db_database} [external = ${db_managed}]".format(db_user = db_properties_dict["db_user"], 
                db_host = db_properties_dict["db_host"], 
                db_port = db_properties_dict["db_port"],
                db_database = db_properties_dict["db_database"],
                db_managed = db_properties_dict["db_managed"])

    _choose_publisher_db_user()

    if not config.config_dictionary["publisher_db_user_passwd"] or force_install:
        publisher_db_user_passwd_input = raw_input("What is the db password for publisher user ({publisher_db_user})?: ".format(publisher_db_user = publisher_db_user))
        if publisher_db_user_passwd_input:
            with open(config.pub_secret_file, "w") as secret_file:
                secret_file.write(publisher_db_user_passwd_input)

    if not os.path.isfile(config.pub_secret_file):
        esg_functions.touch(config.pub_secret_file)
        with open(config.pub_secret_file, "w") as secret_file:
                secret_file.write(config.config_dictionary["publisher_db_user_passwd"])

    os.chmod(config.pub_secret_file, 0640)
    tomcat_group_info = grp.getgrnam(
            config.config_dictionary["tomcat_group"])
    tomcat_group_id = tomcat_group_info[2]
    os.chown(config.esgf_secret_file, config.config_dictionary["installer_uid"], tomcat_group_id)

    if db_properties_dict["db_host"] == db_properties_dict["db_host"] or db_host == "localhost":
        logger.info("db publisher connection string %s@localhost", db_properties_dict["db_user"])
    else:
       logger.info("db publisher connection string %s@%s:%s/%s", db_properties_dict["db_user"], db_host, db_port, db_database)

    esg_functions.deduplicate_properties(config.config_dictionary["config_file"])

    os.chdir(starting_directory)

    return True


def _get_db_conn_str_questionnaire():
    #postgresql://esgcet@localhost:5432/esgcet
    user_ = None
    host_ = None
    port_ = None
    dbname_ = None
    connstring_ = None
    valid_connection_string = None

    #Note the values referenced here should have been set by prior get_property *** calls
    #that sets these values in the script scope. (see the call in questionnaire function - above)   
    if not db_user or not db_host or not db_port or not db_database:
        if not db_host:
            if db_host == esgf_host or db_host == "localhost":
                connstring_ = "{db_user}@localhost"
            else:
                connstring_ = "{db_user}@{db_host}:{db_port}/{db_database}"
    while True:
        print "Please enter the database connection string..."
        print " (form: postgresql://[username]@[host]:[port]/esgcet)"
        db_managed = get_property("db_managed")
        #(if it is a not a force install and we are using a LOCAL (NOT MANAGED) database then db_managed == "no")
        if not connstring_ and db_managed != "yes" and not force_install:
            connstring_ = "dbsuper@localhost:5432/esgcet"
        db_connection_input = raw_input("What is the database connection string? [postgresql://${connstring_}]: postgresql://".format(connstring_ = connstring_)) or connstring_ 
        parsed_db_conn_string = urlparse.urlparse(db_connection_input)
        #result.path[1:] is database name
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

    #write vars to property file
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
    db_managed = esg_functions.get_property("db_managed")
    if not force_install:
        if db_managed == "yes":
            return True
        else:
            return False

    if not db_managed:
        logger.debug("esgf_host = %s", esgf_host)
        logger.debug("db_host = %s", db_host)

        #Try to come up with some "sensible" default value for the user...
        if db_host == esgf_host or db_host == "localhost" or not db_host:
            db_managed_default = "no"
            default_selection_output = "[y/N]:"
        else:
            db_managed_default = "yes"
            default_selection_output = "[Y/n]:"

        external_db_input = raw_input("Is the database external to this node? " + default_selection_output)
        if not external_db_input:
            db_managed = db_managed_default
            esg_functions.write_as_property("db_managed", db_managed)
        else:
            if external_db_input.lower() == "y" or external_db_input.lower() == "yes":
                db_managed == "yes"
            else:
                db_managed == "no"
            esg_functions.write_as_property("db_managed", db_managed)
    else:
        logger.info("db_managed = [%s]", db_managed)

    if db_managed == "yes":
        print "Set to use externally \"managed\" database on host: {db_host}".format(db_host = db_host)
        return True
    else:
        logger.debug("(hmm... setting db_host to localhost)")
        #Note: if not managed and on the local machine... always use "localhost"
        db_host="localhost"
        return False
    pass


def is_in_git(file_name):
    '''
     This determines if a specified file is in a git repository.
     This function will resolve symlinks and check for a .git
     directory in the directory of the actual file as well as its
     parent to avoid attempting to call git unless absolutely needed,
     so as to be able to detect some common cases on a system without
     git actually installed and in the path.
    
     Accepts as an argument the file to be checked
    
     Returns 0 if the specified file is in a git repository
    
     Returns 2 if it could not detect a git repository purely by file
     position and git was not available to complete a rev-parse test
    
     Returns 1 otherwise
    '''
    # test = git.Repo("/Users/williamhill/Development/esgf-installer/installer/esg_init.py").git_dir

    '''
        debug_print "DEBUG: Checking to see if ${1} is in a git repository..."

        REALDIR=$(dirname $(_readlinkf ${1}))
    '''
    try:
        is_git_installed = subprocess.check_output(["which", "git"])
    except subprocess.CalledProcessError, e:
        print "Ping stdout output:\n", e.output
        print "git is not available to finish checking for a repository -- assuming there isn't one!"



    print "DEBUG: Checking to see if %s is in a git repository..." % (file_name)
    absolute_path = esg_functions._readlinkf(file_name)
    one_directory_up = os.path.abspath(os.path.join(absolute_path, os.pardir))
    print "absolute_path: ", absolute_path
    print "parent_path: ", os.path.abspath(os.path.join(absolute_path, os.pardir))
    two_directories_up = os.path.abspath(os.path.join(one_directory_up, os.pardir))
    print "two_directories_up: ", two_directories_up

    '''
        if [ ! -e $1 ] ; then
        debug_print "DEBUG: ${1} does not exist yet, allowing creation"
        return 1
    fi
    '''
    if not os.path.isfile(file_name):
        print "DEBUG: %s does not exist yet, allowing creation" % (file_name)
        return 1

    '''
        if [ -d "${REALDIR}/.git" ] ; then
        debug_print "DEBUG: ${1} is in a git repository"
        return 0
    fi

    '''
    if os.path.isdir(one_directory_up+"/.git"):
        print "%s is in a git repository" % file_name
        return 0

    '''
        if [ -d "${REALDIR}/../.git" ] ; then
        debug_print "DEBUG: ${1} is in a git repository"
        return 0
    fi
    '''
    if os.path.isdir(two_directories_up+"/.git"):
        print "%s is in a git repository" % file_name
        return 0


def check_for_update(filename_1, filename_2 =None):
    '''
         Does an md5 check between local and remote resource
         returns 0 (success) iff there is no match and thus indicating that
         an update is available.
         USAGE: checked_for_update [file] http://www.foo.com/file
        
    '''
    # local_file = None
    # remote_file = None

    if filename_2 == None:
        remote_file = filename_1
        local_file = os.path.realpath(re.search("\w+-\w+$", filename_1).group())
        local_file = local_file + ".py"
        local_file = re.sub(r'\-(?=[^-]*$)', "_", local_file)
        # print "remote_file: ", remote_file
        # print "local_file: ", local_file
    else:
        local_file = filename_1
        remote_file = filename_2

    if not os.path.isfile(local_file):
        print  " WARNING: Could not find local file %s" % (local_file)
        return 0
    if not os.access(local_file, os.X_OK):
        print " WARNING: local file %s not executible" % (local_file)
        os.chmod(local_file, 0755)
 

    remote_file_md5 = requests.get(remote_file+ '.md5').content
    remote_file_md5 = remote_file_md5.split()[0].strip()
    # print "remote_file_md5 in check_for_update: ", remote_file_md5
    local_file_md5 = None

    hasher = hashlib.md5()
    with open(local_file, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
        local_file_md5 = hasher.hexdigest()
        # print "local_file_md5 in check_for_update: ", local_file_md5

    if local_file_md5 != remote_file_md5:
        print " Update Available @ %s" % (remote_file)
        return 0
    return 1

def checked_get(local_file, remote_file = None, force_get = 0, make_backup_file = 1 ):
    '''

     If an update is available then pull it down... then check the md5 sums again!
    
      Yes, this results in 3 network calls to pull down a file, but it
      saves total bandwidth and it also allows the updating from the
      network process to be cronttab-able while parsimonious with
      resources.  It is also very good practice to make sure that code
      being executed is the RIGHT code!
    
      The 3rd token is the "force" flag value 1|0.
      1 = do not check for update, directly go and fetch the file regardless
      0 = first check for update availability. (default)
    
      The 4th token is for indicated whether a backup file should be made flag value 1|0.
      1 = yes, create a .bak file if the file is already there before fetching new
      0 = no, do NOT make a .bak file even if the file is already there, overwrite it
    
      (When using the force flag you MUST specify the first two args!!)
    
     NOTE: Has multiple return values test for (( $? > 1 )) when looking or errors
           A return value of 1 only means that the file is up-to-date and there
           Is no reason to fetch it.
    
     USAGE: checked_get [file] http://www.foo.com/file [<1|0>] [<1|0>]
    
    '''

    '''
           local force_get=${3:-0}
            local make_backup_file=${4:-1} #default to make backup *.bak files if necessary

            local local_file
            local remote_file
            if (( $# == 1 )); then
                remote_file=${1}
                local_file=${1##*/}
            elif (( $# >= 2 )); then
                local_file=${1}
                remote_file=${2}
            else
                echo "function \"checked_get\":  Called with incorrect number of args! (fatal) args[$@]"
                echo " usage: checked_get [<local dest>] <remote source> [force_get (0*|1)] [make_backup_file(0|1*)]"
                exit 1
            fi
    '''
    # try:
 #      force_get = str(sys.argv[3])
    # except IndexError:
 #      force_get = '0'

 #    try:
 #      make_backup_file = str(sys.argv[4])
    # except IndexError:
 #      make_backup_file = '-1'
    # force_get = esg_bash2py.Expand.colonMinus(str(sys.argv[3]), "0")
    # make_backup_file = esg_bash2py.Expand.colonMinus(str(sys.argv[4]), "-1")
    # local_file = None
    # remote_file = None

    if remote_file == None:
        remote_file = local_file
        local_file = re.search("\w+-\w+$", local_file).group()
        print "remote_file in checked_get: ", remote_file
        print "local_file in checked_get: ", local_file

    '''
        if (_is_in_git "${local_file}") ; then
        printf "${local_file} is controlled by Git, not updating"
        return 0
    fi
    '''
    if is_in_git(local_file) == 0:
        print "%s is controlled by Git, not updating" % (local_file)

    '''
        if ((use_local_files)) && [ -e "${local_file}" ]; then
        printf "
    ***************************************************************************
    ALERT....
    NOT FETCHING ANY ESGF UPDATES FROM DISTRIBUTION SERVER!!!! USING LOCAL FILE
    file: $(readlink -f ${local_file})
    ***************************************************************************\n\n"
        return 0
    fi
    '''
    if use_local_files and os.path.isfile(local_file):
        print '''
            ***************************************************************************
            ALERT....
            NOT FETCHING ANY ESGF UPDATES FROM DISTRIBUTION SERVER!!!! USING LOCAL FILE
            file: %s
            ***************************************************************************\n\n
        ''' % (esg_functions._readlinkf(local_file))

    '''
        if ((force_get == 0)); then
        check_for_update $@
        [ $? != 0 ] && return 1
    fi
    '''
    if force_get == 1:
        updates_available = check_for_update(local_file, remote_file)
        if updates_available != 0:
            return 1

    '''
        if [ -e ${local_file} ] && ((make_backup_file)) ; then
        cp -v ${local_file} ${local_file}.bak
        chmod 600 ${local_file}.bak
    fi
    '''
    if os.path.isfile(local_file) and make_backup_file == 1:
        shutil.copyfile(local_file, local_file+".bak")
        os.chmod(local_file+".bak", 600)

    '''
        echo "Fetching file from ${remote_file} -to-> ${local_file}"
    wget --no-check-certificate --progress=bar:force -O ${local_file} ${remote_file}
    [ $? != 0 ] && echo " ERROR: Problem pulling down [${remote_file##*/}] from esg distribution site" && return 2
    diff <(md5sum ${local_file} | tr -s " " | cut -d " " -f 1) <(curl -s -L --insecure ${remote_file}.md5 |head -1| tr -s " " | cut -d " " -f 1) >& /dev/null
    [ $? != 0 ] && echo " WARNING: Could not verify file! ${local_file}" && return 3
    echo "[VERIFIED]"
    return 0
    '''

    print "Fetching file from %s -to-> %s" % (remote_file, local_file)
    r = requests.get(remote_file)
    if not r.status_code == requests.codes.ok:
        print " ERROR: Problem pulling down [%s] from esg distribution site" % (remote_file)
        r.raise_for_status() 
        return 2
    else:
        file = open(local_file, "w")
        file.write(r.content)
        file.close()

    remote_file_md5 = requests.get(remote_file+ '.md5').content
    remote_file_md5 = remote_file_md5.split()[0].strip()
    print "remote_file_md5 in checked_get: ", remote_file_md5
    local_file_md5 = None

    hasher = hashlib.md5()
    with open(local_file, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
        local_file_md5 = hasher.hexdigest()
        print "local_file_md5 in checked_get: ", local_file_md5

    if local_file_md5 != remote_file_md5:
        print " WARNING: Could not verify this file! %s" % (local_file)
        return 3
    else:
        print "[VERIFIED]"
        return 0


# def setup_java():

#   "Checking for java >= %s and valid JAVA_HOME... " % (config.config_dictionary["java_min_version"])
#   print subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT)

#   if os.path.isdir(config.config_dictionary["java_install_dir"]):
#       java_version_check = esg_functions.check_version(config.config_dictionary["java_install_dir"]+"bin/java", config.config_dictionary["java_min_version"], version_command="-version")

#       if java_version_check == 0:
#           print "[OK]"
#           return 0

#   print '''*******************************
#             Setting up Java... %s
#            *******************************    
#        ''' % (config.config_dictionary["java_min_version"])

#   last_java_truststore_file = None
#   default = "Y"
#   dosetup = None

#   if os.path.isdir(config.config_dictionary["java_install_dir"]+"bin/java"):
#       print "Detected an existing java installation..."
#       dosetup = raw_input("Do you want to continue with Java installation and setup? [Y/n]") or default
#       if dosetup != "Y" or dosetup !="y":
#           print "Skipping Java installation and setup - will assume Java is setup properly"
#           return 0
#   last_java_truststore_file = esg_functions._readlinkf(config.config_dictionary["truststore_file"])

#   os.mkdir(config.config_dictionary["workdir"])
#   starting_directory = os.getcwd()
#   os.chdir(config.config_dictionary["workdir"])
#    # source_backup_name = re.search("\w+$", source).group()

#   java_dist_file = re.search("\w+$", config.config_dictionary["java_dist_url"]).group()
#   #strip off -(32|64).tar.gz at the end
#   java_dist_dir = re.search("(.+)-(32|64.*)", config.config_dictionary["java_dist_file"]).group(1)

#   if not os.path.isdir(config.config_dictionary["java_install_dir"]+ java_dist_dir):
#       print "Don't see java distribution dir %s/%s" % (config.config_dictionary["java_install_dir"], java_dist_dir)
#       if not os.path.isfile(java_dist_file):
#           print "Don't see java distribution file %s/%s either" % (os.getcwd(), java_dist_file)
#           print "Downloading Java from %s" % (config.config_dictionary["java_dist_url"])
#           if checked_get(config.config_dictionary["java_dist_file"],config.config_dictionary["java_dist_url"]) != 0:
#               print " ERROR: Could not download Java" 
#               os.chdir(starting_directory)
#               esg_functions.checked_done(1)
#           else:
#               print "unpacking %s..." % (config.config_dictionary["java_dist_file"])
#               extraction_location = re.search("/\w*/\w*[^.*]", config.config_dictionary["java_dist_url"])
#               try:
#                   tar = tarfile.open(config.config_dictionary["java_dist_file"])
#                   tar.extractall(extraction_location) 
#                   tar.close()
#                   print "Extracted in %s" % (extraction_location)
#               except tarfile.TarError:
#                   print " ERROR: Could not extract Java"
#                   os.chdir(starting_directory)
#                   esg_functions.checked_done(1)

#     #If you don't see the directory but see the tar.gz distribution
#     #then expand it

#     '''
#   if [ -e ${java_dist_file} ] && [ ! -e ${java_install_dir%/*}/${java_dist_dir} ]; then
#         echo "unpacking ${java_dist_file}..."
#         tar xzf ${java_dist_file} -C ${java_install_dir%/*} # i.e. /usr/local
#         [ $? != 0 ] && echo " ERROR: Could not extract Java..." && popd && checked_done 1
#     fi    
#     '''
#     if os.path.isfile(java_dist_file) and not os.path.isdir(re.search("/\w*/\w*[^.*]", config.config_dictionary["java_dist_url"])+"/"+config.config_dictionary["java_install_dir"]):
#       print "unpacking %s..." % (java_dist_file)
#       extraction_location = re.search("/\w*/\w*[^.*]", config.config_dictionary["java_dist_url"])
#       try:
#           tar = tarfile.open(config.config_dictionary["java_dist_file"])
#           tar.extractall(extraction_location) 
#           tar.close()
#           print "Extracted in %s" % (extraction_location)
#       except tarfile.TarError:
#           print " ERROR: Could not extract Java"
#           os.chdir(starting_directory)
#           esg_functions.checked_done(1)

#   if not os.path.isdir(config.config_dictionary["java_install_dir"]):
        

def setup_ant():
    pass

# def 


# yb=yum.YumBase()
# inst = yb.rpmdb.returnPackages()
# installed=[x.name for x in inst]
# print "installed: ", installed

# yb.install("java")
# yb.resolveDeps()
# yb.buildTransaction()
# yb.processTransaction()

# packages=['bla1', 'bla2', 'bla3']

# for package in packages:
#         if package in installed:
#                 print('{0} is already installed'.format(package))
#         else:
#                 print('Installing {0}'.format(package))
#                 kwarg = {
#                         'name':package
#                 }
#                 yb.install(**kwarg)
#                 yb.resolveDeps()
#                 yb.buildTransaction()
#                 yb.processTransaction()

    pass
