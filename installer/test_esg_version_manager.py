#!/usr/bin/local/env python

import unittest
import esg_version_manager
import os
import semver
import yaml


with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_version_manager(unittest.TestCase):

    def test_check_module_version(self):
        # output = esg_version_manager.check_module_version("esgcet", "3.0.1")
        # self.assertEqual(output,0)

        output = esg_version_manager.check_module_version("pylint", "1.9")
        self.assertEqual(output,1)

    def test_get_current_esgf_library_version(self):
        output = esg_version_manager.get_current_esgf_library_version("esgf-security")
        self.assertEqual(output, True)

    def test_get_current_webapp_version(self):
        output = esg_version_manager.get_current_webapp_version("esg-orp")
        self.assertEqual(output, "2.9.0")

    def test_check_webapp_version(self):
        output = esg_version_manager.check_webapp_version("esg-orp", "2.0")
        self.assertEqual(output, 0)

        output = esg_version_manager.check_webapp_version("esg-orp", "4.0")
        self.assertEqual(output, 1)

    def test_compare_versions(self):
        self.assertTrue(esg_version_manager.compare_versions("1.8.0_131", "1.8.0_111"))


if __name__ == '__main__':
    unittest.main()
