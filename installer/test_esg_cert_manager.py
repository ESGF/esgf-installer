#!/usr/bin/local/env python

import unittest
import esg_cert_manager
import esg_bash2py
import esg_functions
import esg_logging_manager
from distutils.spawn import find_executable
import os
import shutil
import yaml

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

logger = esg_logging_manager.create_rotating_log(__name__)

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
            os.remove("/tmp/mykey.pem")
            os.remove("/tmp/mycert.pem")
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


    def test_create_self_signed_cert(self):
        esg_cert_manager.create_self_signed_cert("/tmp")
        self.assertTrue(os.path.exists(os.path.join("/tmp", "mykey.pem")))
        self.assertTrue(os.path.exists(os.path.join("/tmp", "mycert.pem")))

        self.assertTrue(esg_cert_manager.check_associate_cert_with_private_key("/tmp/mycert.pem", "/tmp/mykey.pem"))






if __name__ == '__main__':
    unittest.main()
