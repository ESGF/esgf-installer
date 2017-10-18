#!/usr/bin/local/env python

import unittest
import esg_version_manager
import os
import semver
import yaml


with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_version_manager(unittest.TestCase):
    def test_version_comp(self):
        output = esg_version_manager.version_comp("2:2.3.4-5", "3:2.5.3-1")
        self.assertEqual(output, -1)
        test = semver.compare("2.2.3-5", "3.2.5-1")
        print "test:", test
        self.assertEqual(test, -1)

        output = esg_version_manager.version_comp("3:2.5.3-1", "2:2.3.4-5")
        self.assertEqual(output, 1)

        output = esg_version_manager.version_comp("3:2.5.3-1", "3:2.5.3-1")
        self.assertEqual(output, 0)

    def test_version_segment_comp(self):
        output = esg_version_manager.version_segment_comp("2.3.4", "3.2.5")
        self.assertEqual(output, -1)

        output = esg_version_manager.version_segment_comp("2.3.4", "2.2.5")
        self.assertEqual(output, 1)

        output = esg_version_manager.version_segment_comp("3.2.5", "2.3.4")
        self.assertEqual(output, 1)

        output = esg_version_manager.version_segment_comp("3.2.5", "3.2.5")
        self.assertEqual(output, 0)

        output = esg_version_manager.version_segment_comp("3.2.5", "3.2")
        self.assertEqual(output, 1)

    def test_check_version_atleast(self):
        output = esg_version_manager.check_version_atleast("3.2.5", "6.0")
        self.assertEqual(output, 1)

        output = esg_version_manager.check_version_atleast("2.7.10", "2.9.5")
        self.assertEqual(output, 1)

        output = esg_version_manager.check_version_atleast("6.0", "3.2.5")
        self.assertEqual(output, 0)

        output = esg_version_manager.check_version_atleast("6.0", "6.0")
        self.assertEqual(output, 0)

    def test_check_version_between(self):
        output = esg_version_manager.check_version_between("3.2.5", "2.3.4", "6.0")
        self.assertEqual(output, 0)

        output = esg_version_manager.check_version_between("2.3.4", "3.2.5", "6.0")
        self.assertEqual(output, 1)

        output = esg_version_manager.check_version_between("6.0", "2.3.4", "3.2.5")
        self.assertEqual(output, 1)

        output = esg_version_manager.check_version_between("6.0", "3.2.5", "2.3.4")
        self.assertEqual(output, 1)

    def test_check_for_acceptible_version(self):
        output = esg_version_manager.check_for_acceptible_version("python", "2.7")
        self.assertEqual(output, True)

        output = esg_version_manager.check_for_acceptible_version("python", "2.9")
        self.assertEqual(output, False)

        output = esg_version_manager.check_for_acceptible_version("python", "2.9", "3.3")
        self.assertEqual(output, False)

    def test_check_version_with(self):
    	# output = esg_version_manager.check_version_with("java", "java -version", "1.6.0")
    	# self.assertEqual(output, 0)

    	output = esg_version_manager.check_version_with("git", "git --version", "1.6.0")
    	self.assertEqual(output, 0)

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


if __name__ == '__main__':
    unittest.main()
