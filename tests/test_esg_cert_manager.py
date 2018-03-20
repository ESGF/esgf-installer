#!/usr/bin/local/env python

import unittest
import logging
import os
import shutil
from context import esgf_utilities
from esgf_utilities import esg_cert_manager
from esgf_utilities import esg_functions
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_ESG_cert_manager(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree("/esg/tools/")
        except OSError, error:
            print "error:", error

        try:
            os.remove("/tmp/test-keystore")
        except OSError, error:
            print "error:", error

        try:
            os.remove("/tmp/hostkey.pem")
            os.remove("/tmp/hostcert.pem")
            os.remove("/tmp/test-truststore.ts")
            os.remove("/tmp/new-truststore.ts")
            os.remove("/tmp/key.der")
            os.remove("/tmp/temp-truststore.ts")
        except OSError, error:
            print "error:", error

        try:
            shutil.rmtree("/etc/tempcerts")
        except OSError, error:
            print "error:", error

    def test_install_extkeytool(self):
        esg_cert_manager.install_extkeytool()
        self.assertTrue(os.path.isfile("/esg/tools/idptools/bin/extkeytool"))


    def test_create_empty_java_keystore(self):
        esg_cert_manager.create_empty_java_keystore("/tmp/test-keystore", "testing", "password", "CN=ESGF")
        test_keystore_output = esg_functions.call_subprocess("/usr/local/java/bin/keytool -list -keystore /tmp/test-keystore")
        print "test_keystore_output:", test_keystore_output["stdout"]
        self.assertTrue(test_keystore_output["returncode"] == 0)

        keystore_output = esg_cert_manager.check_keystore("/tmp/test-keystore", "password")
        self.assertTrue("testing" in keystore_output.private_keys.keys())

    def test_create_self_signed_cert(self):
        esg_cert_manager.create_self_signed_cert("/tmp")
        self.assertTrue(os.path.exists(os.path.join("/tmp", "hostkey.pem")))
        self.assertTrue(os.path.exists(os.path.join("/tmp", "hostcert.pem")))

        self.assertTrue(esg_cert_manager.check_associate_cert_with_private_key("/tmp/hostcert.pem", "/tmp/hostkey.pem"))

        esg_cert_manager.convert_per_to_dem("/tmp/hostkey.pem", "/tmp")
        self.assertTrue(os.path.exists("/tmp/key.der"))

        esg_cert_manager.create_new_truststore("/tmp/temp-truststore.ts")
        esg_cert_manager._insert_cert_into_truststore("/tmp/hostcert.pem", "/tmp/temp-truststore.ts", "/tmp")
        truststore_output = esg_cert_manager.check_keystore("/tmp/temp-truststore.ts", "changeit")

        truststore_keys = [str(key) for key in truststore_output.certs.keys()]
        print "truststore_keys:", truststore_keys
        self.assertTrue("/tmp/hostcert" in truststore_keys)

    def test_fetch_esgf_certificates(self):
        esg_cert_manager.fetch_esgf_certificates("/tmp")
        self.assertTrue(os.path.exists("/tmp/esg_trusted_certificates"))

        shutil.rmtree("/tmp/esg_trusted_certificates")

    def test_rebuild_truststore(self):
        esg_cert_manager.rebuild_truststore("/tmp/test-truststore.ts")
        self.assertTrue(os.path.isfile("/tmp/test-truststore.ts"))

    def test_create_new_truststore(self):
        esg_cert_manager.create_new_truststore("/tmp/new-truststore.ts")
        self.assertTrue(os.path.isfile("/tmp/new-truststore.ts"))

    def test_setup_temp_ca(self):
        esg_cert_manager.setup_temp_ca(temp_ca_dir="/tmp/tempcerts")
        self.assertTrue(os.listdir("/tmp/tempcerts/CA"))









if __name__ == '__main__':
    unittest.main()
