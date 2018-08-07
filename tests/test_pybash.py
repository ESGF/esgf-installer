#!/usr/bin/local/env python

import unittest
import shutil
import errno
import os
from context import esgf_utilities
from esgf_utilities import pybash
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


class test_pybash(unittest.TestCase):

    def test_trim_string_from_head(self):
        output = pybash.trim_string_from_head("/usr/local/bin/esg_installarg_file")
        self.assertEqual(output, "esg_installarg_file")

    def test_trim_string_from_tail(self):
        output = pybash.trim_string_from_tail("8.0.33")
        self.assertEqual(output, "8")

    def test_touch(self):
        pybash.touch("/tmp/wakanda.txt")
        self.assertTrue(os.path.exists("/tmp/wakanda.txt"))
        os.remove("/tmp/wakanda.txt")

    def test_pushd(self):
        with pybash.pushd("/tmp"):
            self.assertEquals(os.getcwd(), "/tmp")

    def test_mkdir_p(self):
        pybash.mkdir_p("/tmp/wakanda")
        self.assertTrue(os.path.exists("/tmp/wakanda"))

        try:
            shutil.rmtree("/tmp/wakanda")
        except OSError, error:
            if error.errno == errno.ENOENT:
                pass
            else:
                print "error:", error

if __name__ == '__main__':
    unittest.main()
