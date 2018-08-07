#!/usr/bin/local/env python

import unittest
import logging
import os
import shutil
import OpenSSL
from context import esgf_utilities
from esgf_utilities import esg_keystore_manager
from esgf_utilities import esg_functions, pybash
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_ESG_keystore_manager(unittest.TestCase):

    def test_install_extkeytool(self):
        esg_keystore_manager.install_extkeytool()
        self.assertTrue(os.path.isfile("/esg/tools/idptools/bin/extkeytool"))


    def test_create_empty_java_keystore(self):
        esg_keystore_manager.create_empty_java_keystore("/tmp/test-keystore", "testing", "password", "CN=ESGF")
        test_keystore_output = esg_functions.call_subprocess("/usr/local/java/bin/keytool -list -keystore /tmp/test-keystore")
        print "test_keystore_output:", test_keystore_output["stdout"]
        self.assertTrue(test_keystore_output["returncode"] == 0)

        keystore_output = esg_keystore_manager.check_keystore("/tmp/test-keystore", "password")
        self.assertTrue("testing" in keystore_output.private_keys.keys())


if __name__ == '__main__':
    unittest.main()
