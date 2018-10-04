import unittest
import os
import shutil
import errno
import logging
import ConfigParser
from context import esgf_utilities
from context import base
from base import esg_java
from esgf_utilities import esg_functions, esg_property_manager
from esg_purge import purge_java
from idp_node import myproxy
import yaml
from plumbum.commands import ProcessExecutionError
from plumbum.commands import CommandNotFound

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)


class test_esg_java(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logger.info("Setting up esg_java test harness")
        if esg_java.check_for_existing_java():
            purge_java()

    @classmethod
    def tearDownClass(cls):
        logger.info("Tearing down esg_java test harness")
        purge_java()

    def test_setup_ant(self):
        esg_java.setup_ant()
        self.assertTrue(os.path.exists("/usr/bin/ant"))


    def test_check_java_version(self):
        output = esg_java.check_java_version()
        logger.debug("output: %s", output)
        self.assertTrue(output)

    def test_setup_java(self):
        esg_java.setup_java()
        self.assertTrue(esg_java.check_java_version())


if __name__ == '__main__':
    unittest.main()
