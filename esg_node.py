import os
import subprocess
import sys
import logging
import socket
import platform
import glob
import shutil
import stat
import yaml
import semver
import pip
from git import Repo
from lxml import etree
#This needs to be imported before other esg_* modules to properly setup the root logger
from esgf_utilities import esg_logging_manager
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from base import esg_setup
from base import esg_postgres
from data_node import esg_publisher
from esgf_utilities import esg_cli_argument_manager
from base import esg_tomcat_manager
from esgf_utilities import esg_version_manager
from esgf_utilities import esg_mirror_manager
from base import esg_apache_manager
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_questionnaire
from esgf_utilities.esg_exceptions import UnprivilegedUserError, WrongOSError, UnverifiedScriptError


logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

os.environ['LANG'] = "POSIX"
os.umask(022)

node_types = {"INSTALL": False, "DATA": False, "INDEX": False,
                          "IDP": False, "COMPUTE": False, "MIN": 4, "MAX": 64}
node_types["ALL"] = node_types["DATA"] and node_types[
    "INDEX"] and node_types["IDP"] and node_types["COMPUTE"]

node_type_list = []

def get_node_type():
    for key, value in node_types.items():
        if value:
            node_type_list.append(key)

devel = True
recommended_setup = 1

custom_setup = 0
use_local_files = 0


def set_version_info():
    '''Gathers the version info from the latest git tag'''
    repo = Repo(os.path.dirname(__file__))
    repo_tag = repo.git.describe().lstrip("v")
    split_repo_tag = repo_tag.split("-")
    version = split_repo_tag[0]
    maj_version = str(semver.parse_version_info(version).major) +".0"
    release = split_repo_tag[1]

    return version, maj_version, release

progname = "esg-node"
script_version, script_maj_version, script_release = set_version_info()
force_install = False

#--------------
# User Defined / Settable (public)
#--------------
#--------------

def setup_esg_config_permissions():
    '''Set permissions on /esg directory and subdirectories'''
    esg_functions.change_permissions_recursive("/esg/config", 0644)

    root_id = esg_functions.get_user_id("root")
    tomcat_group_id = esg_functions.get_user_id("tomcat")
    for file_name in  glob.glob("/esg/config/.esg*"):
        os.chown(file_name, root_id, tomcat_group_id)
        os.chmod(file_name, 0640)

    tomcat_user_id = esg_functions.get_user_id("tomcat")
    esg_functions.change_ownership_recursive("/esg/config/tomcat", tomcat_user_id, tomcat_group_id)
    os.chmod("/esg/config/tomcat", 0755)
    for file_name in  glob.glob("/esg/config/tomcat/*"):
        os.chmod(file_name, 0600)

    os.chmod("/esg/config/esgcet", 0755)
    for file_name in  glob.glob("/esg/config/esgcet/*"):
        os.chmod(file_name, 0644)
    os.chmod("/esg/config/esgcet/esg.ini", 640)

esg_root_id = esg_functions.get_esg_root_id()

def esgf_node_info():

    print '''
        The goal of this script is to automate as many tasks as possible
     regarding the installation, maintenance and use of the ESGF
     software stack that is know as the \"ESGF Node\".  A software
     stack is a collection of tools that work in concert to perform a
     particular task or set of tasks that are semantically united. The
     software stack is comprised of: Tomcat, Thredds, CDAT & CDMS,
     PostgreSQL, MyProxy, and several ESGF.org custom software
     applications running on a LINUX (RedHat/CentOS) operating system.
     Through the installation process there are different accounts
     that are created that facilitate the communication between the
     software stack entities.  These credentials are internal to the
     stack.  It is recommended that you use the defaults provided
     throughout this installation.  The security impact with regards
     to the visibility and accessibility of the constituent components
     of the stack depends on other factors to be addressed by your
     organization.

     Please be sure that you have gotten your created an account on
     your ESGF IDP Peer.

     The primary IDP Peer for ESGF is esgf-node.llnl.gov
     You may register for an account at LLNL at the following URL:
     https://esgf-node.llnl.gov/user/add/

     Note: Account creation is prerequisite for publication!

     ESGF P2P Node:                                             ESGF P2P Node:
      ---------                                                   ---------
     |Tomcat   |                                                 |Tomcat   |
     |-Node Mgr|   <================= P2P =================>     |-Node Mgr|
     |-Thredds |                                                 |-Thredds |
     |-ORP     |                                                 |-ORP     |
     |---------|                                                 |---------|
     |CDAT/CDMS|                                                 |CDAT/CDMS|
     |---------|                                                 |---------|
     |Postgres |                                                 |Postgres |
     |---------|                                                 |---------|
     | MyProxy |  <===(HTTPS)===> [ESGF Peer Node(s)]*           | MyProxy |
     |---------|                                                 |---------|
     | GridFTP |  <=============> [End User(s)]*                 | GridFTP |
     >---------<                                                 >---------<
     | CentOS  |                                                 | CentOS  |
     |(Virtual)|                                                 |(Virtual)|
     | Machine |                                                 | Machine |
     |---------|                                                 |---------|
      ---------                                                   ---------

     (Visit http://esgf.llnl.gov , http://github.com/ESGF/esgf.github.io/wiki for more information)

    '''


def select_distribution_mirror(install_type):
     # Determining ESGF distribution mirror
    logger.info("before selecting distribution mirror: %s",
                config.esgf_dist_mirror)
    if any(argument in sys.argv for argument in ["install", "update", "upgrade"]):
        logger.debug("interactive")
        config.esgf_dist_mirror = esg_mirror_manager.get_esgf_dist_mirror(
            "interactive", install_type)
    else:
        logger.debug("fastest")
        config.esgf_dist_mirror = esg_mirror_manager.get_esgf_dist_mirror(
            "fastest", install_type)

    logger.info("selected distribution mirror: %s",
                config.esgf_dist_mirror)

def set_esg_dist_url():
    '''Setting esg_dist_url with previously gathered information'''
    esg_dist_url_root = os.path.join(
        "http://", config.esgf_dist_mirror, "dist")
    logger.debug("esg_dist_url_root: %s", esg_dist_url_root)
    if devel is True:
        esg_dist_url = os.path.join("http://", esg_dist_url_root, "/devel")
    else:
        esg_dist_url = esg_dist_url_root

    logger.debug("esg_dist_url: %s", esg_dist_url)

def download_esg_installarg(esg_dist_url):
    ''' Downloading esg-installarg file '''
    if not os.path.isfile(config["esg_installarg_file"]) or force_install or os.path.getmtime(config["esg_installarg_file"]) < os.path.getmtime(os.path.realpath(__file__)):
        esg_installarg_file_name = esg_bash2py.trim_string_from_head(
            config["esg_installarg_file"])
        esg_functions.download_update(config["esg_installarg_file"], os.path.join(
            esg_dist_url, "esgf-installer", esg_installarg_file_name), force_download=force_install)
        try:
            if not os.path.getsize(config["esg_installarg_file"]) > 0:
                os.remove(config["esg_installarg_file"])
            esg_bash2py.touch(config["esg_installarg_file"])
        except IOError:
            logger.exception("Unable to access esg-installarg file")


def check_selected_node_type(node_types, node_type_list):
    ''' Make sure a valid node_type has been selected before performing and install '''

    # node_options_modified = create_new_list_from_keys(node_types)
    # logger.debug("node_options_modified: %s", node_options_modified)
    for option in node_type_list:
        logger.debug("option: %s", option)
        if option in node_types.keys():
            continue
        else:
            print '''
                Sorry no suitable node type has been selected
                Please run the script again with --set-type and provide any number of type values (\"data\", \"index\", \"idp\", \"compute\" [or \"all\"]) you wish to install
                (no quotes - and they can be specified in any combination or use \"all\" as a shortcut)

                Ex:  esg-node --set-type data
                esg-node install

                or do so as a single command line:

                Ex:  esg-node --type data install

                Use the --help | -h option for more information

                Note: The type value is recorded upon successfully starting the node.
                the value is used for subsequent launches so the type value does not have to be
                always specified.  A simple \"esg-node start\" will launch with the last type used
                that successfully launched.  Thus ideal for use in the boot sequence (chkconfig) scenario.
                (more documentation available at https://github.com/ESGF/esgf-installer/wiki)\n\n
                  '''
            sys.exit(1)
    return True


def init_connection():
    """ Initialize Connection to node."""
    logger.info("esg-node initializing...")
    try:
        logger.info(socket.getfqdn())
    except socket.error:
        logger.error(
            "Please be sure this host has a fully qualified hostname and reponds to socket.getfdqn() command")
        sys.exit()


def get_installation_type(script_version):
    # Determining if devel or master directory of the ESGF distribution mirror
    # will be use for download of binaries
    if "devel" in script_version:
        logger.debug("Using devel version")
        return "devel"
    else:
        return "master"


def install_log_info():
    if force_install:
        logger.info("(force install is ON)")
    if node_types["DATA"]:
        logger.info("(data node type selected)")
    if node_types["INDEX"]:
        logger.info("(index node type selected)")
    if node_types["IDP"]:
        logger.info("(idp node type selected)")
    if node_types["COMPUTE"]:
        logger.info("(compute node type selected)")

#TODO: implement
def show_summary():
    #####
    # Show user summary and environment variables that have been set
    #####
    # show_summary() {
    #     if [ $((show_summary_latch == 0)) = 1 ]; then return 0; fi
    #     echo
    #     echo "-------------------"
    #     echo "  esgf node run summary: "
    #     echo "-------------------"
    #     echo "The following environment variables were used during last full install"
    #     echo "They are written to the file ${envfile}"
    #     echo "Please source this file when using these tools"
    #     echo
    #     cat ${envfile}
    #     echo "-------------------"
    #     echo "Installation Log:"
    #     echo
    #     cat ${install_manifest}
    #     echo "-------------------"
    #     echo
    #     return 0
    # }
    pass

def setup_whitelist_files(esg_dist_url_root, whitelist_file_dir=config["esg_config_dir"]):
    '''Setups up whitelist XML files from the distribution mirror'''

    #quick-fix for removing insecure commons-fileupload jar file
    try:
        os.remove("/usr/local/solr/server/solr-webapp/webapp/WEB-INF/lib/commons-fileupload-1.2.1.jar")
    except OSError, error:
        logger.exception(error)

    try:
        shutil.copyfile("{tomcat_install_dir}/webapps/esg-search/WEB-INF/lib/commons-fileupload-1.3.1.jar".format(tomcat_install_dir=config["tomcat_install_dir"]), "/usr/local/solr/server/solr-webapp/webapp/WEB-INF/lib/")
    except OSError, error:
        logger.exception(error)

    conf_file_list = ["esgf_ats.xml.tmpl", "esgf_azs.xml.tmpl", "esgf_idp.xml.tmpl"]

    apache_user_id = esg_functions.get_user_id("apache")
    apache_group_id = esg_functions.get_group_id("apache")
    for file_name in conf_file_list:
        local_file_name = file_name.split(".tmpl")[0]
        local_file_path = os.path.join(whitelist_file_dir, local_file_name)
        remote_file_url = "https://aims1.llnl.gov/esgf/dist/confs/{file_name}".format(file_name=file_name)

        esg_functions.download_update(local_file_path, remote_file_url)

        #replace placeholder.fqdn
        tree = etree.parse(local_file_path)
        #Had to use {http://www.esgf.org/whitelist} in search because the xml has it listed as the namespace
        if file_name == "esgf_ats.xml.tmpl":
            updated_string = tree.find('.//{http://www.esgf.org/whitelist}attribute').text.replace("placeholder.fqdn", "esgf-dev2.llnl.gov")
        else:
            updated_string = tree.find('.//{http://www.esgf.org/whitelist}value').text.replace("placeholder.fqdn", "esgf-dev2.llnl.gov")
        tree.find('.//{http://www.esgf.org/whitelist}value').text = updated_string
        tree.write(file_name)

        os.chown(local_file_path, apache_user_id, apache_group_id)
        current_mode = os.stat(local_file_path)
        #add read permissions to all, i.e. chmod a+r
        os.chmod(local_file_path, current_mode.st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        #TODO: Terrible original design; this file is unrelated to the function and shouldn't be modified here
        current_mode = os.stat("/esg/config/esgf_idp_static.xml")
        os.chmod("/esg/config/esgf_idp_static.xml", current_mode.st_mode | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

def system_component_installation(esg_dist_url):
    #---------------------------------------
    # Installation of basic system components.
    # (Only when one setup in the sequence is okay can we move to the next)
    #---------------------------------------

    if "INSTALL" in node_type_list:
        #TODO: check status of base components; if all running, skip setup
        esg_setup.setup_java()
        esg_setup.setup_ant()
        esg_postgres.setup_postgres()
        esg_tomcat_manager.main()
        esg_apache_manager.main()
    if "DATA" in node_type_list:
        print "\n*******************************"
        print "Installing Data Node Components"
        print "******************************* \n"
        pip.main(['install', "esgprep"])
        esg_publisher.main()
        from data_node import esg_dashboard, orp, thredds
        orp.main()
        thredds.main(node_type_list)
    if "DATA" in node_type_list and "COMPUTE" in node_type_list:
        #CDAT only used on with Publisher; move
        esg_setup.setup_cdat()
    if "INDEX" in node_type_list:
        print "\n*******************************"
        print "Installing Index Node Components"
        print "******************************* \n"
        from index_node import esg_cog, esg_search, solr
        esg_cog.main()
        solr.main()
        esg_search.main()
    if "IDP" in node_type_list:
        print "\n*******************************"
        print "Installing IDP Node Components"
        print "******************************* \n"
        from idp_node import idp
        from idp_node import esg_security
        idp.main()
        esg_security.setup_security(node_type_list, esg_dist_url)

    setup_whitelist_files(esg_dist_url)


def done_remark():
    '''Prints info to denote that the installation has completed'''
    print "\nFinished!..."
    print "In order to see if this node has been installed properly you may direct your browser to:"
    if "DATA" in node_type_list or "INSTALL" in node_type_list:
        esgf_host = esg_functions.get_esgf_host()
        print "http://{esgf_host}/thredds".format(esgf_host=esgf_host)
        print "http://{esgf_host}/esg-orp".format(esgf_host=esgf_host)
    if "INDEX" in node_type_list:
        print "http://{esgf_host}/".format(esgf_host=esgf_host)
    if "COMPUTE" in node_type_list:
        print "http://{esgf_host}/las".format(esgf_host=esgf_host)

    print "Your peer group membership -- :  [{node_peer_group}]".format(node_peer_group=esg_property_manager.get_property("node.peer.group"))
    print "Your specified \"index\" peer - :[{esgf_index_peer}]) (url = http://{esgf_index_peer}/)".format(esgf_index_peer=esg_property_manager.get_property("esgf.index.peer"))

    if os.path.isdir(os.path.join("{thredds_content_dir}".format(thredds_content_dir=config["thredds_content_dir"]), "thredds")):
        print "[Note: Use UNIX group permissions on {thredds_content_dir}/thredds/esgcet to enable users to be able to publish thredds catalogs from data therein]".format(thredds_content_dir=config["thredds_content_dir"])
        print " %> chgrp -R <appropriate unix group for publishing users> {thredds_content_dir}/thredds".format(thredds_content_dir=config["thredds_content_dir"])

    print '''
        -------------------------------------------------------
        Administrators of this node should subscribe to the
        esgf-node-admins@lists.llnl.gov by sending email to: "majordomo@lists.llnl.gov"
        with the body: "subscribe esgf-node-admins"
        -------------------------------------------------------
'''

    show_summary()
    print "(\"Test Project\" -> pcmdi.{esg_root_id}.{node_short_name}.test.mytest)".format(esg_root_id=esg_root_id, node_short_name=esg_property_manager.get_property("node.short.name"))

def setup_esgf_rpm_repo(esg_dist_url):
    '''Creates the esgf repository definition file'''

    print "*******************************"
    print "Setting up ESGF RPM repository"
    print "******************************* \n"

    with open("/etc/yum.repos.d/esgf.repo", "w") as esgf_repo:
        esgf_repo.write('[esgf]\n')
        esgf_repo.write('name=ESGF\n')
        os_version = platform.platform()
        if "centos" in os_version:
            esgf_repo.write("baseurl={esg_dist_url}/RPM/centos/6/x86_64\n".format(esg_dist_url=esg_dist_url))
        if "redhat" in os_version:
            esgf_repo.write("baseurl={esg_dist_url}/RPM/redhat/6/x86_64\n".format(esg_dist_url=esg_dist_url))
        esgf_repo.write('failovermethod=priority\n')
        esgf_repo.write('enabled=1\n')
        esgf_repo.write('priority=90\n')
        esgf_repo.write('gpgcheck=0\n')
        esgf_repo.write('proxy=_none_\n')


def main(node_type_list):
    # default distribution_url
    esg_dist_url = "http://aims1.llnl.gov/esgf/dist"

    # initialize connection
    init_connection()

    # determine installation type
    install_type = get_installation_type(script_version)
    print "install_type:", install_type

    # select_distribution_mirror(install_type)
    # set_esg_dist_url()
    download_esg_installarg(esg_dist_url)

    cli_info = esg_cli_argument_manager.process_arguments(node_type_list, devel, esg_dist_url)
    print "cli_info:", cli_info
    if cli_info:
        node_type_list = cli_info

    esg_setup.check_prerequisites()

    esg_functions.verify_esg_node_script(os.path.basename(
        __file__), esg_dist_url, script_version, script_maj_version, devel)

    logger.debug("node_type_list: %s", node_type_list)
    logger.info("node_type_list: %s", node_type_list)
    print "node_type_list after process_arguments:", node_type_list

    print '''
    -----------------------------------
    ESGF Node Installation Program
    -----------------------------------'''

    #If not type not set from CLI argument, look at previous node type setting
    if not [node_type for node_type in node_type_list if node_type in node_types.keys()]:
        previous_node_type = esg_cli_argument_manager.get_previous_node_type_config(
            config["esg_config_type_file"])
        print "previous_node_type:", previous_node_type
    check_selected_node_type(node_types, node_type_list)

    # Display node information to user
    esgf_node_info()

    if devel is True:
        print "(Installing DEVELOPMENT tree...)"

    esg_setup.init_structure()

    # log info
    install_log_info()

    esg_questionnaire.initial_setup_questionnaire()

    # setup_esgf_rpm_repo(esg_dist_url)

    # install dependencies
    system_component_installation(esg_dist_url)
    done_remark()

def system_launch():
    #---------------------------------------
    #System Launch...
    #---------------------------------------
    #     sanity_check_web_xmls
    #     setup_root_app
    #     [ -e "${tomcat_install_dir}/work/Catalina/localhost" ] && rm -rf ${tomcat_install_dir}/work/Catalina/localhost/* && echo "Cleared tomcat cache... "
    # # Hard coded to remove node manager, desktop and dashboard
    # rm -rf /usr/local/tomcat/webapps/esgf-node-manager
    # rm -rf /usr/local/tomcat/webapps/esgf-desktop
    # rm -rf /usr/local/tomcat/webapps/esgf-dashboard
    # #fix for sensible values for conf files post node-manager removal
    # setup_sensible_confs
    #     start ${sel}
    #     install_bash_completion_file
    #     done_remark
    #     echo "${script_version}" > ${esg_root_dir}/version
    #     echo "${script_version}"
    #     echo
    #     write_as_property version ${script_version}
    #     write_as_property release ${script_release}
    #     write_as_property gridftp_config
    #     echo 'source /usr/local/conda/bin/activate esgf-pub' >> ${envfile}
    #
    #     esg_node_finally
    # }
    #
    # esg_node_finally() {
    #     debug_print "(esg_datanode: cleaning up etc...)"
    #     chown -R ${installer_uid}:${installer_gid} ${X509_CERT_DIR} >& /dev/null
    #
    # if [ $((sel & IDP_BIT)) != 0 ]; then
    # export PGPASSWORD=${pg_sys_acct_passwd}
    #
    # echo Writing additional settings to db.  If these settings already exist, psql will report an error, but ok to disregard.
    # psql -U dbsuper -c "insert into esgf_security.permission values (1, 1, 1, 't'); insert into esgf_security.role values (6, 'user', 'User Data Access');" esgcet
    #     echo "Node installation is complete."
    # fi
    # if [ -p /tmp/outputpipe ]; then
    #     echo "Installer ran to completion. Now cleaning up. There will be a 'Killed' message in your setup-autoinstall terminal, which is not a cause for concern." >/tmp/outputpipe;
    # fi
    #
    # #exec 1>&3 3>&- 2>&4 4>&-
    # #wait $tpid
    # #rm $OUTPUT_PIPE
    #
    #
    #     exit 0
    # }
    pass


if __name__ == '__main__':
    main(node_type_list)
