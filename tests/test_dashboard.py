#!/usr/bin/local/env python

import unittest
import shutil
import os
from context import esgf_utilities
from context import base
from context import data_node
from esgf_utilities import esg_purge
from esgf_utilities import pybash
from base import esg_tomcat_manager
from data_node import esg_dashboard

class test_Dashboard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF Dashboard Test Fixture"
        print "******************************* \n"
        esg_tomcat_manager.main()

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Cleaning up ESGF Dashboard Test Fixture"
        print "******************************* \n"
        pass


    def test_clone_dashboard_repo(self):
        esg_dashboard.clone_dashboard_repo()
        self.assertTrue(os.path.isdir("/usr/local/esgf-dashboard"))
        print "esgf-dashboard repo contents:", os.listdir("/usr/local/esgf-dashboard")


    def test_setup_dashboard(self):
        esg_dashboard.setup_dashboard()
        self.assertTrue(os.path.isdir("/usr/local/tomcat/webapps/esgf-stats-api"))


if __name__ == '__main__':
    unittest.main()
