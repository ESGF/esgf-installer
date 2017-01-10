#!/usr/bin/local/env python

import unittest
import esg_bootstrap
from esg_init import EsgInit
import os


class test_ESG_Bootstrap(unittest.TestCase):

	def test_check_for_root_id(self):
		output = esg_bootstrap.check_for_root_id()
		self.assertEqual(output, 1)

	def test_self_verify(self):
		output = esg_bootstrap.self_verify()
		self.assertEqual(output, 3)

if __name__ == '__main__':
    unittest.main()