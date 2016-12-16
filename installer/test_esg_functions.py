#!/usr/bin/local/env python

import unittest
import esg_functions
from esg_init import EsgInit
import os


class test_ESG_Functions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test = EsgInit()

    # @classmethod
    # def setUpClass(self):
        # try: 
        #     os.makedirs("/esg/esgf-install-manifest")
        # except OSError:
        #     if not os.path.isdir("/esg/esgf-install-manifest"):
        #         raise

    # def setUp(self):
    #     if os.path.isdir("/home/el"):
    #         print "found path"
    #     else:
    #         print "did not find path"

    def test_version_comp(self):
        output = esg_functions.version_comp("2:2.3.4-5", "3:2.5.3-1")

        self.assertEqual(output, -1)

        output = esg_functions.version_comp("3:2.5.3-1", "2:2.3.4-5")
        self.assertEqual(output, 1)

        output = esg_functions.version_comp("3:2.5.3-1", "3:2.5.3-1")
        self.assertEqual(output, 0)

    def test_version_segment_comp(self):
        output = esg_functions.version_segment_comp("2.3.4", "3.2.5")
        self.assertEqual(output, -1)

        output = esg_functions.version_segment_comp("2.3.4", "2.2.5")
        self.assertEqual(output, 1)

        output = esg_functions.version_segment_comp("3.2.5", "2.3.4")
        self.assertEqual(output, 1)

        output = esg_functions.version_segment_comp("3.2.5", "3.2.5")
        self.assertEqual(output, 0)

        output = esg_functions.version_segment_comp("3.2.5", "3.2")
        self.assertEqual(output, 1)

    def test_check_version_atleast(self):
        output = esg_functions.check_version_atleast("3.2.5", "6.0")
        self.assertEqual(output, 1)

        output = esg_functions.check_version_atleast("2.7.10", "2.9.5")
        self.assertEqual(output, 1)

        output = esg_functions.check_version_atleast("6.0", "3.2.5")
        self.assertEqual(output, 0)

        output = esg_functions.check_version_atleast("6.0", "6.0")
        self.assertEqual(output, 0)

    def test_check_version_between(self):
        output = esg_functions.check_version_between("3.2.5", "2.3.4", "6.0")
        self.assertEqual(output, 0)

        output = esg_functions.check_version_between("2.3.4", "3.2.5", "6.0")
        self.assertEqual(output, 1)

        output = esg_functions.check_version_between("6.0", "2.3.4", "3.2.5")
        self.assertEqual(output, 1)

        output = esg_functions.check_version_between("6.0", "3.2.5", "2.3.4")
        self.assertEqual(output, 1)

    def test_check_version(self):
        output = esg_functions.check_version("python", "2.7")
        self.assertEqual(output, 0)

        output = esg_functions.check_version("python", "2.9")
        self.assertEqual(output, 1)

        output = esg_functions.check_version("python", "2.9", "3.3")
        self.assertEqual(output, 1)

    def test_check_version_with(self):
    	output = esg_functions.check_version_with("java", "java -version", "1.6.0")
    	self.assertEqual(output, 0)

    	output = esg_functions.check_version_with("git", "git --version", "1.6.0")
    	self.assertEqual(output, 0)

    def test_check_module_version(self):
        output = esg_functions.check_module_version("esgcet", "3.0.1")
        self.assertEqual(output,0)

        output = esg_functions.check_module_version("pylint", "1.9")
        self.assertEqual(output,1)

    def test_get_current_esgf_library_version(self):
        output = esg_functions.get_current_esgf_library_version("esgf-security")
        self.assertEqual(output, 1)

    def test_get_current_webapp_version(self):
        output = esg_functions.get_current_webapp_version("esg-orp")
        self.assertEqual(output, "2.9.0")

    def test_check_webapp_version(self):
        output = esg_functions.check_webapp_version("esg-orp", "2.0")
        self.assertEqual(output, 0)

        output = esg_functions.check_webapp_version("esg-orp", "4.0")
        self.assertEqual(output, 1)

    def test_remove_env(self):

        target = open(self.test.envfile, 'a')
        target.write("export TEST_ENV=/home")
        target.close()

        output = esg_functions.remove_env("TEST_ENV")
        self.assertEqual(output,True)

        output = esg_functions.remove_env("NEW_ENV")
        self.assertEqual(output,True)


    def test_deduplicate(self):
        target = open(self.test.envfile, 'a')
        target.write("export TEST_ENV=/home\n")
        target.write("export TEST_ENV=/second\n")
        target.close()

        output = esg_functions.deduplicate()
        self.assertEqual(output, 0)

    def test_deduplicate_properties(self):
        target = open(self.test.config_dictionary["config_file"], 'a')
        target.write("test.property=first\n")
        target.write("test.property=second\n")
        target.close()

        output = esg_functions.deduplicate_properties()
        self.assertEqual(output, 0)

    def test_check_postgress_process(self):
        output = esg_functions.check_postgress_process()
        self.assertEqual(output, 0)

    def test_check_esgf_httpd_process(self):
        output = esg_functions.check_esgf_httpd_process()
        self.assertEqual(output, 0)

    def test_path_unique(self):
        output = esg_functions._path_unique("usr/local/bin:/usr/test/bin:usr/local/bin")
        print "output: ", output
        self.assertEqual(output, "usr/local/bin:/usr/test/bin")

    def test_readlinkf(self):
        output = esg_functions._readlinkf(self.test.envfile)
        self.assertEqual(output, "/etc/esg.env")

    def test_load_properties(self):
        output = esg_functions.load_properties()
        self.assertEqual(output, 0)

    def test_get_property(self):
        output = esg_functions.get_property("publisher.config")
        self.assertEqual(output, "esg.ini")

        output = esg_functions.get_property("esgf.http.port")
        self.assertEqual(output, "80")

if __name__ == '__main__':
    unittest.main()
