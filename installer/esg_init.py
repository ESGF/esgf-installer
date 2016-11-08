import re
import os
import subprocess
import pwd
import sys
# from pwd import getpwnam
import esg_bash2py



class EsgInit(object):


	'''
		Public

	'''
	#--------------
	# User Defined / Settable (public)
	#--------------

	# _t=${0%.*} <- 	Strip shortest match of $substring from back of $string
	t = sys.argv[0]
	# _t = subprocess.Popen("${t%.*}")
	print sys.argv[0]
	# print "_t: ", _t.communicate()
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
	# logfile = subprocess.Popen('${logfile:-"/tmp/${_t##*/}.out"}', shell=True)
	# #--------------

	def __init__(self):
		print "initializing"

	def populate_internal_esgf_node_code_versions(self):
	    #--------------------------------
	    # Internal esgf node code versions
	    #--------------------------------
	    internal_code_versions = {}
	    internal_code_versions["apache_frontend_version"] = esg_bash2py.Expand.colonMinus(
	        "apache_frontend_version", "v1.02")
	    internal_code_versions["cdat_version"] = esg_bash2py.Expand.colonMinus("cdat_version", "2.2.0")
	# #    cdat_tag="1.5.1.esgf-v1.7.0"

	    internal_code_versions["esgcet_version"] = esg_bash2py.Expand.colonMinus("esgcet_version", "3.0.1")
	    internal_code_versions["publisher_tag"] = esg_bash2py.Expand.colonMinus("publisher_tag", "v3.0.1")

	#     #see esgf-node-manager project:
	    internal_code_versions["esgf_node_manager_version"] = esg_bash2py.Expand.colonMinus(
	        "esgf_node_manager_version", "0.7.16")
	    internal_code_versions["esgf_node_manager_db_version"] = esg_bash2py.Expand.colonMinus(
	        "esgf_node_manager_db_version", "0.1.5")
	    # return internal_code_versions

	#     #see esgf-security project:
	    internal_code_versions["esgf_security_version"] = esg_bash2py.Expand.colonMinus(
	        "esgf_security_version", "2.7.6")
	    internal_code_versions["esgf_security_db_version"] = esg_bash2py.Expand.colonMinus(
	        "esgf_security_db_version", "0.1.5")

	#     #see esg-orp project:
	    internal_code_versions["esg_orp_version"] = esg_bash2py.Expand.colonMinus(
	        "esg_orp_version", "2.8.10")

	#     #see esgf-idp project:
	    internal_code_versions["esgf_idp_version"] = esg_bash2py.Expand.colonMinus(
	        "esgf_idp_version", "2.7.2")

	#     #see esg-search project:
	    internal_code_versions["esg_search_version"] = esg_bash2py.Expand.colonMinus(
	        "esg_search_version", "4.8.4")

	#     #see esgf-web-fe project:
	    internal_code_versions["esgf_web_fe_version"] = esg_bash2py.Expand.colonMinus(
	        "esgf_web_fe_version", "2.6.5")

	#     #see esgf-dashboard project:
	    internal_code_versions["esgf_dashboard_version"] = esg_bash2py.Expand.colonMinus(
	        "esgf_dashboard_version", "1.3.18")
	    internal_code_versions["esgf_dashboard_db_version"] = esg_bash2py.Expand.colonMinus(
	        "esgf_dashboard_db_version", "0.01")

	#     #see esgf-desktop project:
	    internal_code_versions["esgf_desktop_version"] = esg_bash2py.Expand.colonMinus(
	        "esgf_desktop_version", "0.0.20")
	    return internal_code_versions

# def init():


#     #--------------------------------
#     # External programs' versions
#     #--------------------------------
#     openssl_version = esg_bash2py.Expand.colonMinus(
#         "openssl_version", "0.9.8r")
#     openssl_min_version = esg_bash2py.Expand.colonMinus(
#         "openssl_min_version", "0.9.8e")
#     openssl_max_version = esg_bash2py.Expand.colonMinus(
#         "openssl_max_version", "0.9.9z")
#     java_version = esg_bash2py.Expand.colonMinus("java_version", "1.8.0_92")
#     java_min_version = esg_bash2py.Expand.colonMinus(
#         "java_min_version", "1.8.0_92")
#     ant_version = esg_bash2py.Expand.colonMinus("ant_version", "1.9.1")
#     ant_min_version = esg_bash2py.Expand.colonMinus("ant_min_version", "1.9.1")
#     postgress_version = esg_bash2py.Expand.colonMinus(
#         "postgress_version", "8.4.20")
#     postgress_min_version = esg_bash2py.Expand.colonMinus(
#         "postgress_min_version", "8.4.20")
#     tomcat_version = esg_bash2py.Expand.colonMinus("tomcat_version", "8.0.33")
#     tomcat_min_version = esg_bash2py.Expand.colonMinus(
#         "tomcat_min_version", "8.0.33")
#     tds_version = esg_bash2py.Expand.colonMinus("tds_version", "5.0.0")
#     tds_min_version = esg_bash2py.Expand.colonMinus("tds_min_version", "5.0.0")
#     python_version = esg_bash2py.Expand.colonMinus("python_version", "2.7")
#     # cmake_version=${cmake_version:="2.8.12.2"} ; cmake_min_version=${cmake_min_version:="2.8.10.2"} ; cmake_max_version=${cmake_max_version:="2.8.12.2"}
#     # Since ESGF 1.8, LAS version is declared in esg-product-server
#     # las_version=${las_version:-"8.1"};
#     # las_min_version=${las_min_version:-"8.1"}

#     #--------------------------------
#     # Script vars (~external)
#     #--------------------------------
#     openssl_install_dir = esg_bash2py.Expand.colonMinus(
#         "OPENSSL_HOME", install_prefix + "/openssl")
#     postgress_install_dir = esg_bash2py.Expand.colonMinus(
#         "PGHOME", "/var/lib/pgsql")
#     postgress_bin_dir = esg_bash2py.Expand.colonMinus("PGBINDIR", "/usr/bin")
#     postgress_lib_dir = esg_bash2py.Expand.colonMinus(
#         "PGLIBDIR", "/usr/lib64/pgsql")
#     postgress_user = esg_bash2py.Expand.colonMinus("PGUSER", "dbsuper")

#     # local pg_secret=$(cat ${pg_secret_file} 2> /dev/null)
#     # pg_secret = subprocess.Popen("cat " + pg_secret_file + " 2>/dev/null ")
#     # pg_sys_acct_passwd=${pg_sys_acct_passwd:=${pg_secret:=changeme}}
#     pg_sys_acct_passwd = esg_bash2py.Expand.colonMinus(
#         "pg_sys_acct_passwd", esg_bash2py.Expand.colonMinus("pg_secret", "changeme"))
#     # del pg_secret
#     # local pub_secret=$(cat ${pub_secret_file} 2> /dev/null)
#     # pub_secret = subprocess.Popen("cat " + pub_secret_file + " 2>/dev/null ")
#     # publisher_db_user_passwd=${publisher_db_user_passwd:-${pub_secret}}
#     # publisher_db_user_passwd = esg_bash2py.Expand.colonMinus(
#     # "publisher_db_user_passwd", pub_secret)
#     # del pub_secret
#     postgress_host = esg_bash2py.Expand.colonMinus("PGHOST", "localhost")
#     postgress_port = esg_bash2py.Expand.colonMinus("PGPORT", "5432")
#     # #cmake_install_dir=${CMAKE_HOME:-${install_prefix}/cmake}
#     cdat_home = esg_bash2py.Expand.colonMinus(
#         "CDAT_HOME", install_prefix + "/uvcdat/" + cdat_version)
#     java_opts = esg_bash2py.Expand.colonMinus("JAVA_OPTS", "")
#     java_install_dir = esg_bash2py.Expand.colonMinus(
#         "JAVA_HOME", install_prefix + "/java")
#     ant_install_dir = esg_bash2py.Expand.colonMinus(
#         "ANT_HOME", install_prefix + "/ant")
#     tomcat_install_dir = esg_bash2py.Expand.colonMinus(
#         "CATALINA_HOME", install_prefix + "/tomcat")
#     tomcat_conf_dir = esg_config_dir + "/tomcat"
#     tomcat_opts = esg_bash2py.Expand.colonMinus("CATALINA_OPTS")
#     tomcat_user = esg_bash2py.Expand.colonMinus("tomcat_user", "tomcat")
#     tomcat_group = esg_bash2py.Expand.colonMinus("tomcat_group", tomcat_user)
#     globus_location = esg_bash2py.Expand.colonMinus(
#         "GLOBUS_LOCATION", install_prefix + "/globus")
#     mail_smtp_host = esg_bash2py.Expand.colonMinus(
#         "mail_smtp_host", "smtp.`hostname --domain`")
#     mail_admin_address = esg_bash2py.Expand.colonMinus("mail_admin_address")

#     # if [ -n "${ESGINI}" ]; then
#     #     publisher_home=${ESGINI%/*} <- 	Strip shortest match of $substring from back of $string
#     #     publisher_config=${ESGINI##*/}
#     # fi
#     try:
#         os.environ["ESGINI"]
#     except KeyError:
#         print "Key not found"
#     else:
#         publisher_home = subprocess.Popen("${ESGINI%/*}", shell=True)
#         publisher_config = subprocess.Popen("${ESGINI##*/}", shell=True)

#     ############################################
#     ####  DO NOT EDIT BELOW THIS POINT!!!!! ####
#     ############################################
#     # export GIT_SSL_NO_VERIFY=1 -> os.environ['DISCOVERONLY'] =
#     # Expand.colonMinus("DISCOVERONLY")
#     os.environ['GIT_SSL_NO_VERIFY'] = "1"
#     os.environ['OPENSSL_HOME'] = openssl_install_dir
#     os.environ['PGHOME'] = postgress_install_dir
#     os.environ['PGBINDIR'] = postgress_bin_dir
#     os.environ['PGLIBDIR'] = postgress_lib_dir
#     os.environ['PGUSER'] = postgress_user
#     os.environ['PGHOST'] = postgress_host
#     os.environ['PGPORT'] = postgress_port
#     # #export CMAKE_HOME=${cmake_install_dir}`
#     os.environ['CDAT_HOME'] = cdat_home
#     os.environ['JAVA_HOME'] = java_install_dir
#     os.environ['JAVA_OPTS'] = java_opts
#     os.environ['ANT_HOME'] = ant_install_dir
#     os.environ['CATALINA_HOME'] = tomcat_install_dir
#     os.environ['CATALINA_BASE'] = os.environ["CATALINA_HOME"]
#     os.environ['CATALINA_OPTS'] = tomcat_opts
#     os.environ['GLOBUS_LOCATION'] = globus_location

#     # myPATH=$OPENSSL_HOME/bin:$CMAKE_HOME/bin:$JAVA_HOME/bin:$ANT_HOME/bin:$CDAT_HOME/bin:$CDAT_HOME/Externals/bin:$CATALINA_HOME/bin:$GLOBUS_LOCATION/bin:${install_prefix}/bin:/bin:/sbin:/usr/bin:/usr/sbin
#     myPATH = os.environ["OPENSSL_HOME"] + "/bin:" + os.environ["JAVA_HOME"] + "/bin:" + os.environ["ANT_HOME"] + "/bin:" + os.environ["CDAT_HOME"] + "/bin:" + os.environ[
#         "CDAT_HOME"] + "/Externals/bin:" + os.environ["CATALINA_HOME"] + "/bin:" + os.environ["GLOBUS_LOCATION"] + "/bin:" + install_prefix + "/bin:/sbin:/usr/bin:/usr/sbin"
#     print "myPATH: ", myPATH
#     # myLD_LIBRARY_PATH=$OPENSSL_HOME/lib:$CDAT_HOME/Externals/lib:$GLOBUS_LOCATION/lib:${install_prefix}/geoip/lib:/usr/lib64:/usr/lib
#     myLD_LIBRARY_PATH = os.environ["OPENSSL_HOME"] + "/lib:" + os.environ["CDAT_HOME"] + "/Externals/lib:" + \
#         os.environ["GLOBUS_LOCATION"] + "/lib:" + \
#         install_prefix + "/geoip/lib:/usr/lib64:/usr/lib"
#     print "myLD_LIBRARY_PATH: ", myLD_LIBRARY_PATH
#     # export PATH=$(_path_unique $myPATH:$PATH)
#     # export LD_LIBRARY_PATH=$(_path_unique $myLD_LIBRARY_PATH:$LD_LIBRARY_PATH)
#     # export CFLAGS="-I${OPENSSL_HOME}/include -I/usr/include ${CFLAGS} -fPIC"
#     # export LDFLAGS="-L${OPENSSL_HOME}/lib -L/usr/lib64 -L/usr/lib
#     # -Wl,--rpath,${OPENSSL_HOME}/lib"

#     #--------------
#     # ID Setting
#     #--------------
#     # fix: id will always return the root id no matter what flags we use if we start this via sudo
#     # installer_user=${ESG_USER:-${SUDO_USER:-$(echo $HOME | sed
#     # 's#.*/\([^/]\+\)/\?$#\1#')}}
#     installer_user = esg_bash2py.Expand.colonMinus("ESG_USER", esg_bash2py.Expand.colonMinus("SUDO_USER", subprocess.Popen("$(echo $HOME | sed 's#.*/\([^/]\+\)/\?$#\1#')", shell=True)))
#     # installer_uid=${ESG_USER_UID:-${SUDO_UID:-$(id -u $installer_user)}}
#     installer_uid = esg_bash2py.Expand.colonMinus("ESG_USER_UID", esg_bash2py.Expand.colonMinus(
#         "SUDO_UID", pwd.getpwnam('installer_user').pw_uid))
#     # installer_gid=${ESG_USER_GID:-${SUDO_GID:-$(id -g $installer_user)}}
#     installer_gid = esg_bash2py.Expand.colonMinus("ESG_USER_GID", esg_bash2py.Expand.colonMinus(
#         "SUDO_GID", pwd.getpwnam('installer_user').pw_gid))
#     # installer_home=${ESG_USER_HOME:-/usr/local/src/esgf}
#     installer_home = esg_bash2py.Expand.colonMinus(
#         "ESG_USER_HOME", "/usr/local/src/esgf")

#     # #deprecate SUDO_?ID so we only use one variable for all this
#     # [[ $SUDO_UID ]] && ESG_USER_UID=${SUDO_UID} && unset SUDO_UID
#     try:
#         os.environ["SUDO_UID"]
#     except KeyError:
#         print "SUDO_UID not found"
#     else:
#         os.environ["ESG_USER_UID"] = os.environ["SUDO_UID"]
#         del os.environ["SUDO_UID"]

#     # [[ $SUDO_GID ]] && ESG_USER_GID=${SUDO_GID} && unset SUDO_GID
#     try:
#         os.environ["SUDO_GID"]
#     except KeyError:
#     	print "SUDO_GID not found"
#     else:
#     	os.environ["ESG_USER_GID"] = os.environ["SUDO_GID"]
#     	del os.environ["SUDO_GID"]


 

#     # verbose_print
#     # "${installer_user}:${installer_uid}:${installer_gid}:${installer_home}"
#     print "%s:%s:%s:%s" % (installer_user, installer_uid, installer_gid, installer_home)


#     #--------------
#     # Script vars (internal)
#     #--------------
#     # esg_backup_dir=${esg_backup_dir:-"${esg_root_dir}/backups"}
#     esg_backup_dir = esg_bash2py.Expand.colonMinus("esg_backup_dir", esg_root_dir+"/backups")
#     # esg_config_dir=${esg_config_dir:-"${esg_root_dir}/config"}
#     esg_config_dir = esg_bash2py.Expand.colonMinus("esg_config_dir", esg_root_dir+"/config")
#     # esg_log_dir=${esg_log_dir:-"${esg_root_dir}/log"}
#     esg_log_dir = esg_bash2py.Expand.colonMinus("esg_log_dir", esg_root_dir+"/log")
#     # esg_tools_dir=${esg_tools_dir:-"${esg_root_dir}/tools"}
#     esg_tools_dir = esg_bash2py.Expand.colonMinus("esg_tools_dir", esg_root_dir+"/tools")
#     # esg_etc_dir=${esg_etc_dir:-"${esg_root_dir}/etc"}
#     esg_etc_dir = esg_bash2py.Expand.colonMinus("esg_etc_dir", esg_root_dir+"/etc")
#     # workdir=${workdir:-${ESGF_INSTALL_WORKDIR:-${installer_home}/workbench/esg}}
#     workdir = esg_bash2py.Expand.colonMinus("workdir", esg_bash2py.Expand.colonMinus("ESGF_INSTALL_WORKDIR", installer_home+"/workbench/esg"))

#     # word_size=${word_size:-$(file /bin/bash | perl -ple 's/^.*ELF\s*(32|64)-bit.*$/$1/g')}
#     word_size = esg_bash2py.Expand.colonMinus("word_size", subprocess.Popen("$(file /bin/bash | perl -ple 's/^.*ELF\s*(32|64)-bit.*$/$1/g')"), shell=True )
#     # let num_cpus=1+$(cat /proc/cpuinfo | sed -n 's/^processor[ \t]*:[ \t]*\(.*\)$/\1/p' | tail -1)
#     num_cpus = 1 + subprocess.Popen("$(cat /proc/cpuinfo | sed -n 's/^processor[ \t]*:[ \t]*\(.*\)$/\1/p' | tail -1)", shell = True)
#     # date_format="+%Y_%m_%d_%H%M%S"
#     date_format = subprocess.Popen("+%Y_%m_%d_%H%M%S", shell = True)
#     # num_backups_to_keep=${num_backups_to_keep:-7}
#     num_backups_to_keep = esg_bash2py.Expand.colonMinus("num_backups_to_keep", "7")
#     # compress_extensions=".tar.gz|.tar.bz2|.tgz|.bz2|.tar"
#     compress_extensions = ".tar.gz|.tar.bz2|.tgz|.bz2|.tar"
#     # certificate_extensions="pem|crt|cert|key"
#     certificate_extensions = "pem|crt|cert|key"


#     # openssl_dist_url=http://www.openssl.org/source/openssl-${openssl_version}.tar.gz
#     openssl_dist_url = "http://www.openssl.org/source/openssl-" + openssl_version + ".tar.gz"
#     # java_dist_url=${esg_dist_url_root}/java/${java_version}/jdk${java_version}-${word_size}.tar.gz
#     # java_dist_url="$%s/java/$%s/jdk$%s-$%s.tar.gz" % (esg_dist_url_root, java_version, java_version, word_size)
#     # ant_dist_url=http://archive.apache.org/dist/ant/binaries/apache-ant-${ant_version}-bin.tar.gz
#     ant_dist_url= "http://archive.apache.org/dist/ant/binaries/apache-ant-"+ ant_version + "-bin.tar.gz"
#     # openssl_workdir=${workdir}/openssl
#     openssl_workdir=workdir+"/openssl"
#     # esgf_dashboard_ip_workdir=${workdir}/esgf-dashboard-ip
#     esgf_dashboard_ip_workdir = workdir+"/esgf-dashboard-ip"
#     # bash_completion_url=${esg_dist_url}/thirdparty/bash-completion-20060301-1.noarch.rpm
#     # bash_completion_url = esg_dist_url + "/thirdparty/bash-completion-20060301-1.noarch.rpm"
#     # db_database=${ESGF_DB_NAME:-${db_database:-"esgcet"}}
#     db_database = esg_bash2py.Expand.colonMinus("ESGF_DB_NAME", esg_bash2py.Expand.colonMinus("db_database", "esgcet"))
#     # node_db_name=${db_database}
#     node_db_name = db_database
#     # postgress_jar=postgresql-8.4-703.jdbc3.jar
#     postgress_jar="postgresql-8.4-703.jdbc3.jar"
#     # postgress_driver=org.postgresql.Driver
#     postgress_driver="org.postgresql.Driver"
#     # postgress_protocol=jdbc:postgresql:
#     postgress_protocol="jdbc:postgresql:"
#     # pg_sys_acct=${pg_sys_acct:-postgres}
#     pg_sys_acct = esg_bash2py.Expand.colonMinus("pg_sys_acct", "postgres")
#     # pg_sys_acct_group=${pg_sys_acct_group:-$pg_sys_acct}
#     pg_sys_acct_group = esg_bash2py.Expand.colonMinus("pg_sys_acct_group", pg_sys_acct)
#     # #cmake_workdir=${workdir}/cmake
#     # #cmake_repo=http://www.cmake.org/cmake.git
#     # #cdat_repo=git://github.com/UV-CDAT/uvcdat.git
#     # #cdat_repo_https=https://github.com/UV-CDAT/uvcdat.git
#     # publisher_repo=git://github.com/ESGF/esg-publisher.git
#     publisher_repo="git://github.com/ESGF/esg-publisher.git"
#     # apache_frontend_repo=https://github.com/ESGF/apache-frontend.git
#     apache_frontend_repo="https://github.com/ESGF/apache-frontend.git"
#     # publisher_repo_https=https://github.com/ESGF/esg-publisher.git
#     publisher_repo_https="https://github.com/ESGF/esg-publisher.git"
#     # esgcet_egg_file=esgcet-${esgcet_version}-py${python_version}.egg
#     esgcet_egg_file="esgcet-%s-py%s.egg" % (esgcet_version, python_version)
#     # esg_testdir=${workdir}/../esg_test
#     esg_testdir = workdir+ "/../esg_test"
#     # tomcat_dist_url=http://archive.apache.org/dist/tomcat/tomcat-${tomcat_version%%.*}/v${tomcat_version}/bin/apache-tomcat-${tomcat_version}.tar.gz
#     # tomcat_pid_file=/var/run/tomcat-jsvc.pid
#     tomcat_pid_file="/var/run/tomcat-jsvc.pid"
#     # utils_url=${esg_dist_url}/utils
#     # utils_url = esg_dist_url+"/utils"
#     # thredds_dist_url=ftp://ftp.unidata.ucar.edu/pub/thredds/${tds_version%.*}/${tds_version}/thredds.war
#     # thredds_esg_dist_url=${esg_dist_url}/thredds/${tds_version%.*}/${tds_version}/thredds.war
#     # thredds_content_dir=${thredds_content_dir:-${esg_root_dir}/content}
#     thredds_content_dir = esg_bash2py.Expand.colonMinus("thredds_content_dir", esg_root_dir+"/content")
#     # #NOTE: This root dir should match a root set in the thredds setup
#     # thredds_root_dir=${esg_root_dir}/data
#     thredds_root_dir = esg_root_dir+"/data"
#     # thredds_replica_dir=${thredds_root_dir}/replica
#     thredds_replica_dir = thredds_root_dir+"/replica"
#     # #NOTE: This is another RedHat/CentOS specific portion!!! it will break on another OS!
#     # show_summary_latch=0
#     show_summary_latch="0"
#     # source_latch=0
#     source_latch="0"
#     # scripts_dir=${install_prefix}/bin
#     scripts_dir=install_prefix+ "/bin"
#     # esg_installarg_file=${scripts_dir}/esg-installarg
#     esg_installarg_file=scripts_dir + "/esg-installarg"
#     # no_globus=${no_globus:-0}
#     no_globus = esg_bash2py.Expand.colonMinus("no_globus", "0")
#     # force_install=${force_install:-0}
#     force_install = esg_bash2py.Expand.colonMinus("force_install", "0")
#     # extkeytool_download_url=${esg_dist_url}/etc/idptools.tar.gz
#     # extkeytool_download_url= esg_dist_url + "/etc/idptools.tar.gz"
#     # tomcat_users_file=${tomcat_conf_dir}/tomcat-users.xml
#     tomcat_users_file= tomcat_conf_dir + "/tomcat-users.xml"
#     # keystore_file=${tomcat_conf_dir}/keystore-tomcat
#     keystore_file= tomcat_conf_dir + "/keystore-tomcat"
#     # keystore_alias=${keystore_alias:-my_esgf_node}
#     keystore_alias = esg_bash2py.Expand.colonMinus("keystore_alias", "my_esgf_node")
#     # keystore_password=${keystore_password}
#     # truststore_file=${tomcat_conf_dir}/esg-truststore.ts
#     truststore_file= tomcat_conf_dir + "/esg-truststore.ts"
#     # truststore_password=${truststore_password:-changeit}
#     truststore_password = esg_bash2py.Expand.colonMinus("truststore_password", "changeit")
#     # globus_global_certs_dir=/etc/grid-security/certificates
#     globus_global_certs_dir="/etc/grid-security/certificates"
#     # #NOTE: java keystore style DN...
#     # default_dname="OU=ESGF.ORG, O=ESGF" #zoiks: allow this to be empty to allow prompting of user for fields!
#     default_dname="OU=ESGF.ORG, O=ESGF" #zoiks: allow this to be empty to allow prompting of user for fields!
#     # config_file=${esg_config_dir}/esgf.properties
#     config_file= esg_config_dir + "/esgf.properties"
#     # index_config="master slave"
#     index_config="master slave"




# init()
