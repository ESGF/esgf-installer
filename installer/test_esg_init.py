#!/usr/bin/local/env python

import unittest
from esg_init import EsgInit


class test_ESG_Init(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test = EsgInit()

    def test_populate_internal_esgf_node_code_versions(self):
        output = self.test.populate_internal_esgf_node_code_versions()
        print "vars after populate_internal_esgf_node_code_versions call: ", vars(self.test)
        print "output: ", output
        self.assertNotEqual(output, None)

    # def test_populate_external_programs_versions(self):
    #     test = EsgInit()
    #     output = test.populate_external_programs_versions()
    #     print "output: ", output
    #     self.assertNotEqual(output, None)

    def test_populate_external_script_variables(self):
        print "vars before call: ", vars(self.test)
        output = self.test.populate_external_script_variables()
        print "output: ", output

        self.assertEqual("openssl_install_dir" in output, True)
        self.assertNotEqual(output, None)
if __name__ == '__main__':
    unittest.main()
