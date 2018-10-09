#!/usr/bin/local/env python

import unittest
import os
import shutil
import logging
from context import esgf_utilities
from context import base
from context import data_node
from base import esg_tomcat_manager
from esgf_utilities import pybash
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

        if not os.path.isfile("/esg/config/esgf.properties"):
            pybash.mkdir_p("/esg/config")
            shutil.copyfile(os.path.join(current_directory, "mock_files", "mock_esgf.properties"), "/esg/config/esgf.properties")

        if not os.path.isfile("/esg/config/esgcet/esg.ini"):
            pybash.mkdir_p("/esg/config/esgcet")
            shutil.copyfile(os.path.join(current_directory, "mock_files", "mock_esg.ini"), "/esg/config/esgcet/esg.ini")

        with open("/esg/config/.esgf_pass", "w") as pass_file:
            pass_file.write("foobar")



    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Cleaning up Thredds Test Fixture"
        print "******************************* \n"
        try:
            os.remove("/tmp/mock_esg.ini")
        except OSError:
            pass

        try:
            os.remove("/tmp/mock_tomcat_users.xml")
        except OSError:
            pass

        try:
            os.remove("/esg/config/esgf.properties")
        except OSError:
            pass

        try:
            os.remove("/esg/config/.esgf_pass")
        except OSError:
            pass


    def test_setup_thredds(self):
        thredds.setup_thredds()
        self.assertTrue(os.path.isdir("/usr/local/tomcat/webapps/thredds"))


if __name__ == '__main__':
    unittest.main()
