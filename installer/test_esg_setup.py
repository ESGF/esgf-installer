#!/usr/bin/local/env python

import unittest
import os
import shutil
import esg_functions
from distutils.spawn import find_executable
import sys
import esg_setup


class test_ESG_Setup(unittest.TestCase):

	@classmethod
	def tearDownClass(cls):
		os.remove("/tmp/Miniconda2-latest-Linux-x86_64.sh")
		esg_functions.stream_subprocess_output("/usr/local/testConda/bin/conda install -y anaconda-clean")
		esg_functions.stream_subprocess_output("/usr/local/testConda/bin/anaconda-clean --yes")
		shutil.rmtree("/usr/local/testConda")

		esg_functions.stream_subprocess_output("yum -y remove uvcdat")

	def test_download_conda(self):
		print "path:", sys.path
		esg_setup.download_conda("/usr/local/testConda")
		self.assertTrue(os.path.isfile("/tmp/Miniconda2-latest-Linux-x86_64.sh"))
		print "path after:", sys.path
		self.assertTrue("/usr/local/testConda/bin" in sys.path)
		# self.assertTrue(find_executable("conda"))

	def test_setup_cdat(self):
		self.assertTrue(esg_setup.setup_cdat())




if __name__ == '__main__':
	unittest.main()
