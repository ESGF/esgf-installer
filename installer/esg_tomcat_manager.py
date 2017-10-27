'''
Tomcat Management Functions
'''
import os
import subprocess
import sys
import hashlib
import shutil
import grp
import datetime
import socket
import re
import pwd
import tarfile
import urllib
import shlex
import filecmp
import glob
import yaml
import errno
import progressbar
import requests
import errno
import getpass
from time import sleep
import OpenSSL
from lxml import etree
import esg_functions
import esg_bash2py
import esg_property_manager
import esg_logging_manager
from clint.textui import progress


logger = esg_logging_manager.create_rotating_log(__name__)

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

pbar = None
downloaded = 0
def show_progress(count, block_size, total_size):
    global pbar
    global downloaded
    if pbar is None:
        pbar = progressbar.ProgressBar(maxval=total_size)

    downloaded += block_size
    pbar.update(block_size)
    if downloaded == total_size:
        pbar.finish()
        pbar = None
        downloaded = 0

TOMCAT_VERSION = "8.5.20"
CATALINA_HOME = "/usr/local/tomcat"

def check_tomcat_version():
    esg_functions.call_subprocess("/usr/local/tomcat/bin/version.sh")

def download_tomcat():
    if os.path.isdir("/usr/local/tomcat"):
        print "Tomcat directory found.  Skipping installation."
        check_tomcat_version()
        return False

    tomcat_download_url = "http://archive.apache.org/dist/tomcat/tomcat-8/v8.5.20/bin/apache-tomcat-8.5.20.tar.gz"
    print "downloading Tomcat"
    r = requests.get(tomcat_download_url)
    tomcat_download_path =  "/tmp/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(TOMCAT_VERSION=TOMCAT_VERSION)
    with open(tomcat_download_path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

    return True

def extract_tomcat_tarball(dest_dir="/usr/local"):
    with esg_bash2py.pushd(dest_dir):
        esg_functions.extract_tarball(
            "/tmp/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(TOMCAT_VERSION=TOMCAT_VERSION))

        # Create symlink
        create_symlink(TOMCAT_VERSION)
        try:
            os.remove(
                "/tmp/apache-tomcat-{TOMCAT_VERSION}.tar.gz".format(TOMCAT_VERSION=TOMCAT_VERSION))
        except OSError, error:
            print "error:", error
            pass


def create_symlink(TOMCAT_VERSION):
    esg_bash2py.symlink_force(
        "/usr/local/apache-tomcat-{TOMCAT_VERSION}".format(TOMCAT_VERSION=TOMCAT_VERSION), "/usr/local/tomcat")


# ENV CATALINA_HOME /usr/local/tomcat
#
def remove_example_webapps():
    '''remove Tomcat example applications'''
    with esg_bash2py.pushd("/usr/local/tomcat/webapps"):
        try:
            shutil.rmtree("docs")
            shutil.rmtree("examples")
            shutil.rmtree("host-manager")
            shutil.rmtree("manager")
        except OSError, error:
            if error.errno == errno.ENOENT:
                pass
            else:
                logger.exception()

def copy_config_files():
    '''copy custom configuration'''
    '''server.xml: includes references to keystore, truststore in /esg/config/tomcat'''
    '''context.xml: increases the Tomcat cache to avoid flood of warning messages'''

    print "*******************************"
    print "Copying custom Tomcat config files"
    print "******************************* \n"
    try:
        shutil.copyfile("tomcat_conf/server.xml", "/usr/local/tomcat/conf/server.xml")
        shutil.copyfile("tomcat_conf/context.xml", "/usr/local/tomcat/conf/context.xml")
        shutil.copyfile("certs/esg-truststore.ts", "/esg/config/tomcat/esg-truststore.ts")
        shutil.copyfile("certs/esg-truststore.ts-orig", "/esg/config/tomcat/esg-truststore.ts-orig")
        shutil.copyfile("certs/keystore-tomcat", "/esg/config/tomcat/keystore-tomcat")
        shutil.copyfile("certs/tomcat-users.xml", "/esg/config/tomcat/tomcat-users.xml")
        # shutil.copytree("certs", "/esg/config/tomcat")

        shutil.copy("tomcat_conf/setenv.sh", os.path.join(CATALINA_HOME, "bin"))
    except OSError, error:
        if error.errno == errno.EEXIST:
            pass
        else:
            logger.exception()

def create_tomcat_user():
    esg_functions.call_subprocess("groupadd tomcat")
    esg_functions.call_subprocess("useradd -s /sbin/nologin -g tomcat -d /usr/local/tomcat tomcat")
    tomcat_directory = "/usr/local/apache-tomcat-{TOMCAT_VERSION}".format(TOMCAT_VERSION=TOMCAT_VERSION)
    tomcat_user_id = pwd.getpwnam("tomcat").pw_uid
    tomcat_group_id = grp.getgrnam("tomcat").gr_gid
    esg_functions.change_permissions_recursive(tomcat_directory, tomcat_user_id, tomcat_group_id)

    os.chmod("/usr/local/tomcat/webapps", 0775)

def start_tomcat():
    return esg_functions.call_subprocess("/usr/local/tomcat/bin/catalina.sh run")

def stop_tomcat():
    esg_functions.stream_subprocess_output("/usr/local/tomcat/bin/catalina.sh stop")

def restart_tomcat():
    stop_tomcat()
    print "Sleeping for 7 seconds to allow shutdown"
    sleep(7)
    start_tomcat()

def check_tomcat_status():
    return esg_functions.call_subprocess("service httpd status")

def run_tomcat_config_test():
    esg_functions.stream_subprocess_output("/usr/local/tomcat/bin/catalina.sh configtest")



def create_certificate_chain_list():
    cert_files = []
    #Enter ca_chain file into list
    print "Please enter your Certificate Authority's certificate chain file(s)"
    print "[enter each cert file/url press return, press return with blank entry when done]"
    while True:
        certfile_entry = raw_input("Enter certificate chain file name: ")
        if not certfile_entry:
            break
        else:
            cert_files.append(certfile_entry)

    return cert_files


def create_certificate_chain(cert_files):
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


#arg 1 -> private key
#arg 2 -> public cert (the returned signed CSR)
#arg 3 -> keystore name
#arg 4 -> alias
#arg 5 -> password (The value you want *set* for the keystore and internal private key)
def install_tomcat_keypair(password, private_key=config["tomcat_conf_dir"]+"/hostkey.pem", public_cert=None, keystore_name=config["keystore_file"], keystore_alias=config["keystore_alias"]):
    '''If you want to install a commercial CA issued certificate:
    esg-node --install-keypair <certificate file> <key file>
    When prompted for the cachain file, specify the chain file provided by your CA'''

    #Exit if public_cert(signed CSR isn't found)
    if not public_cert:
        public_cert = os.path.join(config["tomcat_conf_dir"], esg_functions.get_esgf_host(), "-esg-node.pem")

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

    cert_files = create_certificate_chain_list()

    #Copy and rename private_key and cert
    shutil.copyfile(private_key, "/etc/certs/hostkey.pem")
    shutil.copyfile(public_cert, "/etc/certs/hostcert.pem")

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

#
#     #(In order for ORP or any other local service to trust eachother put your own cert into the truststore)
#     [ -e "${truststore_name}" ] && mv -v ${truststore_name}{,.bak}
#     rebuild_truststore ${truststore_name} && add_my_cert_to_truststore --keystore-pass ${store_password}
#     [ $? != 0 ] && echo "ERROR: Problem with truststore generation" && mv ${truststore_name}.bak ${truststore_name} && exit 6
#     #register ${esgf_idp_peer}
#
#     echo "Please restart this node for keys to take effect: \"$0 restart\""
#     echo
# }


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
#     debug_print "curl -s -L --insecure ${esg_dist_url_root}/certs/${esg_trusted_certs_file} | (cd ${globus_global_certs_dir}; pax -r -s ',.*/,,p')"
#     curl -s -L --insecure ${esg_dist_url_root}/certs/${esg_trusted_certs_file} | (cd ${globus_global_certs_dir}; pax -r -s ',.*/,,p')
#     local ret=$?
#     rmdir ${globus_global_certs_dir}/$(echo ${esg_trusted_certs_file} | awk 'gsub(/('$compress_extensions')/,"")')
#     if [ $ret == 0 ]; then
#         [ -e ${globus_global_certs_dir%/*}/${globus_global_certs_dir##*/}.bak.tgz ] && rm ${globus_global_certs_dir%/*}/${globus_global_certs_dir##*/}.bak.tgz
#     fi
#
#     local simpleCA_cert=$(readlink -f $(grep certificate_issuer_cert "${esg_root_dir}/config/myproxy/myproxy-server.config" 2> /dev/null | awk '{print $2}' | tr -d '\"') 2> /dev/null)
#     if [ -n "${simpleCA_cert}" ]; then
#         local simpleCA_cert_hash=$(openssl x509 -noout -in ${simpleCA_cert} -hash)
#         echo "checking for MY cert: ${globus_global_certs_dir}/${simpleCA_cert_hash}.0"
#         [ -e "${globus_global_certs_dir}/${simpleCA_cert_hash}.0" ] && ((!force_install)) && echo "Local CA cert file detected.... $([OK])" && return 0
#         echo "Integrating in local simpleCA_cert... "
#
#         debug_print "Local SimpleCA Root Cert: ${simpleCA_cert}"
#         debug_print "Extracting Signing policy command: tar xvzfO ${simpleCA_cert%/*}/globus_simple_ca_${simpleCA_cert_hash}_setup*.tar.gz globus_simple_ca_${simpleCA_cert_hash}_setup-*/${simpleCA_cert_hash}.signing_policy > ${globus_global_certs_dir}/${simpleCA_cert_hash}.signing_policy"
#
#         (cp -v ${simpleCA_cert} ${globus_global_certs_dir}/${simpleCA_cert_hash}.0 && \
#             tar xvzfO ${simpleCA_cert%/*}/globus_simple_ca_${simpleCA_cert_hash}_setup*.tar.gz globus_simple_ca_${simpleCA_cert_hash}_setup-*/${simpleCA_cert_hash}.signing_policy > ${globus_global_certs_dir}/${simpleCA_cert_hash}.signing_policy && \
#             [ -d ${tomcat_install_dir}/webapps/ROOT ] && openssl x509 -text -hash -in ${simpleCA_cert} > ${tomcat_install_dir}/webapps/ROOT/cacert.pem && \
#             echo " My CA Cert now posted @ http://$(hostname --fqdn)/cacert.pem "
#             chmod 644 ${tomcat_install_dir}/webapps/ROOT/cacert.pem && \
#                 [OK]) || [FAIL]
#         #zoiks
#         #write_as_property node_dn $(extract_openssl_dn ${simpleCA_cert}) && echo "property updated $([OK])"
#     fi
#
#     chmod 755 ${globus_global_certs_dir}
#     chmod 644 ${globus_global_certs_dir}/*
# }


def rebuild_truststore(truststore_file):
    pass
    '''Converts ESG certificates (that can be fetch by above function) into a truststore'''

    print "(Re)building truststore from esg certificates... [{truststore_file}]".format(truststore_file=truststore_file)

    is not os.path.isdir(config["globus_global_certs_dir"]):
        print "Sorry, No esg certificates found... in {globus_global_certs_dir}".format(globus_global_certs_dir=globus_global_certs_dir)
        print "Fetching fresh esg certificates"
        fetch_esgf_certificates()

    #
    #     #If you don't already have a truststore to build on....
    #     #Start building from a solid foundation i.e. Java's set of ca certs...
    #     [ ! -e ${truststore_file_} ] && cp -v ${java_install_dir}/jre/lib/security/cacerts ${truststore_file_}
    #
    #     local tmp_dir=/tmp/esg_scratch
    #     mkdir -p ${tmp_dir}
    #
    #     local cert_files=$(find ${globus_global_certs_dir} | egrep '^.*\.0$')
    #     for cert_file in $cert_files; do
    #         _insert_cert_into_truststore ${cert_file} ${truststore_file_}
    #     done
    #     rmdir ${tmp_dir}
    #
    #     #make sure that MY cert is in the trustore (it should be).
    #     #As a side effect there is sync'ing the truststore with what is in the JVM
    #     (( force_install )) && add_my_cert_to_truststore
    #
    #     sync_with_java_truststore ${truststore_file_}
    #
    #     chown ${tomcat_user}:${tomcat_group} ${truststore_file_}
    #     echo "...done"
    #     return 0
    # }


def generate_tomcat_keystore(keystore_name, keystore_alias, keystore_password, private_key, public_cert, intermediate_certs):
    '''The following helper function creates a new keystore for your tomcat installation'''
    # arg 1 -> keystore name
    # arg 2 -> keystore alias
    # arg 3 -> keystore password
    # arg 4 -> private key
    # arg 5 -> public cert
    # arg 6.. -> intermediate certificate(s)
    # make_fresh_keystore() {
    #     debug_print " make_fresh_keystore() [$@]"
    #     #-------------
    #     #Set default values such that env vars may be used
    #     #-------------
    #     local keystore_name
    #     local keystore_alias
    #     local store_password
    #     local private_key
    #
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

    #TODO:Probably need to clear out cert_bundle_file on each run

    #TODO:Break into separate function
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

    num_of_certs = len(intermediate_certs)
    for index, cert in enumerate(intermediate_certs):
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

        print "checking that key pair is congruent... "
        if check_associate_cert_with_private_key(public_cert, private_key):
            print "The keypair was congruent"
        else:
            print "The keypair was not congruent"
            esg_functions.exit_with_error(1)


        print "creating keystore... "
        #create a keystore with a self-signed cert
        distinguished_name = "CN={esgf_host}".format(esgf_host=esg_functions.get_esgf_host())
        if os.path.isfile(keystore_name):
            shutil.move(keystore_name, os.path.join(keystore_name,".bak"))

        #-------------
        #Make empty keystore...
        #-------------
        java_keytool_executable = "{java_install_dir}/bin/keytool"
        generate_keystore_string = "{java_keytool_executable} -genkey -keyalg RSA -alias {keystore_alias} -keystore {keystore_name} -storepass {keystore_password} -keypass {keystore_password} -validity 360 -dname {distinguished_name} -noprompt".format(java_keytool_executable=java_keytool_executable, keystore_alias=keystore_alias, keystore_name=keystore_name, keystore_password=keystore_password, distinguished_name=distinguished_name)
        keystore_output = esg_functions.call_subprocess(generate_keystore_string)
        if keystore_output["returncode"] !=0:
            print "Problem with generating initial keystore...Exiting."
            esg_functions.exit_with_error(1)


        #-------------
        #Convert your private key into from PEM to DER format that java likes
        #-------------
        print "converting private key... "
        derkey = os.path.join(install_dir,"key.der")
        convert_to_der = esg_functions.call_subprocess("openssl pkcs8 -topk8 -nocrypt -inform PEM -in {private_key} -outform DER -out {derkey}".format(private_key=private_key, derkey=derkey))
        if convert_to_der["returncode"] !=0:
            print "Problem with preparing initial keystore...Exiting."
            esg_functions.exit_with_error(1)



        #-------------
        #Now we gather up all the other keys in the key chain...
        #-------------
        print "checking that chain is valid... "
        if os.path.isfile(ca_chain_bundle):
            valid_chain = esg_functions.call_subprocess("openssl verify -CAfile {ca_chain_bundle} {ca_chain_bundle}".format(ca_chain_bundle=ca_chain_bundle))
            if "error" in valid_chain['stdout'] or "error" in valid_chain['stderr']:
                print "The chain is not valid.  (hint: did you include the root cert for the chain?)"
        else:
            print "Hmmm... no chain provided [${ca_chain_bundle}], skipping this check..."


        print "Constructing new keystore content... "
        command = "{extkeytool} -importkey -keystore {keystore_name} -alias {keystore_alias} -storepass {keystore_password} -keypass {keystore_password} -keyfile {derkey} -certfile {certbundle} -provider {provider}".format(extkeytool=extkeytool_executable, keystore_name=keystore_name, keystore_alias=keystore_alias, keystore_password=keystore_password, derkey=derkey, cert_bundle=cert_bundle, provider=provider)
        construct_keystore_output = esg_functions.call_subprocess(command)
        #FYI: Code 127 is "command not found"
        if construct_keystore_output["returncode"] == 127:
            print "Hmmm... Cannot find extkeytool... :-( Let me get it for you! :-)  [one moment please...]"
            install_extkeytool()
            print "Retrying to build keystore with extkeytool"
            esg_functions.stream_subprocess_output(command)

        #Check keystore output
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

    def install_extkeytool():
        extkeytool_tarfile = esg_bash2py.trim_string_from_head(config["extkeytool_download_url"])
        esg_functions.download_update(extkeytool_tarfile, config["extkeytool_download_url"])
        esg_functions.extract_tarball(extkeytool_tarfile, "/esg/tools")
    def check_associate_cert_with_private_key(cert, private_key):
        """
        :type cert: str
        :type private_key: str
        :rtype: bool
        """
        try:
            private_key_obj = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, private_key)
        except OpenSSL.crypto.Error:
            raise Exception('private key is not correct: %s' % private_key)

        try:
            cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        except OpenSSL.crypto.Error:
            raise Exception('certificate is not correct: %s' % cert)

        context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
        context.use_privatekey(private_key_obj)
        context.use_certificate(cert_obj)
        try:
            context.check_privatekey()
            return True
        except OpenSSL.SSL.Error:
            return False
# # startup
# COPY conf/supervisord.tomcat.conf /etc/supervisor/conf.d/supervisord.tomcat.conf
# CMD ["supervisord", "--nodaemon", "-c", "/etc/supervisord.conf"]
def main():
    print "*******************************"
    print "Setting up Tomcat {TOMCAT_VERSION}".format(TOMCAT_VERSION=TOMCAT_VERSION)
    print "******************************* \n"
    if download_tomcat():
        extract_tomcat_tarball()
        remove_example_webapps()
        copy_config_files()
        create_tomcat_user()
    # pass
if __name__ == '__main__':
    main()
