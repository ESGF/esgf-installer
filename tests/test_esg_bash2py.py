#!/usr/bin/local/env python

import unittest
from context import esgf_utilities
from esgf_utilities import pybash
import os
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


if __name__ == '__main__':
    unittest.main()
