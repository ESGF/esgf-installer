'''
Certificate Management Functions
'''
import os
import shutil
from OpenSSL import crypto
import datetime
import logging
from esg_init import EsgInit
import esg_bash2py


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
config = EsgInit()

expired=0
day=60*60*24
warn=day*7
info=day*3

certs_expired = []
certs_immediate_expire = []
certs_week_expire = []
certs_month_expire = []
def print_cert(certificate_path):
    print "CERTIFICATE = %s" % (certificate_path)
    # cert_file = '/path/to/your/certificate'
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(certificate_path).read())
    print "%s  %s" % (cert.get_subject(), cert.notAfter())
    # subject = cert.get_subject()
    # issued_to = subject.CN    # the Common Name field
    # issuer = cert.get_issuer()
    # issued_by = issuer.CN 

def check_cert_expiry(certificate_path):
    
    print "inspecting %s" % (certificate_path)
    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(certificate_path).read())
        if cert.has_expired():
            certs_expired.append(cert)
            return
        expire_date = datetime.strptime(cert.notAfter(), "%Y%m%d%H%M%SZ")
        expire_in = expire_date - datetime.now()
        if expire_in.days < 0:
            certs_immediate_expire.append(cert)
        elif expire_in.days <= 7:
            certs_week_expire.append(cert)
        elif expire_in.days <= 30:
            certs_month_expire.append(cert)

    except:
        # exit_error(1, 'Certificate date format unknow.')
        print "Certificate date formate unknown."

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
