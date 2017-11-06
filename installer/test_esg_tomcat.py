#!/usr/bin/local/env python

import unittest
import esg_tomcat_manager
import esg_bash2py
import esg_logging_manager
from distutils.spawn import find_executable
import os
import shutil
import yaml

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

logger = esg_logging_manager.create_rotating_log(__name__)

class test_ESG_tomcat(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        try:
            print "Removing tar file in tearDownClass"
            os.remove("/tmp/apache-tomcat-8.5.20.tar.gz")
        except OSError, error:
            # print "error:", error
            pass
        try:
            os.unlink("/usr/local/tomcat")
        except OSError, error:
            print "error:", error
            # shutil.unlink()
            pass
        try:
            shutil.rmtree("/usr/local/tomcat_test/")
        except OSError, error:
            logger.exception("Could not delete tomcat_test directory")
            pass
        esg_tomcat_manager.stop_tomcat()

    def delete_tomcat_download(self):
        os.remove("/tmp/apache-tomcat-8.5.20.tar.gz")

    def test_download_tomcat(self):
        esg_tomcat_manager.download_tomcat()
        self.assertTrue(os.path.isfile("/tmp/apache-tomcat-8.5.20.tar.gz"))
        self.delete_tomcat_download()

    def test_extract_tomcat_tarball(self):
        esg_bash2py.mkdir_p("/usr/local/tomcat_test")
        esg_tomcat_manager.download_tomcat()
        esg_tomcat_manager.extract_tomcat_tarball("/usr/local/tomcat_test")
        self.assertTrue(os.path.isdir("/usr/local/tomcat_test/apache-tomcat-8.5.20"))
        self.assertTrue(os.path.isdir("/usr/local/tomcat_test/"))

        esg_tomcat_manager.copy_config_files()
        self.assertTrue(os.path.isfile("/usr/local/tomcat/conf/server.xml"))

    def test_start_tomcat(self):
        pass

    def test_stop_tomcat(self):
        pass

    def test_restart_tomcat(self):
        pass


    def test_main(self):
        esg_tomcat_manager.main()
        self.assertTrue(os.path.isdir("/usr/local/tomcat"))
        self.assertTrue(find_executable("httpd"))

        esg_tomcat_manager.start_tomcat()
        output = esg_tomcat_manager.check_tomcat_status()
        print "output:", output
        self.assertTrue("running" in output["stdout"])

    def test_setup_temp_certs(self):
        esg_tomcat_manager.setup_temp_certs()
        self.assertTrue(os.path.isdir("CA"))





if __name__ == '__main__':
    unittest.main()
