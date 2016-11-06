import esg_bash2py
import re
import os
import subprocess
'''
	Public

'''
#--------------
# User Defined / Settable (public)
#--------------

# _t=${0%.*} <- 	Strip shortest match of $substring from back of $string
_t = subprocess.Popen("${0%.*}", shell=True)
# expected=${2:-0}  -> expected=Bash2Py(Expand.colonMinus("2","0"))

install_prefix = esg_bash2py.Expand.colonMinus(
    "install_prefix", esg_bash2py.Expand.colonMinus("ESGF_INSTALL_PREFIX", "/usr/local"))
esg_root_dir = esg_bash2py.Expand.colonMinus(
    "esg_root_dir", esg_bash2py.Expand.colonMinus("ESGF_HOME", "/esg"))
esg_config_dir = esg_root_dir + "/config"
esg_config_type_file = esg_config_dir + "/config_type"
esgf_secret_file = esg_config_dir + "/.esgf_pass"
pg_secret_file = esg_config_dir + "/.esg_pg_pass"
pub_secret_file = esg_config_dir + "/.esg_pg_publisher_pass"
ks_secret_file = esg_config_dir + "/.esg_keystore_pass"
install_manifest = esg_bash2py.Expand.colonMinus(
    "install_manifest", esg_root_dir + "/esgf-install-manifest")
# logfile=${logfile:-"/tmp/${_t##*/}.out"}
logfile = subprocess.Popen('${logfile:-"/tmp/${_t##*/}.out"}', shell=True)
# #--------------


def init():
    #--------------------------------
    # Internal esgf node code versions
    #--------------------------------
    apache_frontend_version = esg_bash2py.Expand.colonMinus(
        "apache_frontend_version", "v1.02")
    cdat_version = esg_bash2py.Expand.colonMinus("cdat_version", "2.2.0")
# #    cdat_tag="1.5.1.esgf-v1.7.0"

    esgcet_version = esg_bash2py.Expand.colonMinus("esgcet_version", "3.0.1")
    publisher_tag = esg_bash2py.Expand.colonMinus("publisher_tag", "v3.0.1")

#     #see esgf-node-manager project:
    esgf_node_manager_version = esg_bash2py.Expand.colonMinus(
        "esgf_node_manager_version", "0.7.16")
    esgf_node_manager_db_version = esg_bash2py.Expand.colonMinus(
        "esgf_node_manager_db_version", "0.1.5")

#     #see esgf-security project:
    esgf_security_version = esg_bash2py.Expand.colonMinus(
        "esgf_security_version", "2.7.6")
    esgf_security_db_version = esg_bash2py.Expand.colonMinus(
        "esgf_security_db_version", "0.1.5")

#     #see esg-orp project:
    esg_orp_version = esg_bash2py.Expand.colonMinus(
        "esg_orp_version", "2.8.10")

#     #see esgf-idp project:
    esgf_idp_version = esg_bash2py.Expand.colonMinus(
        "esgf_idp_version", "2.7.2")

#     #see esg-search project:
    esg_search_version = esg_bash2py.Expand.colonMinus(
        "esg_search_version", "4.8.4")

#     #see esgf-web-fe project:
    esgf_web_fe_version = esg_bash2py.Expand.colonMinus(
        "esgf_web_fe_version", "2.6.5")

#     #see esgf-dashboard project:
    esgf_dashboard_version = esg_bash2py.Expand.colonMinus(
        "esgf_dashboard_version", "1.3.18")
    esgf_dashboard_db_version = esg_bash2py.Expand.colonMinus(
        "esgf_dashboard_db_version", "0.01")

#     #see esgf-desktop project:
    esgf_desktop_version = esg_bash2py.Expand.colonMinus(
        "esgf_desktop_version", "0.0.20")

    #--------------------------------
    # External p rograms' versions
    #--------------------------------
    openssl_version = esg_bash2py.Expand.colonMinus(
        "openssl_version", "0.9.8r")
    openssl_min_version = esg_bash2py.Expand.colonMinus(
        "openssl_min_version", "0.9.8e")
    openssl_max_version = esg_bash2py.Expand.colonMinus(
        "openssl_max_version", "0.9.9z")
    java_version = esg_bash2py.Expand.colonMinus("java_version", "1.8.0_92")
    java_min_version = esg_bash2py.Expand.colonMinus(
        "java_min_version", "1.8.0_92")
    ant_version = esg_bash2py.Expand.colonMinus("ant_version", "1.9.1")
    ant_min_version = esg_bash2py.Expand.colonMinus("ant_min_version", "1.9.1")
    postgress_version = esg_bash2py.Expand.colonMinus(
        "postgress_version", "8.4.20")
    postgress_min_version = esg_bash2py.Expand.colonMinus(
        "postgress_min_version", "8.4.20")
    tomcat_version = esg_bash2py.Expand.colonMinus("tomcat_version", "8.0.33")
    tomcat_min_version = esg_bash2py.Expand.colonMinus(
        "tomcat_min_version", "8.0.33")
    tds_version = esg_bash2py.Expand.colonMinus("tds_version", "5.0.0")
    tds_min_version = esg_bash2py.Expand.colonMinus("tds_min_version", "5.0.0")
    python_version = esg_bash2py.Expand.colonMinus("python_version", "2.7")
    # cmake_version=${cmake_version:="2.8.12.2"} ; cmake_min_version=${cmake_min_version:="2.8.10.2"} ; cmake_max_version=${cmake_max_version:="2.8.12.2"}
    # Since ESGF 1.8, LAS version is declared in esg-product-server
    # las_version=${las_version:-"8.1"};
    # las_min_version=${las_min_version:-"8.1"}

    #--------------------------------
    # Script vars (~external)
    #--------------------------------
    openssl_install_dir = esg_bash2py.Expand.colonMinus(
        "OPENSSL_HOME", install_prefix + "/openssl")
    postgress_install_dir = esg_bash2py.Expand.colonMinus(
        "PGHOME", "/var/lib/pgsql")
    postgress_bin_dir = esg_bash2py.Expand.colonMinus("PGBINDIR", "/usr/bin")
    postgress_lib_dir = esg_bash2py.Expand.colonMinus(
        "PGLIBDIR", "/usr/lib64/pgsql")
    postgress_user = esg_bash2py.Expand.colonMinus("PGUSER", "dbsuper")

    # local pg_secret=$(cat ${pg_secret_file} 2> /dev/null)
    # pg_secret = subprocess.Popen("cat " + pg_secret_file + " 2>/dev/null ")
    # pg_sys_acct_passwd=${pg_sys_acct_passwd:=${pg_secret:=changeme}}
    pg_sys_acct_passwd = esg_bash2py.Expand.colonMinus(
        "pg_sys_acct_passwd", esg_bash2py.Expand.colonMinus("pg_secret", "changeme"))
    # del pg_secret
    # local pub_secret=$(cat ${pub_secret_file} 2> /dev/null)
    # pub_secret = subprocess.Popen("cat " + pub_secret_file + " 2>/dev/null ")
    # publisher_db_user_passwd=${publisher_db_user_passwd:-${pub_secret}}
    # publisher_db_user_passwd = esg_bash2py.Expand.colonMinus(
        # "publisher_db_user_passwd", pub_secret)
    # del pub_secret
    postgress_host = esg_bash2py.Expand.colonMinus("PGHOST", "localhost")
    postgress_port = esg_bash2py.Expand.colonMinus("PGPORT", "5432")
    # #cmake_install_dir=${CMAKE_HOME:-${install_prefix}/cmake}
    cdat_home = esg_bash2py.Expand.colonMinus(
        "CDAT_HOME", install_prefix + "/uvcdat/" + cdat_version)
    java_opts = esg_bash2py.Expand.colonMinus("JAVA_OPTS", "")
    java_install_dir = esg_bash2py.Expand.colonMinus("JAVA_HOME", install_prefix + "/java")
    ant_install_dir = esg_bash2py.Expand.colonMinus(
        "ANT_HOME", install_prefix + "/ant")
    tomcat_install_dir = esg_bash2py.Expand.colonMinus(
        "CATALINA_HOME", install_prefix + "/tomcat")
    tomcat_conf_dir = esg_config_dir + "/tomcat"
    tomcat_opts = esg_bash2py.Expand.colonMinus("CATALINA_OPTS")
    tomcat_user = esg_bash2py.Expand.colonMinus("tomcat_user", "tomcat")
    tomcat_group = esg_bash2py.Expand.colonMinus("tomcat_group", tomcat_user)
    globus_location = esg_bash2py.Expand.colonMinus(
        "GLOBUS_LOCATION", install_prefix + "/globus")
    mail_smtp_host = esg_bash2py.Expand.colonMinus(
        "mail_smtp_host", "smtp.`hostname --domain`")
    mail_admin_address = esg_bash2py.Expand.colonMinus("mail_admin_address")

    # if [ -n "${ESGINI}" ]; then
    #     publisher_home=${ESGINI%/*} <- 	Strip shortest match of $substring from back of $string
    #     publisher_config=${ESGINI##*/}
    # fi
    try: 
    	os.environ["ESGINI"]
    except KeyError:
    	print "Key not found"
    else:
        publisher_home = subprocess.Popen("${ESGINI%/*}", shell=True)
        publisher_config = subprocess.Popen("${ESGINI##*/}", shell=True)

    ############################################
    ####  DO NOT EDIT BELOW THIS POINT!!!!! ####
    ############################################
    # export GIT_SSL_NO_VERIFY=1 -> os.environ['DISCOVERONLY'] =
    # Expand.colonMinus("DISCOVERONLY")
    os.environ['GIT_SSL_NO_VERIFY'] = "1"
    os.environ['OPENSSL_HOME'] = openssl_install_dir
    os.environ['PGHOME'] = postgress_install_dir
    os.environ['PGBINDIR'] = postgress_bin_dir
    os.environ['PGLIBDIR'] = postgress_lib_dir
    os.environ['PGUSER'] = postgress_user
    os.environ['PGHOST'] = postgress_host
    os.environ['PGPORT'] = postgress_port
    # #export CMAKE_HOME=${cmake_install_dir}`
    os.environ['CDAT_HOME'] = cdat_home
    os.environ['JAVA_HOME'] = java_install_dir
    os.environ['JAVA_OPTS'] = java_opts
    os.environ['ANT_HOME'] = ant_install_dir
    os.environ['CATALINA_HOME'] = tomcat_install_dir
    os.environ['CATALINA_BASE'] = os.environ["CATALINA_HOME"]
    os.environ['CATALINA_OPTS'] = tomcat_opts
    os.environ['GLOBUS_LOCATION'] = globus_location

    # myPATH=$OPENSSL_HOME/bin:$CMAKE_HOME/bin:$JAVA_HOME/bin:$ANT_HOME/bin:$CDAT_HOME/bin:$CDAT_HOME/Externals/bin:$CATALINA_HOME/bin:$GLOBUS_LOCATION/bin:${install_prefix}/bin:/bin:/sbin:/usr/bin:/usr/sbin
    myPATH = os.environ["OPENSSL_HOME"] + "/bin:"+ os.environ["JAVA_HOME"] +"/bin:" + os.environ["ANT_HOME"] + "/bin:" + os.environ["CDAT_HOME"] + "/bin:" + os.environ["CDAT_HOME"] + "/Externals/bin:" + os.environ["CATALINA_HOME"] + "/bin:" + os.environ["GLOBUS_LOCATION"] + "/bin:" + install_prefix + "/bin:/sbin:/usr/bin:/usr/sbin"
    print "myPATH: ", myPATH
    # myLD_LIBRARY_PATH=$OPENSSL_HOME/lib:$CDAT_HOME/Externals/lib:$GLOBUS_LOCATION/lib:${install_prefix}/geoip/lib:/usr/lib64:/usr/lib
    myLD_LIBRARY_PATH = os.environ["OPENSSL_HOME"] + "/lib:" + os.environ["CDAT_HOME"] + "/Externals/lib:" + os.environ["GLOBUS_LOCATION"] + "/lib:" + install_prefix + "/geoip/lib:/usr/lib64:/usr/lib"
    print "myLD_LIBRARY_PATH: ", myLD_LIBRARY_PATH
    # export PATH=$(_path_unique $myPATH:$PATH)
    # export LD_LIBRARY_PATH=$(_path_unique $myLD_LIBRARY_PATH:$LD_LIBRARY_PATH)
    # export CFLAGS="-I${OPENSSL_HOME}/include -I/usr/include ${CFLAGS} -fPIC"
# export LDFLAGS="-L${OPENSSL_HOME}/lib -L/usr/lib64 -L/usr/lib
# -Wl,--rpath,${OPENSSL_HOME}/lib"


init()
