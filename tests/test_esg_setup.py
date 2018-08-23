#!/usr/bin/local/env python

import unittest
import os
import shutil
import errno
import logging
from distutils.spawn import find_executable
from context import esgf_utilities
from context import base
from esgf_utilities import esg_functions
from base import esg_setup
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_ESG_Setup(unittest.TestCase):

    def test_check_os(self):
        self.assertTrue(esg_setup.check_os())

    def test_check_if_root(self):
        self.assertTrue(esg_setup.check_if_root())

if __name__ == '__main__':
    unittest.main()
