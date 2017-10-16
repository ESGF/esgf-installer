#!/usr/bin/local/env python

import unittest
import esg_functions
import os
import yaml

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_Functions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        esg_functions.call_subprocess("groupdel test_esgf_group")

    def test_check_esgf_httpd_process(self):
        output = esg_functions.check_esgf_httpd_process()
        self.assertEqual(output, 0)

    def test_path_unique(self):
        output = esg_functions.path_unique("usr/local/bin:/usr/test/bin:usr/local/bin")
        print "output: ", output
        self.assertEqual(output, "usr/local/bin:/usr/test/bin")

    def test_readlinkf(self):
        output = esg_functions.readlinkf(config["envfile"])
        self.assertEqual(output, "/etc/esg.env")


    def test_prefix_to_path(self):
        output = esg_functions.prefix_to_path("/path/to/test", "new/path")
        self.assertEqual(output, "new/path:/path/to/test")


    def test_backup(self):
        output = esg_functions.backup(os.getcwd())
        self.assertEqual(output, 0)

    # def test_subprocess_pipe_commands(self):
    #     output = esg_functions.subprocess_pipe_commands("/bin/ps -elf | grep grep")
    #     self.assertIsNotNone(output)

    def test_add_unix_group(self):
        esg_functions.add_unix_group("test_esgf_group")
        print "group_list:", esg_functions.get_group_list()
        self.assertTrue("test_esgf_group" in esg_functions.get_group_list())
if __name__ == '__main__':
    unittest.main()
