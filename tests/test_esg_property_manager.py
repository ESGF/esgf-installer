import os
import unittest
import ConfigParser
from context import esgf_utilities
from esgf_utilities import esg_property_manager
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

class test_ESG_property_manager(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        try:
            print "Removing file test_properties.ini"
            os.remove("/usr/local/test_properties.ini")
        except OSError:
            # print "error:", error
            pass

    def test_get_property(self):
        test_properties_file = "/usr/local/test_properties.ini"
        esg_property_manager.write_as_property("Black Panther", "T'Challa", test_properties_file)
        output = esg_property_manager.get_property("Black Panther", test_properties_file)
        self.assertEqual(output, "T'Challa")

    def test_write_as_property(self):
        test_properties_file = "/usr/local/test_properties.ini"
        esg_property_manager.write_as_property("Batman", "Bruce Wayne", test_properties_file)
        parser = ConfigParser.SafeConfigParser()

        parser.read("/usr/local/test_properties.ini")
        self.assertEqual(parser.get('installer_properties', 'Batman'), "Bruce Wayne")

        esg_property_manager.write_as_property("Batman", "Damian Wayne", test_properties_file)
        parser.read("/usr/local/test_properties.ini")
        self.assertEqual(parser.get('installer_properties', 'Batman'), "Damian Wayne")


if __name__ == '__main__':
    unittest.main()
