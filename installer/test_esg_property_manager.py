#!/usr/bin/local/env python

import unittest
import esg_property_manager
import os
import yaml

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_property_manager(unittest.TestCase):
    def test_load_properties(self):
        output = esg_property_manager.load_properties()
        self.assertEqual(output, 0)

    def test_get_property(self):
        output = esg_property_manager.get_property("publisher.config")
        self.assertEqual(output, "esg.ini")

        output = esg_property_manager.get_property("esgf.http.port")
        self.assertEqual(output, "80")

    def test_remove_property(self):
        target = open(config["config_file"], 'a')
        target.write("test.remove=remove\n")
        target.close()

        output = esg_property_manager.remove_property("test.remove")
        self.assertEqual(output, True)

        output = esg_property_manager.remove_property("non.existant")
        self.assertEqual(output, False)

    def test_write_as_property(self):
        output = esg_property_manager.write_as_property("new.property", "new_value")
        self.assertEqual(output, 0)

        find_value = esg_property_manager.get_property("new.property")
        self.assertEqual(find_value, "new_value")

if __name__ == '__main__':
    unittest.main()
