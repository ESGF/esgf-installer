#!/usr/bin/local/env python

import unittest
import os
import shutil
import logging
import socket
import OpenSSL
from context import esgf_utilities
from context import base
from context import data_node
from esgf_utilities import pybash
from esgf_utilities import CA, esg_functions
from base import esg_tomcat_manager
from data_node import orp
import yaml


current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_CA(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF CA Test Fixture"
        print "******************************* \n"
        pass

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Cleaning up ESGF CA Test Fixture"
        print "******************************* \n"
        pass

    def convert_X509Name_to_string(self, cert):
        subject_components = cert.get_subject().get_components()
        subject_string = ""

        for component in subject_components:
            subject_string = subject_string + "/" +  component[0] + "=" + component[1]

        issuer_components = cert.get_issuer().get_components()
        issuer_string = ""
        for component in issuer_components:
            issuer_string = issuer_string + "/" +  component[0] + "=" + component[1]

        return (subject_string, issuer_string)

    def test_setup_temp_ca(self):
        CA.setup_temp_ca(temp_ca_dir="/tmp/tempcerts")
        self.assertTrue(os.listdir("/tmp/tempcerts/CA"))

        try:
            host_cert_object = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open("/tmp/tempcerts/hostcert.pem").read())
        except OpenSSL.crypto.Error:
            logger.exception("Certificate is not correct.")

        subject_string, issuer_string = self.convert_X509Name_to_string(host_cert_object)
        logger.info("subject_string: %s", subject_string)
        logger.info("issuer_string: %s", issuer_string)
        self.assertNotEqual(subject_string, issuer_string)

    def test_new_ca(self):
        with pybash.pushd("/tmp"):
            CA.new_ca()
            self.assertTrue(os.path.exists("CA"))
            self.assertTrue(os.path.exists("CA/certs"))
            self.assertTrue(os.path.exists("CA/crl"))
            self.assertTrue(os.path.exists("CA/newcerts"))
            self.assertTrue(os.path.exists("CA/private"))
            self.assertTrue(os.path.exists("CA/index.txt"))
            self.assertTrue(os.path.exists("CA/cacert.pem"))

            try:
                cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open("CA/cacert.pem").read())
            except OpenSSL.crypto.Error:
                logger.exception("Certificate is not correct.")

            cert_subject_object = cert_obj.get_subject()
            print "cert_subject_object:", cert_subject_object
            host_name = socket.getfqdn()
            logger.debug("host_name: %s", host_name)
            self.assertEquals(cert_subject_object.OU, "ESGF.ORG")
            self.assertEquals(cert_subject_object.CN, "{}-CA".format(host_name))
            self.assertEquals(cert_subject_object.O, "ESGF")

            #check subject string format
            subject_string_expected = "/O=ESGF/OU=ESGF.ORG/CN={}-CA".format(host_name)
            subject_string, issuer_string = self.convert_X509Name_to_string(cert_obj)
            self.assertEquals(subject_string, subject_string_expected)




if __name__ == '__main__':
    unittest.main(verbosity=2)
