import os
import shutil
import logging
import getpass
import re
import urllib
import requests
from distutils.dir_util import copy_tree
import yaml
from lxml import etree
import zipfile
from clint.textui import progress
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from base import esg_tomcat_manager


logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def check_thredds_version():
    '''Check the MANIFEST.MF file for the Thredds version'''
    with open("/usr/local/tomcat/webapps/thredds/META-INF/MANIFEST.MF", "r") as manifest_file:
        contents = manifest_file.readlines()
        matcher = re.compile("Implementation-Version.*")
        results_list = filter(matcher.match, contents)
        if results_list:
            version_number = results_list[0].split(":")[1].strip().split("-")[1]
            print "Found existing Thredds installation (Thredds version {version})".format(version=version_number)
            return version_number
        else:
            print "Thredds not found on system."

def download_thredds_war(thredds_url):

    print "\n*******************************"
    print "Downloading Thredds war file"
    print "******************************* \n"

    r = requests.get(thredds_url, stream=True)
    path = '/usr/local/tomcat/webapps/thredds/thredds.war'
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

def create_password_hash(tomcat_user_password):
    '''Creates a hash for a Tomcat user's password using Tomcat's digest.sh script'''
    password_hash = esg_functions.call_subprocess("/usr/local/tomcat/bin/digest.sh -a SHA {tomcat_user_password}".format(tomcat_user_password=tomcat_user_password))
    print "password hash:",  password_hash["stdout"]
    return password_hash["stdout"].split(":")[1]

def update_tomcat_users_file(tomcat_username, password_hash, tomcat_users_file=config["tomcat_users_file"]):
    '''Adds a new user to the tomcat-users.xml file'''
    tree = etree.parse(tomcat_users_file)
    root = tree.getroot()
    updated_dnode_user = False
    for param in root.iter():
        if param == "user" and param.get("username") == "dnode_user":
            param.set("password", password_hash)
            param.set("roles", "tdrAdmin,tdsConfig")
            updated_dnode_user = True

    if not updated_dnode_user:
        new_user = etree.SubElement(root, "user")
        new_user.set("username", tomcat_username)
        new_user.set("password", password_hash)
        new_user.set("roles", "tdrAdmin,tdsConfig")

    tree.write(open(tomcat_users_file, "wb"), pretty_print=True)

def add_another_user():
    '''Helper function for deciding to add more Tomcat users or not'''
    valid_selection = False
    done_adding_users = None
    while not valid_selection:
        if esg_property_manager.get_property("add_another_user"):
            another_user = esg_property_manager.get_property("add_another_user")
        else:
            another_user = raw_input("Would you like to add another user? [y/N]:") or "n"

        if another_user.lower().strip() in ["n", "no"]:
            valid_selection = True
            done_adding_users = True
        if another_user.lower().strip() in ["y", "yes"]:
            valid_selection = True
            done_adding_users = False
        else:
            print "Invalid selection"
            continue
    return done_adding_users

def add_tomcat_user():
    '''Add a user to the default Tomcat user database (tomcat-users.xml) for container-managed authentication'''
    print "Create user credentials\n"
    done_adding_users = False
    while not done_adding_users:
        if esg_property_manager.get_property("tomcat_user"):
            tomcat_username = esg_property_manager.get_property("tomcat_user")
        else:
            default_user = "dnode_user"
            tomcat_username = raw_input("Please enter username for tomcat [{default_user}]:  ".format(default_user= default_user)) or default_user

        valid_password = False
        while not valid_password:
            tomcat_user_password = esg_functions.get_security_admin_password()
            if not tomcat_user_password:
                tomcat_user_password = getpass.getpass("Please enter password for user, \"{tomcat_username}\" [********]:   ".format(tomcat_username=tomcat_username))

            if esg_functions.is_valid_password(tomcat_user_password):
                valid_password = True

        password_hash = create_password_hash(tomcat_user_password)

        update_tomcat_users_file(tomcat_username, password_hash)

        done_adding_users = add_another_user()

def get_webxml_file():
    '''Get the templated web.xml file... (with tokens for subsequent filter entries: see [esg-]security-[token|tokenless]-filters[.xml] files)'''
    web_xml_path = os.path.join("{tomcat_install_dir}".format(tomcat_install_dir=config["tomcat_install_dir"]), "webapps", "thredds", "WEB-INF","web.xml")
    web_xml_download_url = "https://aims1.llnl.gov/esgf/dist/devel/thredds/thredds.web.xml"
    esg_functions.download_update(web_xml_path, web_xml_download_url)

    TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
    TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()

    os.chown("/usr/local/tomcat/webapps/thredds/web.xml", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

def update_mail_admin_address():
    mail_admin_address = esg_property_manager.get_property("mail_admin_address")
    esg_functions.stream_subprocess_output('sed -i "s/support@my.group/$mail_admin_address/g" /esg/content/thredds/threddsConfig.xml')


def esgsetup_thredds():
    os.environ["UVCDAT_ANONYMOUS_LOG"] = "no"
    esgsetup_command = '''esgsetup --config --minimal-setup --thredds --publish --gateway pcmdi11.llnl.gov --thredds-password {security_admin_password}'''.format(security_admin_password=esg_functions.get_security_admin_password())
    try:
        esg_functions.stream_subprocess_output(esgsetup_command)
    except Exception:
        logger.exception("Could not finish esgsetup")
        esg_functions.exit_with_error(1)

def copy_public_directory():
    '''HACK ALERT!! For some reason the public directory does not respect thredds' tds.context.root.path property...
    So have to manually move over this directory to avert server not starting! -gavin'''
    content_dir = os.path.join("{thredds_content_dir}".format(thredds_content_dir=config["thredds_content_dir"]), "thredds")
    if not os.path.isdir(content_dir):
        esg_bash2py.mkdir_p(content_dir)
        try:
            public_dir = "{tomcat_install_dir}/webapps/thredds/WEB-INF/altContent/startup/public".format(tomcat_install_dir=config["tomcat_install_dir"])
            copy_tree(public_dir, content_dir)
        except OSError, error:
            esg_functions.exit_with_error(error)

        tomcat_user = esg_functions.get_user_id("tomcat")
        tomcat_group = esg_functions.get_group_id("tomcat")
        esg_functions.change_ownership_recursive(config["thredds_content_dir"], tomcat_user, tomcat_group)

def verify_thredds_credentials():
    thredds_ini_file = "/esg/config/esgcet/esg.ini"

    print "Inspecting tomcat... "
    tree = etree.parse(config["tomcat_users_file"])
    root = tree.getroot()
    user_element = root.find("user")
    tomcat_username = user_element.get("username")
    tomcat_password_hash = user_element.get("password")

    print "Inspecting publisher... "
    # import ConfigParser
    # parser = ConfigParser.SafeConfigParser(allow_no_value=True)
    # parser.read(config_file)
    #
    # section1 = config['DEFAULT']
    print "Inspecting publisher... "
    thredds_username = esg_property_manager.get_property("thredds_username", config_file=thredds_ini_file, section_name="DEFAULT")
    thredds_password = esg_property_manager.get_property("thredds_password", config_file=thredds_ini_file, section_name="DEFAULT")
    thredds_password_hash = create_password_hash(thredds_password)

    print "Checking username... "
    if tomcat_username != thredds_username:
        print "The user_name property in {tomcat_users_file} doesn't match the user_name in {thredds_ini_file}".format(tomcat_users_file=config["tomcat_users_file"], thredds_ini_file=thredds_ini_file)
        raise Exception
        # sys.exit(1)

    print "Checking password... "
    if tomcat_password_hash != thredds_password_hash:
        print "The password property in {tomcat_users_file} doesn't match the password in {thredds_ini_file}".format(tomcat_users_file=config["tomcat_users_file"], thredds_ini_file=thredds_ini_file)
        raise Exception

    print "Verified Thredds crendentials"
    return True

def copy_jar_files():
    # TDS jars necessary to support ESGF security filters
    # some jars are retrieved from the ESGF repository
    # other jars are copied from the unpacked ORP or NM distributions
    esgf_devel_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel")
    urllib.urlretrieve("{esgf_devel_url}/filters/XSGroupRole-1.0.0.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/XSGroupRole-1.0.0.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/commons-httpclient-3.1.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-httpclient-3.1.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/commons-lang-2.6.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-lang-2.6.jar")
    urllib.urlretrieve("{esgf_devel_url}/esg-orp/esg-orp-2.9.3.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/esg-orp-2.9.3.jar")
    urllib.urlretrieve("{esgf_devel_url}/esgf-node-manager/esgf-node-manager-common-1.0.0.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/esgf-node-manager-common-1.0.0.jar")
    urllib.urlretrieve("{esgf_devel_url}/esgf-node-manager/esgf-node-manager-filters-1.0.0.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/esgf-node-manager-filters-1.0.0.jar")
    urllib.urlretrieve("{esgf_devel_url}/esgf-security/esgf-security-2.7.10.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/esgf-security-2.7.10.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/jdom-legacy-1.1.3.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/jdom-legacy-1.1.3.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/opensaml-2.3.2.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/opensaml-2.3.2.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/openws-1.3.1.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/openws-1.3.1.jar")
    urllib.urlretrieve("{esgf_devel_url}/filters/xmltooling-1.2.2.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/xmltooling-1.2.2.jar")

    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/serializer-2.9.1.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/serializer-2.9.1.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/velocity-1.5.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/velocity-1.5.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/xalan-2.7.2.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/xalan-2.7.2.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/xercesImpl-2.10.0.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/xercesImpl-2.10.0.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/xml-apis-1.4.01.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/xml-apis-1.4.01.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/xmlsec-1.4.2.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/xmlsec-1.4.2.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/log4j-1.2.17.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/log4j-1.2.17.jar")
    shutil.copyfile("/usr/local/tomcat/webapps/esg-orp/WEB-INF/lib/commons-io-2.4.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-io-2.4.jar")

    try:
        shutil.copyfile("/usr/local/tomcat/webapps/esgf-node-manager/WEB-INF/lib/commons-dbcp-1.4.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-dbcp-1.4.jar")
    except IOError:
        urllib.urlretrieve("{esgf_devel_url}/filters/commons-dbcp-1.4.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-dbcp-1.4.jar")
    try:
        shutil.copyfile("/usr/local/tomcat/webapps/esgf-node-manager/WEB-INF/lib/commons-dbutils-1.3.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-dbutils-1.3.jar")
    except IOError:
        urllib.urlretrieve("{esgf_devel_url}/filters/commons-dbutils-1.3.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-dbutils-1.3.jar")
    try:
        shutil.copyfile("/usr/local/tomcat/webapps/esgf-node-manager/WEB-INF/lib/commons-pool-1.5.4.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-pool-1.5.4.jar")
    except IOError:
        urllib.urlretrieve("{esgf_devel_url}/filters/commons-pool-1.5.4.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/commons-pool-1.5.4.jar")
    try:
        shutil.copyfile("/usr/local/tomcat/webapps/esgf-node-manager/WEB-INF/lib/postgresql-8.4-703.jdbc3.jar", "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/postgresql-8.4-703.jdbc3.jar")
    except IOError:
        urllib.urlretrieve("{esgf_devel_url}/filters/postgresql-8.4-703.jdbc3.jar".format(esgf_devel_url=esgf_devel_url), "/usr/local/tomcat/webapps/thredds/WEB-INF/lib/postgresql-8.4-703.jdbc3.jar")

def download_thredds_xml():
    '''Download the thredds.xml file from the distribution mirror'''
    thredds_xml_url = "https://aims1.llnl.gov/esgf/dist/externals/bootstrap/tomcat-thredds.xml"
    esg_functions.download_update("{tomcat_conf_dir}/Catalina/localhost/thredds.xml".format(tomcat_conf_dir=config["tomcat_conf_dir"]), thredds_xml_url)

def download_thredds_config_xml():
    '''Download the threddsConfig.xml file from the distribution mirror'''
    thredds_config_url = "https://aims1.llnl.gov/esgf/dist/thredds/threddsConfig.xml.tmpl"
    esg_functions.download_update("/esg/content/thredds/threddsConfig.xml", thredds_config_url)

def download_application_context():
    '''Download the applicationContext.xml file from the distribution mirror'''
    application_context_url = "https://aims1.llnl.gov/esgf/dist/thredds/applicationContext.xml"
    esg_functions.download_update("/usr/local/tomcat/webapps/thredds/WEB-INF/applicationContext.xml", application_context_url)

def download_tomcat_users_xml():
    '''Download the tomcat-users.xml template from the distribution mirror'''
    tomcat_users_xml_url = "https://aims1.llnl.gov/esgf/dist/externals/bootstrap/tomcat-users.xml"
    tomcat_users_xml_local_path = "{tomcat_conf_dir}/tomcat-users.xml".format(tomcat_conf_dir=config["tomcat_conf_dir"])
    esg_functions.download_update(tomcat_users_xml_local_path, tomcat_users_xml_url)
    tomcat_user_id = esg_functions.get_user_id("tomcat")
    tomcat_group_id = esg_functions.get_group_id("tomcat")
    os.chown(tomcat_users_xml_local_path, tomcat_user_id, tomcat_group_id)

def setup_thredds():

    if os.path.isdir("/usr/local/tomcat/webapps/thredds"):
        thredds_install = raw_input("Existing Thredds installation found.  Do you want to continue with the Thredds installation [y/N]: " ) or "no"
        if thredds_install.lower() in ["no", "n"]:
            return

    print "\n*******************************"
    print "Setting up Thredds"
    print "******************************* \n"
    esg_tomcat_manager.stop_tomcat()

    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/thredds")
    thredds_url = os.path.join("http://", config["esgf_dist_mirror"], "dist", "devel", "thredds", "5.0", "5.0.2", "thredds.war")
    download_thredds_war(thredds_url)

    with esg_bash2py.pushd("/usr/local/tomcat/webapps/thredds"):
        with zipfile.ZipFile("/usr/local/tomcat/webapps/thredds/thredds.war", 'r') as zf:
            zf.extractall()
        os.remove("thredds.war")
        TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
        TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
        esg_functions.change_ownership_recursive("/usr/local/tomcat/webapps/thredds", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    download_tomcat_users_xml()
    add_tomcat_user()

    esg_bash2py.mkdir_p("{tomcat_conf_dir}/Catalina/localhost".format(tomcat_conf_dir=config["tomcat_conf_dir"]))
    download_thredds_xml()
    # get_webxml_file()
    shutil.copyfile(os.path.join(current_directory, "thredds_conf/web.xml"), "/usr/local/tomcat/webapps/thredds/web.xml")
    os.chown("/usr/local/tomcat/webapps/thredds/web.xml", TOMCAT_USER_ID, TOMCAT_GROUP_ID)
    copy_public_directory()
    # TDS configuration root
    esg_bash2py.mkdir_p(os.path.join(config["thredds_content_dir"], "thredds"))
    # TDS memory configuration
    download_thredds_config_xml()
    update_mail_admin_address()

    # ESGF root catalog
    shutil.copyfile(os.path.join(current_directory, "thredds_conf/catalog.xml"), "/esg/content/thredds/catalog.xml-esgcet")
    esg_bash2py.mkdir_p("/esg/content/thredds/esgcet")
    # TDS customized applicationContext.xml file with ESGF authorizer
    download_application_context()
    copy_jar_files()

    # TDS customized logging (uses DEBUG)
    shutil.copyfile(os.path.join(current_directory, "thredds_conf/log4j2.xml"), "/usr/local/tomcat/webapps/thredds/WEB-INF/classes/log4j2.xml")

    # data node scripts
    #TODO: Convert data node scripts to Python

    # change ownership of content directory
    TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
    TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
    esg_functions.change_ownership_recursive("/esg/content/thredds/", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    # change ownership of source directory
    esg_functions.change_ownership_recursive("/usr/local/webapps/thredds", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

    #restart tomcat to put modifications in effect.
    esg_tomcat_manager.start_tomcat()

    esgsetup_thredds()

    verify_thredds_credentials()

    # cleanup
    # shutil.rmtree("/usr/local/tomcat/webapps/esgf-node-manager/")

def main():
    setup_thredds()

if __name__ == '__main__':
    main()
