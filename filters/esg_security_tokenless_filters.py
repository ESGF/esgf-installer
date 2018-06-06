'''Description: Installation of the esg-security infrastructure'''
import os
import logging
import shutil
import yaml
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from esgf_utilities import esg_version_manager
from esgf_utilities import esg_cert_manager
from esgf_utilities.esg_exceptions import SubprocessError
from base import esg_tomcat_manager
from base import esg_postgres

logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def setup_security_tokenless_filters():
    esg_bash2py.mkdir_p(config["workdir"])
    with esg_bash2py.pushd(config["workdir"]):
        install_security_tokenless_filters()

#TODO: refactor
def insert_file_at_pattern(target_file, input_file, pattern):
    '''Replace a pattern inside the target file with the contents of the input file'''
    f=open(target_file)
    s=f.read()
    f.close()
    f=open(input_file)
    filter = f.read()
    f.close()
    s=s.replace(pattern,filter)
    f=open(target_file,'w')
    f.write(s)
    f.close()

def install_security_tokenless_filters(dest_dir="/usr/local/tomcat/webapps/thredds", esg_filter_entry_file="esg-access-logging-filter-web.xml"):

    service_name = esg_bash2py.trim_string_from_head(dest_dir)
    esg_filter_entry_pattern = "<!--@@esg_security_tokenless_filter_entry@@-->"

    print "*******************************"
    print "Installing Tomcat ESG SAML/ORP (Tokenless) Security Filters... for {}".format(service_name)
    print "-------------------------------"
    print "ESG ORP Filter: v{}".format(config["esg_orp_version"])
    print "ESGF Security (SAML): v${}".format(config["esgf_security_version"])
    print "*******************************"
    print "Filter installation destination dir = {}".format(dest_dir)
    print "Filter entry file = {}".format(esg_filter_entry_file)
    print "Filter entry pattern = {}".format(esg_filter_entry_pattern)

    #Installs esg filter into web application's web.xml file, by replacing a
    #place holder token with the contents of the filter snippet file
    #"esg-security-filter.xml".

    #pre-checking... make sure the files we need in ${service_name}'s dir are there....
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF")):
        logger.error("WARNING: Could not find %s's installation dir - Filter Not Applied",service_name)
        return False
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF", "lib")):
        logger.error("Could not find WEB-INF/lib installation dir - Filter Not Applied")
        return False
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF", "lib")):
        logger.error("Could not find WEB-INF/lib installation dir - Filter Not Applied")
        return False
    if not os.path.exists(os.path.join(dest_dir, "WEB-INF", "web.xml")):
        logger.error("No web.xml file found for %s - Filter Not Applied", service_name)
        return False

    esg_tomcat_manager.stop_tomcat()

    get_orp_libs(os.path.join(dest_dir, "WEB-INF", "lib"))

    if not esg_filter_entry_pattern in open(os.path.join(dest_dir, "WEB-INF", "web.xml")).read():
        logger.info("No Pattern Found In File [%s/WEB-INF/web.xml] - skipping this filter setup\n", dest_dir)
        return

    with esg_bash2py.pushd(config["workdir"]):
        esg_dist_url = esg_property_manager.get_property("esg.dist.url")
        esg_security_filters_dist_url = "{}/filters".format(esg_dist_url)
        esg_functions.download_update("{}/{}".format(esg_security_filters_dist_url, esg_filter_entry_file))
        esg_filter_entry_file_path = esg_functions.readlinkf(esg_filter_entry_file)

    #Installs esg filter into web application's web.xml file, by replacing a
    #place holder token with the contents of the filter snippet file
    #"esg-security-filter.xml".
    with esg_bash2py.pushd(os.path.join(dest_dir, "WEB-INF")):
        #Replace the filter's place holder token in web app's web.xml file with the filter entry.
        #Use utility function...
        insert_file_at_pattern("web.xml", esg_filter_entry_file_path, esg_filter_entry_pattern)

        orp_host = esg_functions.get_esgf_host() #default assumes local install
        try:
            authorization_service_root = esg_property_manager.get_property("esgf_idp_peer") #ex: pcmdi3.llnl.gov/esgcet[/saml/soap...]
        except ConfigParser.NoOptionError:
            authorization_service_root = esg_functions.get_esgf_host()
        truststore_file = config["truststore_file"]
        truststore_password = config["truststore_password"]
        esg_root_dir = "/esg"

        print "Replacing tokens... "

        with open("web.xml", 'r') as file_handle:
            filedata = file_handle.read()
        filedata = filedata.replace("@orp_host@", orp_host)
        filedata = filedata.replace("@truststore_file@", truststore_file)
        filedata = filedata.replace("@truststore_password@", truststore_password)
        filedata = filedata.replace("@esg_root_dir@", esg_root_dir)

        # Write the file out again
        with open("web.xml", 'w') as file_handle:
            file_handle.write(filedata)

    tomcat_user = esg_functions.get_user_id("tomcat")
    tomcat_group = esg_functions.get_group_id("tomcat")
    esg_functions.change_ownership_recursive(os.path.join(dest_dir, "WEB-INF"), tomcat_user, tomcat_group)

    print "orp/security filters installed..."


def get_orp_libs(service_name="thredds"):
    '''Copies the filter jar file to the web app's lib dir
    arg 1 - The destination web application lib directory (default thredds)'''

    orp_service_app_home = "/usr/local/tomcat/webapps/esg-orp"
    dest_dir = "/usr/local/tomcat/webapps/{}/WEB-INF/lib".format(service_name)
    src_dir = os.path.join(orp_service_app_home, "WEB-INF", "lib")

    #Jar versions...
    opensaml_version = "2.3.2"
    openws_version = "1.3.1"
    xmltooling_version = "1.2.2"
    xsgroup_role_version = "1.0.0"

    #(formerly known as endorsed jars)
    commons_collections_version = "3.2.2"
    serializer_version = "2.9.1"
    velocity_version = "1.5"
    xalan_version = "2.7.2"
    xercesImpl_version = "2.10.0"
    xml_apis_version = "1.4.01"
    xmlsec_version = "1.4.2"
    joda_version = "2.0"
    commons_io_version = "2.4"
    slf4j_version = "1.6.4"

    #------------------------------------------------------------------
    #NOTE: Make sure that this version matches the version that is in
    #the esg-orp project!!!
    spring_version = "4.2.3.RELEASE"
    #------------------------------------------------------------------

    #----------------------------
    #Jar Libraries Needed To Be Present For ORP (tokenless) Filter Support
    #----------------------------
    opensaml_jar = "opensaml-{}.jar".format(opensaml_version)
    openws_jar = "openws-{}.jar".format(openws_version)
    xmltooling_jar = "xmltooling-{}.jar".format(xmltooling_version)
    xsgroup_role_jar = "XSGroupRole-{}.jar".format(xsgroup_role_version)

    #(formerly known as endorsed jars)
    commons_collections_jar = "commons-collections-{}.jar".format(commons_collections_version)
    serializer_jar = "serializer-{}.jar".format(serializer_version)
    velocity_jar = "velocity-{}.jar".format(velocity_version)
    xalan_jar = "xalan-{}.jar".format(xalan_version)
    xercesImpl_jar = "xercesImpl-{}.jar".format(xercesImpl_version)
    xml_apis_jar = "xml-apis-{}.jar".format(xml_apis_version)
    xmlsec_jar = "xmlsec-{}.jar".format(xmlsec_version)
    joda_time_jar = "joda-time-{}.jar".format(joda_version)
    commons_io_jar = "commons-io-{}.jar".format(commons_io_version)
    slf4j_api_jar = "slf4j-api-{}.jar".format(slf4j_version)
    slf4j_log4j_jar = "slf4j-log4j12-{}.jar".format(slf4j_version)

    spring_jar = "spring-core-{}.jar".format(spring_version)
    spring_web_jar = "spring-web-{}.jar".format(spring_version)
    spring_webmvc_jar = "spring-webmvc-{}.jar".format(spring_version)

    jar_list = [opensaml_jar, openws_jar, xmltooling_jar, xsgroup_role_jar, commons_collections_jar, serializer_jar, velocity_jar,
                xalan_jar, xercesImpl_jar, xml_apis_jar, xmlsec_jar, joda_time_jar, commons_io_jar, slf4j_api_jar, slf4j_log4j_jar]

    if os.path.exists(dest_dir):
        #move over SAML libraries...
        print "getting (copying) libary jars from the ORP to {}".format(dest_dir)
        esg_dist_url = esg_property_manager.get_property("esg.dist.url")
        for jar in jar_list:
            if not os.path.exists(os.path.join(dest_dir,jar)):
                shutil.copyfile(os.path.join(src_dir, jar), os.path.join(dest_dir,jar))

        #----------------------------
        #Fetching ORP / Security Jars from Distribution Site...
        #----------------------------

        #values inherited from esg-node calling script
        #-----
        #project generated jarfiles...
        esg_orp_jar = "esg-orp-{}.jar".format(config["esg_orp_version"])
        esgf_security_jar = "esgf-security-{}.jar".format(config["esgf_security_version"])
        #-----

        print  "getting (downloading) library jars from ESGF Distribution Server (ORP/Security) to {} ...".format(dest_dir)
        library_jars = [spring_jar, spring_web_jar, spring_webmvc_jar, esgf_security_jar, esg_orp_jar]

        for jar in library_jars:
            if jar == spring_jar and service_name != "las":
                continue
            if not os.path.exists(os.path.join(dest_dir, jar)) and os.path.exists(os.path.join(src_dir,jar)):
                shutil.copyfile(os.path.join(src_dir,jar), os.path.join(dest_dir, jar))
            else:
                #change url for security jar
                if jar == esgf_security_jar:
                    esg_functions.download_update(os.path.join(dest_dir,jar), "{}/esgf-security/{}".format(esg_dist_url, jar))
                elif jar == esg_orp_jar:
                    esg_functions.download_update(os.path.join(dest_dir,jar), "{}/esgf-orp/{}".format(esg_dist_url, jar))
                else:
                    esg_functions.download_update(os.path.join(dest_dir,jar), "{}/filters/{}".format(esg_dist_url, jar))

        tomcat_user = esg_functions.get_user_id("tomcat")
        tomcat_group = esg_functions.get_group_id("tomcat")
        esg_functions.change_ownership_recursive(os.path.join(dest_dir), tomcat_user, tomcat_group)