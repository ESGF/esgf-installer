'''
Certificate Management Functions
'''
import os
import shutil
from OpenSSL import crypto
import datetime
import glob
import filecmp
import logging
import socket
import requests
import yaml
import OpenSSL
import esg_bash2py
import esg_logging_manager
import esg_functions


logger = esg_logging_manager.create_rotating_log(__name__)

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

expired=0
day=60*60*24
warn=day*7
info=day*3

certs_expired = []
certs_immediate_expire = []
certs_week_expire = []
certs_month_expire = []

def create_certificate_chain_list():
    default_cachain = "/etc/esgfcerts/cachain.pem"
    cert_files = []
    #Enter ca_chain file into list
    print "Please enter your Certificate Authority's certificate chain file(s)"
    print "[enter each cert file/url press return, press return with blank entry when done]"
    while True:
        certfile_entry = raw_input("Enter certificate chain file name: ")
        if not certfile_entry:
            if not cert_files:
                print "Adding default certificate chain file {default_cachain}".format(default_cachain=default_cachain)
                if os.path.isfile(certfile_entry):
                    cert_files.append(certfile_entry)
                else:
                    print "{certfile_entry} does not exist".format(certfile_entry=certfile_entry)
                    break
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
    #Copy the tmpchain and rename to cachain
    with open("/etc/certs/tmpchain", "w") as tmpchain_file:
        for cert in cert_files:
            if not os.path.isfile(cert):
                print "{cert} not found. Exiting.".format(cert=cert)
                esg_functions.exit_with_error(1)

            with open(cert, "r") as cert_file_handle:
                cert_file_contents = cert_file_handle.read()
            tmpchain_file.write(cert_file_contents+"\n")

    shutil.copyfile("/etc/certs/tmpchain", "/etc/certs/cachain.pem")


def fetch_esgf_certificates():
    '''Goes to ESG distribution server and pulls down all certificates for the federation.
    (suitable for crontabbing)'''
    pass
    print "Fetching Freshest ESG Federation Certificates..."
    #if globus_global_certs_dir already exists, backup and delete, then recreate empty directory
    if os.path.isdir(config["globus_global_certs_dir"]):
        esg_functions.backup(config["globus_global_certs_dir"], os.path.join(config["globus_global_certs_dir"], ".bak.tz"))
        shutil.rmtree(config["globus_global_certs_dir"])
    esg_bash2py.mkdir_p(config["globus_global_certs_dir"])

    esg_trusted_certs_file = "esg_trusted_certificates.tar"
    esg_trusted_certs_file_url = "https://aims1.llnl.gov/esgf/dist/certs/{esg_trusted_certs_file}".format(esg_trusted_certs_file=esg_trusted_certs_file)
    esg_functions.download_update(esg_trusted_certs_file, esg_trusted_certs_file_url)
    #untar the esg_trusted_certs_file
    esg_functions.extract_tarball(esg_trusted_certs_file)
    #certificate_issuer_cert "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"
    simpleCA_cert = "/var/lib/globus-connect-server/myproxy-ca/cacert.pem"
    if os.path.isfile(simpleCA_cert):
        simpleCA_cert_hash = esg_functions.get_md5sum(simpleCA_cert)
        print "checking for MY cert: {globus_global_certs_dir}/{simpleCA_cert_hash}.0".format(globus_global_certs_dir=config["globus_global_certs_dir"], simpleCA_cert_hash=simpleCA_cert_hash)
        if os.path.isfile("{globus_global_certs_dir}/{simpleCA_cert_hash}.0".format(globus_global_certs_dir=config["globus_global_certs_dir"], simpleCA_cert_hash=simpleCA_cert_hash)):
            print "Local CA cert file detected...."
            print "Integrating in local simpleCA_cert... "
            print "Local SimpleCA Root Cert: {simpleCA_cert}".format(simpleCA_cert=simpleCA_cert)
            print "Extracting Signing policy"

            #Copy simple CA cert to globus cert directory
            shutil.copyfile(simpleCA_cert, "{globus_global_certs_dir}/{simpleCA_cert_hash}.0".format(globus_global_certs_dir=config["globus_global_certs_dir"], simpleCA_cert_hash=simpleCA_cert_hash))

            #extract simple CA cert tarball and copy to globus cert directory
            simpleCA_cert_parent_dir = esg_functions.get_parent_directory(simpleCA_cert)
            simpleCA_setup_tar_file = os.path.join(simpleCA_cert_parent_dir, "globus_simple_ca_{simpleCA_cert_hash}_setup-0.tar.gz".format(simpleCA_cert_hash=simpleCA_cert_hash))
            esg_functions.extract_tarball(simpleCA_setup_tar_file)
            with esg_bash2py.pushd("globus_simple_ca_{simpleCA_cert_hash}_setup-0".format(simpleCA_cert_hash=simpleCA_cert_hash)):
                shutil.copyfile("{simpleCA_cert_hash}.signing_policy".format(simpleCA_cert_hash=simpleCA_cert_hash), "{globus_global_certs_dir}/{simpleCA_cert_hash}.signing_policy".format(globus_global_certs_dir=config["globus_global_certs_dir"], simpleCA_cert_hash=simpleCA_cert_hash))
            if os.path.isdir("/usr/local/tomcat/webapps/ROOT"):
                esg_functions.stream_subprocess_output("openssl x509 -text -hash -in {simpleCA_cert} > {tomcat_install_dir}/webapps/ROOT/cacert.pem".format(simpleCA_cert=simpleCA_cert, tomcat_install_dir="/usr/loca/tomcat"))
                print " My CA Cert now posted @ http://{fqdn}/cacert.pem ".format(fqdn=socket.getfqdn())
                os.chmod("/usr/local/tomcat/webapps/ROOT/cacert.pem", 0644)

        os.chmod(config["globus_global_certs_dir"], 0755)
        esg_functions.change_permissions_recursive(config["globus_global_certs_dir"], 0644)

def install_extkeytool():
    extkeytool_tarfile = esg_bash2py.trim_string_from_head(config["extkeytool_download_url"])
    esg_functions.download_update(extkeytool_tarfile, config["extkeytool_download_url"])
    esg_functions.extract_tarball(extkeytool_tarfile, "/esg/tools/idptools")

def backup_previous_keystore(keystore_name):
    '''If a previous keystore exists, back it up'''
    if os.path.isfile(keystore_name):
        shutil.move(keystore_name, os.path.join(keystore_name,".bak"))

def create_empty_java_keystore(keystore_name, keystore_alias, keystore_password, distinguished_name):
    '''Create a new empty Java Keystore using the JDK's keytool'''
    java_keytool_executable = "{java_install_dir}/bin/keytool".format(java_install_dir=config["java_install_dir"])
    generate_keystore_string = "{java_keytool_executable} -genkey -keyalg RSA -alias {keystore_alias} -keystore {keystore_name} -storepass {keystore_password} -keypass {keystore_password} -validity 360 -dname {distinguished_name} -noprompt".format(java_keytool_executable=java_keytool_executable, keystore_alias=keystore_alias, keystore_name=keystore_name, keystore_password=keystore_password, distinguished_name=distinguished_name)
    keystore_output = esg_functions.call_subprocess(generate_keystore_string)
    if keystore_output["returncode"] !=0:
        print "Problem with generating initial keystore...Exiting."
        esg_functions.exit_with_error(1)

def convert_per_to_dem(private_key, key_output_dir):
    '''Convert your private key into from PEM to DER format that java likes'''
    print "converting private key from PEM to DER... "
    derkey = os.path.join(key_output_dir,"key.der")
    convert_to_der = esg_functions.call_subprocess("openssl pkcs8 -topk8 -nocrypt -inform PEM -in {private_key} -outform DER -out {derkey}".format(private_key=private_key, derkey=derkey))
    if convert_to_der["returncode"] !=0:
        print "Problem with preparing initial keystore...Exiting."
        esg_functions.exit_with_error(1)
    return derkey

def check_cachain_validity(ca_chain_bundle):
    '''Verify that the CA chain is valid'''
    print "checking that chain is valid... "
    if os.path.isfile(ca_chain_bundle):
        valid_chain = esg_functions.call_subprocess("openssl verify -CAfile {ca_chain_bundle} {ca_chain_bundle}".format(ca_chain_bundle=ca_chain_bundle))
        if "error" in valid_chain['stdout'] or "error" in valid_chain['stderr']:
            print "The chain is not valid.  (hint: did you include the root cert for the chain?)"
    else:
        print "Hmmm... no chain provided [{ca_chain_bundle}], skipping this check..."

def import_cert_into_keystore(keystore_name, keystore_alias, keystore_password, derkey, cert_bundle, provider, extkeytool_executable):
    '''Imports a signed Certificate into the keystore'''
    command = "{extkeytool} -importkey -keystore {keystore_name} -alias {keystore_alias} -storepass {keystore_password} -keypass {keystore_password} -keyfile {derkey} -certfile {certbundle} -provider {provider}".format(extkeytool=extkeytool_executable, keystore_name=keystore_name, keystore_alias=keystore_alias, keystore_password=keystore_password, derkey=derkey, cert_bundle=cert_bundle, provider=provider)
    construct_keystore_output = esg_functions.call_subprocess(command)
    #FYI: Code 127 is "command not found"
    if construct_keystore_output["returncode"] == 127:
        print "Hmmm... Cannot find extkeytool... :-( Let me get it for you! :-)  [one moment please...]"
        install_extkeytool()
        print "Retrying to build keystore with extkeytool"
        esg_functions.stream_subprocess_output(command)

def bundle_certificates(public_cert, ca_chain, idptools_install_dir):
    cert_bundle = os.path.join(idptools_install_dir, "cert.bundle")
    ca_chain_bundle = os.path.join(idptools_install_dir, "ca_chain.bundle")

    '''Create certificate bundle from public cert and cachain'''
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

def generate_tomcat_keystore(keystore_name, keystore_alias, keystore_password, private_key, public_cert, intermediate_certs):
    '''The following helper function creates a new keystore for your tomcat installation'''
    # arg 1 -> keystore name
    # arg 2 -> keystore alias
    # arg 3 -> keystore password
    # arg 4 -> private key
    # arg 5 -> public cert
    # arg 6.. -> intermediate certificate(s)
    provider = "org.bouncycastle.jce.provider.BouncyCastleProvider"
    idptools_install_dir = os.path.join(config["esg_tools_dir"], "idptools")

    if len(intermediate_certs) < 1:
        print "No intermediate_certs files given"
        esg_functions.exit_with_error(1)

    if not os.path.isfile(private_key):
        print "Private key file {private_key} does not exist".format(private_key=private_key)
    #

    #-------------
    #Display values
    #-------------
    print "Keystore name : {keystore_name}".format(keystore_name=keystore_name)
    print "Keystore alias: {keystore_alias}".format(keystore_alias=keystore_alias)
    print "Keystore password: {keystore_password}".format(keystore_password=keystore_password)
    print "Private key   : {private_key}".format(private_key=private_key)
    print "Certificates..."

    esg_bash2py.mkdir_p(idptools_install_dir)
    extkeytool_executable = os.path.join(idptools_install_dir, "bin", "extkeytool")

    cert_bundle = os.path.join(idptools_install_dir, "cert.bundle")
    ca_chain_bundle = os.path.join(idptools_install_dir, "ca_chain.bundle")

    cert_bundle, ca_chain_bundle = bundle_certificates(public_cert, intermediate_certs, idptools_install_dir)

    print "checking that key pair is congruent... "
    if check_associate_cert_with_private_key(public_cert, private_key):
        print "The keypair was congruent"
    else:
        print "The keypair was not congruent"
        esg_functions.exit_with_error(1)


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
        import_cert_into_keystore(keystore_name, keystore_alias, keystore_password, derkey, cert_bundle, provider, extkeytool_executable)

        #Check keystore output
        java_keytool_executable = "{java_install_dir}/bin/keytool".format(java_install_dir=config["java_install_dir"])
        check_keystore_command = "{java_keytool_executable} -v -list -keystore {keystore_name} -storepass {store_password} | egrep '(Owner|Issuer|MD5|SHA1|Serial number):'".format(java_keytool_executable=java_keytool_executable, keystore_name=keystore_name, store_password=keystore_password)
        keystore_output = esg_functions.call_subprocess(check_keystore_command)
        if keystore_output["returncode"] == 0:
            print "Mmmm, freshly baked keystore!"
            print "If Everything looks good... then replace your current tomcat keystore with {keystore_name}, if necessary.".format(keystore_name=keystore_name)
            print "Don't forget to change your tomcat's server.xml entry accordingly :-)"
            print "Remember: Keep your private key {private_key} and signed cert {public_cert} in a safe place!!!".format(private_key=private_key, public_cert=public_cert)
        else:
            print "Failed to check keystore"
            esg_functions.exit_with_error(1)

    '''Generate a keystore for'''


def check_associate_cert_with_private_key(cert, private_key):
    """
    :type cert: str
    :type private_key: str
    :rtype: bool
    """
    try:
        private_key_obj = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, private_key)
    except OpenSSL.crypto.Error:
        logger.exception("Private key is not correct.")

    try:
        cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
    except OpenSSL.crypto.Error:
        logger.exception("Certificate is not correct.")
        # raise Exception('certificate is not correct: %s' % cert)

    context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
    context.use_privatekey(private_key_obj)
    context.use_certificate(cert_obj)
    try:
        context.check_privatekey()
        return True
    except OpenSSL.SSL.Error:
        return False


#------------------------------------
#   Truststore functions
#------------------------------------
def rebuild_truststore(truststore_file):
    '''Converts ESG certificates (that can be fetch by above function) into a truststore'''

    print "(Re)building truststore from esg certificates... [{truststore_file}]".format(truststore_file=truststore_file)

    if not os.path.isdir(config["globus_global_certs_dir"]):
        print "Sorry, No esg certificates found... in {globus_global_certs_dir}".format(globus_global_certs_dir=config["globus_global_certs_dir"])
        print "Fetching fresh esg certificates"
        fetch_esgf_certificates()

        #If you don't already have a truststore to build on....
        #Start building from a solid foundation i.e. Java's set of ca certs...
        if not os.path.isfile(truststore_file):
            shutil.copyfile("{java_install_dir}/jre/lib/security/cacerts".format(java_install_dir=config["java_install_dir"]), truststore_file)

        tmp_dir = "/tmp/esg_scratch"
        esg_bash2py.mkdir_p(tmp_dir)

        cert_files = glob.glob('{globus_global_certs_dir}/*.0'.format(globus_global_certs_dir=config["globus_global_certs_dir"]))
        for cert in cert_files:
            _insert_cert_into_truststore(cert, truststore_file, tmp_dir)
        shutil.rmtree(tmp_dir)

        sync_with_java_truststore(truststore_file)
        os.chown(truststore_file, esg_functions.get_user_id("tomcat"), esg_functions.get_group_id("tomcat"))


def add_my_cert_to_truststore(truststore_file, keystore_file, keystore_alias):
    #----------------------------------------------------------------
    #Re-integrate my public key (I mean, my "certificate") from my keystore into the truststore (the place housing all public keys I allow to talk to me)
    #----------------------------------------------------------------
    if os.path.isfile(truststore_file):
        print "Re-Integrating keystore's certificate into truststore.... "
        print "Extracting keystore's certificate... "
        keystore_password = esg_functions.get_java_keystore_password()
        extract_cert_output= esg_functions.call_subprocess("{java_install_dir}/bin/keytool -export -alias {keystore_alias} -file {keystore_file}.cer -keystore {keystore_file} -storepass {keystore_password}".format(java_install_dir=config["java_install_dir"], keystore_alias=keystore_alias, keystore_file=keystore_file, keystore_password=keystore_password))
        if extract_cert_output["returncode"] !=0:
            print "Could not extract certificate from keystore"
            esg_functions.exit_with_error(1)

        print "Importing keystore's certificate into truststore... "
        import_to_truststore_output = esg_functions.call_subprocess("{java_install_dir}/bin/keytool -import -v -trustcacerts -alias {keystore_alias} -keypass {keystore_password} -file {keystore_file}.cer -keystore {truststore_file} -storepass {truststore_password_} -noprompt".format(java_install_dir=config["java_install_dir"], keystore_alias=keystore_alias, keystore_file=keystore_file, keystore_password=keystore_password))
        if import_to_truststore_output["returncode"] !=0:
            print "Could not import the certificate into the truststore"
            esg_functions.exit_with_error(1)

        sync_with_java_truststore(truststore_file)

        try:
            os.remove(keystore_file+".cer")
        except OSError:
            logger.exception("Could not delete extracted cert file")

    os.chown(truststore_file, esg_functions.get_user_id("tomcat"), esg_functions.get_group_id("tomcat"))


def sync_with_java_truststore(truststore_file):
    jssecacerts_path = "{java_install_dir}/jre/lib/security/jssecacerts"
    cacerts_path = "{java_install_dir}/jre/lib/security/cacerts"
    if not os.path.isfile(jssecacerts_path) and os.path.isfile(cacerts_path):
        shutil.copyfile(cacerts_path, jssecacerts_path)

    if not os.path.join(truststore_file):
        print "{truststore_file} does not exist. Exiting."
        esg_functions.exit_with_error(1)

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


def _insert_cert_into_truststore(cert_file, truststore_file, tmp_dir):
    #Takes full path to a pem certificate file and incorporates it into the given truststore

    print "{cert_file} ->".format(cert_file=cert_file)
    cert_hash = cert_file.split(".")[0]
    der_file = os.path.join(tmp_dir, cert_hash+".der")
    #--------------
    # Convert from PEM format to DER format - for ingest into keystore
    cert_pem = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_file)
    with open(der_file, "w") as der_file_handle:
        der_file_handle.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_ASN1,cert_pem))

    #--------------
    if os.path.isfile(truststore_file):
        output = esg_functions.call_subprocess("/usr/local/java/bin/keytool -delete -alias {cert_hash} -keystore {truststore_file} -storepass {truststore_password}".format(cert_hash=cert_hash, truststore_file=truststore_file, truststore_password=config["truststore_password"]))
        if output["returncode"] == 0:
            print "Deleted cert hash"

        output = esg_functions.call_subprocess("/usr/local/java/bin/keytool -import -alias {cert_hash} -file {der_file} -keystore {truststore_file} -storepass {truststore_password} -noprompt".format(cert_hash=cert_hash, der_file=der_file, truststore_file=truststore_file, truststore_password=config["truststore_password"]))
        if output["returncode"] == 0:
            print "added {der_file} to {truststore_file}".format(der_file=der_file, truststore_file=truststore_file)
        os.remove(der_file)

def install_tomcat_keypair(private_key="/etc/esgfcerts/hostkey.pem", public_cert="/etc/esgfcerts/hostcert.pem", keystore_name=config["keystore_file"], keystore_alias=config["keystore_alias"]):
    '''If you want to install a commercial CA issued certificate:
    esg-node --install-keypair <certificate file> <key file>
    When prompted for the cachain file, specify the chain file provided by your CA'''

    #Exit if public_cert(signed CSR isn't found)
    if not os.path.isfile(public_cert):
        print "{public_cert} not found. Exiting.".format(public_cert=public_cert)
        esg_functions.exit_with_error(1)

    if not os.path.isfile(private_key):
        print "{private_key} not found. Exiting.".format(private_key=private_key)
        esg_functions.exit_with_error(1)

    print "private key = ", private_key
    print "public cert = ", public_cert
    print "keystore name  = ", keystore_name
    print "keystore alias = ", keystore_alias

    #TODO: Maybe move this to generate_tomcat_keystore() function for better cohesion; #Setting the password to be used in keystore creation; Can be moved to more relevant function
    keystore_password = esg_functions.get_java_keystore_password()

    #Copy and rename private_key and cert
    shutil.copyfile(private_key, "/etc/certs/hostkey.pem")
    shutil.copyfile(public_cert, "/etc/certs/hostcert.pem")

    cert_files = create_certificate_chain_list()
    create_certificate_chain(cert_files)

    os.chmod("/etc/certs/hostkey.pem", 0400)
    os.chmod("/etc/certs/hostcert.pem", 0644)
    os.chmod("/etc/certs/cachain.pem", 0644)


    generate_tomcat_keystore(keystore_name, keystore_alias, keystore_password, private_key, public_cert, cert_files)

    #Check for newer version of public_cert; if found backup old cert
    try:
        if os.path.getctime(public_cert) > os.path.getctime(os.path.join(config["tomcat_conf_dir"], esg_functions.get_esgf_host(), "-esg-node.pem")):
            shutil.move(os.path.join(config["tomcat_conf_dir"], esg_functions.get_esgf_host(), "-esg-node.pem"), os.path.join(config["tomcat_conf_dir"], esg_functions.get_esgf_host(), "-esg-node.pem.old"))
            shutil.copyfile(public_cert, os.path.join(config["tomcat_conf_dir"], esg_functions.get_esgf_host(), "-esg-node.pem"))
    except IOError:
        logger.exception("Error while copying public cert")

    if os.path.isfile(config["truststore_file"]):
        shutil.move(config["truststore_file"], config["truststore_file"]+".bak")

    #(In order for ORP or any other local service to trust eachother put your own cert into the truststore)
    rebuild_truststore(config["truststore_file"])
    add_my_cert_to_truststore(config["truststore_file"], keystore_name, keystore_alias)
    #     #register ${esgf_idp_peer}
    #
    #     echo "Please restart this node for keys to take effect: \"$0 restart\""
    #     echo
    # }


def print_cert(certificate_path):
    print "CERTIFICATE = %s" % (certificate_path)
    # cert_file = '/path/to/your/certificate'
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(certificate_path).read())
    print cert
    # subject = cert.get_subject()
    # issued_to = subject.CN    # the Common Name field
    # issuer = cert.get_issuer()
    # issued_by = issuer.CN

def check_cert_expiry(certificate_path):
    pass

    # print "inspecting %s" % (certificate_path)
    # try:
    #     cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(certificate_path).read())
    #     if cert.has_expired():
    #         certs_expired.append(cert)
    #         return
    #     expire_date = datetime.strptime(cert.notAfter(), "%Y%m%d%H%M%SZ")
    #     expire_in = expire_date - datetime.now()
    #     if expire_in.days < 0:
    #         certs_immediate_expire.append(cert)
    #     elif expire_in.days <= 7:
    #         certs_week_expire.append(cert)
    #     elif expire_in.days <= 30:
    #         certs_month_expire.append(cert)
    #
    # except:
    #     # exit_error(1, 'Certificate date format unknow.')
    #     print "Certificate date formate unknown."

def check_cert_expiry_for_files(file_path):
    print "Checking for expired certs [file(s): %s]..." % (file_path)

    # for file in $@
    # do
    #     [ ! -e "${file}" ] && echo "no such file: ${file}, skipping... " && continue
    #     check_cert_expiry ${file}
    # done
    for file in file_path:
        if not os.path.isfile(file):
            print "no such file: %s, skipping... " % (file)
            continue
        check_cert_expiry(file)

    # ocal message=
    # [ "$var_expire" ] && message=$message"Certificates will expire in:\n$var_expire\n"
    # [ "$certs_expire" ] && message=$message"Certificates already expired :\n$certs_expire\n"
    # [ "$certs_day" ] && message=$message"Certificates will expire within a day:\n$certs_day\n"
    # [ "$certs_warn" ] && message=$message"Certificates expiring this week:\n$certs_warn\n"
    # [ "$certs_info" ] && message=$message"Certificates expiring this month:\n$certs_info\n"

    # #mail -s "Certificates Expiration closes" gavin@llnl.gov < <(printf "$message")
    # printf "$message"
    print  "Certificates already expired :\n%s\n" % (certs_expired)
    print "Certificates will expire within a day:\n%s\n" % (certs_immediate_expire)
    print "Certificates expiring this week:\n%s\n" % (certs_week_expire)
    print "Certificates expiring this month:\n%s\n" % (certs_month_expire)

# TODO: No uses found
def check_certs_in_dir():
    pass

def trash_expired_cert(certificate_path):
    trash_directory = esg_bash2py.Expand.colonMinus("ESGF_PROJECT_ROOT", "/tmp")+"/trash"
    os.mkdir(trash_directory)
    shutil.move(certificate_path, trash_directory)
    print "Trashed expired certificate %s" % (certificate_path)


# TODO: No uses found
def set_aside_web_app():
    pass

# TODO: No uses found
def set_aside_web_app_cleanup():
    pass


def create_self_signed_cert(cert_dir):
    """
    If datacard.crt and datacard.key don't exist in cert_dir, create a new
    self-signed cert and keypair and write them into that directory.

    Source: https://skippylovesmalorie.wordpress.com/2010/02/12/how-to-generate-a-self-signed-certificate-using-pyopenssl/
    """
    CERT_FILE = "mycert.pem"
    KEY_FILE = "mykey.pem"

    if not os.path.exists(os.path.join(cert_dir, CERT_FILE)) \
            or not os.path.exists(os.path.join(cert_dir, KEY_FILE)):

        # create a key pair
        k = OpenSSL.crypto.PKey()
        k.generate_key(OpenSSL.crypto.TYPE_RSA, 1024)

        # create a self-signed cert
        cert = OpenSSL.crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "California"
        cert.get_subject().L = "Livermore"
        cert.get_subject().O = "LLNL"
        cert.get_subject().OU = "ESGF"
        cert.get_subject().CN = socket.gethostname()
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha1')

        open(os.path.join(cert_dir, CERT_FILE), "wt").write(
            OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert))
        open(os.path.join(cert_dir, KEY_FILE), "wt").write(
            OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, k))
