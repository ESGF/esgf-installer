import ConfigParser
import logging
import os
import random
import shutil
import tarfile

import jks
import OpenSSL.crypto as crypto
import yaml

import esg_functions
import esg_property_manager
from .pybash import mkdir_p, touch

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


def globus_services(identity=None, ca=None):
    '''
    If a host identity (ESGF signed key-cert pair) and a CA (another ESGF signed key-cert pair) are
    provided, use those. Otherwise, generate a temporary identity and CA. Additionally, if signed
    certs are not provided, generate two private keys, a certifcate signing request (CSR) for
    each and a so called 'globus pack' for the generated temporary CA.
    '''

    gen_temp = identity is None and ca is None
    if gen_temp:
        key, cert, ca_key, ca_cert = self_signed()
        # CA certifcate signing request
        generate_csr(
            "globus_ca_key.pem",
            "globus_ca_csr.pem",
            O="ESGF",
            OU="ESGF.ORG",
            CN=esg_functions.get_esgf_host()+"-CA"
        )
        # Identity certificate signing request
        generate_csr(
            "globus_id_key.pem",
            "globus_id_csr.pem",
            O="ESGF",
            OU="ESGF.ORG",
            CN=esg_functions.get_esgf_host()
        )
        globus_pack = generate_globus_pack(ca_cert)
    else:
        key, cert = identity
        ca_key, ca_cert, globus_pack = ca

    # Install trusted certs into the globus certs directory
    globus_trusted_certs()

    # Copy identity key and cert as well as CA key and cert into place for globus
    globus_local_certs(key, cert, ca_key, ca_cert, globus_pack)

def web_services(key=None, cert=None):
    '''
    If a key and certificate is provided it is assumed to be signed by a known CA. Otherwise, a
    temporary, self-signed, CA is generated and used to sign a certificate. If a key and certificate
    is provided a CA chain will be generated, first referencing the 'cachain.path' property, if this
    is not populated it will then prompt the user for a comma seperated list of CA certificate
    files. These files will be placed into places that httpd and tomcat will look for them.
    '''
    # Generate self-signed or use existing
    if key is None and cert is None:
        key, cert, _, ca_chain = self_signed()
        ca_cert = ca_chain
    else:
        ca_chain = build_cachain()
        ca_cert = None

    tomcat(key, cert, ca_chain, ca_cert)
    httpd(key, cert, ca_chain, ca_cert)

def globus_local_certs(key, cert, ca_key, ca_cert, globus_pack):

    # Copy identity key and cert into place for globus
    grid_sec_dir = os.path.join(os.sep, "etc", "grid-security")
    key_dest = os.path.join(grid_sec_dir, "hostkey.pem")
    shutil.copy(key, key_dest)
    cert_dest = os.path.join(grid_sec_dir, "hostcert.pem")
    shutil.copy(cert, cert_dest)

    # Copy CA key and cert into required places
    myproxy_ca_dir = os.path.join(os.sep, "var", "lib", "globus-connect-server", "myproxy-ca")
    myproxy_private = os.path.join(myproxy_ca_dir, "private")
    mkdir_p(myproxy_private)
    ca_key_dest = os.path.join(myproxy_private, "cakey.pem")
    shutil.copy(ca_key, ca_key_dest)
    ca_cert_dest = os.path.join(myproxy_ca_dir, "cacert.pem")
    shutil.copy(ca_cert, ca_cert_dest)

    # Extract "globus pack" and copy contents into the globus certificate directory
    globus_cert_dir = os.path.join(os.sep, "etc", "grid-security", "certificates")
    globus_pack_name = os.path.basename(globus_pack).split(".tar")[0]
    extracted_location = os.path.join(os.sep, "tmp", globus_pack_name)
    shutil.rmtree(extracted_location)
    with tarfile.open(globus_pack, "r") as globus_pack_tar:
        globus_pack_tar.extractall(os.path.join(os.sep, "tmp"))
    for entry in os.listdir(extracted_location):
        if os.path.isfile(entry):
            full_file_name = os.path.join(extracted_location, entry)
            dest = os.path.join(globus_cert_dir, entry)
            shutil.copy(full_file_name, dest)


def globus_trusted_certs():
    # Retrieve trusted certificates
    trustcerts_file_name = "esg_trusted_certificates.tar"
    remote_file = "{}/certs/{}".format(
        esg_property_manager.get_property("esg.root.url"),
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
        esg_property_manager.get_property("esg.root.url"),
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
        esg_property_manager.get_property("esg.root.url"),
        ca_bundle_file_name
    )
    ca_bundle_file = os.path.join(cert_dir, ca_bundle_file_name)
    esg_functions.download_update(ca_bundle_file, remote_ca_bundle)

    # Add self-signed CA, otherwise it is assumed the CA is already trusted.
    if ca_cert_file is not None:
        with open(ca_bundle_file, "a") as ca_bundle:
            with open(ca_cert_file, "r") as new_trusted_ca:
                ca_bundle.write(new_trusted_ca.read())

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
    ca_cert.gmtime_adj_notAfter(30*24*60*60)

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
    client_cert.gmtime_adj_notAfter(30*24*60*60)

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
    ''' Append intermediate certs until the root cert is reached, intermediates first '''
    try:
        cert_files = esg_property_manager.get_property("cachain.path")
    except ConfigParser.NoOptionError:
        print "Please enter your Certificate Authority's certificate chain file(s).  If there are multiple files, enter them separated by commas."
        cert_files = raw_input("Enter certificate file names: ")

    cert_files_list = [cert_path.strip() for cert_path in cert_files.split(",")]
    for filename in cert_files_list:
        if not os.path.isfile(filename.strip()):
            raise OSError

    #Copy the tmpchain and rename to cachain
    tmp_cachain = os.path.join(os.sep, "etc", "certs", "tmpchain")
    with open(tmp_cachain, "w") as tmpchain_file:
        for cert in cert_files_list:
            with open(cert.strip(), "r") as cert_file_handle:
                cert_file_contents = cert_file_handle.read()
            tmpchain_file.write(cert_file_contents+"\n")

    return tmp_cachain

def generate_csr(keyout, csrout, **name):
    '''modified from: https://github.com/pyca/pyopenssl/blob/master/examples/certgen.py'''
    """
    Create a certificate request.
    Argument:  **name - The name of the subject of the request, possible
                        arguments are:
                          C     - Country name
                          ST    - State or province name
                          L     - Locality name
                          O     - Organization name
                          OU    - Organizational unit name
                          CN    - Common name
                          emailAddress - E-mail address
    """
    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 4096)

    req = crypto.X509Req()
    subj = req.get_subject()

    setattr(subj, "O", name["O"])
    setattr(subj, "OU", name["OU"])
    setattr(subj, "CN", name["CN"])

    req.set_pubkey(pkey)
    req.sign(pkey, "sha256")
    with open(keyout, "w") as keyout_file:
        keyout_file.write(
            crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)
        )
    with open(csrout, "w") as keyout_file:
        keyout_file.write(
            crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
        )

def generate_globus_pack(cert_file):

    # Load certificate object
    with open(cert_file, "r") as cert_filep:
        cert_obj = crypto.load_certificate(crypto.FILETYPE_PEM, cert_filep.read())

    # Get unique hash of the subject name
    local_hash = esg_functions.convert_hash_to_hex(cert_obj.subject_name_hash())

    # Make the directory to store the needed files for a "globus pack"
    globus_pack = "globus_simple_ca_{}_setup-0".format(local_hash)
    globus_pack = os.path.join(os.sep, "etc", "tempcerts", globus_pack)
    mkdir_p(globus_pack)

    # Copy the required signing policy into place
    signing_policy_tmpl = os.path.join(os.path.dirname(__file__), "signing-policy.template")
    shutil.copyfile(cert_file, os.path.join(globus_pack, local_hash+".0"))
    signing_policy = os.path.join(globus_pack, local_hash+".signing_policy")
    shutil.copyfile(signing_policy_tmpl, signing_policy)

    # Populate the signing policy template
    cert_subject_object = cert_obj.get_subject()
    cert_subject = "/O={O}/OU={OU}/CN={CN}".format(
        O=cert_subject_object.O,
        OU=cert_subject_object.OU,
        CN=cert_subject_object.CN
    )
    esg_functions.replace_string_in_file(
        signing_policy,
        '/O=ESGF/OU=ESGF.ORG/CN=placeholder',
        cert_subject
    )

    # This was here, but I am unsure of its purpose
    shutil.copyfile(signing_policy, os.path.join(os.sep, "etc", "tempcerts", "signing-policy"))

    # tar -cvzf globus_simple_ca_${localhash}_setup-0.tar.gz $tgtdir;
    globus_pack_tar = globus_pack+".tar.gz"
    with tarfile.open(globus_pack_tar, "w:gz") as tar:
        tar.add(globus_pack)

    return globus_pack_tar

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
