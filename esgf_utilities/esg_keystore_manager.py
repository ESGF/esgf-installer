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

def generate_tomcat_keystore(keystore_name, keystore_alias, private_key, public_cert, cachain_file):
    '''The following helper function creates a new keystore for your tomcat installation'''

    # provider = "org.bouncycastle.jce.provider.BouncyCastleProvider"
    idptools_install_dir = os.path.join(config["esg_tools_dir"], "idptools")

    if not os.path.isfile(private_key):
        print "Private key file {private_key} does not exist".format(private_key=private_key)

    keystore_password = esg_functions.get_java_keystore_password()

    #-------------
    #Display values
    #-------------
    print "Keystore name : {keystore_name}".format(keystore_name=keystore_name)
    print "Keystore alias: {keystore_alias}".format(keystore_alias=keystore_alias)
    print "Keystore password: {keystore_password}".format(keystore_password=keystore_password)
    print "Private key   : {private_key}".format(private_key=private_key)
    print "Public cert  : {public_cert}".format(public_cert=public_cert)
    print "Certificates..."

    pybash.mkdir_p(idptools_install_dir)

    print "checking that key pair is congruent... "
    if check_associate_cert_with_private_key(public_cert, private_key):
        print "The keypair was congruent"
    else:
        raise RuntimeError("The keypair was not congruent")

    print "creating keystore... "

    # if previous keystore is found; backup
    backup_previous_keystore(keystore_name)

    # Converting PEM files to DER aka ASN1 strings
    with open(public_cert, "r") as certfile:
        dumped_cert = OpenSSL.crypto.dump_certificate(
            OpenSSL.crypto.FILETYPE_ASN1,
            OpenSSL.crypto.load_certificate(
                OpenSSL.crypto.FILETYPE_PEM,
                certfile.read()
            )
        )
    with open(cachain_file, "r") as certfile:
        dumped_cachain = OpenSSL.crypto.dump_certificate(
            OpenSSL.crypto.FILETYPE_ASN1,
            OpenSSL.crypto.load_certificate(
                OpenSSL.crypto.FILETYPE_PEM,
                certfile.read()
            )
        )
    with open(private_key, "r") as keyfile:
        dumped_key = OpenSSL.crypto.dump_privatekey(
            OpenSSL.crypto.FILETYPE_ASN1,
            OpenSSL.crypto.load_privatekey(
                OpenSSL.crypto.FILETYPE_PEM,
                keyfile.read()
            )
        )
    print "Constructing new keystore content... "
    pke = jks.PrivateKeyEntry.new(
        config["keystore_alias"],
        [dumped_cert, dumped_cachain],
        dumped_key,
        'rsa_raw'
    )
    keystore = jks.KeyStore.new('jks', [pke])
    keystore_dir = os.path.dirname(keystore_name)
    pybash.mkdir_p(keystore_dir)
    logger.debug("Adding %s to JavaKeystore at %s", private_key, keystore_name)
    # File, password
    keystore.save(config["keystore_file"], esg_functions.get_java_keystore_password())
    #-------------
    #Make empty keystore...
    #-------------
    # create_empty_java_keystore(keystore_name, keystore_alias, keystore_password, distinguished_name)


    #-------------
    #Now we gather up all the other keys in the key chain...
    #-------------
    check_cachain_validity(cachain_file)

    #Check keystore output
    java_keytool_executable = "{java_install_dir}/bin/keytool".format(java_install_dir=config["java_install_dir"])
    check_keystore_options = ["-v", "-list", "-keystore", keystore_name, "-storepass", keystore_password]
    try:
        esg_functions.call_binary(java_keytool_executable, check_keystore_options)
    except ProcessExecutionError:
        logger.error("Failed to check keystore")
        raise
    else:
        print "Keystore made at {}".format(keystore_name)
        print "Remember: Keep your private key {private_key} and signed cert {public_cert} in a safe place".format(private_key=private_key, public_cert=public_cert)

def check_associate_cert_with_private_key(cert, private_key):
    """
    :type cert: str
    :type private_key: str
    :rtype: bool
    """
    with open(private_key, "r") as private_key_file:
        private_key_contents = private_key_file.read()
    try:
        private_key_obj = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, private_key_contents)
    except OpenSSL.crypto.Error:
        logger.exception("Private key is not correct.")

    try:
        cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open(cert).read())
    except OpenSSL.crypto.Error:
        logger.exception("Certificate is not correct.")

    context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
    context.use_privatekey(private_key_obj)
    context.use_certificate(cert_obj)
    try:
        context.check_privatekey()
        return True
    except OpenSSL.SSL.Error:
        return False

def check_keystore(keystore_name, keystore_password):
    '''Check the contents of a given keystore or truststore'''

    keystore = jks.KeyStore.load(keystore_name, keystore_password)
    print "keystore:", keystore
    return keystore


def create_empty_java_keystore(keystore_name, keystore_alias, keystore_password, distinguished_name):
    '''Create a new empty Java Keystore using the JDK's keytool'''
    java_keytool_executable = "{java_install_dir}/bin/keytool".format(java_install_dir=config["java_install_dir"])
    generate_keystore_options = ["-genkey", "-keyalg", "RSA", "-alias", keystore_alias, "-keystore", keystore_name, "-storepass", keystore_password, "-keypass", keystore_password, "-validity", "360", "-dname", distinguished_name, "-noprompt"]
    try:
        esg_functions.call_binary(java_keytool_executable, generate_keystore_options)
    except ProcessExecutionError:
        logger.error("Could not create new empty Java Keystore")
        raise
    else:
        logger.info("Created new empty Java keystore")


def backup_previous_keystore(keystore_name):
    '''If a previous keystore exists, back it up'''
    if os.path.isfile(keystore_name):
        shutil.move(keystore_name, os.path.join(keystore_name+".bak"))

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

    os.chmod("/etc/certs/hostkey.pem", 0400)
    os.chmod("/etc/certs/hostcert.pem", 0644)
    os.chmod("/etc/certs/cachain.pem", 0644)

    try:
        esg_functions.call_binary("openssl",  ["verify", "-verbose", "-purpose", "sslserver", "-CAfile", "/etc/certs/cachain.pem", "/etc/certs/hostcert.pem"])
    except ProcessExecutionError:
        logger.error("Incomplete or incorrect chain. Try again")
        raise


    generate_tomcat_keystore(keystore_name, keystore_alias, private_key, public_cert, "/etc/certs/cachain.pem")

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

def check_cachain_validity(ca_chain_bundle):
    '''Verify that the CA chain is valid'''
    print "checking that chain is valid... "
    if os.path.isfile(ca_chain_bundle):
        check_cachain_options = ["verify", "-CAfile", ca_chain_bundle, ca_chain_bundle]
        try:
            esg_functions.call_binary("openssl", check_cachain_options)
        except ProcessExecutionError:
            logger.error("Error verifying cachain: Did you include the root cert for the chain?")
            raise
        else:
            logger.info("%s is valid", ca_chain_bundle)
    else:
        print "Hmmm... no chain provided [{ca_chain_bundle}], skipping this check..."


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
