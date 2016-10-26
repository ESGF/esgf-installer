#!/usr/bin/local/env python

import unittest
import esg_setup

class test_ESG_Setup(unittest.TestCase):
	def test_hello_world(self):
		print "Testing:", esg_setup.print_hello()
		self.assertEqual(esg_setup.print_hello(), "hello world")


if __name__ == '__main__':
	unittest.main()
