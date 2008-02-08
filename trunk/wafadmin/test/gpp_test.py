#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

import os, sys, unittest
import common_test
from cpp_family_test import CppFamilyTester

# allow importing from wafadmin dir when ran from sub-directory 
sys.path.append(os.path.abspath(os.path.pardir))
import Params


class CppTester(CppFamilyTester):
	def __init__(self, methodName):
		self.tool_name 		= 'g++'
		CppFamilyTester.__init__(self, methodName)

def run_tests(verbose=2):
	try:
		suite = unittest.TestLoader().loadTestsFromTestCase(CppTester)
		# use the next line to run only specific tests: 
#		suite = unittest.TestLoader().loadTestsFromName("test_customized_debug_level", CppTester)
		unittest.TextTestRunner(verbosity=verbose).run(suite)
	except common_test.StartupError, e:
		Params.error( e.message )

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	os.chdir(os.path.pardir)
	run_tests()