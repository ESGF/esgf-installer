import unittest
import os
import esg_node


class test_ESG_Node(unittest.TestCase):
    def setUp(self):
        self.bit_boolean_dictionary = {"INSTALL_BIT": False, "TEST_BIT": False, "DATA_BIT": False,
                                       "INDEX_BIT": False, "IDP_BIT": False, "COMPUTE_BIT": False, "WRITE_ENV_BIT": False}
        self.node_type_list = ["data", "index"]

    def test_check_selected_node_type(self):
        found_valid_type = esg_node.check_selected_node_type(
            self.bit_boolean_dictionary, self.node_type_list)
        self.assertTrue(found_valid_type, True)

    def test_set_version_info(self):
        version, maj_version, release = esg_node.set_version_info()
        print "version:", version
        print "maj_version:", maj_version
        print "release:", release


if __name__ == '__main__':
    unittest.main()
