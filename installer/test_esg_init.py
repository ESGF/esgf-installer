#!/usr/bin/local/env python

import unittest
import esg_init
import esg_version_manager


class Test_ESG_Init(unittest.TestCase):
    def setup(self):
        self.var = ["apache_frontend_version", "cdat_version"]
    def test_init(self):
        for x in esg_init.init():
            self.assertTrue(x in self.var)

if __name__ == '__main__':
    unittest.main()
