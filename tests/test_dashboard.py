#!/usr/bin/local/env python

import unittest
import shutil
import os
from esgf_utilities import esg_purge
from esgf_utilities import esg_bash2py
from base import esg_tomcat_manager
from data_node import esg_dashboard

class test_Dashboard(unittest.TestCase):

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


    def test_clone_dashboard_repo(self):
        esg_dashboard.clone_dashboard_repo()
        self.assertTrue(os.path.isdir("/usr/local/esgf-dashboard"))
        print "esgf-dashboard repo contents:", os.listdir("/usr/local/esgf-dashboard")


    def test_setup_dashboard(self):
        esg_dashboard.setup_dashboard()
        self.assertTrue(os.path.isdir("/usr/local/tomcat/webapps/esgf-stats-api"))


if __name__ == '__main__':
    unittest.main()
