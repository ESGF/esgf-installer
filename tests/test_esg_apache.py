#!/usr/bin/local/env python

import unittest
import os
import errno
import shutil
from context import esgf_utilities
from context import base
from base import esg_apache_manager
from esgf_utilities import esg_functions
import yaml
import pip

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

class test_ESG_apache(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        esg_functions.stream_subprocess_output("yum remove -y httpd")
        pip.main(["uninstall", "mod_wsgi"])
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


    def test_install_apache_httpd(self):
        esg_apache_manager.install_apache_httpd()
        output = esg_functions.call_subprocess("httpd -version")["stdout"]
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
        self.assertTrue(os.path.isfile("/etc/httpd/conf.d/httpd.conf"))
        self.assertTrue(os.path.isfile("/etc/httpd/conf.d/ssl.conf"))
        self.assertTrue(os.listdir("/var/www/html/"))
        self.assertTrue(os.listdir("/etc/certs"))



if __name__ == '__main__':
    unittest.main()
