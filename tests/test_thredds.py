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
        if not os.path.isdir("/usr/local/tomcat"):
            esg_tomcat_manager.main()
        try:
            os.remove("/tmp/mock_esg.ini")
        except OSError:
            pass

        try:
            os.remove("/tmp/mock_tomcat_users.xml")
        except OSError:
            pass

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Cleaning up ESGF Subsystem Test Fixture"
        print "******************************* \n"
        pass

    def test_setup_thredds(self):
        thredds.setup_thredds()
        self.assertTrue(os.path.isdir("/usr/local/tomcat/webapps/thredds"))
    def test_check_thredds_version(self):
        output = thredds.check_thredds_version()
        self.assertEqual(output, "5.0")

    def test_verify_thredds_credentials(self):
        if not os.path.isfile("/tmp/mock_esg.ini"):
            shutil.copyfile(os.path.join(current_directory, "mock_files", "mock_esg.ini"), "/tmp/mock_esg.ini")
        if not os.path.isfile("/tmp/mock_tomcat_users.xml"):
            shutil.copyfile(os.path.join(current_directory, "mock_files", "mock_tomcat_users.xml"), "/tmp/mock_tomcat_users.xml")

        password_hash = thredds.create_password_hash("test_password")
        thredds.update_tomcat_users_file("test_user", password_hash, tomcat_users_file="/tmp/mock_tomcat_users.xml")

        output = thredds.verify_thredds_credentials(thredds_ini_file="/tmp/mock_esg.ini", tomcat_users_file="/tmp/mock_tomcat_users.xml")
        logger.info("output: %s", output)
        self.assertTrue(output)


if __name__ == '__main__':
    unittest.main()
