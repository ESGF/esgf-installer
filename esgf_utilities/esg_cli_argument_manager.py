import os
import sys
import shutil
import logging
import argparse
import psutil
import pprint
import ConfigParser
from time import sleep
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from esgf_utilities import esg_cert_manager
from base import esg_setup
from base import esg_apache_manager
from base import esg_tomcat_manager
from base import esg_postgres
from esgf_utilities.esg_exceptions import NoNodeTypeError, SubprocessError
from idp_node import globus
from index_node import solr

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def generate_esgf_csrs():
    pass

def generate_esgf_csrs_ext():
    pass

def usage():
    with open(os.path.join(os.path.dirname(__file__), os.pardir, 'docs', 'usage.txt'), 'r') as usage_file:
        print usage_file.read()

def cert_howto():
    with open(os.path.join(os.path.dirname(__file__), os.pardir, 'docs', 'cert_howto.txt'), 'r') as howto_file:
        print howto_file.read()

def start(node_types):
    '''Start ESGF Services'''
    #base components
    esg_apache_manager.start_apache()
    esg_tomcat_manager.start_tomcat()
    esg_postgres.start_postgres()

    if "DATA" in node_types:
        globus.start_globus("DATA")

    if "IDP" in node_types:
        globus.start_globus("IDP")

    if "INDEX" in node_types:
        solr_shards = solr.read_shard_config()
        for config_type, port_number in solr_shards:
            solr.start_solr(config_type, port_number)

    return get_node_status()

def stop(node_types):
    '''Stop ESGF Services'''
    #base components
    esg_apache_manager.stop_apache()
    esg_tomcat_manager.stop_tomcat()
    esg_postgres.stop_postgres()


    if "DATA" in node_types:
        globus.stop_globus("DATA")

    if "IDP" in node_types:
        globus.stop_globus("IDP")

    if "INDEX" in node_types:
        solr_shards = solr.read_shard_config()
        for config_type, port_number in solr_shards:
            solr.stop_solr()

def get_node_status():
    '''
        Shows which ESGF services are currently running
    '''
    node_running = True
    node_type = get_node_type()
    try:
        postgres_status = esg_postgres.postgres_status()
        if not postgres_status:
            node_running = False
    except SubprocessError, error:
        print "Postgres is stopped"
        logger.info(error)

    tomcat_status = esg_tomcat_manager.check_tomcat_status()
    if tomcat_status:
        print "Tomcat is running"
        tomcat_pid = int(tomcat_status.strip())
        tomcat_process = psutil.Process(tomcat_pid)
        pinfo = tomcat_process.as_dict(attrs=['pid', 'username', 'cpu_percent', 'name'])
        print pinfo
    else:
        print "Tomcat is stopped."
        node_running = False

    apache_status = esg_apache_manager.check_apache_status()
    if apache_status:
        print "Httpd is running"
    else:
        print "httpd is stopped"
        node_running = False

    if "DATA" in node_type:
        if not globus.gridftp_server_status():
            node_running = False

    if "IDP" in node_type:
        if not globus.myproxy_status():
            node_running = False

    if "INDEX" in node_type:
        if not solr.check_solr_process():
            node_running = False

    print "\n*******************************"
    print "ESGF Node Status"
    print "******************************* \n"
    if node_running:
        print "Node is running"
        show_esgf_process_list()
        return True
    else:
        print "Node is stopped"
        show_esgf_process_list()
        return False

    #TODO conditionally reflect the status of globus (gridftp) process
        #This is here for sanity checking...


def show_esgf_process_list():
    print "\n*******************************"
    print "Active ESGF processes"
    print "******************************* \n"
    procs = ["postgres", "jsvc", "globus-gr", "java", "myproxy", "httpd", "postmaster"]
    esgf_processes = [p.info for p in psutil.process_iter(attrs=['pid', 'name', 'username', 'cmdline']) if any(proc_name in p.info['name'] for proc_name in procs)]
    for process in esgf_processes:
        print process


def update_script(script_name, script_directory):
    '''
        arg (1) - name of installation script root name. Ex:security which resolves to script file esg-security
        arg (2) - directory on the distribution site where script is fetched from Ex: orp
        usage: update_script security orp - looks for the script esg-security in the distriubtion directory "orp"
    '''
    pass

def set_local_mirror(mirror_url):
    try:
        os.path.exists(mirror_url)
        esg_property_manager.set_property("use_local_mirror", True)
        esg_property_manager.set_property("local_mirror", mirror_url)
    except OSError, error:
        esg_functions.exit_with_error(error)

#Formerly get_bit_value
def set_node_type_value(node_type, config_file=config["esg_config_type_file"]):

    node_type = [node.upper() for node in node_type]
    with open(config_file, "w") as esg_config_file:
        esg_config_file.write(" ".join(node_type))


def get_node_type(config_file=config["esg_config_type_file"]):
    '''
        Helper method for reading the last state of node type config from config dir file "config_type"
        Every successful, explicit call to --type|-t gets recorded in the "config_type" file
        If the configuration type is not explicity set the value is read from this file.
    '''
    try:
        last_config_type = open(config_file, "r")
        node_type_list = last_config_type.read().split()
        if node_type_list:
            return node_type_list
        else:
            raise NoNodeTypeError
    except IOError:
        raise NoNodeTypeError
    except NoNodeTypeError:
        logger.exception('''No node type selected nor available! \n Consult usage with --help flag... look for the \"--type\" flag
        \n(must come BEFORE \"[start|stop|restart|update]\" args)\n\n''')
        sys.exit(1)


def define_acceptable_arguments():
    #TODO: Add mutually exclusive groups to prevent long, incompatible argument lists
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", dest="install", help="Goes through the installation process and automatically starts up node services", action="store_true")
    parser.add_argument("--base", dest="base", help="Install on base third party components", action="store_true")
    parser.add_argument("--update", help="Updates the node manager", action="store_true")
    parser.add_argument("--upgrade", help="Upgrade the node manager", action="store_true")
    parser.add_argument("--install-local-certs", dest="installlocalcerts", help="Install local certificates", action="store_true")
    parser.add_argument("--generate-esgf-csrs", dest="generateesgfcsrs", help="Generate CSRs for a simpleCA CA certificate and/or web container certificate", action="store_true")
    parser.add_argument("--generate-esgf-csrs-ext", dest="generateesgfcsrsext", help="Generate CSRs for a node other than the one you are running", action="store_true")
    parser.add_argument("--cert-howto", dest="certhowto", help="Provides information about certificate management", action="store_true")
    parser.add_argument("--fix-perms","--fixperms", dest="fixperms", help="Fix permissions", action="store_true")
    parser.add_argument("--type", "-t", "--flavor", dest="type", help="Set type", nargs="+", choices=["data", "index", "idp", "compute", "all"])
    parser.add_argument("--set-type",  dest="settype", help="Sets the type value to be used at next start up", nargs="+", choices=["data", "index", "idp", "compute", "all"])
    parser.add_argument("--get-type", "--show-type", dest="gettype", help="Returns the last stored type code value of the last run node configuration (data=4 +| index=8 +| idp=16)", action="store_true")
    parser.add_argument("--start", help="Start the node's services", action="store_true")
    parser.add_argument("--stop", "--shutdown", dest="stop", help="Stops the node's services", action="store_true")
    parser.add_argument("--restart", help="Restarts the node's services (calls stop then start :-/)", action="store_true")
    parser.add_argument("--status", help="Status on node's services", action="store_true")
    parser.add_argument("--update-apache-conf", dest="updateapacheconf", help="Update Apache configuration", action="store_true")
    parser.add_argument("-v","--version", dest="version", help="Displays the version of this script", action="store_true")
    parser.add_argument("--recommended_setup", dest="recommendedsetup", help="Sets esgsetup to use the recommended, minimal setup", action="store_true")
    parser.add_argument("--custom_setup", dest="customsetup", help="Sets esgsetup to use a custom, user-defined setup", action="store_true")
    parser.add_argument("--use-local-files", dest="uselocalfiles", help="Sets a flag for using local files instead of attempting to fetch a remote file", action="store_true")
    parser.add_argument("--use-local-mirror", dest="uselocalmirror", help="Sets the installer to fetch files from a mirror directory that is on the same server in which the installation is being run", action="store_true")
    parser.add_argument("--devel", help="Sets the installation type to the devel build", action="store_true")
    parser.add_argument("--prod", help="Sets the installation type to the production build", action="store_true")
    parser.add_argument("--usage", dest="usage", help="Displays the options of the ESGF command line interface", action="store_true")
    parser.add_argument("--debug", dest="debug", help="Sets the logging level to debug", action="store_true")
    parser.add_argument("--clear-envfile", dest="clearenvfile", help="Delete (and backup) existing envfile (/etc/esg.env)", action="store_true")
    parser.add_argument("--clear-my-certs", dest="clearmycerts", help="Delete certficates from $HOME/.globus/certificates", action="store_true")
    parser.add_argument("--info", dest="info", help="Print basic info about ESGF installation", action="store_true")
    parser.add_argument("--config-db", dest="configdb", help="configures the database i.e. sets up table schema based on the the node type.", action="store_true")
    parser.add_argument("--backup-db", dest="backupdb", help="Backs up the Postgres database", action="store_true")
    parser.add_argument("--restore-db", dest="restoredb", help="Restores the Postgres database from a previous backup", action="store_true")
    parser.add_argument("--verify-thredds-credentials", dest="verifythreddscredentials", help="Verifies Thredds credentials", action="store_true")
    parser.add_argument("--uninstall", "--purge", dest="uninstall", help="Uninstalls the ESGF installation", action="store_true")
    parser.add_argument("--get-idp-peer", dest="getidppeer", help="Displays the IDP peer node name", action="store_true")
    parser.add_argument("--set-idp-peer", "--set-admin-peer", dest="setidppeer", help="Selects the IDP peer node", action="store_true")
    parser.add_argument("--get-index-peer", dest="getindexpeer", help="Displays the index peer node name", action="store_true")
    parser.add_argument("--set-index-peer", dest="setindexpeer", help="Sets the (index peer) node to which we will publish", action="store_true")
    parser.add_argument("--set-publication-target", dest="setpublicationtarget", help="Sets the publication target", action="store_true")
    parser.add_argument("--get-default-peer", dest="getdefaultpeer", help="Displays the default peer", action="store_true")
    parser.add_argument("--set-default-peer", dest="setdefaultpeer", help="Sets the default peer", action="store_true")
    parser.add_argument("--get-peer-group", "--get-peer-groups",  dest="getpeergroup", help="Displays the peer groups", action="store_true")
    parser.add_argument("--set-peer-group", "--set-peer-groups",  dest="setpeergroup", help="Sets the peer groups", action="store_true")
    parser.add_argument("--no-auto-fetch-certs", dest="noautofetchcerts", help="", action="store_true")
    parser.add_argument("--set-auto-fetch-certs", dest="setautofetchcerts", help="", action="store_true")
    parser.add_argument("--fetch-esgf-certs", dest="fetchesgfcerts", help="", action="store_true")
    parser.add_argument("--rebuild-truststore", dest="rebuildtrustore", help="", action="store_true")
    parser.add_argument("--add-my-cert-to-truststore", dest="addmycerttotruststore", help="", action="store_true")
    parser.add_argument("--generate-ssl-key-and-csr", dest="generatesslkeyandcsr", help="", action="store_true")
    parser.add_argument("--migrate-tomcat-credentials-to-esgf", dest="migratetomcatcredentialstoesgf", help="", action="store_true")
    parser.add_argument("--update-temp-ca", dest="updatetempca", help="", action="store_true")
    parser.add_argument("--check-certs", dest="checkcerts", help="", action="store_true")
    parser.add_argument("--install-ssl-keypair", "--install-keypair", dest="installsslkeypair", help="", action="store_true")
    parser.add_argument("--optimize-index", dest="optimizeindex", help="", action="store_true")
    parser.add_argument("--myproxy-sanity-check", dest="myproxysanitycheck", help="", action="store_true")
    parser.add_argument("--noglobus", dest="noglobus", help="", action="store_true")
    parser.add_argument("--force-install", dest="forceinstall", help="", action="store_true")
    parser.add_argument("--index-config", dest="indexconfig", help="", action="store_true")
    parser.add_argument("--check-shards", dest="checkshards", help="", action="store_true")
    parser.add_argument("--add-replica-shard", dest="addreplicashard", help="", action="store_true")
    parser.add_argument("--remove-replica-shard", dest="removereplicashard", help="", action="store_true")
    parser.add_argument("--time-shards", dest="timeshards", help="", action="store_true")
    parser.add_argument("--update-publisher-resources", dest="updatepublisherresources", help="", action="store_true")

    # args = parser.parse_args()
    # return (args, parser)
    return parser

def process_arguments():
    # args, parser = _define_acceptable_arguments()

    parser = define_acceptable_arguments()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.install:
        if args.type:
            set_node_type_value(args.type)
        logger.debug("Install Services")
        if args.base:
            return ["INSTALL"]
        node_type_list = get_node_type()
        return node_type_list + ["INSTALL"]
    if args.update or args.upgrade:
        if args.type:
            set_node_type_value(args.type)
        logger.debug("Update Services")
        if args.base:
            return ["INSTALL"]
        node_type_list = get_node_type()
        return node_type_list + ["INSTALL"]
    if args.fixperms:
        logger.debug("fixing permissions")
        esg_functions.setup_whitelist_files()
        sys.exit(0)
    if args.installlocalcerts:
        logger.debug("installing local certs")
        get_node_type(config["esg_config_type_file"])
        node_type_list = get_node_type()
        esg_cert_manager.install_local_certs(node_type_list)
        sys.exit(0)
    if args.generateesgfcsrs:
        logger.debug("generating esgf csrs")
        get_node_type(config["esg_config_type_file"])
        generate_esgf_csrs()
        sys.exit(0)
    if args.generateesgfcsrsext:
        logger.debug("generating esgf csrs for other node")
        get_node_type(config["esg_config_type_file"])
        generate_esgf_csrs_ext()
        sys.exit(0)
    if args.certhowto:
        cert_howto()
        sys.exit(0)
    elif args.type:
        set_node_type_value(args.type)
        sys.exit(0)
    elif args.settype:
        logger.debug("Selecting type for next start up")
        set_node_type_value(args.type)
        sys.exit(0)
    elif args.gettype:
        print get_node_type(config["esg_config_type_file"])
        sys.exit(0)
    elif args.start:
        logger.debug("args: %s", args)
        if not esg_setup.check_prerequisites():
            logger.error("Prerequisites for startup not satisfied.  Exiting.")
            sys.exit(1)
        logger.debug("START SERVICES: %s", node_type_list)
        # esg_setup.init_structure()
        node_type_list = get_node_type()
        return start(node_type_list)
    elif args.stop:
        if not esg_setup.check_prerequisites():
            logger.error("Prerequisites for startup not satisfied.  Exiting.")
            sys.exit(1)
        logger.debug("STOP SERVICES")
        esg_setup.init_structure()
        stop(node_type_list)
        sys.exit(0)
    elif args.restart:
        if not esg_setup.check_prerequisites():
            logger.error("Prerequisites for startup not satisfied.  Exiting.")
            sys.exit(1)
        logger.debug("RESTARTING SERVICES")
        esg_setup.init_structure()
        stop(node_type_list)
        sleep(2)
        start(node_type_list)
        sys.exit(0)
    elif args.status:
        get_node_status()
        sys.exit(0)
    # elif args.updateapacheconf:
    #     logger.debug("checking for updated apache frontend configuration")
    #     esg_apache_manager.update_apache_conf()
    #     sys.exit(0)
    elif args.version:
        script_version, script_maj_version, script_release = esg_version_manager.set_version_info()
        print "Version: %s", script_version
        print "Release: %s", script_release
        print "Earth Systems Grid Federation (http://esgf.llnl.gov)"
        print "ESGF Node Installation Script"
        sys.exit(0)
    elif args.recommendedsetup:
        esg_property_manager.set_property("recommended_setup", True)
    elif args.customsetup:
        esg_property_manager.set_property("recommended_setup", False)
    elif args.uselocalfiles:
        esg_property_manager.set_property("use_local_files", True)
    elif args.uselocalmirror:
        set_local_mirror(args.uselocalmirror)
    elif args.devel:
        esg_property_manager.set_property("devel", True)
    elif args.prod:
        esg_property_manager.set_property("devel", False)
    elif args.usage:
        usage()
        sys.exit(0)
    elif args.debug:
        pass
    elif args.clearenvfile:
        try:
            shutil.copyfile("/etc/esg.env", "/etc/esg.env.bak")
            os.remove("/etc/esg.env")
            print "Cleared envfile: /etc/esg.env"
        except OSError:
            logger.exception()
    elif args.clearmycerts:
        try:
            shutil.rmtree(os.path.expanduser('~/.globus/certificates'))
            print "Cleared out certs..."
        except OSError:
            logger.exception("Could not clear out certs")
    elif args.info:
        esg_functions.esgf_node_info()
    elif args.configdb:
        node_type_list = get_node_type()
        if "DATA" in node_type_list:
            logger.info("Node Manager not currently implemented. Skipping config_db")
        if "IDP" in node_type_list:
            from idp_node import esg_security
            esg_dist_url = esg_property_manager.get_property("esg.dist.url")
            esg_security.configure_postgress(node_type_list, esg_dist_url, config["esgf_security_version"])
    elif args.backupdb:
        db_name = args.backupdb[0]
        user_name = args.backupdb[1]
        esg_postgres.backup_db(db_name, user_name)
    elif args.restoredb:
        pass
    elif args.verifythreddscredentials:
        from data_node import thredds
        thredds.verify_thredds_credentials()
    elif args.uninstall:
        import esg_purge
        esg_purge.main()
    elif args.getidppeer:
        try:
            print "Current IDP peer: {}".format(esg_property_manager.get_property("esgf_idp_peer"))
        except ConfigParser.NoOptionError:
            logger.error("Could not find IDP peer")
    elif args.setidppeer:
        node_type_list = get_node_type()
        from data_node import thredds
        thredds.select_idp_peer(node_type_list)
    elif args.getindexpeer:
        try:
            print "Current Index Peer: {}".format(esg_property_manager.get_property("esgf_index_peer"))
        except ConfigParser.NoOptionError:
            logger.error("Could not find Index peer")
    elif args.setindexpeer:
        from data_node import esg_publisher
        esg_publisher.set_index_peer()
    elif args.setpublicationtarget:
        pass
    elif args.getdefaultpeer:
        try:
            print "Current Default Peer: {}".format(esg_property_manager.get_property("esgf_default_peer"))
        except ConfigParser.NoOptionError:
            logger.error("Could not find default peer")
    elif args.setdefaultpeer:
        esg_property_manager.set_property("esgf_default_peer", args.setdefaultpeer)
        check_for_group_intersection_with(esg_property_manager.get_property("esgf_default_peer"))
        print "  Default Peer set to: [{}]".format(args.setdefaultpeer)
        print "  (restart node to enable default peer value)"
    elif args.getpeergroup:
        try:
            print "Configured to participate in peer group(s): {}".format(esg_property_manager.get_property("node_peer_group"))
        except ConfigParser.NoOptionError:
            logger.error("Could not find peer groups")
    elif args.setpeergroup:
        esg_property_manager.set_property("node_peer_group", args.setpeergroup)
        check_for_group_intersection_with(esg_property_manager.get_property("node_peer_group"))
        print "  Peer Group is set to: [{}]".format(args.setpeergroup)
        print "  (restart node to enable group value)"
    elif args.noautofetchcerts:
        esg_property_manager.set_property("node.auto.fetch.certs", False)
    elif args.setautofetchcerts:
        if args.setautofetchcerts == "off" or args.setautofetchcerts == False:
            esg_property_manager.set_property("node.auto.fetch.certs", False)
        else:
            esg_property_manager.set_property("node.auto.fetch.certs", True)
    elif args.fetchesgfcerts:
        esg_dist_url = esg_property_manager.get_property("esg.dist.url")
        from esgf_utilities import esg_cert_manager
        esg_cert_manager.fetch_esgf_certificates()
    elif args.rebuildtrustore:
        from esgf_utilities import esg_cert_manager
        esg_cert_manager.rebuild_truststore()
    elif args.addmycerttotruststore:
        from esgf_utilities import esg_cert_manager
        esg_cert_manager.add_my_cert_to_truststore()
    elif args.generatesslkeyandcsr:
        esg_cert_manager.generate_ssl_key_and_csr(args.generatesslkeyandcsr)
    elif args.migratetomcatcredentialstoesgf:
        from base import esg_tomcat_manager
        esg_tomcat_manager.migrate_tomcat_credentials_to_esgf()
        esg_tomcat_manager.sanity_check_web_xmls()
    elif args.updatetempca:
        from esgf_utilities import esg_cert_manager
        logger.debug("updating temporary CA")
        esg_cert_manager.setup_temp_ca()
        esg_cert_manager.install_local_certs("firstrun")
    elif args.checkcerts:
        esg_cert_manager.check_certificates()
    elif args.installsslkeypair:
        install_keypair()
    elif args.optimizeindex:
        if not os.path.exists(os.path.join(config["scripts_dir"], "esgf-optimize-index")):
            print "The flag --optimize-index is not enabled..."
        pass
    elif args.myproxysanitycheck:
        from idp_node import globus
        globus.sanity_check_myproxy_configurations()
    elif args.noglobus:
        esg_property_manager.set_property("no.globus", True)
    elif args.forceinstall:
        esg_property_manager.set_property("force.install", True)
    elif args.indexconfig:
        node_type_list = get_node_type()
        if "INDEX" not in node_type_list:
            print "Sorry, the --index-config flag may only be used for \"index\" installation type"
            sys.exit()

        if args.indexconfig not in ["master", "slave"]:
            print "Invalid arguments. Valid arguments are 'master' and/or 'slave'"

        esg_property_manager.set_property("index.config", args.indexconfig)
    elif args.checkshards:
        from index_node import esg_search
        esg_search.check_shards()
    elif args.addreplicashard:
        from index_node import esg_search
        #expecting <hostname>:<solr port> | master | slave
        esg_search.add_shard()
    elif args.removereplicashard:
        from index_node import esg_search
        esg_search.remove_shard()
    elif args.timeshard:
        from index_node import esg_search
        esg_search.time_shards()
    elif args.updatepublisherresources:
        from index_node import esg_search
        esg_search.setup_publisher_resources()
