import unittest
import os
import shutil
import errno
import logging
from context import esgf_utilities
from context import base
from esgf_utilities import esg_functions
from idp_node import myproxy
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_myproxy(unittest.TestCase):
    def test_copy_myproxy_config(self):
        myproxy.copy_myproxy_server_config(config_path="/tmp/myproxy-server.config")
        self.assertTrue(os.path.exists("/tmp/myproxy-server.config"))


    def test_edit_etc_myproxyd(self):
        myproxy.edit_etc_myproxyd("/tmp/myproxy-esgf")
        self.assertTrue(os.path.exists("/tmp/myproxy-esgf"))






if __name__ == '__main__':
    unittest.main()
