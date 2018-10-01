#!/usr/bin/local/env python

import unittest
import logging
import os
import shutil
import OpenSSL
from context import esgf_utilities
from esgf_utilities import esg_cert_manager
from esgf_utilities import esg_functions, pybash
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_ESG_cert_manager(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        pass


    def test_create_key_pair(self):
        key_pair = esg_cert_manager.create_key_pair(OpenSSL.crypto.TYPE_RSA, 1024)
        self.assertTrue(key_pair.bits(), 1024)
        self.assertEqual(key_pair.type(), OpenSSL.crypto.TYPE_RSA)
        self.assertTrue(key_pair.check())


if __name__ == '__main__':
    unittest.main()
