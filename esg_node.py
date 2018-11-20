'''Main control script for the ESGF Installer'''
import os
import sys
import logging
import socket
import platform
import glob
import shutil
import errno
import filecmp
import ConfigParser
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import pybash
from base import esg_setup
from base import esg_postgres
from base import esg_java
from data_node import esg_publisher
from esgf_utilities import esg_cli_argument_manager
from base import esg_tomcat_manager
from esgf_utilities import esg_version_manager
from esgf_utilities import esg_mirror_manager
from base import esg_apache_manager
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_questionnaire
from esgf_utilities import esg_cert_manager
from filters import access_logging_filters, esg_security_tokenless_filters
from esgf_utilities.esg_env_manager import EnvWriter


logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

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


def esgf_node_info():
    '''Print basic info about ESGF installation'''
    with open(os.path.join(os.path.dirname(__file__), 'docs', 'esgf_node_info.txt'), 'r') as info_file:
        print info_file.read()



def set_esg_dist_url(install_type, script_maj_version="2.6", script_release="8"):
    '''Sets the distribution mirror url'''
    try:
        local_mirror = esg_property_manager.get_property("local_mirror")
    except ConfigParser.NoOptionError:
        pass
    else:
        if local_mirror.lower() in ["y", "yes"]:
            logger.debug("Using local mirror %s", local_mirror)
            esg_property_manager.set_property("esg.dist.url", local_mirror)
            return

    try:
        if esg_mirror_manager.is_valid_mirror(esg_property_manager.get_property("esg.root.url")):
            esg_property_manager.set_property("esg.dist.url", esg_property_manager.get_property("esg.root.url")+"/{}/{}".format(script_maj_version, script_release))
            return
        elif esg_property_manager.get_property("esg.root.url") == "fastest":
            esg_property_manager.set_property("esg.root.url", esg_mirror_manager.find_fastest_mirror(install_type))
            esg_property_manager.set_property("esg.dist.url", esg_property_manager.get_property("esg.root.url")+"/{}/{}".format(script_maj_version, script_release))
        else:
            selected_mirror = esg_mirror_manager.select_dist_mirror()
            esg_property_manager.set_property("esg.root.url", selected_mirror)
            esg_property_manager.set_property("esg.dist.url", esg_property_manager.get_property("esg.root.url")+"/{}/{}".format(script_maj_version, script_release))
    except ConfigParser.NoOptionError:
        selected_mirror = esg_mirror_manager.select_dist_mirror()
        esg_property_manager.set_property("esg.root.url", selected_mirror)
        esg_property_manager.set_property("esg.dist.url", esg_property_manager.get_property("esg.root.url")+"/{}/{}".format(script_maj_version, script_release))

def get_installation_type(script_version):
    '''Determining if devel or master directory of the ESGF distribution mirror
    will be use for download of binaries'''
    if "devel" in script_version:
        logger.debug("Using devel version")
        return "devel"
    else:
        return "master"


def install_log_info(node_type_list):
    '''Logs out the selected installation types'''
    if force_install:
        logger.info("(force install is ON)")
    if "DATA" in node_type_list:
        logger.info("(data node type selected)")
    if "INDEX" in node_type_list:
        logger.info("(index node type selected)")
    if "IDP" in node_type_list:
        logger.info("(idp node type selected)")
    if "COMPUTE" in node_type_list:
        logger.info("(compute node type selected)")

def show_summary():
    '''Show user summary and environment variables that have been set'''
    print "-------------------"
    print " esgf_node Run Summary: "
    print "-------------------"

    print "The following environment variables were used during last full install"
    print "They are written to the file {}".format(EnvWriter.envfile)
    print "Please source this file when using these tools"

    try:
        print EnvWriter.read()
    except IOError, error:
        logger.exception(error)

    print "-------------------"
    print "Installation Log:"
    try:
        with open(config["install_manifest"], 'r') as env_file:
            print env_file.read()
    except IOError, error:
        logger.exception(error)
    print "-------------------"



def system_component_installation(esg_dist_url, node_type_list):
    '''
    Installation of basic system components.
    (Only when one setup in the sequence is okay can we move to the next)
    '''
    if "INSTALL" in node_type_list:
        esg_java.setup_java()
        esg_postgres.setup_postgres()
        esg_tomcat_manager.main()
        esg_apache_manager.main()
    if "DATA" in node_type_list:
        print "\n*******************************"
        print "Installing Data Node Components"
        print "******************************* \n"
        esg_publisher.main()
        from data_node import orp, thredds, esg_node_manager
        from idp_node import globus
        from data_node import esg_dashboard
        thredds.main()
        esg_node_manager.main()
        esg_dashboard.main()
        orp.main()
        access_logging_filters.install_access_logging_filter()
        esg_security_tokenless_filters.setup_security_tokenless_filters()
        globus.setup_globus("DATA")
    if "IDP" in node_type_list:
        print "\n*******************************"
        print "Installing IDP Node Components"
        print "******************************* \n"
        from idp_node import idp, esg_security, globus
        idp.main()
        esg_security.setup_security(node_type_list, esg_dist_url)
        globus.setup_globus("IDP")
        idp.setup_slcs()
    esg_cert_manager.install_local_certs(node_type_list, "firstrun")
    if "INDEX" in node_type_list:
        print "\n*******************************"
        print "Installing Index Node Components"
        print "******************************* \n"
        if "DATA" not in node_type_list:
            from data_node import orp
            orp.main()
        from index_node import esg_cog, esg_search, solr
        esg_cog.main()
        solr.main()
        esg_search.main()



def done_remark(node_type_list):
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
        esgf-node-admins@lists.llnl.gov by sending email to: "sasha@llnl.gov"
        with the body: "subscribe esgf-node-admins"
        -------------------------------------------------------
'''

    show_summary()

    try:
        esg_org_name = esg_property_manager.get_property("esg.org.name")
    except ConfigParser.NoOptionError:
        logger.exception("esg.org.name could not be found in config file")
    print "(\"Test Project\" -> pcmdi.{esg_org_name}.{node_short_name}.test.mytest)".format(esg_org_name=esg_org_name, node_short_name=esg_property_manager.get_property("node.short.name"))

def setup_esgf_rpm_repo():
    '''Creates the esgf repository definition file'''

    print "*******************************"
    print "Setting up ESGF RPM repository"
    print "******************************* \n"

    esg_mirror_url = esg_property_manager.get_property("esg.root.url").rsplit("/", 1)[0]

    parser = ConfigParser.SafeConfigParser()
    parser.read("esgf_utilities/esgf.repo")
    os_version = platform.platform()

    if "centos" in os_version:
        parser.set("esgf", "baseurl", "{}/RPM/centos/6/x86_64\n".format(esg_mirror_url))
    elif "redhat" in os_version:
        parser.set("esgf", "baseurl", "{}/RPM/redhat/6/x86_64\n".format(esg_mirror_url))

    with open("/etc/yum.repos.d/esgf.repo", "w") as repo_file_object:
        parser.write(repo_file_object)


def main():
    '''Main function'''

    esg_setup.check_prerequisites()
    esg_setup.create_esg_directories()

    script_version, script_maj_version, script_release = esg_version_manager.set_version_info()

    # determine installation type
    install_type = get_installation_type(script_version)

    cli_info = esg_cli_argument_manager.process_arguments()
    logger.debug("cli_info: %s", cli_info)
    if cli_info:
        node_type_list = cli_info

    try:
        devel = bool(esg_property_manager.get_property("devel"))
    except ConfigParser.NoOptionError:
        devel = False


    set_esg_dist_url(install_type)
    esg_dist_url = esg_property_manager.get_property("esg.dist.url")

    logger.debug("node_type_list: %s", node_type_list)

    print '''
    -----------------------------------
    ESGF Node Installation Program
    -----------------------------------'''

    # Display node information to user
    esgf_node_info()

    if devel:
        print "(Installing DEVELOPMENT tree...)"

    # log info
    install_log_info(node_type_list)

    esg_questionnaire.initial_setup_questionnaire()

    setup_esgf_rpm_repo()

    # install dependencies
    system_component_installation(esg_dist_url, node_type_list)
    system_launch(esg_dist_url, node_type_list, script_version, script_release)


def sanity_check_web_xmls():
    '''Editing web.xml files for projects who use the authorizationService'''
    print "sanity checking webapps' web.xml files accordingly... "

    with pybash.pushd("/usr/local/tomcat/webapps"):
        webapps = os.listdir("/usr/local/tomcat/webapps")
        if not webapps:
            return

        instruct_to_reboot = False
        tomcat_user = esg_functions.get_user_id("tomcat")
        tomcat_group = esg_functions.get_group_id("tomcat")

        orp_host = esg_functions.get_esgf_host()
        truststore_file = config["truststore_file"]

        try:
            authorization_service_root = esg_property_manager.get_property("esgf_idp_peer") #ex: pcmdi3.llnl.gov/esgcet[/saml/soap...]
        except ConfigParser.NoOptionError:
            authorization_service_root = esg_functions.get_esgf_host()

        for app in webapps:
            if not os.path.exists(os.path.join(app, "WEB-INF")):
                continue
            with pybash.pushd(os.path.join(app, "WEB-INF")):
                print " |--setting ownership of web.xml files... to ${tomcat_user}.${tomcat_group}"
                os.chown("web.xml", tomcat_user, tomcat_group)

                with open("web.xml", 'r') as file_handle:
                    filedata = file_handle.read()

                filedata = filedata.replace("@orp_host@", orp_host)
                filedata = filedata.replace("@truststore_file@", truststore_file)
                filedata = filedata.replace("@authorization_service_root@", authorization_service_root)

                # Write the file out again
                with open("web.xml", 'w') as file_handle:
                    file_handle.write(filedata)

                try:
                    if not filecmp.cmp("web.xml", "web.xml.bak", shallow=False):
                        logger.debug("%s/web.xml file was edited. Reboot needed", os.getcwd())
                        instruct_to_reboot = True
                except OSError, error:
                    pass

        if instruct_to_reboot:
            print '''-------------------------------------------------------------------------------------------------
            webapp web.xml files have been modified - you must restart node stack for changes to be in effect
            (esg-node restart)
            -------------------------------------------------------------------------------------------------'''

def clear_tomcat_cache():
    '''Delete the tomcat cache directories'''
    try:
        cache_directories = glob.glob("/usr/local/tomcat/work/Catalina/localhost/*")
        for directory in cache_directories:
            shutil.rmtree(directory)
        print "Cleared tomcat cache... "
    except OSError, error:
        logger.exception(error)

def remove_unused_esgf_webapps():
    '''Hard coded to remove node manager'''
    try:
        shutil.rmtree("/usr/local/tomcat/webapps/esgf-node-manager")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass

def install_bash_completion_file(esg_dist_url):
    '''Install bash_completion file from distribution mirror'''
    if os.path.exists("/etc/bash_completion") and not os.path.exists("/etc/bash_completion.d/esg-node"):
        esg_functions.download_update("/etc/bash_completion.d/esg-node", "{}/esgf-installer/esg-node.completion".format(esg_dist_url))

def write_script_version_file(script_version):
    '''Write version file'''
    with open(os.path.join(config["esg_root_dir"], "version"), "w") as version_file:
        version_file.write(script_version)

def system_launch(esg_dist_url, node_type_list, script_version, script_release):
    '''Prepare the node to start'''
    #---------------------------------------
    #System Launch...
    #---------------------------------------
    sanity_check_web_xmls()
    clear_tomcat_cache()
    remove_unused_esgf_webapps()

    esg_functions.update_fileupload_jar()
    esg_functions.setup_whitelist_files()

    esg_cli_argument_manager.run_startup_hooks(node_type_list)
    esg_cert_manager.check_for_commercial_ca()
    esg_cli_argument_manager.start(node_type_list)

    install_bash_completion_file(esg_dist_url)
    done_remark(node_type_list)
    write_script_version_file(script_version)
    print script_version

    esg_property_manager.set_property("version", script_version)
    esg_property_manager.set_property("release", script_release)
    EnvWriter.add_source("/usr/local/conda/bin/activate esgf-pub")
    #     write_as_property gridftp_config
    esg_node_finally(node_type_list)

def esg_node_finally(node_type_list):
    '''Runs after installation, final setup'''
    global_x509_cert_dir = "/etc/grid-security/certificates"
    esg_functions.change_ownership_recursive(global_x509_cert_dir, config["installer_uid"], config["installer_gid"])

    if "IDP" in node_type_list:
        os.environ["PGPASSWORD"] = esg_functions.get_postgres_password()
        print "Writing additional settings to db.  If these settings already exist, psql will report an error, but ok to disregard."
        # psql -U dbsuper -c "insert into esgf_security.permission values (1, 1, 1, 't'); insert into esgf_security.role values (6, 'user', 'User Data Access');" esgcet
        #     echo "Node installation is complete."


if __name__ == '__main__':
    main()
