#!/usr/bin/local/env python

import unittest
import os
import shutil
import logging
from context import esgf_utilities
from context import base
from context import data_node
from esgf_utilities import pybash
from base import esg_tomcat_manager
from data_node import orp
import yaml


current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_Thredds(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF ORP Test Fixture"
        print "******************************* \n"
        esg_tomcat_manager.main()

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Cleaning up ESGF ORP Test Fixture"
        print "******************************* \n"
        pass

    def test_download_orp_war(self):
        pybash.mkdir_p("/usr/local/tomcat/webapps/esg-orp")
        orp.download_orp_war("http://aims1.llnl.gov/esgf/dist/devel/esg-orp/esg-orp.war")
        self.assertTrue(os.path.isfile("/usr/local/tomcat/webapps/esg-orp/esg-orp.war"))
        st = os.stat("/usr/local/tomcat/webapps/esg-orp/esg-orp.war")
        print "war file size:", st.st_size

    def test_setup_orp(self):
        orp.setup_orp()
        self.assertTrue(os.path.isdir("/usr/local/tomcat/webapps/esg-orp"))
        self.assertTrue(os.path.exists("/usr/local/tomcat/webapps/esg-orp/WEB-INF/classes/esg-orp.properties"))
        self.assertTrue(os.path.exists("/esg/config/esgf_known_providers.xml"))
        self.assertTrue(os.path.exists("/esg/esgf-install-manifest"))


if __name__ == '__main__':
    unittest.main()
