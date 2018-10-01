import unittest
import os
import shutil
import fnmatch
import logging
import re
from context import esgf_utilities
from context import base
from context import data_node
from data_node import esg_publisher
from data_node import thredds
from base import esg_postgres
from esgf_utilities import pybash
from esgf_utilities import esg_functions
from esgf_utilities.esg_exceptions import SubprocessError
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_ESG_publisher(unittest.TestCase):

    def purge_publisher(self):
        try:
            shutil.rmtree("/tmp/esg-publisher")
        except OSError, error:
            print "Could not purge esg-publisher", error

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF Publisher Test Fixture"
        print "******************************* \n"
        pybash.mkdir_p(config["esg_config_dir"])
        esg_postgres.setup_postgres()

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Tearing down ESGF Publisher Test Fixture"
        print "******************************* \n"
        try:
            shutil.rmtree("/tmp/esg-publisher")
        except OSError, error:
            print "Error deleting /tmp/esg-publisher", error

        try:
            shutil.rmtree("/esg/config/esgcet")
        except OSError, error:
            print "Error deleting /esg/config/esgcet", error

    def test_clone_publisher_repo(self):
        esg_publisher.clone_publisher_repo("/tmp/esg-publisher")
        self.assertTrue(os.path.isdir("/tmp/esg-publisher/.git"))

        repo = esg_publisher.checkout_publisher_branch("/tmp/esg-publisher", "devel")
        branch = repo.active_branch
        print "active branch:", branch.name
        self.assertEquals(branch.name, "devel")

        self.purge_publisher()

    def test_setup_publisher(self):
        esg_publisher.setup_publisher()
        python_module_files = os.listdir("/usr/local/conda/envs/esgf-pub/lib/python2.7/site-packages")
        matches = fnmatch.filter(python_module_files, "esgcet-*-py2.7.egg")
        print "esgcet egg files:", matches
        self.assertTrue(matches)

        output = esg_publisher.check_publisher_version()
        print "esg_publisher version:", output
        match = re.search(r'\d.*', output).group()
        self.assertTrue(match)

        pybash.mkdir_p("/esg/config/esgcet")
        os.environ["UVCDAT_ANONYMOUS_LOG"] = "no"
        esg_publisher.run_esgsetup()
        self.assertTrue(os.path.isfile("/esg/config/esgcet/esg.ini"))

        os.environ["ESGINI"] = "/esg/config/esgcet/esg.ini"
        esg_publisher.run_esginitialize()

    def test_generate_esgsetup_options(self):
        output = esg_publisher.generate_esgsetup_options()
        print "output:", output
        self.assertTrue(output)


if __name__ == '__main__':
    unittest.main()
