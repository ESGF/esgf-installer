import re
import os
import subprocess
import pwd
import sys
import magic
import logging
# from pwd import getpwnam
import esg_functions
import esg_bash2py


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
class EsgInit(object):

    '''
            Public

    '''
    #--------------
    # User Defined / Settable (public)
    #--------------
    # Note: got no output for _t or logfile variables when testing on pcmdi7
    # _t=${0%.*} <-     Strip shortest match of $substring from back of $string
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
    envfile = "/etc/esg.env"
    config_dictionary = {}
    # #--------------

    def __init__(self):
        print "initializing"
        self.populate_internal_esgf_node_code_versions()
        self.populate_external_programs_versions()
        self.populate_external_script_variables()
        self.populate_environment_constants()
        self.populate_id_settings()
        self.populate_internal_script_variables()

    def populate_internal_esgf_node_code_versions(self):
        '''
        #--------------------------------
        # Internal esgf node code versions
        #--------------------------------
        '''
        internal_code_versions = {}
        internal_code_versions["apache_frontend_version"] = esg_bash2py.Expand.colonMinus(
            "apache_frontend_version", "v1.02")
        internal_code_versions["cdat_version"] = esg_bash2py.Expand.colonMinus(
            "cdat_version", "2.2.0")
        #cdat_tag="1.5.1.esgf-v1.7.0"

        internal_code_versions["esgcet_version"] = esg_bash2py.Expand.colonMinus(
            "esgcet_version", "3.0.1")
        internal_code_versions["publisher_tag"] = esg_bash2py.Expand.colonMinus(
            "publisher_tag", "v3.0.1")

        # see esgf-node-manager project:
        internal_code_versions["esgf_node_manager_version"] = esg_bash2py.Expand.colonMinus(
            "esgf_node_manager_version", "0.7.16")
        internal_code_versions["esgf_node_manager_db_version"] = esg_bash2py.Expand.colonMinus(
            "esgf_node_manager_db_version", "0.1.5")

        # see esgf-security project:
        internal_code_versions["esgf_security_version"] = esg_bash2py.Expand.colonMinus(
            "esgf_security_version", "2.7.6")
        internal_code_versions["esgf_security_db_version"] = esg_bash2py.Expand.colonMinus(
            "esgf_security_db_version", "0.1.5")

        # see esg-orp project:
        internal_code_versions["esg_orp_version"] = esg_bash2py.Expand.colonMinus(
            "esg_orp_version", "2.8.10")

        # see esgf-idp project:
        internal_code_versions["esgf_idp_version"] = esg_bash2py.Expand.colonMinus(
            "esgf_idp_version", "2.7.2")

        # see esg-search project:
        internal_code_versions["esg_search_version"] = esg_bash2py.Expand.colonMinus(
            "esg_search_version", "4.8.4")

        # see esgf-web-fe project:
        internal_code_versions["esgf_web_fe_version"] = esg_bash2py.Expand.colonMinus(
            "esgf_web_fe_version", "2.6.5")

        # see esgf-dashboard project:
        internal_code_versions["esgf_dashboard_version"] = esg_bash2py.Expand.colonMinus(
            "esgf_dashboard_version", "1.3.18")
        internal_code_versions["esgf_dashboard_db_version"] = esg_bash2py.Expand.colonMinus(
            "esgf_dashboard_db_version", "0.01")

        # see esgf-desktop project:
        internal_code_versions["esgf_desktop_version"] = esg_bash2py.Expand.colonMinus(
            "esgf_desktop_version", "0.0.20")

        self.config_dictionary.update(internal_code_versions)
        return internal_code_versions

    def populate_external_programs_versions(self):
        '''
        #--------------------------------
        # External programs' versions
        #--------------------------------
        '''
        external_program_versions = {}
        external_program_versions["openssl_version"] = esg_bash2py.Expand.colonMinus(
            "openssl_version", "0.9.8r")
        external_program_versions["openssl_min_version"] = esg_bash2py.Expand.colonMinus(
            "openssl_min_version", "0.9.8e")
        external_program_versions["openssl_max_version"] = esg_bash2py.Expand.colonMinus(
            "openssl_max_version", "0.9.9z")
        external_program_versions["java_version"] = esg_bash2py.Expand.colonMinus(
            "java_version", "1.8.0_92")
        external_program_versions["java_min_version"] = esg_bash2py.Expand.colonMinus(
            "java_min_version", "1.8.0_92")
        external_program_versions["ant_version"] = esg_bash2py.Expand.colonMinus(
            "ant_version", "1.9.1")
        external_program_versions["ant_min_version"] = esg_bash2py.Expand.colonMinus(
            "ant_min_version", "1.9.1")
        external_program_versions["postgress_version"] = esg_bash2py.Expand.colonMinus(
            "postgress_version", "8.4.20")
        external_program_versions["postgress_min_version"] = esg_bash2py.Expand.colonMinus(
            "postgress_min_version", "8.4.20")
        external_program_versions["tomcat_version"] = esg_bash2py.Expand.colonMinus(
            "tomcat_version", "8.0.33")
        external_program_versions["tomcat_min_version"] = esg_bash2py.Expand.colonMinus(
            "tomcat_min_version", "8.0.33")
        external_program_versions["tds_version"] = esg_bash2py.Expand.colonMinus(
            "tds_version", "5.0.0")
        external_program_versions["tds_min_version"] = esg_bash2py.Expand.colonMinus(
            "tds_min_version", "5.0.0")
        external_program_versions["python_version"] = esg_bash2py.Expand.colonMinus(
            "python_version", "2.7")
        self.config_dictionary.update(external_program_versions)
        return external_program_versions
        # cmake_version=${cmake_version:="2.8.12.2"} ; cmake_min_version=${cmake_min_version:="2.8.10.2"} ; cmake_max_version=${cmake_max_version:="2.8.12.2"}
        # Since ESGF 1.8, LAS version is declared in esg-product-server
        # las_version=${las_version:-"8.1"};
        # las_min_version=${las_min_version:-"8.1"}

    def populate_external_script_variables(self):
        '''
        #--------------------------------
        # Script vars (~external)
        #--------------------------------
        '''
        external_script_variables = {}
        external_script_variables["openssl_install_dir"] = esg_bash2py.Expand.colonMinus(
            "OPENSSL_HOME", self.install_prefix + "/openssl")
        external_script_variables["postgress_install_dir"] = esg_bash2py.Expand.colonMinus(
            "PGHOME", "/var/lib/pgsql")
        external_script_variables["postgress_bin_dir"] = esg_bash2py.Expand.colonMinus(
            "PGBINDIR", "/usr/bin")
        external_script_variables["postgress_lib_dir"] = esg_bash2py.Expand.colonMinus(
            "PGLIBDIR", "/usr/lib64/pgsql")
        external_script_variables[
            "postgress_user"] = esg_bash2py.Expand.colonMinus("PGUSER", "dbsuper")

        # local pg_secret=$(cat ${pg_secret_file} 2> /dev/null)
        # pg_secret = subprocess.check_output("cat " + pg_secret_file + " 2>/dev/null ") <- This redirects stderr to a named pipe called /dev/null; In the same way, command 2> file will change the standard error and will make it point to file. Standard error is used by applications to print errors. 
        # pg_sys_acct_passwd=${pg_sys_acct_passwd:=${pg_secret:=changeme}}
        external_script_variables["pg_sys_acct_passwd"] = esg_bash2py.Expand.colonMinus(
            "pg_sys_acct_passwd", esg_bash2py.Expand.colonMinus("pg_secret", "changeme"))
        # del pg_secret
        # local pub_secret=$(cat ${pub_secret_file} 2> /dev/null)
        # pub_secret = subprocess.check_output("cat " + pub_secret_file + " 2>/dev/null ")
        try:
            with open(self.pub_secret_file, 'rb') as f:
                external_script_variables["pub_secret"] = f.read()
            # publisher_db_user_passwd=${publisher_db_user_passwd:-${pub_secret}}
            external_script_variables["publisher_db_user_passwd"] = esg_bash2py.Expand.colonMinus(
            "publisher_db_user_passwd", external_script_variables["pub_secret"])
        except IOError, error:
            logger.debug(error)
        
        # del pub_secret
        external_script_variables[
            "postgress_host"] = esg_bash2py.Expand.colonMinus("PGHOST", "localhost")
        external_script_variables[
            "postgress_port"] = esg_bash2py.Expand.colonMinus("PGPORT", "5432")
        # #cmake_install_dir=${CMAKE_HOME:-${install_prefix}/cmake}
        external_script_variables["cdat_home"] = esg_bash2py.Expand.colonMinus(
            "CDAT_HOME", self.install_prefix + "/uvcdat/" + esg_bash2py.Expand.colonMinus(
                "cdat_version", "2.2.0"))
        external_script_variables[
            "java_opts"] = esg_bash2py.Expand.colonMinus("JAVA_OPTS", "")
        external_script_variables["java_install_dir"] = esg_bash2py.Expand.colonMinus(
            "JAVA_HOME", self.install_prefix + "/java")
        external_script_variables["ant_install_dir"] = esg_bash2py.Expand.colonMinus(
            "ANT_HOME", self.install_prefix + "/ant")
        external_script_variables["tomcat_install_dir"] = esg_bash2py.Expand.colonMinus(
            "CATALINA_HOME", self.install_prefix + "/tomcat")
        external_script_variables[
            "tomcat_conf_dir"] = self.esg_config_dir + "/tomcat"
        external_script_variables[
            "tomcat_opts"] = esg_bash2py.Expand.colonMinus("CATALINA_OPTS")
        external_script_variables["tomcat_user"] = esg_bash2py.Expand.colonMinus(
            "tomcat_user", "tomcat")
        external_script_variables["tomcat_group"] = esg_bash2py.Expand.colonMinus(
            "tomcat_group", external_script_variables["tomcat_user"])
        external_script_variables["globus_location"] = esg_bash2py.Expand.colonMinus(
            "GLOBUS_LOCATION", self.install_prefix + "/globus")
        external_script_variables["mail_smtp_host"] = esg_bash2py.Expand.colonMinus(
            "mail_smtp_host", "smtp.`hostname --domain`")
        external_script_variables[
            "mail_admin_address"] = esg_bash2py.Expand.colonMinus("mail_admin_address")

        # if [ -n "${ESGINI}" ]; then
        #     publisher_home=${ESGINI%/*} <-  Strip shortest match of $substring from back of $string
        #     publisher_config=${ESGINI##*/}
        # fi
        try:
            os.environ["ESGINI"]
        except KeyError:
            # print "os.environ['ESGINI'] not found"
            # external_script_variables["publisher_home"] = subprocess.check_output(
            #     "${ESGINI%/*}", shell=True)
            external_script_variables["publisher_home"] = self.esg_config_dir+"/esgcet"
            # external_script_variables["publisher_config"] = subprocess.check_output(
            #     "${ESGINI##*/}", shell=True)
            external_script_variables["publisher_config"] = "esg.ini"
            external_script_variables["ESGINI"] = external_script_variables["publisher_home"] + "/" + external_script_variables["publisher_config"]
            

        self.config_dictionary.update(external_script_variables)
        return external_script_variables

    def populate_environment_constants(self):
        '''
        ############################################
        ####  DO NOT EDIT BELOW THIS POINT!!!!! ####
        ############################################
        '''
        # export GIT_SSL_NO_VERIFY=1 -> os.environ['DISCOVERONLY']
        # =Expand.colonMinus("DISCOVERONLY")
        os.environ['GIT_SSL_NO_VERIFY'] = "1"
        os.environ['OPENSSL_HOME'] = self.config_dictionary[
            "openssl_install_dir"]
        os.environ['PGHOME'] = self.config_dictionary["postgress_install_dir"]
        os.environ['PGBINDIR'] = self.config_dictionary["postgress_bin_dir"]
        os.environ['PGLIBDIR'] = self.config_dictionary["postgress_lib_dir"]
        os.environ['PGUSER'] = self.config_dictionary["postgress_user"]
        os.environ['PGHOST'] = self.config_dictionary["postgress_host"]
        os.environ['PGPORT'] = self.config_dictionary["postgress_port"]
        # #export CMAKE_HOME=${cmake_install_dir}`
        os.environ['CDAT_HOME'] = self.config_dictionary["cdat_home"]
        os.environ['JAVA_HOME'] = self.config_dictionary["java_install_dir"]
        os.environ['JAVA_OPTS'] = self.config_dictionary["java_opts"]
        os.environ['ANT_HOME'] = self.config_dictionary["ant_install_dir"]
        os.environ['CATALINA_HOME'] = self.config_dictionary[
            "tomcat_install_dir"]
        os.environ['CATALINA_BASE'] = os.environ["CATALINA_HOME"]
        os.environ['CATALINA_OPTS'] = self.config_dictionary["tomcat_opts"]
        os.environ['GLOBUS_LOCATION'] = self.config_dictionary[
            "globus_location"]

        self.myPATH = os.environ["OPENSSL_HOME"] + "/bin:" + os.environ["JAVA_HOME"] + "/bin:" + os.environ["ANT_HOME"] + "/bin:" + os.environ["CDAT_HOME"] + "/bin:" + os.environ[
            "CDAT_HOME"] + "/Externals/bin:" + os.environ["CATALINA_HOME"] + "/bin:" + os.environ["GLOBUS_LOCATION"] + "/bin:" + self.install_prefix + "/bin:/sbin:/usr/bin:/usr/sbin"
        
        logger.debug("myPath: %s", self.myPATH)
        self.myLD_LIBRARY_PATH = os.environ["OPENSSL_HOME"] + "/lib:" + os.environ["CDAT_HOME"] + "/Externals/lib:" + \
            os.environ["GLOBUS_LOCATION"] + "/lib:" + \
            self.install_prefix + "/geoip/lib:/usr/lib64:/usr/lib"

        os.environ["PATH"] = esg_functions.path_unique(self.myPATH+':'+os.environ["PATH"])
        try:
            os.environ["LD_LIBRARY_PATH"] = self.myLD_LIBRARY_PATH+':'+os.environ["LD_LIBRARY_PATH"]
        except KeyError, error:
            logger.error(error)
            os.environ["LD_LIBRARY_PATH"] = self.myLD_LIBRARY_PATH
            logger.debug("LD_LIBRARY_PATH: %s", os.environ["LD_LIBRARY_PATH"])

        # os.environ["PATH"] = esg_functions.path_unique()
        # export PATH=$(_path_unique $myPATH:$PATH)
        # export LD_LIBRARY_PATH=$(_path_unique $myLD_LIBRARY_PATH:$LD_LIBRARY_PATH)
        # export CFLAGS="-I${OPENSSL_HOME}/include -I/usr/include ${CFLAGS} -fPIC"
        # export LDFLAGS="-L${OPENSSL_HOME}/lib -L/usr/lib64 -L/usr/lib
        # -Wl,--rpath,${OPENSSL_HOME}/lib"
        self.config_dictionary.update(os.environ)
        return os.environ

    def populate_id_settings(self):
        '''
        #--------------
        # ID Setting
        #--------------
        '''
        id_settings = {}
        id_settings["installer_user"] = pwd.getpwuid(os.getuid())[0]
        id_settings["installer_uid"] = esg_bash2py.Expand.colonMinus("ESG_USER_UID", esg_bash2py.Expand.colonMinus(
            "SUDO_UID", pwd.getpwnam(id_settings["installer_user"]).pw_uid))
        id_settings["installer_gid"] = esg_bash2py.Expand.colonMinus("ESG_USER_GID", esg_bash2py.Expand.colonMinus(
            "SUDO_GID", pwd.getpwnam(id_settings["installer_user"]).pw_gid))
        id_settings["installer_home"] = esg_bash2py.Expand.colonMinus(
            "ESG_USER_HOME", "/usr/local/src/esgf")

        # #deprecate SUDO_?ID so we only use one variable for all this
        # [[ $SUDO_UID ]] && ESG_USER_UID=${SUDO_UID} && unset SUDO_UID
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

        print "%s:%s:%s:%s" % (id_settings["installer_user"], id_settings["installer_uid"], id_settings["installer_gid"],
                               id_settings["installer_home"])

        self.config_dictionary.update(id_settings)
        return id_settings

    def populate_internal_script_variables(self):
        #--------------
        # Script vars (internal)
        #--------------
        internal_script_variables = {}
        internal_script_variables["esg_backup_dir"] = esg_bash2py.Expand.colonMinus(
            "esg_backup_dir", self.esg_root_dir + "/backups")
        # internal_script_variables["esg_config_dir"] = esg_bash2py.Expand.colonMinus(
        #     "esg_config_dir", self.esg_root_dir + "/config")
        internal_script_variables["esg_log_dir"] = esg_bash2py.Expand.colonMinus(
            "esg_log_dir", self.esg_root_dir + "/log")
        internal_script_variables["esg_tools_dir"] = esg_bash2py.Expand.colonMinus(
            "esg_tools_dir", self.esg_root_dir + "/tools")
        internal_script_variables["esg_etc_dir"] = esg_bash2py.Expand.colonMinus(
            "esg_etc_dir", self.esg_root_dir + "/etc")
        internal_script_variables["workdir"] = esg_bash2py.Expand.colonMinus("workdir", esg_bash2py.Expand.colonMinus(
            "ESGF_INSTALL_WORKDIR", self.config_dictionary["installer_home"] + "/workbench/esg"))

        # word_size=${word_size:-$(file /bin/bash | perl -ple
        # 's/^.*ELF\s*(32|64)-bit.*$/$1/g')}
        # internal_script_variables["word_size"] = esg_bash2py.Expand.colonMinus("word_size", subprocess.check_output(
        #     "$(file /bin/bash | perl -ple 's/^.*ELF\s*(32|64)-bit.*$/$1/g')", shell=True))
        internal_script_variables["word_size"] = re.search(r'(\d\d)-bit?', magic.from_file("/bin/bash")).group(1)
        # print 'internal_script_variables["word_size"]: ', internal_script_variables["word_size"]
        # let num_cpus=1+$(cat /proc/cpuinfo | sed -n 's/^processor[ \t]*:[
        # \t]*\(.*\)$/\1/p' | tail -1)
        # internal_script_variables["num_cpus"] = 1 + subprocess.check_output(
        #     "$(cat /proc/cpuinfo | sed -n 's/^processor[ \t]*:[ \t]*\(.*\)$/\1/p' | tail -1)", shell=True)
        # date_format="+%Y_%m_%d_%H%M%S"
        internal_script_variables["date_format"] = "+%Y_%m_%d_%H%M%S"
        # num_backups_to_keep=${num_backups_to_keep:-7}
        internal_script_variables["num_backups_to_keep"] = esg_bash2py.Expand.colonMinus(
            "num_backups_to_keep", "7")
        # compress_extensions=".tar.gz|.tar.bz2|.tgz|.bz2|.tar"
        internal_script_variables[
            "compress_extensions"] = ".tar.gz|.tar.bz2|.tgz|.bz2|.tar"
        # certificate_extensions="pem|crt|cert|key"
        internal_script_variables[
            "certificate_extensions"] = "pem|crt|cert|key"

        # openssl_dist_url=http://www.openssl.org/source/openssl-${openssl_version}.tar.gz
        internal_script_variables["openssl_dist_url"] = "http://www.openssl.org/source/openssl-" + \
            self.config_dictionary["openssl_version"] + ".tar.gz"
        internal_script_variables["esgf_dist_mirror"] = "aims1.llnl.gov/esgf"
        internal_script_variables["esg_dist_url_root"] = internal_script_variables["esgf_dist_mirror"]+ "/dist"
        # java_dist_url=${esg_dist_url_root}/java/${java_version}/jdk${java_version}-${word_size}.tar.gz
        java_dist_url="$%s/java/$%s/jdk$%s-$%s.tar.gz" % (internal_script_variables["esg_dist_url_root"], self.config_dictionary["java_version"], self.config_dictionary["java_version"], internal_script_variables["word_size"])
        # ant_dist_url=http://archive.apache.org/dist/ant/binaries/apache-ant-${ant_version}-bin.tar.gz
        internal_script_variables["ant_dist_url"] = "http://archive.apache.org/dist/ant/binaries/apache-ant-" + \
            self.config_dictionary["ant_version"] + "-bin.tar.gz"
        # openssl_workdir=${workdir}/openssl
        internal_script_variables["openssl_workdir"] = internal_script_variables[
            "workdir"] + "/openssl"
        # esgf_dashboard_ip_workdir=${workdir}/esgf-dashboard-ip
        internal_script_variables["esgf_dashboard_ip_workdir"] = internal_script_variables[
            "workdir"] + "/esgf-dashboard-ip"
        # bash_completion_url=${esg_dist_url}/thirdparty/bash-completion-20060301-1.noarch.rpm
        # bash_completion_url = esg_dist_url + "/thirdparty/bash-completion-20060301-1.noarch.rpm"
        # db_database=${ESGF_DB_NAME:-${db_database:-"esgcet"}}
        internal_script_variables["db_database"] = esg_bash2py.Expand.colonMinus(
            "ESGF_DB_NAME", esg_bash2py.Expand.colonMinus("db_database", "esgcet"))
        # node_db_name=${db_database}
        internal_script_variables[
            "node_db_name"] = internal_script_variables["db_database"]
        # postgress_jar=postgresql-8.4-703.jdbc3.jar
        internal_script_variables[
            "postgress_jar"] = "postgresql-8.4-703.jdbc3.jar"
        # postgress_driver=org.postgresql.Driver
        internal_script_variables["postgress_driver"] = "org.postgresql.Driver"
        # postgress_protocol=jdbc:postgresql:
        internal_script_variables["postgress_protocol"] = "jdbc:postgresql:"
        # pg_sys_acct=${pg_sys_acct:-postgres}
        internal_script_variables["pg_sys_acct"] = esg_bash2py.Expand.colonMinus(
            "pg_sys_acct", "postgres")
        # pg_sys_acct_group=${pg_sys_acct_group:-$pg_sys_acct}
        internal_script_variables["pg_sys_acct_group"] = esg_bash2py.Expand.colonMinus(
            "pg_sys_acct_group", internal_script_variables["pg_sys_acct"])
        # #cmake_workdir=${workdir}/cmake
        # #cmake_repo=http://www.cmake.org/cmake.git
        # #cdat_repo=git://github.com/UV-CDAT/uvcdat.git
        # #cdat_repo_https=https://github.com/UV-CDAT/uvcdat.git
        # publisher_repo=git://github.com/ESGF/esg-publisher.git
        internal_script_variables[
            "publisher_repo"] = "git://github.com/ESGF/esg-publisher.git"
        internal_script_variables[
            "apache_frontend_repo"] = "https://github.com/ESGF/apache-frontend.git"
        internal_script_variables[
            "publisher_repo_https"] = "https://github.com/ESGF/esg-publisher.git"
        internal_script_variables["esgcet_egg_file"] = "esgcet-%s-py%s.egg" % (
            self.config_dictionary["esgcet_version"], self.config_dictionary["python_version"])
        internal_script_variables["esg_testdir"] = internal_script_variables[
            "workdir"] + "/../esg_test"
        # tomcat_dist_url=http://archive.apache.org/dist/tomcat/tomcat-${tomcat_version%%.*}/v${tomcat_version}/bin/apache-tomcat-${tomcat_version}.tar.gz
        # tomcat_pid_file=/var/run/tomcat-jsvc.pid
        internal_script_variables[
            "tomcat_pid_file"] = "/var/run/tomcat-jsvc.pid"
        # utils_url=${esg_dist_url}/utils
        # utils_url = esg_dist_url+"/utils"
        # thredds_dist_url=ftp://ftp.unidata.ucar.edu/pub/thredds/${tds_version%.*}/${tds_version}/thredds.war
        # thredds_esg_dist_url=${esg_dist_url}/thredds/${tds_version%.*}/${tds_version}/thredds.war
        # thredds_content_dir=${thredds_content_dir:-${esg_root_dir}/content}
        internal_script_variables["thredds_content_dir"] = esg_bash2py.Expand.colonMinus(
            "thredds_content_dir", self.esg_root_dir + "/content")
        # #NOTE: This root dir should match a root set in the thredds setup
        # thredds_root_dir=${esg_root_dir}/data
        internal_script_variables[
            "thredds_root_dir"] = self.esg_root_dir + "/data"
        # thredds_replica_dir=${thredds_root_dir}/replica
        internal_script_variables["thredds_replica_dir"] = internal_script_variables[
            "thredds_root_dir"] + "/replica"
        # #NOTE: This is another RedHat/CentOS specific portion!!! it will break on another OS!
        internal_script_variables["show_summary_latch"] = 0
        internal_script_variables["source_latch"] = "0"
        # scripts_dir=${install_prefix}/bin
        internal_script_variables["scripts_dir"] = self.install_prefix + "/bin"
        # esg_installarg_file=${scripts_dir}/esg-installarg
        internal_script_variables["esg_installarg_file"] = internal_script_variables[
            "scripts_dir"] + "/esg-installarg"
        internal_script_variables[
            "no_globus"] = esg_bash2py.Expand.colonMinus("no_globus", "0")
        internal_script_variables[
            "force_install"] = esg_bash2py.Expand.colonMinus("force_install", "0")
        # extkeytool_download_url=${esg_dist_url}/etc/idptools.tar.gz
        # extkeytool_download_url= esg_dist_url + "/etc/idptools.tar.gz"
        # tomcat_users_file=${tomcat_conf_dir}/tomcat-users.xml
        internal_script_variables["tomcat_users_file"] = self.config_dictionary[
            "tomcat_conf_dir"] + "/tomcat-users.xml"
        # keystore_file=${tomcat_conf_dir}/keystore-tomcat
        internal_script_variables["keystore_file"] = self.config_dictionary[
            "tomcat_conf_dir"] + "/keystore-tomcat"
        # keystore_alias=${keystore_alias:-my_esgf_node}
        internal_script_variables["keystore_alias"] = esg_bash2py.Expand.colonMinus(
            "keystore_alias", "my_esgf_node")
        # keystore_password=${keystore_password}
        # truststore_file=${tomcat_conf_dir}/esg-truststore.ts
        internal_script_variables["truststore_file"] = self.config_dictionary[
            "tomcat_conf_dir"] + "/esg-truststore.ts"
        # truststore_password=${truststore_password:-changeit}
        internal_script_variables["truststore_password"] = esg_bash2py.Expand.colonMinus(
            "truststore_password", "changeit")
        # globus_global_certs_dir=/etc/grid-security/certificates
        internal_script_variables[
            "globus_global_certs_dir"] = "/etc/grid-security/certificates"
        # #NOTE: java keystore style DN...
        # default_dname="OU=ESGF.ORG, O=ESGF" #zoiks: allow this to be empty to
        # allow prompting of user for fields!
        # zoiks: allow this to be empty to allow prompting of user for fields!
        internal_script_variables["default_dname"] = "OU=ESGF.ORG, O=ESGF"
        # config_file=${esg_config_dir}/esgf.properties
        internal_script_variables[
            "config_file"] = self.esg_config_dir + "/esgf.properties"
        internal_script_variables["index_config"] = "master slave"

        # print "internal_script_variables: ", internal_script_variables
        self.config_dictionary.update(internal_script_variables)
        return internal_script_variables


# init()
