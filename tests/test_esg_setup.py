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

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove("/tmp/Miniconda2-latest-Linux-x86_64.sh")
        except OSError, error:
            if error.errno == errno.EEXIST:
                pass
        esg_functions.stream_subprocess_output(
            "/usr/local/testConda/bin/conda install -y anaconda-clean")
        esg_functions.stream_subprocess_output("/usr/local/testConda/bin/anaconda-clean --yes")
        try:
            shutil.rmtree("/usr/local/testConda")
        except OSError, error:
            if error.errno == errno.EEXIST:
                pass

        print "\n*******************************"
        print "Purging Java"
        print "******************************* \n"

        try:
            shutil.rmtree("/usr/local/java")
        except OSError:
            logger.exception("No Java installation found to delete")

        try:
            shutil.rmtree("/usr/bin/java")
        except OSError:
            logger.exception("No Java installation found to delete at /usr/bin/java")


    def test_setup_cdat(self):
        self.assertTrue(esg_setup.setup_cdat())

    def test_check_for_existing_java(self):
        output = esg_setup.check_for_existing_java()
        self.assertIsNotNone(output)

    def test_setup_java(self):
        esg_setup.setup_java()
        self.assertTrue(os.path.exists("/usr/local/java"))
        self.assertTrue(find_executable("java"))


if __name__ == '__main__':
    unittest.main()