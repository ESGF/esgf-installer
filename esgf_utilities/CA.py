import os
import shutil
import glob
import logging
import tarfile
import OpenSSL
import errno
import OpenSSL
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_functions, esg_cert_manager

logger = logging.getLogger("esgf_logger" +"."+ __name__)

def new_ca():
    '''Mimics perl CA.pl -newca'''
    esg_bash2py.mkdir_p("CA")
    esg_bash2py.mkdir_p("CA/certs")
    esg_bash2py.mkdir_p("CA/crl")
    esg_bash2py.mkdir_p("CA/newcerts")
    esg_bash2py.mkdir_p("CA/private")
    esg_bash2py.touch("CA/index.txt")
    with open("CA/crlnumber", "w") as crlnumber_file:
        crlnumber_file.write("01\n")

    cakey = esg_cert_manager.createKeyPair(OpenSSL.crypto.TYPE_RSA, 4096)
    ca_answer = "{fqdn}-CA".format(fqdn=esg_functions.get_esgf_host())
    careq = esg_cert_manager.createCertRequest(cakey, CN=ca_answer, O="ESGF", OU="ESGF.ORG")
    # CA certificate is valid for five years.
    cacert = esg_cert_manager.createCertificate(careq, (careq, cakey), 0, (0, 60*60*24*365*5))

    print('Creating Certificate Authority private key in "CA/private/cakey.pem"')
    with open('CA/private/cakey.pem', 'w') as capkey:
        capkey.write(
            OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, cakey).decode('utf-8')
    )

    print('Creating Certificate Authority certificate in "CA/cacert.pem"')
    with open('CA/cacert.pem', 'w') as ca:
        ca.write(
            OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cacert).decode('utf-8')
    )


def newreq_nodes():
    '''Mimics perl CA.pl -newreq-nodes'''

    new_req_key = esg_cert_manager.createKeyPair(OpenSSL.crypto.TYPE_RSA, 4096)
    new_careq = esg_cert_manager.createCertRequest(new_req_key, CN=esg_functions.get_esgf_host(), O="ESGF", OU="ESGF.ORG")

    print('Creating Certificate Authority private key in "newkey.pem"')
    with open('newkey.pem', 'w') as new_key_file:
        new_key_file.write(
            OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, new_req_key).decode('utf-8')
    )

    print('Creating Certificate Authority private key in "newreq.pem"')
    with open('newreq.pem', 'w') as new_req_file:
        new_req_file.write(
            OpenSSL.crypto.dump_certificate_request(OpenSSL.crypto.FILETYPE_PEM, new_careq).decode('utf-8')
    )
    print "Request is in newreq.pem, private key is in newkey.pem\n";

    return new_careq, new_req_key



def sign_request(ca_req, req_key):
    '''Mimics perl CA.pl -sign'''
    newcert = esg_cert_manager.createCertificate(ca_req, (ca_req, req_key), 0, (0, 60*60*24*365*5))

    with open('newcert.pem', 'w') as ca:
        ca.write(
            OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, newcert).decode('utf-8')
    )
    print "Signed certificate is in newcert.pem\n";

def delete_existing_temp_CA():
    try:
        shutil.rmtree("CA")
    except OSError, error:
        if error.errno == errno.ENOENT:
            pass
    file_extensions = ["*.pem", "*.gz", "*.ans", "*.tmpl"]
    files_to_delete = []
    for ext in file_extensions:
        files_to_delete.extend(glob.glob(ext))
    for file_name in files_to_delete:
        try:
            shutil.rmtree(file_name)
        except OSError, error:
            if error.errno == errno.ENOENT:
                pass

def setup_temp_ca(temp_ca_dir="/etc/tempcerts"):
    print "*******************************"
    print "Setting up Temp CA"
    print "******************************* \n"

    esg_bash2py.mkdir_p(temp_ca_dir)

    with esg_bash2py.pushd(temp_ca_dir):
        delete_existing_temp_CA()
        new_ca()

        # openssl rsa -in CA/private/cakey.pem -out clearkey.pem -passin pass:placeholderpass && mv clearkey.pem CA/private/cakey.pem
        private_cakey = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, open("CA/private/cakey.pem").read())

        with open('clearkey.pem', 'w') as clearkey:
            clearkey.write(
                OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, private_cakey).decode('utf-8')
        )

        shutil.copyfile("clearkey.pem", "CA/private/cakey.pem")

        # perl CA.pl -newreq-nodes <reqhost.ans
        new_careq, new_req_key = newreq_nodes()
        # perl CA.pl -sign <setuphost.ans
        sign_request(new_careq, new_req_key)

        # openssl x509 -in CA/cacert.pem -inform pem -outform pem >cacert.pem
        try:
            cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open("CA/cacert.pem").read())
        except OpenSSL.crypto.Error:
            logger.exception("Certificate is not correct.")

        with open('cacert.pem', 'w') as ca:
            ca.write(
                OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_obj).decode('utf-8')
        )
        # cp CA/private/cakey.pem cakey.pem
        shutil.copyfile("CA/private/cakey.pem", "cakey.pem")

        # openssl x509 -in newcert.pem -inform pem -outform pem >hostcert.pem
        try:
            cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open("newcert.pem").read())
        except OpenSSL.crypto.Error:
            logger.exception("Certificate is not correct.")

        with open('hostcert.pem', 'w') as ca:
            ca.write(
                OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_obj).decode('utf-8')
        )

        # mv newkey.pem hostkey.pem
        shutil.move("newkey.pem", "hostkey.pem")

        # chmod 400 cakey.pem
        os.chmod("cakey.pem", 0400)

        # chmod 400 hostkey.pem
        os.chmod("hostkey.pem", 0400)

        # rm -f new*.pem
        new_pem_files = glob.glob('new*.pem')
        for pem_file in new_pem_files:
            os.remove(pem_file)

        try:
            cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open("cacert.pem").read())
        except OpenSSL.crypto.Error:
            logger.exception("Certificate is not correct.")

        local_hash = esg_cert_manager.convert_hash_to_hex(cert_obj.subject_name_hash())
        globus_cert_dir = "globus_simple_ca_{}_setup-0".format(local_hash)
        esg_bash2py.mkdir_p(globus_cert_dir)

        shutil.copyfile("cacert.pem", os.path.join(globus_cert_dir,local_hash+".0"))

        cert_subject_object = cert_obj.get_subject()
        cert_subject = "/OU={OU}/CN={CN}/O={O}".format(OU=cert_subject_object.OU, CN=cert_subject_object.CN, O=cert_subject_object.O)
        esg_functions.replace_string_in_file(os.path.join(globus_cert_dir,local_hash+".signing_policy"), '/O=ESGF/OU=ESGF.ORG/CN=placeholder', cert_subject)
        shutil.copyfile(os.path.join(globus_cert_dir,local_hash+".signing_policy"), "signing-policy")

        # tar -cvzf globus_simple_ca_${localhash}_setup-0.tar.gz $tgtdir;
        with tarfile.open(globus_cert_dir+".tar.gz", "w:gz") as tar:
            tar.add(globus_cert_dir)

        # rm -rf $tgtdir;
        shutil.rmtree(globus_cert_dir)

        # mkdir -p /etc/certs
        esg_bash2py.mkdir_p("/etc/certs")
    	# cp openssl.cnf /etc/certs/
        shutil.copyfile("openssl.cnf", "/etc/certs/openssl.cnf")
    	# cp host*.pem /etc/certs/
        host_pem_files = glob.glob('new*.pem')
        for pem_file in host_pem_files:
            shutil.copyfile(pem_file, "/etc/certs/{}".format(pem_file))
    	# cp cacert.pem /etc/certs/cachain.pem
        shutil.copyfile("cacert.pem", "/etc/certs/cachain.pem")
    	# mkdir -p /etc/esgfcerts
        esg_bash2py.mkdir_p("/etc/esgfcerts")
