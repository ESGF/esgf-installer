#!/usr/bin/local/env python

import unittest
import os
import errno
import shutil
import logging
from context import esgf_utilities
from context import base
from base import esg_apache_manager
from esgf_utilities import esg_functions, pybash
import yaml
import pip
from plumbum.commands import ProcessExecutionError

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_ESG_apache(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logger.info("Setting up esg_apache_manager test harness")
        if esg_functions.call_binary("httpd", ["-version"]):
            esg_functions.call_binary("yum", ["-y", "remove", "httpd"])
        pybash.mkdir_p("/etc/tempcerts")
        pybash.touch("/etc/tempcerts/cacert.pem")

    @classmethod
    def tearDownClass(cls):
        logger.info("Tearing down esg_apache_manager test harness")
        esg_functions.call_binary("yum", ["-y", "remove", "httpd"])
        try:
            shutil.rmtree("/var/www/.python-eggs")
            shutil.rmtree('/var/www/html/')
            shutil.rmtree('/etc/certs/')
        except OSError, error:
            if error.errno == errno.ENOENT:
                pass
            else:
                print "error:", error
        # os.unlink("/etc/httpd/modules/mod_wsgi-py27.so")

    def test_start_apache(self):
        try:
            esg_apache_manager.start_apache()
        except ProcessExecutionError, err:
            logger.error("Error occurred starting apache: %s", err)
            self.fail("start_apache() failed")

    def test_install_apache_httpd(self):
        esg_apache_manager.install_apache_httpd()
        output = esg_functions.call_binary("httpd", ["-version"])
        print "output:", output
        self.assertIsNotNone(output)


        esg_apache_manager.install_mod_wsgi()
        self.assertTrue(os.path.isfile("/etc/httpd/modules/mod_wsgi-py27.so"))


        esg_apache_manager.make_python_eggs_dir()
        self.assertTrue(os.path.isdir("/var/www/.python-eggs"))
        owner, group = esg_functions.get_dir_owner_and_group("/var/www/.python-eggs")
        self.assertEqual(owner, "apache")
        self.assertEqual(group, "apache")

        esg_apache_manager.copy_apache_conf_files()
        self.assertTrue(os.path.isfile("/etc/httpd/conf.d/ssl.conf"))
        self.assertTrue(os.listdir("/var/www/html/"))
        self.assertTrue(os.listdir("/etc/certs"))

if __name__ == '__main__':
    unittest.main(verbosity=2)
