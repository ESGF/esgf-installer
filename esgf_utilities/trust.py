import ConfigParser
import logging
import os
import random
import shutil

import jks
import OpenSSL.crypto as crypto
import yaml

import esg_functions
import esg_property_manager
from .pybash import mkdir_p, touch

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def install_keypair(key_file=None, cert_file=None):

    # Generate self-signed or use existing
    if key_file is None and cert_file is None:
        key_file, cert_file, ca_key, ca_chain_file = self_signed()
        ca_cert = ca_chain_file
    else:
        ca_chain_file = build_cachain()
        ca_key, ca_cert = None, None

    tomcat(key_file, cert_file, ca_chain_file, ca_cert)
    httpd(key_file, cert_file, ca_chain_file, ca_cert)
    globus(key_file, cert_file, ca_chain_file, ca_cert, ca_key)

def tomcat(key_file, cert_file, ca_chain_file, ca_cert_file=None):

    # Dump to string encoded in DER aka ASN1 for JavaKeystore (JKS)
    dumped_key = _dump_der_key(key_file)
    dumped_cert = _dump_der_cert(cert_file)
    dumped_ca_chain = _dump_der_cert(ca_chain_file)

    # Generate entry and KeyStore
    alias = config["keystore_alias"]
    pke = jks.PrivateKeyEntry.new(alias, [dumped_cert, dumped_ca_chain], dumped_key, 'rsa_raw')
    keystore = jks.KeyStore.new('jks', [pke])
    # File, password
    keystore_dir = os.path.dirname(config["keystore_file"])
    mkdir_p(keystore_dir)
    keystore.save(config["keystore_file"], esg_functions.get_java_keystore_password())

    # Retrieve truststore from remote
    truststore_file_name = os.path.basename(config["truststore_file"])
    truststore_dir = os.path.dirname(config["truststore_file"])
    mkdir_p(truststore_dir)
    remote_truststore = "{}/certs/{}".format(
        esg_property_manager.get_property("esgf.root.url"),
        truststore_file_name
    )
    esg_functions.download_update(config["truststore_file"], remote_truststore)

    # Add self-signed CA, otherwise it is assumed the CA is already trusted.
    if ca_cert_file is not None:
        dumped_ca_cert = _dump_der_cert(ca_cert_file)
        truststore = jks.KeyStore.load(config["truststore_file"], "changeit")
        entries = [truststore.entries[ts_alias] for ts_alias in truststore.entries]
        new_entry = jks.TrustedCertEntry.new(alias, dumped_ca_cert)
        entries += [new_entry]
        new_truststore = jks.KeyStore.new('jks', entries)
        new_truststore.save(config["truststore_file"], "changeit")


def httpd(key_file, cert_file, ca_chain_file, ca_cert_file=None):

    # Place the certs will be looked for by httpd
    cert_dir = os.path.join(os.sep, "etc", "certs")
    mkdir_p(cert_dir)
    key_location = os.path.join(cert_dir, "hostkey.pem")
    shutil.copy(key_file, key_location)
    cert_location = os.path.join(cert_dir, "hostcert.pem")
    shutil.copy(cert_file, cert_location)
    ca_chain_location = os.path.join(cert_dir, "cachain.pem")
    shutil.copy(ca_chain_file, ca_chain_location)

    # Retrieve bundle from remote
    ca_bundle_file_name = "esgf-ca-bundle.crt"
    remote_ca_bundle = "{}/certs/{}".format(
        esg_property_manager.get_property("esgf.root.url"),
        ca_bundle_file_name
    )
    ca_bundle_file = os.path.join(cert_dir, ca_bundle_file_name)
    esg_functions.download_update(ca_bundle_file, remote_ca_bundle)

    # Add self-signed CA, otherwise it is assumed the CA is already trusted.
    if ca_cert_file is not None:
        with open(ca_bundle_file, "a") as ca_bundle:
            with open(ca_cert_file, "r") as new_trusted_ca:
                ca_bundle.write(new_trusted_ca.read())


def globus(key_file, cert_file, ca_chain_file, ca_cert_file=None, ca_key_file=None):

    # Retrieve trusted certificates
    trustcerts_file_name = "esg_trusted_certificates.tar"
    remote_file = "{}/certs/{}".format(
        esg_property_manager.get_property("esgf.root.url"),
        trustcerts_file_name
    )
    globus_cert_dir = os.path.join(os.sep, "etc", "grid-security", "certificates")
    mkdir_p(globus_cert_dir)
    trustcerts_file = os.path.join(globus_cert_dir, trustcerts_file_name)
    esg_functions.download_update(trustcerts_file, remote_file)

    # Extract trusted certificates
    esg_functions.extract_tarball(trustcerts_file, globus_cert_dir)
    extracted_certs_dir = os.path.join(globus_cert_dir, "esg_trusted_certificates")
    cert_files = os.listdir(extracted_certs_dir)
    for file_name in cert_files:
        full_file_name = os.path.join(extracted_certs_dir, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, globus_cert_dir)

    # Copy key pair into place for globus
    grid_sec_dir = os.path.join(os.sep, "etc", "grid-security")
    key_dest = os.path.join(grid_sec_dir, "hostkey.pem")
    shutil.copy(key_file, key_dest)
    cert_dest = os.path.join(grid_sec_dir, "hostcert.pem")
    shutil.copy(cert_file, cert_dest)

    # Use Temp CA to issue/sign myproxy certificates
    if ca_key_file is not None:
        myproxy_ca_dir = os.path.join(os.sep, "var", "lib", "globus-connect-server", "myproxy-ca")
        myproxy_private = os.path.join(myproxy_ca_dir, "private")
        mkdir_p(myproxy_private)
        ca_key_dest = os.path.join(myproxy_private, "cakey.pem")
        shutil.copy(ca_key_file, ca_key_dest)
        ca_cert_dest = os.path.join(myproxy_ca_dir, "cacert.pem")
        shutil.copy(ca_cert_file, ca_cert_dest)



def self_signed():
    # Make a CA
    ca_key = crypto.PKey()
    ca_key.generate_key(crypto.TYPE_RSA, 4096)

    ca_cert = crypto.X509()
    ca_cert.set_version(2)
    ca_cert.set_serial_number(0)

    ca_subj = ca_cert.get_subject()
    ca_subj.O = "ESGF"
    ca_subj.OU = "ESGF.ORG"
    ca_subj.CN = esg_functions.get_esgf_host()+"-CA"

    # Extensions?

    ca_cert.set_issuer(ca_subj)
    ca_cert.set_pubkey(ca_key)

    ca_cert.gmtime_adj_notBefore(0)
    ca_cert.gmtime_adj_notAfter(10*365*24*60*60)

    ca_cert.sign(ca_key, 'sha256')

    # Write to file
    self_signed_dir = os.path.join(os.sep, "etc", "tempcerts")
    mkdir_p(self_signed_dir)
    ca_cert_file = os.path.join(self_signed_dir, "cacert.pem")
    with open(ca_cert_file, "w") as ca_cert_filep:
        ca_cert_filep.write(
            crypto.dump_certificate(crypto.FILETYPE_PEM, ca_cert)
        )

    ca_key_file = os.path.join(self_signed_dir, "cakey.pem")
    with open(ca_key_file, "w") as ca_key_filep:
        ca_key_filep.write(
            crypto.dump_privatekey(crypto.FILETYPE_PEM, ca_key)
        )

    # Begin "client" cert

    client_key = crypto.PKey()
    client_key.generate_key(crypto.TYPE_RSA, 4096)

    client_cert = crypto.X509()
    client_cert.set_version(2)
    client_cert.set_serial_number(random.randint(1, pow(2, 30)))

    client_subj = client_cert.get_subject()
    client_subj.O = "ESGF"
    client_subj.OU = "ESGF.ORG"
    client_subj.CN = esg_functions.get_esgf_host()

    # Extensions?

    client_cert.set_issuer(ca_subj)
    client_cert.set_pubkey(client_key)

    client_cert.gmtime_adj_notBefore(0)
    client_cert.gmtime_adj_notAfter(10*365*24*60*60)

    client_cert.sign(ca_key, 'sha256')

    client_cert_file = os.path.join(self_signed_dir, "hostcert.pem")
    with open(client_cert_file, "w") as client_cert_filep:
        client_cert_filep.write(
            crypto.dump_certificate(crypto.FILETYPE_PEM, client_cert)
        )

    client_key_file = os.path.join(self_signed_dir, "hostkey.pem")
    with open(client_key_file, "w") as client_key_filep:
        client_key_filep.write(
            crypto.dump_privatekey(crypto.FILETYPE_PEM, client_key)
        )
    return client_key_file, client_cert_file, ca_key_file, ca_cert_file

def build_cachain():
    default_cachain = "/etc/esgfcerts/cachain.pem"

    try:
        cert_files = esg_property_manager.get_property("cachain.path")
    except ConfigParser.NoOptionError:
        print "Please enter your Certificate Authority's certificate chain file(s).  If there are multiple files, enter them separated by commas."
        cert_files = raw_input("Enter certificate chain file name: ")

    if cert_files:
        cert_files_list = [cert_path.strip() for cert_path in cert_files.split(",")]
        for filename in cert_files_list:
            if not os.path.isfile(filename.strip()):
                raise OSError
    else:
        print "Adding default certificate chain file {}".format(default_cachain)
        if not os.path.isfile(default_cachain):
            print "{} does not exist".format(default_cachain)
            print "Creating {}".format(default_cachain)
            mkdir_p("/etc/esgfcerts")
            touch(default_cachain)
        cert_files_list = [default_cachain]
    #Copy the tmpchain and rename to cachain
    tmp_cachain = os.path.join(os.sep, "etc", "certs", "tmpchain")
    with open(tmp_cachain, "w") as tmpchain_file:
        for cert in cert_files:
            if not os.path.isfile(cert):
                raise OSError("{} not found. Exiting.".format(cert))
            with open(cert, "r") as cert_file_handle:
                cert_file_contents = cert_file_handle.read()
            tmpchain_file.write(cert_file_contents+"\n")
    return tmp_cachain

def _dump_der_key(key_file):
    with open(key_file, "r") as key_filep:
        key_contents = key_filep.read()
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_contents)
    return crypto.dump_privatekey(crypto.FILETYPE_ASN1, key)

def _dump_der_cert(cert_file):
    with open(cert_file, "r") as cert_filep:
        cert_contents = cert_filep.read()
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_contents)
    return crypto.dump_certificate(crypto.FILETYPE_ASN1, cert)
