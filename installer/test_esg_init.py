#!/usr/bin/local/env python

import unittest
from esg_init import EsgInit
import esg_functions


class test_ESG_Init(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test = EsgInit()

    def test_populate_internal_esgf_node_code_versions(self):
        output = self.test.populate_internal_esgf_node_code_versions()
        # print "vars after populate_internal_esgf_node_code_versions call: ", vars(self.test)
        # print "output: ", output
        # self.assertNotEqual(output, None)
        self.assertEqual("esgf_desktop_version" in output, True)
        self.assertEqual(esg_functions.check_version_atleast(output["esgf_desktop_version"], '0.0.20'), 0)

    def test_populate_external_programs_versions(self):
        output = self.test.populate_external_programs_versions()
        # print "output: ", output
        self.assertNotEqual(output, None)
        self.assertEqual("java_version" in output, True)
        self.assertEqual(esg_functions.check_version_atleast(output["java_version"], '1.8.0_92'), 0)
        self.assertEqual(esg_functions.check_version_atleast(output["python_version"], '2.7'), 0)

    def test_populate_external_script_variables(self):
        output = self.test.populate_external_script_variables()
        # print "output: ", output

        self.assertEqual("openssl_install_dir" in output, True)
        self.assertNotEqual(output, None)

    def test_populate_environment_constants(self):
        output = self.test.populate_environment_constants()

        self.assertNotEqual(output, None)
        self.assertEqual("JAVA_OPTS" in output, True)

    def test_populate_ID_settings(self):
        output = self.test.populate_ID_settings()

        self.assertEqual("installer_user" in output, True)

    def test_populate_internal_script_variables(self):
        output = self.test.populate_internal_script_variables()

        self.assertEqual("esg_backup_dir" in output, True)
if __name__ == '__main__':
    unittest.main()
