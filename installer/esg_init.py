"""Something about module"""
import os
import pwd
import logging
import platform
import multiprocessing
#import sys

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


def init():
    """ Return a list of all local vaiables."""
    #--------------
    # User Defined / Settable (public)
    #--------------
    install_prefix = os.path.join("usr", "local")
    esg_root_dir = os.path.join("esg")
    esg_config_dir = os.path.join(esg_root_dir, "config")
    esg_config_type_file = os.path.join(esg_config_dir, "config_type")
    esgf_secret_file = os.path.join(esg_config_dir, ".esgf_pass")
    pg_secret_file = os.path.join(esg_config_dir, ".esg_pg_pass")
    pub_secret_file = os.path.join(esg_config_dir, ".esg_pg_publisher_pass")
    ks_secret_file = os.path.join(esg_config_dir, ".esg_keystore_pass")
    install_manifest = os.path.join(esg_root_dir, "esgf-install-manifest")
    envfile = os.path.join("etc", "esg.env")

    #--------------------------------
    # Internal esgf node code versions
    #--------------------------------
    apache_frontend_version = "v1.02"
    cdat_version = "2.2.0"
    # cdat_tag = "1.5.1.esgf-v1.7.0"
    esgcet_version = "3.0.1"
    publisher_tag = "v3.0.1"
    # see esgf-node-manager project:
    esgf_node_manager_version = "0.7.16"
    esgf_node_manager_db_version = "0.1.5"
    # see esgf-security project:
    esgf_security_version = "2.7.6"
    esgf_security_db_version = "0.1.5"
    # see esg-orp project:
    esg_orp_version = "2.8.10"
    # see esgf-idp project:
    esgf_idp_version = "2.7.2"
    # see esg-search project:
    esg_search_version = "4.8.4"
    # see esgf-web-fe project:
    esgf_web_fe_version = "2.6.5"
    # see esgf-dashboard project:
    esgf_dashboard_version = "1.3.18"
    esgf_dashboard_db_version = "0.01"
    # see esgf-desktop project:
    esgf_desktop_version = "0.0.20"

    #--------------------------------
    # External programs' versions
    #--------------------------------
    openssl_version = "0.9.8r"
    openssl_min_version = "0.9.8e"
    openssl_max_version = "0.9.9z"
    java_version = "1.8.0_112"
    java_min_version = "1.8.0_112"
    ant_version = "1.9.1"
    ant_min_version = "1.9.1"
    postgress_version = "8.4.20"
    postgress_min_version = "8.4.20"
    tomcat_version = "8.5.9"
    tomcat_min_version = "8.5.9"
    tds_version = "5.0.0"
    tds_min_version = "5.0.0"
    python_version = "2.7"

    #--------------------------------
    # Script vars (~external)
    #--------------------------------
    openssl_install_dir = os.path.join(install_prefix, "openssl")
    postgress_install_dir = os.path.join("var", "lib", "pgsql")
    postgress_bin_dir = os.path.join("usr", "bin")
    postgress_lib_dir = os.path("usr", "lib64", "pgsql")
    postgress_user = "dbsuper"
    pg_sys_acct_passwd = "changeme"
    pub_secret = ""
    publisher_db_user_passwd = ""
    try:
        with open(pub_secret_file, 'rb') as filedata:
            pub_secret = filedata.read().strip()
        # publisher_db_user_passwd=${publisher_db_user_passwd:-${pub_secret}}
        publisher_db_user_passwd = pub_secret
    except IOError, error:
        LOGGER.debug(error)

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
    mail_smtp_host = "smtp.`hostname --domain`"
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
    os.environ["GIT_SSL_NO_VERIFY"] = "1"
    os.environ["OPENSSL_HOME"] = openssl_install_dir
    os.environ["PGHOME"] = postgress_install_dir
    os.environ["PGBINDIR"] = postgress_bin_dir
    os.environ["PGLIBDIR"] = postgress_lib_dir
    os.environ["PGUSER"] = postgress_user
    os.environ["PGHOST"] = postgress_host
    os.environ["PGPORT"] = postgress_port
    os.environ["CDAT_HOME"] = cdat_home
    os.environ["JAVA_HOME"] = java_install_dir
    os.environ["JAVA_OPTS"] = java_opts
    os.environ["ANT_HOME"] = ant_install_dir
    os.environ["CATALINA_HOME"] = tomcat_install_dir
    os.environ["CATALINA_BASE"] = os.environ["CATALINA_HOME"]
    os.environ["CATALINA_OPTS"] = tomcat_opts
    os.environ["GLOBUS_LOCATION"] = globus_location

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
    os.environ["LD_LIBRARY_PATH"] = ""
    try:
        os.environ["LD_LIBRARY_PATH"] = myLD_LIBRARY_PATH + \
            ':' + os.environ["LD_LIBRARY_PATH"]
    except KeyError, error:
        LOGGER.error(error)
        os.environ["LD_LIBRARY_PATH"] = myLD_LIBRARY_PATH

    #--------------
    # ID Setting
    #--------------
    installer_user = pwd.getpwuid(os.getuid())[0]
    installer_uid = pwd.getpwnam(installer_user).pw_uid
    installer_gid = pwd.getpwnam(installer_user).pw_gid
    installer_home = os.path.join("usr", "local", "src", "esgf")
    try:
        os.environ["SUDO_UID"]
    except KeyError:
        # print "SUDO_UID not found"
        pass
    else:
        os.environ["ESG_USER_UID"] = os.environ["SUDO_UID"]
        del os.environ["SUDO_UID"]

    # [[ $SUDO_GID ]] && ESG_USER_GID=${SUDO_GID} && unset SUDO_GID
    try:
        os.environ["SUDO_GID"]
    except KeyError:
        # print "SUDO_GID not found"
        pass
    else:
        os.environ["ESG_USER_GID"] = os.environ["SUDO_GID"]
        del os.environ["SUDO_GID"]

    LOGGER.debug("%s:%s:%s:%s", installer_user,
                 installer_uid, installer_gid, installer_home)

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
    openssl_dist_url = os.path.join("http://www.openssl.org/source/openssl-",
                                    openssl_version, ".tar.gz")
    esgf_dist_mirror = os.path.join("aims1.llnl.gov", "esgf")
    esg_dist_url_root = os.path.join(esgf_dist_mirror, "dist")
    esgf_coffee_dist_mirror = "distrib-coffee.ipsl.jussieu.fr/pub/esgf"
    esg_coffee_dist_url_root = os.path.join(esgf_coffee_dist_mirror, "dist")
    java_dist_url = "$%s/java/$%s/jdk$%s-$%s.tar.gz" % (
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
    esgcet_egg_file = "esgcet-%s-py%s.egg" % (esgcet_version, python_version)
    esg_testdir = workdir + "/../esg_test"
    tomcat_major_version = tomcat_version.split(".")[0]
    tomcat_http_path = "http://archive.apache.org/dist/tomcat/tomcat"
    tomcat_dist_url = tomcat_http_path+"-{0}/v{1}/bin/apache-tomcat-{1}.tar.gz".format(
        tomcat_major_version, tomcat_version)
    tomcat_pid_file = "/var/run/tomcat-jsvc.pid"
    thredds_content_dir = os.path.join(esg_root_dir, "content")
    # #NOTE: This root dir should match a root set in the thredds setup
    # thredds_root_dir=${esg_root_dir}/data
    thredds_root_dir = os.path.join(esg_root_dir, "data")
    thredds_replica_dir = os.path.join(thredds_root_dir, "replica")
    # #NOTE: This is another RedHat/CentOS specific portion!!! it will break on another OS!
    show_summary_latch = 0
    source_latch = "0"
    scripts_dir = os.path.join(install_prefix, "bin")
    esg_installarg_file = os.path.join(scripts_dir, "esg-installarg")
    no_globus = "0"
    force_install = "0"
    # extkeytool_download_url=${esg_dist_url}/etc/idptools.tar.gz
    # extkeytool_download_url= esg_dist_url + "/etc/idptools.tar.gz"
    # tomcat_users_file=${tomcat_conf_dir}/tomcat-users.xml
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
    config_file = os.path.join(esg_config_dir, "esgf.properties")
    index_config = "master slave"

    return locals()
