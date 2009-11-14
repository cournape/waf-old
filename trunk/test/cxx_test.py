#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008, 2009

import os, sys, unittest
import common_test
from cxx_family_test import CxxFamilyTester
import Logs
import Utils
import Options
import Scripting
import Build
import Constants

class CxxTester(CxxFamilyTester):
	def __init__(self, methodName):
		self.tool_name 		= 'g++'
		CxxFamilyTester.__init__(self, methodName)

	def test_no_tool_was_defined(self):
		# black_box test: cannot create a task gen for type without defining
		# its tool first.
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	pass

def build(bld):
	bld.new_task_gen('cxx')
"""
		self._write_wscript(wscript_contents, use_dic=False)
		self._test_configure()
		(stdout, stderr) = self._test_build(False)
		self.assert_('cxx is not a valid task generator' in stderr,
					 "missing error message, got %s" % stderr)

	def test_invalid_task_generator(self):
		# black_box test: invalid task generator
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def build(bld):
	# no taskgen with such name...
	obj = bld.new_task_gen('gjk.hwer.kg')

def configure(conf):
	conf.check_tool('g++')
"""
		self._write_wscript(wscript_contents, use_dic=False)
		self._test_configure()
		(stdout, stderr) = self._test_build(False)
		self.assert_('gjk.hwer.kg is not a valid task generator' in stderr,
					 "missing error message, got %s" % stderr)

def run_tests(verbose=1):
	try:
		suite = unittest.TestLoader().loadTestsFromTestCase(CxxTester)
		# use the next line to run only specific tests: 
#		suite = unittest.TestLoader().loadTestsFromName("test_customized_debug_level", CxxTester)
		return unittest.TextTestRunner(verbosity=verbose).run(suite)
	except common_test.StartupError, e:
		Logs.error(e)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	options = common_test.get_args_options()
	run_tests(options.verbose)
