#!/usr/bin/local/env python

import unittest
import esg_subsystem
import esg_purge
import shutil
import os
import esg_tomcat_manager
import esg_bash2py

class test_ESGF_subsystem(unittest.TestCase):

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
        except Exception, error:
            print "error:", error
        esg_purge.purge_tomcat()
        try:
            shutil.rmtree("/esg")
        except OSError, error:
            print "error deleting /esg:", error
    # def cleanup(self):
    #     try:
    #         shutil.rmtree("/usr/local/esgf-dashboard")
    #     except Exception, error:
    #         print "error:", error

    def test_clone_dashboard_repo(self):
        esg_subsystem.clone_dashboard_repo()
        self.assertTrue(os.path.isdir("/usr/local/esgf-dashboard"))
        os.listdir("/usr/local/esgf-dashboard")

    def test_download_orp_war(self):
        esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esg-orp")
        esg_subsystem.download_orp_war("http://aims1.llnl.gov/esgf/dist/devel/esg-orp/esg-orp.war")
        self.assertTrue(os.path.isfile("/usr/local/tomcat/webapps/esg-orp/esg-orp.war"))
        st = os.stat("/usr/local/tomcat/webapps/esg-orp/esg-orp.war")
        print "war file size:", st.st_size

    def test_setup_orp(self):
        esg_subsystem.setup_orp()
        self.assertTrue(os.path.isdir("/usr/local/tomcat/webapps/esg-orp"))
    def test_setup_node_manager_old(self):
        esg_subsystem.setup_node_manager_old()
        self.assertTrue(os.path.isdir("/usr/local/tomcat/webapps/esgf-node-manager"))

if __name__ == '__main__':
    unittest.main()
