'''
Certificate Management Functions
'''
import os
import shutil
import logging
import tarfile
import datetime
import random
import re
import ConfigParser
import yaml
import OpenSSL
import pybash
import esg_functions
import esg_property_manager
import esg_keystore_manager
from plumbum.commands import ProcessExecutionError

logger = logging.getLogger("esgf_logger" + "." + __name__)
current_directory = os.path.join(os.path.dirname(__file__))

NO_LIST = ["n", "no", "N", "No", "NO"]
YES_LIST = ["y", "yes", "Y", "Yes", "YES"]


with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

# ----------------------------------------------
#   Certificate Creation functions (pyopenssl)
# ---------------------------------------------


def create_key_pair(key_type, bits):
    '''source: https://github.com/pyca/pyopenssl/blob/master/examples/certgen.py'''
    """
    Create a public/private key pair.
    Arguments: key_type - Key type, must be one of TYPE_RSA and TYPE_DSA
               bits - Number of bits to use in the key
    Returns:   The public/private key pair in a PKey object
    """
    pkey = OpenSSL.crypto.PKey()
    pkey.generate_key(key_type, bits)
    return pkey


def create_cert_request(pkey, digest="sha256", **name):
    '''source: https://github.com/pyca/pyopenssl/blob/master/examples/certgen.py'''
    """
    Create a certificate request.
    Arguments: pkey   - The key to associate with the request
               digest - Digestion method to use for signing, default is sha256
               **name - The name of the subject of the request, possible
                        arguments are:
                          C     - Country name
                          ST    - State or province name
                          L     - Locality name
                          O     - Organization name
                          OU    - Organizational unit name
                          CN    - Common name
                          emailAddress - E-mail address
    Returns:   The certificate request in an X509Req object
    """
    req = OpenSSL.crypto.X509Req()
    subj = req.get_subject()

    setattr(subj, "O", name["O"])
    setattr(subj, "OU", name["OU"])
    setattr(subj, "CN", name["CN"])

    req.set_pubkey(pkey)
    req.sign(pkey, digest)
    return req


def create_certificate(req, issuer_cert_key, serial, validity_period,
                       digest="sha256"):
    """
    Generate a certificate given a certificate request.
    Arguments: req        - Certificate request to use
               issuer_cert - The certificate of the issuer
               issuer_key  - The private key of the issuer
               serial     - Serial number for the certificate
               not_before  - Timestamp (relative to now) when the certificate
                            starts being valid
               not_after   - Timestamp (relative to now) when the certificate
                            stops being valid
               digest     - Digest method to use for signing, default is sha256
    Returns:   The signed certificate in an X509 object
    """
    issuer_cert, issuer_key = issuer_cert_key
    not_before, not_after = validity_period
    cert = OpenSSL.crypto.X509()
    cert.set_serial_number(serial)
    cert.gmtime_adj_notBefore(not_before)
    cert.gmtime_adj_notAfter(not_after)
    cert.set_issuer(issuer_cert.get_subject())
    cert.set_subject(req.get_subject())
    cert.set_pubkey(req.get_pubkey())
    cert.sign(issuer_key, digest)
    return cert


# ------------------------------------
#   Certificate functions
# ------------------------------------

def set_commercial_ca_paths():
    '''Set locations of the commercial CA key and cert'''
    try:
        commercial_key_path = esg_property_manager.get_property("commercial.key.path")
    except ConfigParser.NoOptionError:
        commercial_key_path = raw_input("Enter the file path of the commercial key: ")

    try:
        commercial_cert_path = esg_property_manager.get_property("commercial.cert.path")
    except ConfigParser.NoOptionError:
        commercial_cert_path = raw_input("Enter the file path of the commercial cert: ")

    try:
        ca_chain_path = esg_property_manager.get_property("cachain.path")
    except ConfigParser.NoOptionError:
        ca_chain_path = raw_input("Enter the file path of the ca chain: ")

    return (commercial_key_path, commercial_cert_path, ca_chain_path)


# ------------------------------------
#   Install Cert functions
# ------------------------------------
def check_for_commercial_ca():
    '''Checks if Commerical CA directory has been created; asks user if they would like proceed with
    Commercial CA installation if directory is found'''

    print "*******************************"
    print "Checking for Commercial CA"
    print "******************************* \n"

    try:
        commercial_ca_setup = esg_property_manager.get_property("install.signed.certs")
    except ConfigParser.NoOptionError:
        commercial_ca_setup = raw_input(
            "Do you have a commercial CA that you want to install [Y/n]: ") or "yes"

    if commercial_ca_setup in YES_LIST:
        commercial_key_path, commercial_cert_path, ca_chain_path = set_commercial_ca_paths()

        # Backup existing certs
        backup_existing_certs()
        esg_keystore_manager.install_keypair(commercial_key_path, commercial_cert_path)

        print "Local installation of certs complete."


def install_local_certs(node_type_list, firstrun=None):
    '''Installs local certs to /var/lib/globus-connect-server/myproxy-ca and /etc/grid-security'''
    if firstrun:
        file_list = ("cakey.pem", "cacert.pem", "hostcert.pem",
                     "hostkey.pem", "myproxy-server.config")
        certdir = "/etc/tempcerts"
    else:
        if "IDP" in node_type_list:
            file_list = ("cakey.pem", "cacert.pem", "hostcert.pem", "hostkey.pem")
        else:
            file_list = ("hostcert.pem", "hostkey.pem")

        certdir = "/etc/esgfcerts"

    with pybash.pushd(certdir):
        for file_name in file_list:
            if not os.path.exists(file_name):
                raise OSError(
                    "File {} is not found in {}; Please place it there and reexecute esg_node.py --install-local-certs".format(file_name, certdir))

        if "IDP" in node_type_list:
            try:
                cert_obj = OpenSSL.crypto.load_certificate(
                    OpenSSL.crypto.FILETYPE_PEM, open("cacert.pem").read())
            except OpenSSL.crypto.Error:
                logger.exception("Certificate is not correct.")

            local_hash = esg_functions.convert_hash_to_hex(cert_obj.subject_name_hash())
            globus_pack = "globus_simple_ca_{}_setup-0.tar.gz".format(local_hash)
            if not os.path.exists(globus_pack):
                raise OSError(
                    "File {} is not found in {}; Please place it there and reexecute esg_node.py --install-local-certs".format(globus_pack, certdir))

        if "IDP" in node_type_list:
            shutil.copyfile("cacert.pem", "/var/lib/globus-connect-server/myproxy-ca/cacert.pem")
            shutil.copyfile(
                "cakey.pem", "/var/lib/globus-connect-server/myproxy-ca/private/cakey.pem")
            shutil.copyfile(
                globus_pack, "/var/lib/globus-connect-server/myproxy-ca/{}".format(globus_pack))
            shutil.copyfile(globus_pack, "/etc/grid-security/certificates/{}".format(globus_pack))

        if os.path.exists("hostkey.pem"):
            shutil.copyfile("hostkey.pem", "/etc/grid-security/hostkey.pem")
            os.chmod("/etc/grid-security/hostkey.pem", 0600)
        if os.path.exists("hostcert.pem"):
            shutil.copyfile("hostcert.pem", "/etc/grid-security/hostcert.pem")

        print "Local installation of certs complete."


# ----------------------------------------------
#   CSR functions
# ---------------------------------------------

def generate_ssl_key_and_csr(private_key="/usr/local/tomcat/hostkey.pem", public_cert_req=None):
    '''Create a SSL keypair and CSR'''
    print "Generating private host key... "
    key_pair = create_key_pair(OpenSSL.crypto.TYPE_RSA, 1024)
    with open(private_key, "wt") as key_file_handle:
        key_file_handle.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key_pair))

    os.chmod(private_key, 0400)

    print "Generating Certificate Signing Request (csr)... "
    if not public_cert_req:
        public_cert_req = "/usr/local/tomcat/{}-esg-node.csr".format(esg_functions.get_esgf_host())

    public_cert_dn = extract_keystore_dn()
    if public_cert_dn:
        careq = create_cert_request(private_key, public_cert_dn)
    else:
        careq = create_cert_request(private_key, O="ESGF", OU="ESGF.ORG",
                                    CN=esg_functions.get_esgf_host())

    print "Generating 30 day temporary self-signed certificate... "

    newcert = create_certificate(careq, (careq, private_key), random.randint(1, pow(2,30)), (0, 30*60*24*365*5))

    with open('/usr/local/tomcat/{}-esg-node.pem'.format(esg_functions.get_esgf_host()), 'w') as ca_file:
        ca_file.write(
            OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, newcert).decode('utf-8')
        )

        print "--------------------------------------------------------"
        print "In Directory: /usr/local/tomcat"
        print "Generated private key: {}".format(private_key)
        print "Generated certificate: /usr/local/tomcat/{}-esg-node.pem".format(
            esg_functions.get_esgf_host())
        print "Please obtain and install appropriate certificates at the earliest. Execute esg_node.py --cert-howto for details."
        #print "Then run %> esg-node --install-ssl-keypair <signed cert> <private key> (use --help for details)"
        print "--------------------------------------------------------"


def generate_esgf_csrs(node_type_list):
    '''Generates a CSR to be signed by a ESGF CA'''
    if "IDP" in node_type_list:
        key_pair = create_key_pair(OpenSSL.crypto.TYPE_RSA, 1024)
        with open("/etc/esgfcerts/cakey.pem", "wt") as key_file_handle:
            key_file_handle.write(OpenSSL.crypto.dump_privatekey(
                OpenSSL.crypto.FILETYPE_PEM, key_pair))

        key_string = open("/etc/esgfcerts/cakey.pem", 'rt').read()
        key_object = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, key_string)

        careq = create_cert_request(key_object, O="ESGF", OU="ESGF.ORG",
                                    CN=esg_functions.get_esgf_host()+"-CA")
        with open('/etc/esgfcerts/cacert_req.csr', 'w') as csr:
            csr.write(
                OpenSSL.crypto.dump_certificate_request(
                    OpenSSL.crypto.FILETYPE_PEM, careq).decode('utf-8')
            )
        print "Successfully generated request for a simpleCA CA certificate: /etc/esgfcerts/cacert_req.csr"

    print "You are strongly advised to obtain and install commercial CA issued certificates for the web container."

    key_pair = create_key_pair(OpenSSL.crypto.TYPE_RSA, 1024)
    with open("/etc/esgfcerts/hostkey.pem", "wt") as key_file_handle:
        key_file_handle.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key_pair))

    key_string = open("/etc/esgfcerts/hostkey.pem", 'rt').read()
    key_object = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, key_string)

    careq = create_cert_request(key_object, O="ESGF", OU="ESGF.ORG", CN=esg_functions.get_esgf_host())
    with open('/etc/esgfcerts/hostcert_req.csr', 'w') as csr:
        csr.write(
            OpenSSL.crypto.dump_certificate_request(
                OpenSSL.crypto.FILETYPE_PEM, careq).decode('utf-8')
        )
    print "Successfully generated request for a simpleCA CA certificate: /etc/esgfcerts/hostcert_req.csr"

    print "Please mail the csr files for signing to Lukasz Lacinski <lukasz@uchicago.edu>, Prashanth Dwarakanath <pchengi@nsc.liu.se>, or Sebastien Denvil <sebastien.denvil@ipsl.jussieu.fr>"
    print "When you receive the signed certificate pack, untar all files into /etc/esgfcerts and execute esg_node.py --install-local-certs"
    print "If you also want to install the local certs for the tomcat web-container, execute esg_node.py --install-keypair /etc/esgfcerts/hostcert.pem /etc/esgfcerts/hostkey.pem"
    print "When prompted for the cachain file, specify /etc/esgfcerts/cachain.pem"


def generate_esgf_csrs_ext(node_type):
    '''Generates a CSR to be signed by a ESGF CA'''
    print "Are you requesting certs for an index-node or a datanode? (index/data)?"
    if node_type.lower() != "index" or node_type != "data":
        print "Please specify index or data as node type"
        return

    req_node_hostname = raw_input("Enter FQDN of node you are requesting certificates for")

    pybash.mkdir_p("/etc/extcsrs")

    cert_files = ['hostkey.pem', 'hostcert_req.csr']
    if node_type == "index":
        cert_files.append('cacert_req.csr')
        cert_files.append('cakey.pem')

        key_pair = create_key_pair(OpenSSL.crypto.TYPE_RSA, 1024)
        with open("/etc/extcsrs/cakey.pem", "wt") as key_file_handle:
            key_file_handle.write(OpenSSL.crypto.dump_privatekey(
                OpenSSL.crypto.FILETYPE_PEM, key_pair))

        key_string = open("/etc/extcsrs/cakey.pem", 'rt').read()
        key_object = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, key_string)

        careq = create_cert_request(key_object, O="ESGF", OU="ESGF.ORG",
                                    CN=esg_functions.get_esgf_host()+"-CA")
        with open('/etc/extcsrs/cacert_req.csr', 'w') as csr:
            csr.write(
                OpenSSL.crypto.dump_certificate_request(
                    OpenSSL.crypto.FILETYPE_PEM, careq).decode('utf-8')
            )
        print "Successfully generated request for a simpleCA CA certificate: /etc/extcsrs/cacert_req.csr"

    print "You are strongly advised to obtain and install commercial CA issued certificates for the web container."

    key_pair = create_key_pair(OpenSSL.crypto.TYPE_RSA, 1024)
    with open("/etc/extcsrs/hostkey.pem", "wt") as key_file_handle:
        key_file_handle.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key_pair))

    key_string = open("/etc/extcsrs/hostkey.pem", 'rt').read()
    key_object = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, key_string)

    careq = create_cert_request(key_object, O="ESGF", OU="ESGF.ORG", CN=req_node_hostname)
    with open('/etc/extcsrs/hostcert_req.csr', 'w') as csr:
        csr.write(
            OpenSSL.crypto.dump_certificate_request(
                OpenSSL.crypto.FILETYPE_PEM, careq).decode('utf-8')
        )
    print "Successfully generated request for a simpleCA CA certificate: /etc/extcsrs/hostcert_req.csr"

    with pybash.pushd("/etc/extcsrs"):
        try:
            with tarfile.open(req_node_hostname, "w:tgz") as tar:
                for file_name in cert_files:
                    tar.add(file_name)
            print "A copy of the generated keys and CSRs has been saved as /etc/extcsrs/{}.tgz".format(
                req_node_hostname)
        except Exception:
            print "ERROR: Problem with creating backup archive: {}".format(req_node_hostname)

    print "Please mail the csr files for signing to Lukasz Lacinski <lukasz@uchicago.edu>, Prashanth Dwarakanath <pchengi@nsc.liu.se>, or Sebastien Denvil <sebastien.denvil@ipsl.jussieu.fr>"
    print "When you receive the signed certificate pack, untar all files into /etc/esgfcerts and execute esg_node.py --install-local-certs"
    print "If you also want to install the local certs for the tomcat web-container, execute esg_node.py --install-keypair /etc/esgfcerts/hostcert.pem /etc/esgfcerts/hostkey.pem"
    print "When prompted for the cachain file, specify /etc/esgfcerts/cachain.pem"

# ------------------------------------
#   Utility functions
# ------------------------------------


def check_cert_expiry(cert_name):
    '''Check if a certificate is valid or has expired'''
    if not os.path.exists(cert_name):
        print "Certficate file {} does not exists".format(cert_name)
        return

    cert_data = open(cert_name).read()
    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_data)
    expire_date = x509.get_notAfter()

    if x509.has_expired():
        print "{} is expired".format(cert_name)

    print "{} will expire {}".format(cert_name, str(expire_date))


def extract_openssl_dn(public_cert="/etc/grid-security/hostcert.pem"):
    '''Regex's the output from openssl's x509 output in "openssl" format:
    Subject: O=Grid, OU=GlobusTest, OU=simpleCA-pcmdi3.llnl.gov, CN=pcmdi7.llnl.gov
    and transforms it to our "standard" format
    /O=Grid/OU=GlobusTest/OU=simpleCA-pcmdi3.llnl.gov/CN=pcmdi7.llnl.gov
    arg 1 -> the location of the x509 pem file'''

    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open(public_cert).read())
    subject_components = x509.get_subject().get_components()
    subject_string = ""

    for component in subject_components:
        subject_string = subject_string + "/" + component[0] + "=" + component[1]

    return subject_string


def extract_keystore_dn():
    '''Returns the distinguished name from the Java keystore'''
    try:
        keystore_info = esg_functions.call_binary("/usr/local/java/bin/keytool", ["-list", "-v", "-keystore", "/esg/config/tomcat/keystore-tomcat"])
    except ProcessExecutionError:
        logger.error("Could not extract distinguished name from keystore")
        raise
    keystore_owner = re.search("Owner:.*", keystore_info)
    distinguished_name = keystore_owner.split()[1]
    return distinguished_name


def check_certificates():
    '''Check the validity of the ESGF and Globus certificates'''
    print "check_certificates..."
    tomcat_cert_file = "{}/{}-esg-node.pem".format(
        config["tomcat_conf_dir"], esg_functions.get_esgf_host())
    check_cert_expiry(tomcat_cert_file)

    from idp_node import globus
    globus.globus_check_certificates()


def backup_existing_certs():
    '''Backup existing SSL certs on system'''
    if os.path.isfile("/etc/certs/hostcert.pem"):
        shutil.copyfile("/etc/certs/hostcert.pem",
                        "/etc/certs/hostcert.pem.{date}.bak".format(date=str(datetime.date.today())))
    if os.path.isfile("/etc/certs/hostkey.pem"):
        shutil.copyfile("/etc/certs/hostkey.pem",
                        "/etc/certs/hostkey.pem.{date}.bak".format(date=str(datetime.date.today())))
