"""Initializes global configuration variables"""
import os
import pwd
import platform
import socket
import multiprocessing
import logging
import yaml

logger = logging.getLogger("esgf_logger" +"."+ __name__)

def init():
    """ Return a list of all local variables."""
    # TODO make this esgf-test or esgf-prod as specified
    esgf_config_repo = "https://raw.githubusercontent.com/ESGF/esgf-config/master/esgf-prod"
    #--------------
    # User Defined / Settable (public)
    #--------------
    install_prefix = os.path.join("/","usr", "local")
    esg_root_dir = os.path.join("/","esg")
    esg_config_dir = os.path.join(esg_root_dir, "config")
    esg_config_type_file = os.path.join(esg_config_dir, "config_type")
    esgf_secret_file = os.path.join(esg_config_dir, ".esgf_pass")
    pg_secret_file = os.path.join(esg_config_dir, ".esg_pg_pass")
    pub_secret_file = os.path.join(esg_config_dir, ".esg_pg_publisher_pass")
    ks_secret_file = os.path.join(esg_config_dir, ".esg_keystore_pass")
    install_manifest = os.path.join(esg_root_dir, "esgf-install-manifest")
    envfile = "/etc/esg.env"

    #--------------------------------
    # Internal esgf node code versions
    #--------------------------------

    esgcet_version = "2.6a0"
    publisher_tag = "v2.6a0"

    esgprep_version="2.8.1"

    #see esgf-node-manager project:
    esgf_node_manager_version = "1.0.1"

    esgf_node_manager_db_version = "0.1.5"

    #see esgf-security project:
    esgf_security_version = "2.7.17"
    esgf_security_db_version = "0.1.5"

    #see esg-orp project:
    esg_orp_version = "2.9.10"

    #see esgf-idp project:
    esgf_idp_version = "2.7.14"

    #see esg-search project:
    esg_search_version = "4.15.8"

    #see esgf-web-fe project:

    #see esgf-dashboard project:
    esgf_dashboard_version = "1.5.19"
    esgf_dashboard_db_version = "0.0.2"

    #see esgf-desktop project:
    esgf_desktop_version = "0.0.22"

    esgf_stats_api_version = "1.0.5"
    #--------------------------------
    # External programs' versions
    #--------------------------------
    java_version = "1.8.0_162"
    java_min_version = "1.8.0_162"
    postgress_version = "8.4.20"
    postgress_min_version = "8.4.20"
    tomcat_version = "8.5.9"
    tomcat_min_version = "8.5.9"
    tds_version = "5.0.2"
    tds_min_version = "5.0.2"
    sqlalchemy_version = "0.7.10"
    sqlalchemy_min_version = "0.7.10"
    python_version = "2.7"

    #--------------------------------
    # Script vars (~external)
    #--------------------------------
    openssl_install_dir = os.path.join(install_prefix, "openssl")
    postgress_install_dir = os.path.join("/","var", "lib", "pgsql")
    postgress_bin_dir = os.path.join("/","usr", "bin")
    postgress_lib_dir = os.path.join("/","usr", "lib64", "pgsql")
    postgress_user = "dbsuper"
    pg_sys_acct_passwd = "changeme"
    pub_secret = ""
    publisher_db_user_passwd = ""
    try:
        with open(pub_secret_file, 'rb') as filedata:
            pub_secret = filedata.read().strip()
        publisher_db_user_passwd = pub_secret
    except IOError, error:
        logger.debug(error)

    postgress_host = "localhost"
    postgress_port = "5432"
    # Double Check HERE
    cdat_home = os.path.join(install_prefix, "uvcdat", "2.2.0")
    java_opts = ""
    java_install_dir = os.path.join(install_prefix, "java")
    ant_install_dir = os.path.join(install_prefix, "ant")
    tomcat_install_dir = os.path.join(install_prefix, "tomcat")
    tomcat_conf_dir = os.path.join(esg_config_dir, "tomcat")
    tomcat_opts = ""
    tomcat_user = "tomcat"
    tomcat_group = tomcat_user
    globus_location = os.path.join(install_prefix, "globus")
    socket_fqdn = socket.getfqdn().split('.', 1)
    if len(socket_fqdn) > 1:
        mail_smtp_host = "smtp."+socket_fqdn[1]
    mail_admin_address = ""
    publisher_home = ""
    publisher_config = ""
    ESGINI = ""
    try:
        os.environ["ESGINI"]
    except KeyError:
        publisher_home = os.path.join(esg_config_dir, "esgcet")
        publisher_config = "esg.ini"
        ESGINI = os.path.join(publisher_home, publisher_config)

    ############################################
    ####  DO NOT EDIT BELOW THIS POINT!!!!! ####
    ############################################

    myPATH = os.environ["OPENSSL_HOME"] + "/bin:" + os.environ["JAVA_HOME"] + "/bin:" + \
        os.environ["ANT_HOME"] + "/bin:" + os.environ["CDAT_HOME"] + "/bin:" + \
        os.environ["CDAT_HOME"] + "/Externals/bin:" + os.environ["CATALINA_HOME"] + \
        "/bin:" + os.environ["GLOBUS_LOCATION"] + "/bin:" + install_prefix + \
        "/bin:/sbin:/usr/bin:/usr/sbin"

    myLD_LIBRARY_PATH = os.environ["OPENSSL_HOME"] + "/lib:" + \
        os.environ["CDAT_HOME"] + "/Externals/lib:" + \
        os.environ["GLOBUS_LOCATION"] + "/lib:" + \
        install_prefix + "/geoip/lib:/usr/lib64:/usr/lib"

    os.environ["PATH"] = myPATH + ':' + os.environ["PATH"]
    PATH = myPATH + ':' + os.environ["PATH"]

    LD_LIBRARY_PATH = "/usr/local/conda/envs/esgf-pub/lib/:/usr/local/conda/envs/esgf-pub/lib/python2.7/:/usr/local/conda/envs/esgf-pub/lib/python2.7/site-packages/mod_wsgi/server"

    #--------------
    # ID Setting
    #--------------
    installer_user = pwd.getpwuid(os.getuid())[0]
    installer_uid = pwd.getpwnam(installer_user).pw_uid
    installer_gid = pwd.getpwnam(installer_user).pw_gid
    installer_home = os.path.join("/usr", "local", "src", "esgf")

    #--------------
    # Script vars (internal)
    #--------------
    esg_backup_dir = os.path.join(esg_root_dir, "backups")
    esg_log_dir = os.path.join(esg_root_dir, "log")
    esg_tools_dir = os.path.join(esg_root_dir, "tools")
    esg_etc_dir = os.path.join(esg_root_dir, "etc")
    workdir = os.path.join(installer_home, "workbench", "esg")
    word_size = platform.architecture()[0].split('bit')[0]
    number_of_cpus = multiprocessing.cpu_count()
    date_format = "+%Y_%m_%d_%H%M%S"
    num_backups_to_keep = "7"
    compress_extensions = ".tar.gz|.tar.bz2|.tgz|.bz2|.tar"
    certificate_extensions = "pem|crt|cert|key"
    esgf_dist_mirror = os.path.join("http://aims1.llnl.gov", "esgf")
    esg_dist_url_root = os.path.join(esgf_dist_mirror, "dist")
    esgf_coffee_dist_mirror = "distrib-coffee.ipsl.jussieu.fr/pub/esgf"
    esg_coffee_dist_url_root = os.path.join(esgf_coffee_dist_mirror, "dist")
    java_dist_url = "%s/java/%s/jdk%s-%s.tar.gz" % (
        esg_dist_url_root, java_version, java_version, word_size)
    java_rpm_url = "{0}/java/{1}/jdk-8u112-linux-x64.rpm".format(
        esg_dist_url_root, java_version)
    ant_dist_url = "http://archive.apache.org/dist/ant/binaries/apache-ant-" + \
        ant_version + "-bin.tar.gz"
    openssl_workdir = os.path.join(workdir, "openssl")
    esgf_dashboard_ip_workdir = os.path.join(workdir, "esgf-dashboard-ip")
    db_database = "esgcet"
    node_db_name = db_database
    postgress_jar = "postgresql-8.4-703.jdbc3.jar"
    postgress_driver = "org.postgresql.Driver"
    postgress_protocol = "jdbc:postgresql:"
    pg_sys_acct = "postgres"
    pg_sys_acct_group = pg_sys_acct
    publisher_repo = "git://github.com/ESGF/esg-publisher.git"
    apache_frontend_repo = "https://github.com/ESGF/apache-frontend.git"
    publisher_repo_https = "https://github.com/ESGF/esg-publisher.git"
    esg_testdir = workdir + "/../esg_test"
    tomcat_major_version = tomcat_version.split(".")[0]
    tomcat_http_path = "http://archive.apache.org/dist/tomcat/tomcat"
    tomcat_dist_url = tomcat_http_path+"-{0}/v{1}/bin/apache-tomcat-{1}.tar.gz".format(
        tomcat_major_version, tomcat_version)
    tomcat_pid_file = "/var/run/tomcat-jsvc.pid"
    thredds_content_dir = os.path.join(esg_root_dir, "content")
    # #NOTE: This root dir should match a root set in the thredds setup
    thredds_root_dir = os.path.join(esg_root_dir, "data")
    thredds_replica_dir = os.path.join(thredds_root_dir, "replica")
    # #NOTE: This is another RedHat/CentOS specific portion!!! it will break on another OS!
    show_summary_latch = 0
    source_latch = "0"
    scripts_dir = os.path.join(install_prefix, "bin")
    esg_installarg_file = os.path.join(scripts_dir, "esg-installarg")
    no_globus = False
    force_install = False
    extkeytool_download_url= esg_dist_url_root + "/etc/idptools.tar.gz"
    tomcat_users_file = os.path.join(tomcat_conf_dir, "tomcat-users.xml")
    keystore_file = os.path.join(tomcat_conf_dir, "keystore-tomcat")
    keystore_alias = "my_esgf_node"
    keystore_password = ""
    truststore_file = os.path.join(tomcat_conf_dir, "esg-truststore.ts")
    truststore_password = "changeit"
    globus_global_certs_dir = "/etc/grid-security/certificates"
    # #NOTE: java keystore style DN...
    # default_dname="OU=ESGF.ORG, O=ESGF" #zoiks: allow this to be empty to
    # allow prompting of user for fields!
    # zoiks: allow this to be empty to allow prompting of user for fields!
    default_distinguished_name = "OU=ESGF.ORG, O=ESGF"
    property_file = os.path.join(esg_config_dir, "esgf.properties")
    index_config = "master slave"


    with open("esg_config.yaml", "w") as esg_config:
        yaml.dump(locals(), esg_config)


    return locals()

if __name__ == "__main__":
    init()
