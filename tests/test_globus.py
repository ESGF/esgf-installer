import unittest
import os
import shutil
import fnmatch
import logging
import re
from context import esgf_utilities
from context import base
from context import data_node
from context import idp_node
from data_node import esg_publisher
from data_node import thredds
from base import esg_postgres
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_functions
from idp_node import globus
from esgf_utilities.esg_exceptions import SubprocessError
from esg_purge import purge_globus
import yaml

current_directory = os.path.join(os.path.dirname(__file__))


with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)


class test_ESG_Globus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        purge_globus()

    def test_setup_globus_data(self):
        globus.setup_globus("DATA")
        self.assertTrue(os.path.exists("/usr/bin/globus-version"))
        self.assertTrue(os.path.exists("/usr/local/globus"))

    def test_setup_globus_idp(self):
        globus.setup_globus("IDP")
        self.assertTrue(os.path.exists("/usr/bin/globus-version"))
        self.assertTrue(os.path.exists("/usr/local/globus"))



if __name__ == '__main__':
    unittest.main()
