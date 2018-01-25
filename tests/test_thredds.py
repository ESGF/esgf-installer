#!/usr/bin/local/env python

import unittest
import os
import shutil
import logging
from context import esgf_utilities
from context import base
from context import data_node
from base import esg_tomcat_manager
from data_node import thredds
import yaml


current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_Thredds(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF Subsystem Test Fixture"
        print "******************************* \n"
        esg_tomcat_manager.main()
    # def setUp(self):
    #     # purge_and_clone_fresh_repos.main(os.path.join(os.environ["HOME"], "Development", "ESGF"))
    #     pass

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Cleaning up ESGF Subsystem Test Fixture"
        print "******************************* \n"
        try:
            shutil.rmtree("/usr/local/esgf-dashboard")
        except OSError, error:
            print "error:", error
        try:
            shutil.rmtree("/esg")
        except OSError, error:
            print "error deleting /esg:", error

        try:
            shutil.rmtree("/tmp/cog")
        except OSError, error:
            print "error deleting /tmp/cog:", error

    def test_setup_thredds(self):
        thredds.setup_thredds()
        self.assertTrue(os.path.isdir("/usr/local/tomcat/webapps/thredds"))
    def test_check_thredds_version(self):
        output = thredds.check_thredds_version()
        self.assertEqual(output, "5.0")

    def test_verify_thredds_credentials(self):
        if not os.path.isdir("/tmp/mock_esg.ini"):
            shutil.copyfile(os.path.join(current_directory, "mock_files", "mock_esg.ini"), "/tmp/mock_esg.ini")
        output = thredds.verify_thredds_credentials(thredds_ini_file="/tmp/mock_esg.ini")
        logger.info("output: %s", output)
        self.assertTrue(output)


if __name__ == '__main__':
    unittest.main()
