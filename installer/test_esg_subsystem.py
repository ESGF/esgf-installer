#!/usr/bin/local/env python

import unittest
import esg_subsystem
import shutil
import os
import esg_tomcat_manager

class test_ESGF_BUILD(unittest.TestCase):

    def setUp(self):
        # purge_and_clone_fresh_repos.main(os.path.join(os.environ["HOME"], "Development", "ESGF"))
        pass

    def cleanup(self):
        try:
            shutil.rmtree("/usr/local/esgf-dashboard")
        except Exception, error:
            print "error:", error

    def test_clone_dashboard_repo(self):
        esg_subsystem.clone_dashboard_repo()
        self.assertTrue(os.path.isdir("/usr/local/esgf-dashboard"))
        os.listdir("/usr/local/esgf-dashboard")

    def test_setup_orp(self):
        esg_subsystem.setup_orp()
        self.assertTrue(os.path.isdir("/usr/local/tomcat/webapps/esg-orp"))

if __name__ == '__main__':
    unittest.main()
