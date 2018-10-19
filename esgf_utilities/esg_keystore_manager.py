import os
import shutil
import datetime
import errno
import logging
import ConfigParser
import yaml
import jks
import OpenSSL
import requests
import pybash
import esg_functions
import esg_property_manager
import esg_truststore_manager
from plumbum.commands import ProcessExecutionError


logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

NO_LIST = ["n", "no", "N", "No", "NO"]
YES_LIST = ["y", "yes", "Y", "Yes", "YES"]

#------------------------------------
#   Keystore functions
#------------------------------------
def check_keystore(keystore_name, keystore_password):
    '''Check the contents of a given keystore or truststore'''

    keystore = jks.KeyStore.load(keystore_name, keystore_password)
    print "keystore:", keystore
    return keystore

def install_keypair(private_key="/etc/esgfcerts/hostkey.pem", public_cert="/etc/esgfcerts/hostcert.pem", keystore_name=config["keystore_file"], keystore_alias=config["keystore_alias"]):
    '''
    Once you have submitted the CSR and have gotten it back *signed*; now install the keypair
    If you want to install a commercial CA issued certificate:
    esg-node --install-keypair <certificate file> <key file>
    When prompted for the cachain file, specify the chain file provided by your CA'''


    #Exit if public_cert(signed CSR isn't found)
    if not os.path.isfile(public_cert):
        raise OSError("{} not found. Exiting.".format(public_cert))

    if not os.path.isfile(private_key):
        raise OSError ("{} not found. Exiting.".format(private_key))

    print "private key = ", private_key
    print "public cert = ", public_cert
    print "keystore name  = ", keystore_name
    print "keystore alias = ", keystore_alias


    #Copy and rename private_key and cert
    try:
        shutil.copyfile(private_key, "/etc/certs/hostkey.pem")
    except shutil.Error:
        if os.path.samefile(private_key, "/etc/certs/hostkey.pem"):
            logger.debug("%s and /etc/certs/hostkey.pem are the same file", private_key)
        else:
            logger.exception("Error copying private key.")
            raise
    try:
        shutil.copyfile(public_cert, "/etc/certs/hostcert.pem")
    except shutil.Error:
        if os.path.samefile(public_cert, "/etc/certs/hostcert.pem"):
            logger.debug("%s and /etc/certs/hostcert.pem are the same file", public_cert)
        else:
            logger.exception("Error copying host cert.")
            raise

    cert_files = create_certificate_chain_list()
    create_certificate_chain(cert_files)

    signed_cert_file = "/etc/certs/hostcert.pem"
    key_file = "/etc/certs/hostkey.pem"
    ca_chain_file = "/etc/certs/cachain.pem"

    os.chmod(key_file, 0400)
    os.chmod(signed_cert_file, 0644)
    os.chmod(ca_chain_file, 0644)

    



    try:
        esg_functions.call_binary("openssl",  ["verify", "-verbose", "-purpose", "sslserver", "-CAfile", ca_chain_file, signed_cert_file])
    except ProcessExecutionError:
        logger.error("Incomplete or incorrect chain. Try again")
        raise

    tmp_pkcs12_file = "/tmp/keystore.p12"
    pkcs12_export = [
        "pkcs12",
        "-export",
        "-nodes",
        "-in", signed_cert_file,
        "-inkey", key_file,
        "-certfile", ca_chain_file,
        "-passout", "pass:"+esg_functions.get_java_keystore_password(),
        "-out", tmp_pkcs12_file
    ]
    try:
        esg_functions.call_binary("openssl", pkcs12_export)
    except ProcessExecutionError:
        logger.error("Could not export pkcs12 keystore")
        raise

    pkcs12_import = [
        "-importkeystore",
        "-srckeystore", tmp_pkcs12_file,
        "-srcstoretype", "pkcs12",
        "-destkeystore", keystore_name,
        "-deststoretype", "JKS",
        "-srcstorepass", esg_functions.get_java_keystore_password(),
        "-deststorepass", esg_functions.get_java_keystore_password(),
        "-srcalias", "1",
        "-destalias", keystore_alias
    ]
    try:
        esg_functions.call_binary("/usr/local/java/bin/keytool", pkcs12_import)
    except ProcessExecutionError:
        logger.error("Could not import pkcs12 keystore")
        raise
    #generate_tomcat_keystore(keystore_name, keystore_alias, private_key, public_cert, cert_files)

    copy_cert_to_tomcat_conf(public_cert)

    if os.path.isfile(config["truststore_file"]):
        shutil.move(config["truststore_file"], config["truststore_file"]+".bak")

    #(In order for ORP or any other local service to trust eachother put your own cert into the truststore)
    esg_truststore_manager.rebuild_truststore(config["truststore_file"])
    esg_truststore_manager.add_my_cert_to_truststore(config["truststore_file"], keystore_name, keystore_alias)
    #     #register ${esgf_idp_peer}
    #
    #     echo "Please restart this node for keys to take effect: \"$0 restart\""
    #     echo
    # }

#------------------------------------
#   Utility functions
#------------------------------------

def install_extkeytool():
    '''Install the Extkeytool from the distribution mirror'''
    print "\n*******************************"
    print "Installing Extkeytool"
    print "******************************* \n"
    extkeytool_tarfile = pybash.trim_string_from_head(config["extkeytool_download_url"])
    esg_functions.download_update(extkeytool_tarfile, config["extkeytool_download_url"])
    esg_functions.extract_tarball(extkeytool_tarfile, "/esg/tools/idptools")

def copy_cert_to_tomcat_conf(public_cert):
    '''Copy the signed cert to the ESGF Tomcat config directory (i.e. /esg/config/tomcat)'''
    #Check for newer version of public_cert; if found backup old cert
    esgf_cert_name = os.path.join(config["tomcat_conf_dir"], "{esgf_host}-esg-node.pem".format(esgf_host=esg_functions.get_esgf_host()))

    try:
        if os.path.getctime(public_cert) > os.path.getctime(esgf_cert_name):
            backed_up_cert_name = "{esgf_cert_name}_{date}".format(esgf_cert_name=esgf_cert_name, date=str(datetime.date.today()))
            shutil.move(esgf_cert_name, backed_up_cert_name)
            shutil.copyfile(public_cert, esgf_cert_name)
    except IOError:
        logger.exception("Error while copying public cert")
        raise
    except OSError, error:
        if error.errno == errno.ENOENT:
            logger.info("Existing cert %s not found.  Copying public cert to Tomcat config directory: %s", esgf_cert_name, config["tomcat_conf_dir"])
            shutil.copyfile(public_cert, esgf_cert_name)
        else:
            raise

def create_certificate_chain_list():
    '''Create a list of the certificates that will be a part of the certificate
        chain file'''
    default_cachain = "/etc/esgfcerts/cachain.pem"
    try:
        cert_files = esg_property_manager.get_property("cachain.path")
    except ConfigParser.NoOptionError:
        print "Please enter your Certificate Authority's certificate chain file(s).  If there are multiple files, enter them separated by commas."
        cert_files = raw_input("Enter certificate chain file name: ")

    if cert_files:
        cert_files_list = [cert_path.strip() for cert_path in cert_files.split(",")]
        logger.info("cert_files_list: %s", cert_files_list)
        for filename in cert_files_list:
            if not os.path.isfile(filename.strip()):
                logger.error("%s does not exist.", filename)
                raise OSError
    else:
        print "Adding default certificate chain file {}".format(default_cachain)
        if not os.path.isfile(default_cachain):
            print "{} does not exist".format(default_cachain)
            print "Creating {}".format(default_cachain)
            pybash.mkdir_p("/etc/esgfcerts")
            pybash.touch(default_cachain)
        cert_files_list = [default_cachain]

    return cert_files_list


def create_certificate_chain(cert_files):
    '''Concatenate the certificates in the chain and copy them to /etc/certs'''
    print "\n*******************************"
    print "Creating Certificate Chain"
    print "******************************* \n"

    #Copy the tmpchain and rename to cachain
    with open("/etc/certs/tmpchain", "w") as tmpchain_file:
        for cert in cert_files:
            if not os.path.isfile(cert):
                raise OSError("{} not found. Exiting.".format(cert))

            with open(cert, "r") as cert_file_handle:
                cert_file_contents = cert_file_handle.read()
            tmpchain_file.write(cert_file_contents+"\n")

    shutil.copyfile("/etc/certs/tmpchain", "/etc/certs/cachain.pem")
