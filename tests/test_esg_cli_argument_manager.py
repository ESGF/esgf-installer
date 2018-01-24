import unittest
import os
import sys
import pprint
from esgf_utilities import esg_cli_argument_manager

class test_ESG_CLI_Argument_Manager(unittest.TestCase):

    def setUp(self):
        self.node_type_list = ["data"]
        self.installater_mode_dictionary = {"install_mode": False, "upgrade_mode": False}
        self.devel = True
        self.esg_dist_url = "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"
    # def tearDown(self):
    #     os.remove('test_config.txt')
    @classmethod
    def tearDownClass(cls):
        os.remove('test_config.txt')

    def test_set_node_type_config(self):
        esg_cli_argument_manager.set_node_type_config(self.node_type_list, 'test_config.txt')
        with open('test_config.txt', 'r') as config_file:
            config_file_contents = config_file.read().strip()
            print "config_file_contents:", config_file_contents
        self.assertEqual(config_file_contents, "".join(self.node_type_list))

    def test_get_previous_node_type_config(self):
        esg_cli_argument_manager.set_node_type_config(self.node_type_list, 'test_config.txt')

        node_list_from_file = esg_cli_argument_manager.get_previous_node_type_config('test_config.txt')
        print "node_list_from_file:", node_list_from_file
        self.assertEqual(self.node_type_list, node_list_from_file)

    def test_set_node_type_value(self):
        print "esg_cli_argument_manager.node_type_dictionary:", esg_cli_argument_manager.node_type_dictionary

        esg_cli_argument_manager.set_node_type_value("install", True)
        self.assertEqual(esg_cli_argument_manager.node_type_dictionary["INSTALL_BIT"], True)

        esg_cli_argument_manager.set_node_type_value("data", True)
        self.assertEqual(esg_cli_argument_manager.node_type_dictionary["DATA_BIT"], True)


    def test_process_arguments_install(self):
        sys.argv.append("--install")
        pprint.pprint(sys.argv)

        esg_cli_argument_manager.process_arguments(self.installater_mode_dictionary["install_mode"], self.installater_mode_dictionary["upgrade_mode"], self.node_type_list, self.devel, self.esg_dist_url)
        self.assertEqual(esg_cli_argument_manager.installater_mode_dictionary["install_mode"], True)
        self.assertEqual(esg_cli_argument_manager.installater_mode_dictionary["upgrade_mode"], False)

    def test_process_arguments_upgrade(self):
        sys.argv.append("--upgrade")

        esg_cli_argument_manager.process_arguments(self.installater_mode_dictionary["install_mode"], self.installater_mode_dictionary["upgrade_mode"], self.node_type_list, self.devel, self.esg_dist_url)
        self.assertEqual(esg_cli_argument_manager.installater_mode_dictionary["install_mode"], False)
        self.assertEqual(esg_cli_argument_manager.installater_mode_dictionary["upgrade_mode"], True)


if __name__ == '__main__':
    unittest.main()
