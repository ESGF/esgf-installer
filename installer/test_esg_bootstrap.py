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

	def test_check_for_update(self):
		output = esg_bootstrap.check_for_update("http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist/esgf-installer/2.0/esg-init")
		self.assertEqual(output, 0)

		output = esg_bootstrap.check_for_update("/Users/williamhill/Development/esgf-installer/installer/esg_init.py", "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist/esgf-installer/2.0/esg-init")
		self.assertEqual(output, 0)

	def test_checked_get(self):
		output = esg_bootstrap.checked_get("/Users/williamhill/Development/esgf-installer/shell_scripts/esg-init", "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist/esgf-installer/2.0/esg-init")
		self.assertEqual(output, 0)

		output = esg_bootstrap.checked_get("/Users/williamhill/Development/esgf-installer/shell_scripts/esg-functions", "http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist/esgf-installer/2.0/esg-functions")
		self.assertEqual(output, 0)

if __name__ == '__main__':
    unittest.main()