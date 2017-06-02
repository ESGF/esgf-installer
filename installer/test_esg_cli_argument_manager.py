import unittest
import esg_cli_argument_manager
import os


class test_ESG_CLI_Argument_Manager(unittest.TestCase):

    def setUp(self):
        self.node_type_list = ["data"]

    def tearDown(self):
        os.remove('test_config.txt')

    def test_set_node_type_config(self):
        esg_cli_argument_manager.set_node_type_config(self.node_type_list, 'test_config.txt')
        with open('test_config.txt', 'r') as config_file:
            config_file_contents = config_file.read().strip()
            print "config_file_contents:", config_file_contents
        self.assertEqual(config_file_contents, "".join(self.node_type_list))        


if __name__ == '__main__':
    unittest.main()