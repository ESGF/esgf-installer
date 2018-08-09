#!/usr/bin/local/env python

import unittest
import os
import shutil
import logging
import datetime
from context import esgf_utilities
from esgf_utilities import esg_functions
from esgf_utilities import pybash
from esgf_utilities import esg_property_manager
from esgf_utilities.esg_exceptions import SubprocessError
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)


class test_ESG_Functions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        try:
            esg_functions.stream_subprocess_output("groupdel test_esgf_group")
        except SubprocessError:
            pass
        try:
            shutil.rmtree("/esg/test_backup")
        except OSError:
            pass

    def test_path_unique(self):
        output = esg_functions.path_unique("usr/local/bin:/usr/test/bin:usr/local/bin")
        print "output: ", output
        self.assertEqual(output, "usr/local/bin:/usr/test/bin")

    def test_readlinkf(self):
        output = esg_functions.readlinkf(config["install_prefix"])
        self.assertEqual(output, "/usr/local")

    def test_prefix_to_path(self):
        output = esg_functions.prefix_to_path("/path/to/test", "new/path")
        self.assertEqual(output, "new/path:/path/to/test")

    def test_backup(self):
        test_backup_dir = "/esg/test_backup"
        pybash.mkdir_p(test_backup_dir)
        output = esg_functions.backup(os.getcwd(), backup_dir=test_backup_dir)
        self.assertEqual(output, 0)

    def test_is_in_git_repo(self):
        output = esg_functions.is_in_git_repo(os.getcwd())
        self.assertTrue(output)

    def test_add_unix_group(self):
        esg_functions.add_unix_group("test_esgf_group")
        print "group_list:", esg_functions.get_group_list()
        self.assertTrue("test_esgf_group" in esg_functions.get_group_list())

    def test_write_to_install_manifest(self):
        esg_functions.write_to_install_manifest("foo_app", "/tmp/foo", "1.0", "/tmp/install_manifest")
        self.assertTrue(os.path.isfile("/tmp/install_manifest"))
        prop = esg_functions.get_version_from_install_manifest("foo_app")
        logger.info("prop: %s", prop)
        self.assertEqual("1.0", prop)

    def test_is_valid_password(self):
        self.assertTrue(esg_functions.is_valid_password("Esgf4Dev"))

    def test_setup_whitelist_files(self):
        esg_functions.setup_whitelist_files(whitelist_file_dir="/tmp")
        self.assertTrue(os.path.isfile("/tmp/esgf_ats.xml"))

    def test_stream_subprocess_output(self):
        try:
            esg_functions.stream_subprocess_output("groupadd -r cogadmin")
        except SubprocessError, error:
            print "error:", error



if __name__ == '__main__':
    unittest.main()
