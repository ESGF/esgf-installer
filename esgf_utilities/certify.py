import ConfigParser
import logging
import os
import random
import shutil

import jks
import OpenSSL.crypto as crypto
import yaml

from .esg_functions import get_esgf_host
import esg_property_manager
from .pybash import mkdir_p, touch

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def install_keypair(key_file=None, cert_file=None):

    if key_file is None and cert_file is None:
        key_file, cert_file, ca_chain_file = self_signed()
    else:
        ca_chain_file = build_cachain()

    cert_dir = os.path.join(os.sep, "etc", "certs")
    key_location = os.path.join(cert_dir, "hostkey.pem")
    shutil.copy(key_file, key_location)
    cert_location = os.path.join(cert_dir, "hostcert.pem")
    shutil.copy(cert_file, cert_location)

    with open(key_file, "r") as key_filep:
        key_contents = key_filep.read()
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_contents)

    with open(cert_file, "r") as cert_filep:
        cert_contents = cert_filep.read()
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_contents)

    with open(ca_chain_file, "r") as ca_chain_filep:
        ca_chain_contents = ca_chain_filep.read()
        ca_chain = crypto.load_certificate(crypto.FILETYPE_PEM, ca_chain_contents)
    # Dump to string encoded in DER aka ASN1
    dumped_key = crypto.dump_privatekey(crypto.FILETYPE_ASN1, key)
    dumped_cert = crypto.dump_certificate(crypto.FILETYPE_ASN1, cert)
    dumped_ca_chain = crypto.dump_certificate(crypto.FILETYPE_ASN1, ca_chain)

    alias = config["keystore_alias"]
    pke = jks.PrivateKeyEntry.new(alias, [dumped_cert, dumped_ca_chain], dumped_key, "rsa_raw")
    keystore = jks.KeyStore.new('jks', [pke])
    keystore.save("samplekeystore.jks", "test")

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
    ca_subj.CN = get_esgf_host()+"-CA"

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
    client_key.generate_key(crypto.TYPE_RSA, 2048)

    client_cert = crypto.X509()
    client_cert.set_version(2)
    client_cert.set_serial_number(random.randint(1, pow(2, 30)))

    client_subj = client_cert.get_subject()
    client_subj.O = "ESGF"
    client_subj.OU = "ESGF.ORG"
    client_subj.CN = get_esgf_host()

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
    return client_key_file, client_cert_file, ca_cert_file

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
    with open("/etc/certs/tmpchain", "w") as tmpchain_file:
        for cert in cert_files:
            if not os.path.isfile(cert):
                raise OSError("{} not found. Exiting.".format(cert))

            with open(cert, "r") as cert_file_handle:
                cert_file_contents = cert_file_handle.read()
            tmpchain_file.write(cert_file_contents+"\n")
    ca_chain_file = "/etc/certs/cachain.pem"
    shutil.copyfile("/etc/certs/tmpchain", ca_chain_file)
    return ca_chain_file
