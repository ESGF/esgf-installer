#!/usr/bin/local/env python

import unittest
import os
import shutil
import logging
from context import esgf_utilities
from context import base
from context import data_node
from esgf_utilities import esg_bash2py
from esgf_utilities import CA
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
        print "Setting up ESGF Subsystem Test Fixture"
        print "******************************* \n"
        pass

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Cleaning up ESGF Subsystem Test Fixture"
        print "******************************* \n"
        pass

    def test_new_ca(self):
        CA.new_ca(ca_dir="/tmp/tempcerts")
        self.assertTrue(os.path.exists("/tmp/tempcerts/CA"))
        self.assertTrue(os.path.exists("/tmp/tempcerts/CA/certs"))
        self.assertTrue(os.path.exists("/tmp/tempcerts/CA/crl"))
        self.assertTrue(os.path.exists("/tmp/tempcerts/CA/private/cakey.pem"))



if __name__ == '__main__':
    unittest.main()
