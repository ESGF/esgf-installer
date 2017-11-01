#!/usr/bin/local/env python

import unittest
import esg_cert_manager
import esg_bash2py
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

    def test_install_extkeytool(self):
        esg_cert_manager.install_extkeytool()
        self.assertTrue(os.path.isfile("/esg/tools/idptools/bin/extkeytool"))






if __name__ == '__main__':
    unittest.main()
