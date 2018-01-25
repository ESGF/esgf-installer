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
from index_node import esg_cog

class test_Cog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up COG Test Fixture"
        print "******************************* \n"
        pass

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Cleaning up COG Test Fixture"
        print "******************************* \n"
        try:
            shutil.rmtree("/tmp/cog")
        except OSError, error:
            print "error deleting /tmp/cog:", error


    def test_clone_cog_repo(self):
        esg_cog.clone_cog_repo("/tmp/cog/cog_install", )
        self.assertTrue(os.path.isdir("/tmp/cog/cog_install/.git"))

        repo = esg_cog.checkout_cog_branch("/tmp/cog/cog_install", "devel")
        branch = repo.active_branch
        print "active branch:", branch.name
        self.assertEquals(branch.name, "devel")

    def test_setup_django_openid_auth(self):
        esg_cog.setup_django_openid_auth("/tmp/django-openid-auth")
        self.assertTrue(os.path.isdir("/tmp/django-openid-auth"))

    def test_transfer_api_client_python(self):
        esg_cog.transfer_api_client_python("/tmp/transfer-api-client-python")
        self.assertTrue(os.path.isdir("/tmp/transfer-api-client-python"))

    def test_setup_cog(self):
        esg_cog.setup_cog("/tmp/cog")
        self.assertTrue(os.path.isdir("/tmp/cog"))
        self.assertTrue(os.listdir("/tmp/cog"))


if __name__ == '__main__':
    unittest.main()
