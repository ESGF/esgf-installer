import os
import shutil
import glob
import filecmp
import logging
import socket
import ConfigParser
import yaml
import OpenSSL
import jks
import pybash
import esg_functions
from esgf_utilities import esg_property_manager
from plumbum.commands import ProcessExecutionError


logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

NO_LIST = ["n", "no", "N", "No", "NO"]
YES_LIST = ["y", "yes", "Y", "Yes", "YES"]


with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

#------------------------------------
#   Truststore functions
#------------------------------------

def create_new_truststore(truststore_file):
    '''Create a new Java Truststore file by copying the JRE's cacerts file'''
    shutil.copyfile("{java_install_dir}/jre/lib/security/cacerts".format(java_install_dir=config["java_install_dir"]), truststore_file)

def rebuild_truststore(truststore_file, certs_dir=config["globus_global_certs_dir"]):
    '''Converts ESG certificates (that can be fetch by above function) into a truststore'''

    print "(Re)building truststore from esg certificates... [{truststore_file}]".format(truststore_file=truststore_file)

    if not os.path.isdir(certs_dir):
        print "Sorry, No esg certificates found... in {certs_dir}".format(certs_dir=certs_dir)
        fetch_esgf_certificates(certs_dir)

    #If you don't already have a truststore to build on....
    #Start building from a solid foundation i.e. Java's set of ca certs...
    if not os.path.isfile(truststore_file):
        create_new_truststore(truststore_file)

    cert_files = glob.glob('{certs_dir}/*.0'.format(certs_dir=certs_dir))
    for cert in cert_files:
        _insert_cert_into_truststore(cert, truststore_file)

    sync_with_java_truststore(truststore_file)
    os.chown(truststore_file, esg_functions.get_user_id("tomcat"), esg_functions.get_group_id("tomcat"))


def add_my_cert_to_truststore(truststore_file=config["truststore_file"], keystore_file=config["keystore_file"], keystore_alias=config["keystore_alias"]):
    '''
        #This takes our certificate from the keystore and adds it to the
        #truststore.  This is done for other services that use originating
        #from this server talking to another service on this same host.  This
        #is the interaction scenario with part of the ORP security mechanism.
        #The param here is the password of the *keystore*
    '''
    #----------------------------------------------------------------
    #Re-integrate my public key (I mean, my "certificate") from my keystore into the truststore (the place housing all public keys I allow to talk to me)
    #----------------------------------------------------------------

    print "\n*******************************"
    print "Adding public key to truststore file {truststore_file}".format(truststore_file=truststore_file)
    print "******************************* \n"
    if os.path.isfile(truststore_file):
        print "Re-Integrating keystore's certificate into truststore.... "
        print "Extracting keystore's certificate... "
        keystore_password = esg_functions.get_java_keystore_password()
        keytool_binary = "{}/bin/keytool".format(config["java_install_dir"])
        extract_cert_options = ["-export", "-alias", keystore_alias, "-keystore", keystore_file, "-file", "{}.cer".format(keystore_file), "-storepass", keystore_password]
        try:
            esg_functions.call_binary(keytool_binary, extract_cert_options)
        except ProcessExecutionError:
            logger.error("Error extracting the certificate from the keystore %s", keystore_alias)
            raise
        else:
            logger.info("Extracted %s from %s", "{}.cer".format(keystore_file), keystore_alias)

        print "Importing keystore's certificate into truststore... "
        import_keystore_options = ["-import", "-v", "-trustcacerts", "-alias", keystore_alias, "-keypass", keystore_password, "-file", "{}.cer".format(keystore_file), "-keystore", config["truststore_file"], "-storepass", config["truststore_password"], "-noprompt"]
        try:
            esg_functions.call_binary(keytool_binary, import_keystore_options)
        except ProcessExecutionError:
            logger.error("Error importing certificate %s into truststore %s", "{}.cer".format(keystore_file), config["truststore_file"])
            raise
        else:
            logger.info("Imported %s into truststore %s", "{}.cer".format(keystore_file), config["truststore_file"])

        sync_with_java_truststore(truststore_file)

        try:
            os.remove(keystore_file+".cer")
        except OSError:
            logger.exception("Could not delete extracted cert file")

    os.chown(truststore_file, esg_functions.get_user_id("tomcat"), esg_functions.get_group_id("tomcat"))

def sync_with_java_truststore(truststore_file):
    jssecacerts_path = "{java_install_dir}/jre/lib/security/jssecacerts".format(java_install_dir=config["java_install_dir"])
    cacerts_path = "{java_install_dir}/jre/lib/security/cacerts".format(java_install_dir=config["java_install_dir"])
    if not os.path.isfile(jssecacerts_path) and os.path.isfile(cacerts_path):
        shutil.copyfile(cacerts_path, jssecacerts_path)

    if not os.path.join(truststore_file):
        logger.error("%s does not exist. Exiting.", truststore_file)
        raise OSError

    print "Syncing {truststore_file} with {java_truststore} ... ".format(truststore_file=truststore_file, java_truststore=jssecacerts_path)
    if filecmp.cmp(truststore_file, jssecacerts_path):
        print "Files already in sync"
        return

    try:
        shutil.copyfile(jssecacerts_path, jssecacerts_path+".bak")
    except OSError:
        logger.exception("Could not back up java truststore file.")

    try:
        shutil.copyfile(truststore_file, jssecacerts_path)
    except OSError:
        logger.exception("Could not sync truststore files.")

    os.chmod(jssecacerts_path, 0644)
    os.chown(jssecacerts_path, esg_functions.get_user_id("root"), esg_functions.get_group_id("root"))


def _insert_cert_into_truststore(cert_file, truststore_file):
    '''
    Takes full path to a pem certificate file and incorporates it into the
    given truststore
    '''

    print "Adding {cert_file} -> {truststore_file}".format(
        cert_file=cert_file,
        truststore_file=truststore_file
    )
    if not os.path.isfile(cert_file):
        raise IOError("{} not found".format(cert_file))

    logger.debug("cert_file: %s", cert_file)
    cert_name = pybash.trim_string_from_head(cert_file)
    logger.debug("cert_name: %s", cert_name)
    cert_hash = cert_name.split(".")[0]
    logger.debug("cert_hash: %s", cert_hash)

    # Convert from PEM format to DER aka ASN1 format - for ingest into keystore
    cert_pem = OpenSSL.crypto.load_certificate(
        OpenSSL.crypto.FILETYPE_PEM,
        open(cert_file).read()
    )
    dumped_cert_der = OpenSSL.crypto.dump_certificate(
        OpenSSL.crypto.FILETYPE_ASN1,
        cert_pem
    )

    truststore = jks.KeyStore.load(
        truststore_file,
        config["truststore_password"]
    )

    alias = cert_hash
    truststore.entries[alias] = jks.TrustedCertEntry.new(
        alias,
        dumped_cert_der
    )

    truststore.save(
        truststore_file,
        config["truststore_password"]
    )

def add_simpleca_cert_to_globus(globus_certs_dir="/etc/grid-security/certificates"):
    #certificate_issuer_cert "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"
    simple_CA_cert = "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"
    if os.path.isfile(simple_CA_cert):
        try:
            cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open(simple_CA_cert).read())
        except OpenSSL.crypto.Error:
            logger.exception("Certificate is not correct.")
            raise

        simpleCA_cert_hash = esg_functions.convert_hash_to_hex(cert_obj.subject_name_hash())
        my_cert = os.path.join(globus_certs_dir, simpleCA_cert_hash)
        print "checking for MY cert: {}.0".format(my_cert)
        if os.path.isfile("{}.0".format(my_cert)):
            print "Local CA cert file detected...."
            return
        else:
            print "Integrating in local simple_CA_cert... "
            logger.debug("Local SimpleCA Root Cert: %s", simple_CA_cert)
            logger.debug("Extracting Signing policy")

            #Copy simple CA cert to globus cert directory
            shutil.copyfile(simple_CA_cert, "{}/{}.0".format(globus_certs_dir, simpleCA_cert_hash))

            #extract simple CA cert tarball and copy to globus cert directory
            simpleCA_cert_parent_dir = esg_functions.get_parent_directory(simple_CA_cert)
            logger.debug("simpleCA_cert_parent_dir: %s", simpleCA_cert_parent_dir)
            simpleCA_setup_tar_file = os.path.join(simpleCA_cert_parent_dir, "globus_simple_ca_{}_setup-0.tar.gz".format(simpleCA_cert_hash))
            logger.debug("simpleCA_setup_tar_file: %s", simpleCA_setup_tar_file)
            esg_functions.extract_tarball(simpleCA_setup_tar_file)

            with pybash.pushd("globus_simple_ca_{}_setup-0".format(simpleCA_cert_hash)):
                shutil.copyfile("{}.signing_policy".format(simpleCA_cert_hash), "{}/{}.signing_policy".format(globus_certs_dir, simpleCA_cert_hash))

        os.chmod(globus_certs_dir, 0755)
        esg_functions.change_permissions_recursive(globus_certs_dir, 0644)

def fetch_esgf_certificates(globus_certs_dir="/etc/grid-security/certificates"):
    '''Goes to ESG distribution server and pulls down all certificates for the federation.
    (suitable for crontabbing)'''

    print "\n*******************************"
    print "Fetching freshest ESG Federation Certificates..."
    print "******************************* \n"
    #if globus_global_certs_dir already exists, backup and delete, then recreate empty directory
    if os.path.isdir(globus_certs_dir):
        cert_backup_dir = os.path.abspath(os.path.join(globus_certs_dir, os.pardir))
        esg_functions.backup(globus_certs_dir, cert_backup_dir)
        shutil.rmtree(globus_certs_dir)
    pybash.mkdir_p(globus_certs_dir)

    #Download trusted certs tarball
    esg_trusted_certs_file = "esg_trusted_certificates.tar"
    esg_root_url = esg_property_manager.get_property("esg.root.url")
    #TODO: Add in check of node-peer-group
    esg_trusted_certs_file_url = "{esg_root_url}/certs/{esg_trusted_certs_file}".format(esg_root_url=esg_root_url, esg_trusted_certs_file=esg_trusted_certs_file)
    esg_functions.download_update(os.path.join(globus_certs_dir, esg_trusted_certs_file), esg_trusted_certs_file_url)

    #untar the esg_trusted_certs_file
    esg_functions.extract_tarball(os.path.join(globus_certs_dir, esg_trusted_certs_file), globus_certs_dir)
    extracted_certs_dir = os.path.join(globus_certs_dir, "esg_trusted_certificates")
    cert_files = os.listdir(extracted_certs_dir)
    for file_name in cert_files:
        full_file_name = os.path.join(extracted_certs_dir, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, globus_certs_dir)
    os.remove(os.path.join(globus_certs_dir, esg_trusted_certs_file))

    add_simpleca_cert_to_globus()


def backup_truststore(truststore_file=config["truststore_file"]):
    '''Create backup of truststore file'''
    if os.path.exists(truststore_file):
        shutil.copyfile(truststore_file, truststore_file+".bak")

def backup_apache_truststore(apache_truststore='/etc/certs/esgf-ca-bundle.crt'):
    '''Create backup of Apache truststore file'''
    if os.path.exists(apache_truststore):
        shutil.copyfile(apache_truststore, apache_truststore+".bak")

def download_truststore(truststore_file, esg_root_url, node_peer_group):
    '''Download truststore file from distribution mirror'''
    #separate file name from the rest of the file path (esg-truststore.ts by default)
    truststore_file_name = pybash.trim_string_from_head(truststore_file)

    if node_peer_group == "esgf-test":
        shutil.copyfile(os.path.join(current_directory, "../config/esg-truststore-test-federation.ts"), truststore_file)
    else:
        shutil.copyfile(os.path.join(current_directory, "../config/esg-truststore.ts"), truststore_file)

def download_apache_truststore(apache_truststore, esg_root_url, node_peer_group):
    '''Download apache truststore file from distribution mirror'''
    backup_apache_truststore(apache_truststore)

    #separate file name from the rest of the file path (esgf-ca-bundle.crt by default)
    apache_truststore_file_name = pybash.trim_string_from_head(apache_truststore)

    if not os.path.exists(apache_truststore):
        print "\n*******************************"
        print "Downloading Apache Truststore... "
        print "******************************* \n"
        if node_peer_group == "esgf-test":
            shutil.copyfile(os.path.join(current_directory, "../config/esgf-ca-bundle-test-federation.crt"), apache_truststore)
        else:
            shutil.copyfile(os.path.join(current_directory, "../config/esgf-ca-bundle.crt"), apache_truststore)

def fetch_esgf_truststore(truststore_file=config["truststore_file"], apache_truststore='/etc/certs/esgf-ca-bundle.crt', globus_certs_dir="/etc/grid-security/certificates"):
    '''Download ESGF Truststore from the distribution mirror'''
    print "\n*******************************"
    print "Fetching ESGF Federation Truststore... "
    print "*******************************\n"

    esg_root_url = esg_property_manager.get_property("esg.root.url")

    backup_truststore(truststore_file)

    if not os.path.exists(truststore_file):
        try:
            node_peer_group = esg_property_manager.get_property("node_peer_group")
        except ConfigParser.NoOptionError:
            raise "Could not find node peer group property"

        #download_truststore
        download_truststore(truststore_file, esg_root_url, node_peer_group)
        #download_apache_truststore
        download_apache_truststore(apache_truststore, esg_root_url, node_peer_group)

        #append cacert.pem to apache_truststore
        with open(apache_truststore, "a") as apache_truststore_file:
            ca_cert = open("/etc/tempcerts/cacert.pem").read()
            apache_truststore_file.write(ca_cert)

        simple_CA_cert = find_certificate_issuer_cert()

        simpleCA_cert_hash = get_certificate_subject_hash(simple_CA_cert)

        simpleCA_cert_hash_file = os.path.join(globus_certs_dir, simpleCA_cert_hash+".0")
        _insert_cert_into_truststore(simpleCA_cert_hash_file, truststore_file)

        add_my_cert_to_truststore()

#------------------------------------
#   Utility functions
#------------------------------------

def get_certificate_subject_hash(cert_path):
    '''Get certificate subject hash from certificate'''
    try:
        cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open(cert_path).read())
    except OpenSSL.crypto.Error:
        logger.exception("Certificate is not correct.")
    except IOError:
        logger.exception("Could not open %s", cert_path)

    return esg_functions.convert_hash_to_hex(cert_obj.subject_name_hash())

def find_certificate_issuer_cert():
    '''Returns path of certificate_issuer_cert from /esg/config/myproxy/myproxy-server.config'''
    myproxy_config_file = "{}/config/myproxy/myproxy-server.config".format(config["esg_root_dir"])
    if os.path.exists(myproxy_config_file):
        try:
            with open(myproxy_config_file) as myproxy_conf:
                for line in myproxy_conf.readlines():
                    if "certificate_issuer_cert" in line:
                        #.strip('\"') is for removing quotes
                        simple_CA_cert = line.split()[1].strip('\"')
                        return simple_CA_cert
        except IOError:
            raise


def install_peer_node_cert(remote_host):
    '''This function is for pulling in keys from hosts we wish to
    communicate with over an encrypted ssl connection.  This function
    must be run after tomcat is set up since it references server.xml.

    (called by setup_idp_peer)
    arg1 - hostname of the machine with the cert you want to get
    (arg2 - password to truststore where cert will be inserted)
    (arg3 - password to keystore - only applicable in "local" registration scenario)
    Formerly called register()
    '''

    print "Installing Public Certificate of Target Peer Node...[{}]".format(remote_host)

    with pybash.pushd(config["tomcat_conf_dir"]):
        esgf_host = esg_functions.get_esgf_host()
        ssl_endpoint = remote_host
        ssl_port = "443"

        if ssl_endpoint == esgf_host:
            #For local scenario need to pull from local keystore and put into local truststore... need keystore password in addition
            add_my_cert_to_truststore()
        else:
            pybash.mkdir_p(config["workdir"])
            with pybash.pushd(config["workdir"]):
                esg_dist_url = esg_property_manager.get_property("esg.dist.url")
                if not esg_functions.download_update('./InstallCert.class', "{}/utils/InstallCert.class".format(esg_dist_url)):
                    raise RuntimeError("Could not download utility class(1) for installing certificates")
                if not esg_functions.download_update('./InstallCert$SavingTrustManager.class', "{}/utils/InstallCert$SavingTrustManager.class".format(esg_dist_url)):
                    raise RuntimeError("Could not download utility class(2) for installing certificates")

            class_path = ".:{}".format(config["workdir"])

            #NOTE: The InstallCert code fetches Java's jssecacerts file (if
            #not there then uses the cacerts file) from java's jre and then adds the target's cert to it.
            #The output of the program is a new file named jssecacerts!      So here we get the output and rename it.
            esg_functions.call_binary("/usr/local/java/bin/java", ["-classpath", class_path, "InstallCert", "{}:{}".format(ssl_endpoint, ssl_port), config["truststore_password"], config["truststore_file"]])

            with pybash.pushd(config["tomcat_conf_dir"]):
                os.chmod(config["truststore_file"], 0644)

                tomcat_user = esg_functions.get_user_id("tomcat")
                tomcat_group = esg_functions.get_group_id("tomcat")

                os.chown(config["truststore_file"], tomcat_user, tomcat_group)

                sync_with_java_truststore(config["truststore_file"])
