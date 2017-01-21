#!/usr/bin/local/env python

import unittest
import esg_setup

class test_ESG_Setup(unittest.TestCase):
	# def test_hello_world(self):
	# 	print "Testing:", esg_setup.print_hello()
	# 	self.assertEqual(esg_setup.print_hello(), "hello world")

	def test_is_in_git(self):
		output = esg_setup.is_in_git("/Users/hill119/Development/esgf-installer/installer/esg_init.py")
		self.assertEqual(output, 0)


if __name__ == '__main__':
	unittest.main()
