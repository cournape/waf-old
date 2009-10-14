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
		
	def test_invalid_task_generator(self):
		# white_box test: invalid task generator
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def build(bld):
	bld.new_task_gen(features=['cc'])

def configure(conf):
	conf.check_tool('cc')
"""
		self._write_wscript(wscript_contents, use_dic=False)
		self._test_configure()
		# TODO: check for WafError
		stderr = self._test_build(False)[1]
		err_msg = 'At least one compiler (gcc, ..) must be selected'
		self.assert_(err_msg in stderr, "'%s' was supposed in stderr, but '%s' was found..." % (err_msg, stderr))

def run_tests(verbose=1):
	try:
		suite = unittest.TestLoader().loadTestsFromTestCase(GccTester)
		return unittest.TextTestRunner(verbosity=verbose).run(suite)
	except common_test.StartupError, e:
		logging.warning( str(e) )
		raise (e)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	options = common_test.get_args_options()
	run_tests(options.verbose)
