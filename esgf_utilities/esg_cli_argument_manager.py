import os
import sys
import shutil
import logging
import psutil
import ConfigParser
from time import sleep
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import esg_cli
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from esgf_utilities import esg_truststore_manager
from base import esg_apache_manager
from base import esg_tomcat_manager
from base import esg_postgres
from data_node import esg_dashboard, esg_publisher, orp
from esgf_utilities.esg_exceptions import NoNodeTypeError, InvalidNodeTypeError
from idp_node import globus, gridftp, myproxy, esg_security, idp
from index_node import solr, esg_search
from plumbum.commands import ProcessExecutionError

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def usage():
    with open(os.path.join(os.path.dirname(__file__), os.pardir, 'docs', 'usage.txt'), 'r') as usage_file:
        print usage_file.read()

def cert_howto():
    with open(os.path.join(os.path.dirname(__file__), os.pardir, 'docs', 'cert_howto.txt'), 'r') as howto_file:
        print howto_file.read()

def run_startup_hooks(node_type_list):
    '''Run commands that need to be done to set the stage before any of the aparatus begins their launch sequence.
    Here is a good place to; copy files, set configurations, etc... BEFORE you start running and need them!
    In the submodule script the convention is <module>_startup_hook() (where module does not contain esg(f) prefix)'''

    print "Running startup hooks..."
    esg_functions.setup_whitelist_files()
    esg_publisher.esgcet_startup_hook()
    orp.orp_startup_hook()
    esg_security.security_startup_hook(node_type_list)
    esg_search.search_startup_hook()

    #When starting up pull down necessary federation certificates
    try:
        esg_property_manager.get_property("node_auto_fetch_certs")
    except ConfigParser.NoOptionError:
        esg_property_manager.set_property("node_auto_fetch_certs", "true")

    if esg_property_manager.get_property("node_auto_fetch_certs") == "true":
        print "Fetching federation certificates... "
        esg_truststore_manager.fetch_esgf_certificates()

        print "Fetching federation truststore..... "
        esg_truststore_manager.fetch_esgf_truststore()

def start(node_types):
    '''Start ESGF Services'''
    print "\n*******************************"
    print "Starting ESGF Node"
    print "******************************* \n"

    print "Starting Services.."
    run_startup_hooks(node_types)
    #base components
    try:
        esg_apache_manager.start_apache()
    except ProcessExecutionError, error:
        logger.error("Could not start Apache httpd: %s", error)
        raise

    try:
        esg_tomcat_manager.start_tomcat()
    except ProcessExecutionError, error:
        logger.error("Could not start Tomcat: %s", error)
        raise
    try:
        esg_postgres.start_postgres()
    except ProcessExecutionError, error:
        logger.error("Could not start Postgres: %s", error)
        raise

    if "DATA" in node_types:
        try:
            globus.start_globus("DATA")
        except ProcessExecutionError, error:
            logger.error("Could not start globus: %s", error)
            raise
        try:
            esg_dashboard.start_dashboard_service()
        except ProcessExecutionError, error:
            logger.error("Could not start esgf-dashboard-ip: %s", error)
            raise

    if "IDP" in node_types:
        try:
            globus.start_globus("IDP")
        except ProcessExecutionError, error:
            logger.error("Could not start globus: %s", error)
        idp.slcs_apachectl("start")

    if "INDEX" in node_types:
        esg_search.start_search_services()

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
        idp.slcs_apachectl("stop")

    if "INDEX" in node_types:
        solr_shards = solr.read_shard_config()
        for config_type, port_number in solr_shards:
            solr.stop_solr()

def get_node_status():
    '''
        Shows which ESGF services are currently running
    '''
    print "\n*******************************"
    print "Checking ESGF Node component's status"
    print "******************************* \n"
    node_running = True
    node_type = esg_functions.get_node_type()

    print "\n*******************************"
    print "Postgres status"
    print "******************************* \n"
    try:
        postgres_status = esg_postgres.postgres_status()
        if not postgres_status:
            node_running = False
    except ProcessExecutionError, error:
        print "Postgres is stopped"
        logger.info(error)


    print "\n*******************************"
    print "Tomcat status"
    print "******************************* \n"
    tomcat_status = esg_tomcat_manager.check_tomcat_status()
    logger.debug("tomcat_status: %s", tomcat_status)
    if tomcat_status:
        print "Tomcat is running"
        tomcat_pid = int(tomcat_status.strip())
        tomcat_process = psutil.Process(tomcat_pid)
        pinfo = tomcat_process.as_dict(attrs=['pid', 'username', 'cpu_percent', 'name'])
        print pinfo
    else:
        print "Tomcat is stopped."
        node_running = False

    print "\n*******************************"
    print "Apache status"
    print "******************************* \n"
    apache_status = esg_apache_manager.check_apache_status()
    if apache_status:
        print "Httpd is running"
    else:
        print "httpd is stopped"
        node_running = False

    if "DATA" in node_type:
        print "\n*******************************"
        print "GridFTP status"
        print "******************************* \n"
        if not gridftp.gridftp_server_status():
            node_running = False

    if "IDP" in node_type:
        print "\n*******************************"
        print "MyProxy status"
        print "******************************* \n"
        if not myproxy.myproxy_status():
            node_running = False

    if "INDEX" in node_type:
        print "\n*******************************"
        print "Solr status"
        print "******************************* \n"
        if not solr.solr_status():
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


def set_local_mirror(mirror_url):
    try:
        os.path.exists(mirror_url)
        esg_property_manager.set_property("use_local_mirror", True)
        esg_property_manager.set_property("local_mirror", mirror_url)
    except OSError:
        logger.error("Local mirror {} not found".format(mirror_url))
        raise

#Formerly get_bit_value
def set_node_type_value(node_type, config_file=config["esg_config_type_file"]):

    check_for_valid_node_type(node_type)

    if "all" in node_type:
        node_type = ["data", "index", "idp", "compute"]

    node_type = [node.upper() for node in node_type]
    with open(config_file, "w") as esg_config_file:
        esg_config_file.write(" ".join(node_type))


def check_for_valid_node_type(node_type_args):
    '''The observed valid combinations appear to be as follows: "all" "index idp" and "data";
    raise error and exit if an invalid node combination is given'''
    valid_node_types = ["all", "idp index", "data", "compute data idp index"]
    node_type_args = [node.lower() for node in node_type_args]
    node_type = " ".join(sorted(node_type_args))

    logger.debug("node_type: %s", node_type)

    if node_type not in valid_node_types:
        raise InvalidNodeTypeError("%s is not a valid node type.\n The valid node types are: 'all', 'idp index', 'data', 'compute data idp index'", node_type)

    return True

def process_arguments():

    parser = esg_cli.argparser()

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
        node_type_list = esg_functions.get_node_type()
        check_for_valid_node_type(node_type_list)
        return node_type_list + ["INSTALL"]
    if args.update or args.upgrade:
        if args.type:
            set_node_type_value(args.type)
        logger.debug("Update Services")
        if args.base:
            return ["INSTALL"]
        node_type_list = esg_functions.get_node_type()
        check_for_valid_node_type(node_type_list)
        return node_type_list + ["INSTALL"]
    if args.fixperms:
        logger.debug("fixing permissions")
        esg_functions.setup_whitelist_files()
        sys.exit(0)
    if args.installlocalcerts:
        logger.debug("installing local certs")
        esg_functions.get_node_type()
        node_type_list = esg_functions.get_node_type()
        from esgf_utilities import esg_cert_manager
        esg_cert_manager.install_local_certs(node_type_list)
        sys.exit(0)
    if args.generateesgfcsrs:
        logger.debug("generating esgf csrs")
        node_type_list = esg_functions.get_node_type()
        from esgf_utilities import esg_cert_manager
        esg_cert_manager.generate_esgf_csrs(node_type_list)
        sys.exit(0)
    if args.generateesgfcsrsext:
        logger.debug("generating esgf csrs for other node")
        node_type_list = esg_functions.get_node_type()
        from esgf_utilities import esg_cert_manager
        esg_cert_manager.generate_esgf_csrs_ext(node_type_list)
        sys.exit(0)
    if args.certhowto:
        cert_howto()
        sys.exit(0)
    elif args.type:
        set_node_type_value(args.type)
        sys.exit(0)
    elif args.settype:
        logger.debug("Selecting type for next start up")
        logger.debug("args.settype %s", args.settype)
        set_node_type_value(args.settype)
        sys.exit(0)
    elif args.gettype:
        print esg_functions.get_node_type(config["esg_config_type_file"])
        sys.exit(0)
    elif args.start:
        logger.debug("args: %s", args)
        node_type_list = esg_functions.get_node_type()
        logger.debug("START SERVICES: %s", node_type_list)
        start(node_type_list)
        sys.exit(0)
    elif args.stop:
        logger.debug("STOP SERVICES")
        node_type_list = esg_functions.get_node_type()
        stop(node_type_list)
        sys.exit(0)
    elif args.restart:
        logger.debug("RESTARTING SERVICES")
        node_type_list = esg_functions.get_node_type()
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
        node_type_list = esg_functions.get_node_type()
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
        node_type_list = esg_functions.get_node_type()
        from data_node import thredds
        thredds.select_idp_peer()
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
        esg_truststore_manager.fetch_esgf_certificates()
    elif args.rebuildtrustore:
        from esgf_utilities import esg_cert_manager
        esg_cert_manager.rebuild_truststore()
    elif args.addmycerttotruststore:
        from esgf_utilities import esg_cert_manager
        esg_truststore_manager.add_my_cert_to_truststore()
    elif args.generatesslkeyandcsr:
        esg_cert_manager.generate_ssl_key_and_csr(args.generatesslkeyandcsr)
    elif args.migratetomcatcredentialstoesgf:
        from base import esg_tomcat_manager
        esg_tomcat_manager.migrate_tomcat_credentials_to_esgf()
    elif args.updatetempca:
        from esgf_utilities import CA
        logger.debug("updating temporary CA")
        CA.setup_temp_ca()
        esg_cert_manager.install_local_certs("firstrun")
    elif args.checkcerts:
        esg_cert_manager.check_certificates()
    elif args.installsslkeypair:
        from esgf_utilities import esg_keystore_manager
        key, cert = args.installsslkeypair
        esg_keystore_manager.install_keypair(key, cert)
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
        node_type_list = esg_functions.get_node_type()
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
        hostname = args.addreplicashard[0]
        port = args.addreplicashard[1]
        solr.add_shards(hostname, port)
    elif args.removereplicashard:
        hostname = args.removereplicashard[0]
        port = args.removereplicashard[1]
        solr.remove_shard(hostname, port)
    elif args.updatepublisherresources:
        from index_node import esg_search
        esg_search.setup_publisher_resources()
