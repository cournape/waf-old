#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
A tester for gcc tool, inherits from ccFamilyTester
"""
import os, sys, unittest, logging
import common_test
from cc_family_test import CcFamilyTester

class GccTester(CcFamilyTester):
	def __init__(self, methodName):
		self.tool_name 		= 'gcc'
		CcFamilyTester.__init__(self, methodName)

def run_tests(verbose=2):
	try:
		if verbose > 1: common_test.hide_output = False

		suite = unittest.TestLoader().loadTestsFromTestCase(GccTester)
		unittest.TextTestRunner(verbosity=verbose).run(suite)
	except common_test.StartupError, e:
		logging.warning( e.message )
		raise (e)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	run_tests()
