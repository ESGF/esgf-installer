import os
import shutil
import datetime
import errno
import logging
import yaml
import jks
import OpenSSL
import requests
import pybash
import esg_functions
import esg_property_manager
import esg_truststore_manager
from esg_exceptions import SubprocessError


logger = logging.getLogger("esgf_logger" +"."+ __name__)
current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

NO_LIST = ["n", "no", "N", "No", "NO"]
YES_LIST = ["y", "yes", "Y", "Yes", "YES"]

#------------------------------------
#   Keystore functions
#------------------------------------

def generate_tomcat_keystore(keystore_name, keystore_alias, private_key, public_cert, intermediate_certs):
    '''The following helper function creates a new keystore for your tomcat installation'''

    provider = "org.bouncycastle.jce.provider.BouncyCastleProvider"
    idptools_install_dir = os.path.join(config["esg_tools_dir"], "idptools")

    if len(intermediate_certs) < 1:
        print "No intermediate_certs files given"
        esg_functions.exit_with_error()

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

    cert_bundle = os.path.join(idptools_install_dir, "cert.bundle")
    ca_chain_bundle = os.path.join(idptools_install_dir, "ca_chain.bundle")

    cert_bundle, ca_chain_bundle = bundle_certificates(public_cert, intermediate_certs, idptools_install_dir)

    print "checking that key pair is congruent... "
    if check_associate_cert_with_private_key(public_cert, private_key):
        print "The keypair was congruent"
    else:
        print "The keypair was not congruent"
        esg_functions.exit_with_error()


    print "creating keystore... "
    #create a keystore with a self-signed cert
    distinguished_name = "CN={esgf_host}".format(esgf_host=esg_functions.get_esgf_host())

    #if previous keystore is found; backup
    backup_previous_keystore(keystore_name)

    #-------------
    #Make empty keystore...
    #-------------
    create_empty_java_keystore(keystore_name, keystore_alias, keystore_password, distinguished_name)

    #-------------
    #Convert your private key into from PEM to DER format that java likes
    #-------------
    derkey = convert_per_to_dem(private_key, idptools_install_dir)

    #-------------
    #Now we gather up all the other keys in the key chain...
    #-------------
    check_cachain_validity(ca_chain_bundle)

    print "Constructing new keystore content... "
    import_cert_into_keystore(keystore_name, keystore_alias, keystore_password, derkey, cert_bundle, provider)

    #Check keystore output
    java_keytool_executable = "{java_install_dir}/bin/keytool".format(java_install_dir=config["java_install_dir"])
    #TODO: Look at using pyjks to list Owner, Issuer, MD5, SHA1, and Serial Number
    check_keystore_command = "{java_keytool_executable} -v -list -keystore {keystore_name} -storepass {store_password}".format(java_keytool_executable=java_keytool_executable, keystore_name=keystore_name, store_password=keystore_password)
    print "check_keystore_command:", check_keystore_command
    keystore_output = esg_functions.call_subprocess(check_keystore_command)
    if keystore_output["returncode"] == 0:
        print "Mmmm, freshly baked keystore!"
        print "If Everything looks good... then replace your current tomcat keystore with {keystore_name}, if necessary.".format(keystore_name=keystore_name)
        print "Don't forget to change your tomcat's server.xml entry accordingly :-)"
        print "Remember: Keep your private key {private_key} and signed cert {public_cert} in a safe place!!!".format(private_key=private_key, public_cert=public_cert)
    else:
        print "Failed to check keystore"
        esg_functions.exit_with_error(keystore_output["stderr"])

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
    generate_keystore_string = "{java_keytool_executable} -genkey -keyalg RSA -alias {keystore_alias} -keystore {keystore_name} -storepass {keystore_password} -keypass {keystore_password} -validity 360 -dname {distinguished_name} -noprompt".format(java_keytool_executable=java_keytool_executable, keystore_alias=keystore_alias, keystore_name=keystore_name, keystore_password=keystore_password, distinguished_name=distinguished_name)
    keystore_output = esg_functions.call_subprocess(generate_keystore_string)
    if keystore_output["returncode"] != 0:
        print "Problem with generating initial keystore...Exiting."
        esg_functions.exit_with_error(keystore_output["stderr"])


def backup_previous_keystore(keystore_name):
    '''If a previous keystore exists, back it up'''
    if os.path.isfile(keystore_name):
        shutil.move(keystore_name, os.path.join(keystore_name+".bak"))

def import_cert_into_keystore(keystore_name, keystore_alias, keystore_password, derkey, cert_bundle, provider):
    '''Imports a signed Certificate into the keystore'''

    idptools_install_dir = os.path.join(config["esg_tools_dir"], "idptools")
    extkeytool_executable = os.path.join(idptools_install_dir, "bin", "extkeytool")
    if not os.path.isfile(extkeytool_executable):
        install_extkeytool()

    command = "{extkeytool} -importkey -keystore {keystore_name} -alias {keystore_alias} -storepass {keystore_password} -keypass {keystore_password} -keyfile {derkey} -certfile {cert_bundle} -provider {provider}".format(extkeytool=extkeytool_executable, keystore_name=keystore_name, keystore_alias=keystore_alias, keystore_password=keystore_password, derkey=derkey, cert_bundle=cert_bundle, provider=provider)
    construct_keystore_output = esg_functions.call_subprocess(command)
    if construct_keystore_output["returncode"] != 0:
        print "Could not import cert %s into keystore %s" % (cert_bundle, keystore_name)

def install_keypair(private_key="/etc/esgfcerts/hostkey.pem", public_cert="/etc/esgfcerts/hostcert.pem", keystore_name=config["keystore_file"], keystore_alias=config["keystore_alias"]):
    '''
    Once you have submitted the CSR and have gotten it back *signed*; now install the keypair
    If you want to install a commercial CA issued certificate:
    esg-node --install-keypair <certificate file> <key file>
    When prompted for the cachain file, specify the chain file provided by your CA'''


    #Exit if public_cert(signed CSR isn't found)
    if not os.path.isfile(public_cert):
        print "{public_cert} not found. Exiting.".format(public_cert=public_cert)
        esg_functions.exit_with_error()

    if not os.path.isfile(private_key):
        print "{private_key} not found. Exiting.".format(private_key=private_key)
        esg_functions.exit_with_error()

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
    try:
        shutil.copyfile(public_cert, "/etc/certs/hostcert.pem")
    except shutil.Error:
        if os.path.samefile(public_cert, "/etc/certs/hostcert.pem"):
            logger.debug("%s and /etc/certs/hostcert.pem are the same file", public_cert)
        else:
            logger.exception("Error copying host cert.")

    cert_files = create_certificate_chain_list()
    create_certificate_chain(cert_files)

    os.chmod("/etc/certs/hostkey.pem", 0400)
    os.chmod("/etc/certs/hostcert.pem", 0644)
    os.chmod("/etc/certs/cachain.pem", 0644)


    generate_tomcat_keystore(keystore_name, keystore_alias, private_key, public_cert, cert_files)

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
    except OSError, error:
        if error.errno == errno.ENOENT:
            logger.info("Existing cert %s not found.  Copying public cert to Tomcat config directory: %s", esgf_cert_name, config["tomcat_conf_dir"])
            shutil.copyfile(public_cert, esgf_cert_name)

def convert_per_to_dem(private_key, key_output_dir):
    '''Convert your private key into from PEM to DER format that java likes'''
    print "\n*******************************"
    print "converting private key from PEM to DER... "
    print "******************************* \n"
    derkey = os.path.join(key_output_dir, "key.der")
    convert_to_der = esg_functions.call_subprocess("openssl pkcs8 -topk8 -nocrypt -inform PEM -in {private_key} -outform DER -out {derkey}".format(private_key=private_key, derkey=derkey))
    if convert_to_der["returncode"] != 0:
        print "Problem with preparing initial keystore...Exiting."
        esg_functions.exit_with_error(convert_to_der["stderr"])
    return derkey


def check_cachain_validity(ca_chain_bundle):
    '''Verify that the CA chain is valid'''
    print "checking that chain is valid... "
    if os.path.isfile(ca_chain_bundle):
        try:
            valid_chain = esg_functions.call_subprocess("openssl verify -CAfile {ca_chain_bundle} {ca_chain_bundle}".format(ca_chain_bundle=ca_chain_bundle))
            if "error" in valid_chain['stdout'] or "error" in valid_chain['stderr']:
                print "The chain is not valid.  (hint: did you include the root cert for the chain?)"
            else:
                print "{ca_chain_bundle} is valid.".format(ca_chain_bundle=ca_chain_bundle)
        except SubprocessError, error:
            print "Error verifying cachain:", error
    else:
        print "Hmmm... no chain provided [{ca_chain_bundle}], skipping this check..."

def bundle_certificates(public_cert, ca_chain, idptools_install_dir):
    '''Create certificate bundle from public cert and cachain'''
    print "\n*******************************"
    print "Bundling Certificates"
    print "******************************* \n"

    cert_bundle = os.path.join(idptools_install_dir, "cert.bundle")
    ca_chain_bundle = os.path.join(idptools_install_dir, "ca_chain.bundle")

    print "public_cert:", public_cert
    print "ca_chain:", ca_chain

    #Write public_cert to bundle first
    print "Signed Cert -----> ", public_cert
    if "http" not in public_cert:
        #Write contents of cert to cert_bundle_file
        with open(public_cert, "r") as cert_data:
            cert_contents = cert_data.read()
        with open(cert_bundle, "a") as cert_bundle_file:
            cert_bundle_file.write(cert_contents)
    else:
        #Make request for public_cert, then write public_cert contents to cert_bundle_file
        cert_contents = requests.get(public_cert).content
        with open(cert_bundle, "a") as cert_bundle_file:
            cert_bundle_file.write(cert_contents)

    num_of_certs = len(ca_chain)
    if num_of_certs > 0:
        for index, cert in enumerate(ca_chain):
            if index == num_of_certs-1:
                print "Root Cert -------> ", cert
                if "http" not in cert:
                    #Write contents of cert to cert_bundle_file and ca_chain_bundle
                    with open(cert, "r") as cert_data:
                        cert_contents = cert_data.read()
                    with open(cert_bundle, "a") as cert_bundle_file:
                        cert_bundle_file.write(cert_contents)
                    with open(ca_chain_bundle, "a") as ca_chain_bundle_file:
                        ca_chain_bundle_file.write(cert_contents)
                else:
                    cert_contents = requests.get(cert).content
                    with open(cert_bundle, "a") as cert_bundle_file:
                        cert_bundle_file.write(cert_contents)
                    with open(ca_chain_bundle, "a") as ca_chain_bundle_file:
                        ca_chain_bundle_file.write(cert_contents)
            else:
                print "Intermediate cert #{index} ----> {cert}".format(index=index, cert=cert)
                if "http" not in cert:
                    with open(cert, "r") as cert_data:
                        cert_contents = cert_data.read()
                    with open(cert_bundle, "a") as cert_bundle_file:
                        cert_bundle_file.write(cert_contents)
                    with open(ca_chain_bundle, "a") as ca_chain_bundle_file:
                        ca_chain_bundle_file.write(cert_contents)
                else:
                    cert_contents = requests.get(cert).content
                    with open(cert_bundle, "a") as cert_bundle_file:
                        cert_bundle_file.write(cert_contents)
                    with open(ca_chain_bundle, "a") as ca_chain_bundle_file:
                        ca_chain_bundle_file.write(cert_contents)

    return cert_bundle, ca_chain_bundle


def create_certificate_chain_list():
    '''Create a list of the certificates that will be a part of the certificate
        chain file'''
    default_cachain = "/etc/esgfcerts/cachain.pem"
    cert_files = []
    #Enter ca_chain file into list
    while True:
        if esg_property_manager.get_property("certfile.entry") in NO_LIST:
            certfile_entry = None
        else:
            print "Please enter your Certificate Authority's certificate chain file(s)"
            print "[enter each cert file/url press return, press return with blank entry when done]"
            certfile_entry = raw_input("Enter certificate chain file name: ")
        if not certfile_entry:
            if not cert_files:
                print "Adding default certificate chain file {default_cachain}".format(default_cachain=default_cachain)
                if os.path.isfile(default_cachain):
                    cert_files.append(default_cachain)
                    break
                else:
                    print "{default_cachain} does not exist".format(default_cachain=default_cachain)
                    print "Creating {default_cachain}".format(default_cachain=default_cachain)
                    pybash.mkdir_p("/etc/esgfcerts")
                    pybash.touch(default_cachain)
                    cert_files.append(default_cachain)
                    break
                    # esg_functions.exit_with_error(1)
            else:
                break
        else:
            if os.path.isfile(certfile_entry):
                cert_files.append(certfile_entry)
            else:
                print "{certfile_entry} does not exist".format(certfile_entry=certfile_entry)

    return cert_files


def create_certificate_chain(cert_files):
    '''Concatenate the certificates in the chain and copy them to /etc/certs'''
    print "\n*******************************"
    print "Creating Certificate Chain"
    print "******************************* \n"

    #Copy the tmpchain and rename to cachain
    with open("/etc/certs/tmpchain", "w") as tmpchain_file:
        for cert in cert_files:
            if not os.path.isfile(cert):
                print "{cert} not found. Exiting.".format(cert=cert)
                esg_functions.exit_with_error()

            with open(cert, "r") as cert_file_handle:
                cert_file_contents = cert_file_handle.read()
            tmpchain_file.write(cert_file_contents+"\n")

    shutil.copyfile("/etc/certs/tmpchain", "/etc/certs/cachain.pem")