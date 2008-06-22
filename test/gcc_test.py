#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
A tester for gcc tool, inherits from ccFamilyTester
"""
import os, sys, unittest
import common_test
from cc_family_test import CcFamilyTester

# allow importing from wafadmin dir when ran from sub-directory 
sys.path.append(os.path.abspath(os.path.pardir))
import Test, Params

class GccTester(CcFamilyTester):
	def __init__(self, methodName):
		self.tool_name 		= 'gcc'
		CcFamilyTester.__init__(self, methodName)

def run_tests(verbose=2):
	try:
		suite = unittest.TestLoader().loadTestsFromTestCase(GccTester)
		unittest.TextTestRunner(verbosity=verbose).run(suite)
	except common_test.StartupError, e:
		Params.warning( e.message )
		raise (e)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	os.chdir(os.path.pardir)
	run_tests()