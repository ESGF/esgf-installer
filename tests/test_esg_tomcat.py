#!/usr/bin/local/env python

import unittest
import os
import shutil
import logging
from distutils.spawn import find_executable
from context import esgf_utilities
from context import base
from base import esg_tomcat_manager
from esg_purge import purge_tomcat
from esgf_utilities.esg_exceptions import SubprocessError
from esgf_utilities import pybash
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_ESG_tomcat(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logger.info("Setting up esg_tomcat test harness")
        if os.path.exists("/usr/local/tomcat"):
            purge_tomcat()

    @classmethod
    def tearDownClass(cls):
        logger.info("Tearing down esg_tomcat test harness")
        purge_tomcat()

    def test_main(self):
        esg_tomcat_manager.main()
        self.assertTrue(os.path.isdir("/usr/local/tomcat"))
        try:
            esg_tomcat_manager.run_tomcat_config_test()
        except SubprocessError:
            self.fail("Config Test failed")

        # esg_tomcat_manager.start_tomcat()
        # output = esg_tomcat_manager.check_tomcat_status()
        # print "output:", output
        # self.assertTrue("running" in output["stdout"])


if __name__ == '__main__':
    unittest.main()
