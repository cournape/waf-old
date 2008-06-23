#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

import os, sys, unittest, logging
import common_test
from cxx_family_test import CxxFamilyTester

class CxxTester(CxxFamilyTester):
	def __init__(self, methodName):
		self.tool_name 		= 'g++'
		CxxFamilyTester.__init__(self, methodName)

def run_tests(verbose=2):
	try:
		if verbose > 1: common_test.hide_output = False

		suite = unittest.TestLoader().loadTestsFromTestCase(CxxTester)
		# use the next line to run only specific tests: 
#		suite =
#		unittest.TestLoader().loadTestsFromName("test_customized_debug_level", CxxTester)
		unittest.TextTestRunner(verbosity=verbose).run(suite)
	except common_test.StartupError, e:
		logging.error( e.message )

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	run_tests()
