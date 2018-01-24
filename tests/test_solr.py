#!/usr/bin/local/env python

import unittest
import shutil
import os
from context import esgf_utilities
from context import base
from context import index_node
from esgf_utilities import esg_purge
from esgf_utilities import esg_bash2py
from base import esg_tomcat_manager
from index_node import solr

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

    def test_setup_solr(self):
        solr.setup_solr(SOLR_INSTALL_DIR="/tmp/solr", SOLR_HOME="/tmp/solr-home")
        self.assertTrue(os.path.isdir("/tmp/solr"))


if __name__ == '__main__':
    unittest.main()
