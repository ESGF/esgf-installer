import unittest
import os
import sys
import pprint
from context import esgf_utilities
from esgf_utilities import esg_cli_argument_manager

class test_ESG_CLI_Argument_Manager(unittest.TestCase):

    def setUp(self):
        self.node_type_list = ["DATA"]
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
        esg_cli_argument_manager.set_node_type_value(self.node_type_list, 'test_config.txt')
        with open('test_config.txt', 'r') as config_file:
            config_file_contents = config_file.read().strip()
            print "config_file_contents:", config_file_contents
        self.assertEqual(config_file_contents, "".join(self.node_type_list))

    def test_get_previous_node_type_config(self):
        esg_cli_argument_manager.set_node_type_value(self.node_type_list, 'test_config.txt')

        node_list_from_file = esg_cli_argument_manager.get_node_type('test_config.txt')
        print "node_list_from_file:", node_list_from_file
        self.assertEqual(self.node_type_list, node_list_from_file)

    def test_start(self):
        sys.argv.append("--start")
        pprint.pprint(sys.argv)
        status = esg_cli_argument_manager.process_arguments()
        self.assertTrue(status)

    def test_set_type(self):
        sys.argv.append("--set-type index idp")
        # pprint.pprint("args:", sys.argv)
        print "args:", sys.argv
        status = esg_cli_argument_manager.process_arguments()
        self.assertTrue(status)

    def test_type(self):
        sys.argv.append("--type data")
        status = esg_cli_argument_manager.process_arguments()
        self.assertTrue(status)

    def test_check_for_valid_node_combo(self):
        sys.argv.append("--set-type index idp")
        pprint.pprint(sys.argv)
        self.assertTrue(esg_cli_argument_manager.check_for_valid_node_combo("index idp"))

if __name__ == '__main__':
    unittest.main()
