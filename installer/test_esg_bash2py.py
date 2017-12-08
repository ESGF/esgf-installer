#!/usr/bin/local/env python

import unittest
import esg_bash2py
import os
import yaml

with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_bash2py(unittest.TestCase):

    def test_trim_string_from_head(self):
        output = esg_bash2py.trim_string_from_head("/usr/local/bin/esg_installarg_file")
        self.assertEqual(output, "esg_installarg_file")

    def test_trim_string_from_tail(self):
        output = esg_bash2py.trim_string_from_tail("8.0.33")
        self.assertEqual(output, "8")


if __name__ == '__main__':
    unittest.main()
