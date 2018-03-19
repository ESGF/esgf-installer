import os
import shutil
import glob
import filecmp
import logging
import socket
import datetime
import re
import errno
import requests
import yaml
import jks
import OpenSSL
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_functions
from esg_exceptions import SubprocessError


CATOP = "CA"
DIRMODE = "0777";
CAKEY = "cakey.pem";
CACERT = "cacert.pem";
CAREQ = "careq.pem";
REQ = "openssl req -config ./openssl.cnf";
CA = "openssl ca -config ./openssl.cnf";
CADAYS = "-days 30";	# 30 days
def new_ca(ca_dir="/etc/tempcerts"):

    esg_bash2py.mkdir_p(ca_dir)
    with esg_bash2py.pushd(ca_dir):

        esg_bash2py.mkdir_p(CATOP)
        esg_bash2py.mkdir_p(os.path.join(CATOP, "certs"))
        esg_bash2py.mkdir_p(os.path.join(CATOP, "crl"))
        esg_bash2py.mkdir_p(os.path.join(CATOP, "newcerts"))
        esg_bash2py.mkdir_p(os.path.join(CATOP, "private"))

        esg_bash2py.touch(os.path.join(CATOP, "index.txt"))
        with open(os.path.join(CATOP, "crlnumber"), "w") as crlnumber_file:
            crlnumber_file.write("01\n")

        if not os.path.exists(os.path.exists(CATOP, "private", CAKEY)):
            CA_cert_filename = raw_input("CA certificate filename (or enter to create)")

        if CA_cert_filename and os.path.exists(CA_cert_filename):
            cert_file_handle = open(CA_cert_filename, "r")
            cert_string = ""
            key_string = ""
            for aline in cert_file_handle.readlines():
                if "BEGIN CERTIFICATE" in aline:
                    cert_string = cert_string + aline
                elif "END CERTIFICATE" in aline:
                    with open(os.path.join(CATOP, CACERT)) as cert_file:
                        cert_file.write(cert_string)
                    cert_string = ""
                elif cert_string:
                    cert_string = cert_string + aline
                elif re.match('BEGIN.* PRIVATE KEY', aline):
                    key_string = key_string + aline
                elif re.match('END.* PRIVATE KEY', aline):
                    with open(os.path.join(CATOP, "private", CAKEY)) as key_file:
                        key_file.write(key_string)
                    key_string = ""
                elif key_string:
                    key_string = key_string + aline
        else:
            print "Making CA certificate ...\n";
            esg_functions.stream_subprocess_output("{REQ} -passout pass:placeholderpass -newkey rsa:4096 -keyout {CATOP}/private/{CAKEY} -out {CATOP}/{CAREQ}".format(REQ=REQ, CATOP=CATOP, CAKEY=CAKEY, CAREQ=CAREQ))
            print "now done with key gen"
            esg_functions.stream_subprocess_output("{CA} -create_serial -out {CATOP}/{CACERT} {CADAYS} -batch -keyfile {CATOP}/private/{CAKEY} -selfsign -extensions v3_ca -passin pass:placeholderpass -infiles {CATOP}/{CAREQ}".format(CA=CA, CATOP=CATOP, CAKEY=CAKEY, CAREQ=CAREQ, CADAYS=CADAYS))
