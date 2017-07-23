#!/usr/bin/local/env python

import unittest
import esg_env_manager
import os
import yaml

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_env_manager(unittest.TestCase):
    def test_remove_env(self):

        target = open(config["envfile"], 'a')
        target.write("export TEST_ENV=/home")
        target.close()

        output = esg_env_manager.remove_env("TEST_ENV")
        self.assertEqual(output,True)

        output = esg_env_manager.remove_env("NEW_ENV")
        self.assertEqual(output,True)


    def test_deduplicate_settings_in_file(self):
        target = open(config["envfile"], 'a')
        target.write("export TEST_ENV=/home\n")
        target.write("export TEST_ENV=/second\n")
        target.close()
        output = esg_env_manager.deduplicate_settings_in_file()
        self.assertEqual(output, True)

    def test_deduplicate_properties(self):
        target = open(config["config_file"], 'a')
        target.write("test.property=first\n")
        target.write("test.property=second\n")
        target.close()

        output = esg_env_manager.deduplicate_properties()
        self.assertEqual(output, 0)


if __name__ == '__main__':
    unittest.main()
