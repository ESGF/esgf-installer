import unittest
import os
import sys
import pprint
from context import esgf_utilities
from esgf_utilities import esg_cli_argument_manager

class test_ESG_CLI_Argument_Manager(unittest.TestCase):

    def setUp(self):
        self.node_type_list = ["data"]
        self.installater_mode_dictionary = {"install_mode": False, "upgrade_mode": False}
        self.devel = True
        self.esg_dist_url = "http://aims1.llnl.gov/esgf/dist"
    # def tearDown(self):
    #     os.remove('test_config.txt')
    @classmethod
    def tearDownClass(cls):
        try:
            os.remove('test_config.txt')
        except OSError:
            pass

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

    def test_start(self):
        sys.argv.append("--start")
        pprint.pprint("arguments:", sys.argv)
        status = esg_cli_argument_manager.process_arguments(self.node_type_list, self.devel, self.esg_dist_url)
        self.assertTrue(status)

    def test_process_arguments_install(self):
        sys.argv.append("--install")
        pprint.pprint(sys.argv)



if __name__ == '__main__':
    unittest.main()
