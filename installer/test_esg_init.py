#!/usr/bin/local/env python

import unittest
import esg_init
#import esg_version_manager


class TestESGInit(unittest.TestCase):
    """
        Test class for the esg_init.py module

        Functions:
            test_return_dictionary -> test the return value of the init method
            test_contain_vars -> test if the returns value contains data
    """
    def test_return_dictionary(self):
        """ Test if the return value of the init() function is a dictionary."""
        self.assertEqual(type(esg_init.init()), type({}))

    def test_contain_vars(self):
        """ The if the init() function contains a min of 100 variables."""
        self.assertTrue(esg_init.init() > 100)
        print "datatype: {}".format(type(esg_init.init()))
        for key, value in esg_init.init().iteritems():
            print "Key:{} Value: {}".format(key, value)

    def test_vars_values(self):
        """ Not Implimented."""
        pass

if __name__ == '__main__':
    unittest.main()
