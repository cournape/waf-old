#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Tests Configure.py
"""

# TODO: most of Configure functions and features are not tested here yet...

import os, unittest, shutil, tempfile
import common_test

from Constants import *
import Options
import Configure
import Tools.config_c   # to make conf.create_* functions work
import Utils
import Scripting
import Build

# import the Environment module, set configure command to False to avoid setting the prefix too...
Options.commands['configure'] = 0
import Environment

# The following string is a wscript for tests.
# Note the embedded string that changed by more_config
wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	conf.check_tool('%(tool)s')
	%(more_config)s

def set_options(opt):
	opt.tool_options('%(tool)s')
"""

class ConfigureTester(common_test.CommonTester):
	def __init__(self, methodName):
		common_test.CommonTester.__init__(self, methodName)
		self._test_dic = {}
		self._blddir = 'build' # has to be the same as in wscript above

	def setUp(self):
		# define & create temporary testing directories
		self._test_dir_root = tempfile.mkdtemp("", ".waf-testing_")
		self._wscript_file_path = os.path.join(self._test_dir_root, WSCRIPT_FILE)
		self._source_file_path = os.path.join(self._test_dir_root, "test.cpp")
		os.chdir(self._test_dir_root)

	def tearDown(self):
		'''tearDown - deletes the directories and files created by the tests ran '''
		os.chdir(self._waf_root_dir)

		if os.path.isdir(self._test_dir_root):
			shutil.rmtree(self._test_dir_root)

	def _populate_dictionary(self, more_config):
		"""
		standard template for functions below - single (write) access point to dictionary.
		"""
		self._test_dic['more_config']	= more_config
		self._test_dic['tool']	= self._tool_name

	def _write_wscript(self, contents = '', use_dic=True):
		wscript_file_path = self._wscript_file_path
		try:
			wscript_file = open( wscript_file_path, 'w' )
			if contents:
				if use_dic:
					wscript_file.write( contents % self._test_dic )
				else:
					wscript_file.write(contents)
			else:
				wscript_file.write( wscript_contents % self._test_dic )
		finally:
			wscript_file.close()

	def _write_files(self):
		self._write_wscript()

	def _setup_configure(self):
		# Configure uses arguments defined by Options
		opt_obj = Options.Handler()
		opt_obj.parse_args()
		return Configure.ConfigurationContext()

	def test_simple_configure(self):
		# regular configuration
		self._populate_dictionary('pass')
		self._write_files()
		self._test_configure()

class CcConfigureTester(ConfigureTester):
	def __init__(self, methodName):
		self._tool_name = 'compiler_cc'
		self._object_type = 'cc'
		ConfigureTester.__init__(self, methodName)

	def test_valid_flag(self):
		# black-box test: valid flag
		self._populate_dictionary("""conf.check_cc(msg="checking for flag='-Werror'", ccflags='-Werror', mandatory=1)""")
		self._write_files()
		self._test_configure()

	def test_invalid_flag(self):
		# black-box test: invalid flag
		self._populate_dictionary("""conf.check_cc(msg="checking for flag='blah'", ccflags='blah', mandatory=1)""")
		self._write_files()
		self._test_configure(False)

class CxxConfigureTester(ConfigureTester):
	def __init__(self, methodName):
		self._tool_name = 'compiler_cxx'
		self._object_type = 'cxx'
		ConfigureTester.__init__(self, methodName)

	def test_valid_flag(self):
		# black-box test: valid flag
		self._populate_dictionary("""conf.check_cxx(msg="checking for flag='-ansi'", cxxflags='-ansi', mandatory=1)""")
		self._write_files()
		self._test_configure()

	def test_library_configurator(self):
		# black-box test: configurates a library
		self._populate_dictionary("""conf.check_cxx(lib='z', mandatory=1)""")
		self._write_files()
		self._test_configure()
		
		env = Environment.Environment('build/c4che/default.cache.py')
		self.assert_(env['LIB_Z']==['z'], "it seems that libz was not configured properly, run waf check -vv to see the exact error...")

	def test_invalid_flag(self):
		# black-box test: invalid flag
		self._populate_dictionary("""conf.check_cxx(msg="checking for flag='gkerwvgew'", cxxflags='gkerwvgew', mandatory=1)""")
		self._write_files()
		self._test_configure(False)

	def test_cxx_is_missing(self):
		# white_box test: 'compiler_cxx' options are essential for its configuration
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	conf.check_tool('compiler_cxx')

def set_options(opt):
	pass
"""
		self._write_wscript(wscript_contents, use_dic=False)
		opt_obj = Options.Handler()
		opt_obj.parse_args()
		Utils.set_main_module(self._wscript_file_path)
		self.failUnlessRaises(Configure.ConfigurationError, Scripting.configure)

	def test_invalid_tool(self):
		# white_box test: tool not exists
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	conf.check_tool('no_way_such_a_tool_exists_gwerghergjekrhgker')

def set_options(opt):
	pass
"""
		self._write_wscript(wscript_contents, use_dic=False)
		opt_obj = Options.Handler()
		opt_obj.parse_args()
		Utils.set_main_module(self._wscript_file_path)
		self.failUnlessRaises(Configure.ConfigurationError, Scripting.configure)

	def test_nothing_to_store(self):
		# white-box test: fails if all_envs are not defined.
		conf = self._setup_configure()
		conf.all_envs = None
		self.failUnlessRaises(Configure.ConfigurationError, conf.store)

def run_tests(verbose=1):
	if verbose > 1: common_test.hide_output = False

	cc_suite = unittest.TestLoader().loadTestsFromTestCase(CcConfigureTester)
	cpp_suite = unittest.TestLoader().loadTestsFromTestCase(CxxConfigureTester)
	all_tests = unittest.TestSuite((cc_suite, cpp_suite))
	unittest.TextTestRunner(verbosity=verbose).run(all_tests)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	run_tests()
