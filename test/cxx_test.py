#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

import os, sys, unittest
import common_test
from cxx_family_test import CxxFamilyTester
import Logs, Utils, Options, Scripting, Build

class CxxTester(CxxFamilyTester):
	def __init__(self, methodName):
		self.tool_name 		= 'g++'
		CxxFamilyTester.__init__(self, methodName)

	def test_invalid_task_generator(self):
		# white_box test: invalid task generator
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	pass

def set_options(opt):
	pass
"""
		self._write_wscript(wscript_contents, use_dic=False)
		opt_obj = Options.Handler()
		opt_obj.parse_args()
		Utils.set_main_module(self._wscript_file_path)
		Scripting.configure()
		bld = Build.Build()
		self.failUnlessRaises(Utils.WscriptError, bld.new_task_gen, 'cxx')

def run_tests(verbose=1):
	try:
		if verbose > 1: common_test.hide_output = False

		suite = unittest.TestLoader().loadTestsFromTestCase(CxxTester)
		# use the next line to run only specific tests: 
#		suite =
#		unittest.TestLoader().loadTestsFromName("test_customized_debug_level", CxxTester)
		unittest.TextTestRunner(verbosity=verbose).run(suite)
	except common_test.StartupError, e:
		Logs.error(e)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	run_tests()
