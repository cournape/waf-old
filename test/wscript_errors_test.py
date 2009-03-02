#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Tests wscript errors handling
"""

import os, unittest, tempfile, shutil, imp
import common_test

import Test
from Constants import *
import Options
import Scripting
import Build
import Utils
import Configure

non_exist_path = '/non/exist/path'

class WscriptErrorsTester(common_test.CommonTester):
	def __init__(self, methodName):
		common_test.CommonTester.__init__(self, methodName)

	def setUp(self):
		'''setup the foundations needed for tests'''
		self._bld = Build.BuildContext()
		setattr(self._bld.__class__, 'recurse', Scripting.recurse)
		# define & create temporary testing directories - 
		# needed to make sure it will run in same manner always 
		self._test_dir_root = tempfile.mkdtemp("", ".waf-testing_")
		self._wscript_file_path = os.path.join(self._test_dir_root, WSCRIPT_FILE)
		os.chdir(self._test_dir_root)

	def tearDown(self):
		'''tearDown - cleanup after each test'''
		del self._bld
		os.chdir(self._waf_root_dir)

		if os.path.isdir(self._test_dir_root):
			shutil.rmtree(self._test_dir_root)

class WhiteWscriptTester(WscriptErrorsTester):
	"""white-box tests for Wscript Errors"""
	
	def _setup_options(self):
		opt_obj = Options.Handler()
		setattr(opt_obj.__class__, 'recurse', Scripting.recurse)
		opt_obj.parse_args()
		Options.options.prefix = Options.default_prefix

	def test_nonexist_blddir(self):
		self._bld.load_dirs(srcdir=non_exist_path, blddir=os.path.join(non_exist_path, 'out'))
		self.failUnlessRaises(Utils.WscriptError, Scripting.add_subdir, self._test_dir_root, self._bld)

	def test_nonexist_subdir(self):
		self._bld.load_dirs(srcdir=self._test_dir_root, blddir=os.path.join(self._test_dir_root, 'out'))
		self.failUnlessRaises(Utils.WscriptError, Scripting.add_subdir, non_exist_path, self._bld)
		
	def test_missing_blddir(self):
		self._setup_options()
		Utils.g_module = imp.new_module('main_wscript')
		Utils.g_module.srcdir = '.'
		# TODO: tests for WafError upon change
		self.failUnlessRaises(Utils.WscriptError, Scripting.configure)

	def test_missing_srcdir(self):
		self._setup_options()
		Utils.g_module = imp.new_module('main_wscript')
		Utils.g_module.blddir = '.'
		# TODO: tests for WafError upon change
		self.failUnlessRaises(Utils.WscriptError, Scripting.configure)

	def test_missing_configure(self):
		# white_box test: missing def configure()
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def set_options(opt):
	pass
"""
		self._write_wscript(wscript_contents, use_dic=False)
		self._setup_options()
		Utils.set_main_module(self._wscript_file_path)
		self.failUnlessRaises(Utils.WscriptError, Scripting.configure)

	def test_attr_err_in_configure(self):
		# white_box test: configure raised AttributeError - don't raise WafError becasue of that
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	raise AttributeError
"""
		self._write_wscript(wscript_contents, use_dic=False)
		self._setup_options()
		Utils.set_main_module(self._wscript_file_path)
		self.failUnlessRaises(AttributeError, Scripting.configure)

	def test_set_options_is_optional(self):
		# white_box test: set_options() is not required anymore
		self._write_wscript("\n", use_dic=False)
		opt_obj = Options.Handler()
		opt_obj.sub_options('')

	def test_attr_err_in_set_options(self):
		# white_box test: set_options raised AttributeError - don't raise WafError because of that
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def set_options(opt):
	raise AttributeError
"""
		self._write_wscript(wscript_contents, use_dic=False)
		opt_obj = Options.Handler()
		self.failUnlessRaises(AttributeError, opt_obj.sub_options, '.')

	def test_no_wscript_for_config(self):
		conf = Configure.ConfigurationContext()
		self.failUnlessRaises(Utils.WscriptError, conf.sub_config, non_exist_path)

	def test_no_tool_to_set_options(self):
		# white_box test: set_options raise WafError when cannot find a tool
		Options.tooldir = os.path.join(self._waf_root_dir, Test.DIRS.WAFADMIN, Test.DIRS.TOOLS)
		opt = Options.Handler()
		self.failUnlessRaises(Utils.WscriptError, opt.tool_options, 'kk', '.')

class BlackWscriptTester(WscriptErrorsTester):
	"""Black box tests for wscript errors"""
	def test_missing_build_def(self):
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	 conf.check_tool('compiler_cxx')

def set_options(opt):
	opt.tool_options('compiler_cxx')
"""
		wscript_file_path = os.path.join(self._test_dir_root, WSCRIPT_FILE)
		try:
			wscript_file = open( wscript_file_path, 'w' )
			wscript_file.write(wscript_contents)
		finally:
			if wscript_file: wscript_file.close()

		self._test_configure()
		
		# TODO: this should be white-box test - make sure the proper exception was raised
		self._test_build(False)
		#Scripting.main()

def run_tests(verbose=1):
	if verbose > 1: common_test.hide_output = False

	white_suite = unittest.TestLoader().loadTestsFromTestCase(WhiteWscriptTester)
	black_suite = unittest.TestLoader().loadTestsFromTestCase(BlackWscriptTester)
	all_tests = unittest.TestSuite((white_suite, black_suite))
	unittest.TextTestRunner(verbosity=verbose).run(all_tests)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	run_tests()
