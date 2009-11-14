#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Tests Options
"""

import os, unittest, shutil, tempfile
import common_test

import Test

from Constants import *
import Options
import Utils

class OptionsTester(common_test.CommonTester):
	def __init__(self, methodName):
		common_test.CommonTester.__init__(self, methodName)

	def setUp(self):
		# define & create temporary testing directories
		self._test_dir_root = tempfile.mkdtemp("", ".waf-testing_")
		self._wscript_file_path = os.path.join(self._test_dir_root, WSCRIPT_FILE)
		os.chdir(self._test_dir_root)

	def tearDown(self):
		'''tearDown - deletes the directories and files created by the tests ran '''
		os.chdir(self._waf_root_dir)
		
		if os.path.isdir(self._test_dir_root):
			shutil.rmtree(self._test_dir_root)

	def test_no_tool_to_set_options(self):
		# white_box test: set_options raise WafError when cannot find a tool
		Options.tooldir = os.path.join(self._waf_root_dir, Test.DIRS.WAFADMIN, Test.DIRS.TOOLS)
		opt = Options.Handler()
		self.failUnlessRaises(Utils.WscriptError, opt.tool_options, 'kk', '.')

def run_tests(verbose=1):
	suite = unittest.TestLoader().loadTestsFromTestCase(OptionsTester)
	return unittest.TextTestRunner(verbosity=verbose).run(suite)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	options = common_test.get_args_options()
	run_tests(options.verbose)
