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
import Tools.checks 	# to make compile_configurator function work
import Utils
import Scripting
import Build

# The following string is a wscript for tests.
# Note the embedded string that changed by more_config
wscript_contents = """
import Logs
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
		self._test_dic['more_config'] 	= more_config
		self._test_dic['tool'] 	= self._tool_name

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
		return Configure.Configure()

	def test_simple_configure(self):
		# regular configuration
		self._populate_dictionary('pass')
		self._write_files()
		self._test_configure()

	def test_common_include1(self):
		# black-box test: makes sure that a header is added to COMMON_INLCUDES
		self._populate_dictionary("""com_conf = conf.create_common_include_configurator()
	com_conf.name = 'stdio.h'
	com_conf.run()""")
		self._write_files()
		self._test_configure()
		self._same_env(dict(COMMON_INCLUDES=['/usr/include/stdio.h']))

	def test_common_include2(self):
		# black-box test: makes sure that a header is written to config.h
		self._populate_dictionary("""com_conf = conf.create_common_include_configurator()
	com_conf.name = 'stdio.h'
	com_conf.run()
	conf.write_config_header()""")
		self._write_files()
		self._test_configure()
		config_file = open('build/default/config.h', 'r')
		config_file_content = config_file.read()
		self.assert_(config_file_content.find('#include "/usr/include/stdio.h"') > -1 )

	def test_common_include3(self):
		# white-box test: make sure it finds standard includes
		conf = self._setup_configure()
		com_conf = conf.create_common_include_configurator()
		com_conf.name = 'stdio.h'
		com_conf.want_message = False
		self.assert_( com_conf.run(), "directory was not returned." )

	def test_common_include4(self):
		# white-box test: make sure it returns False/empty string for non-exist header
		conf = self._setup_configure()
		com_conf = conf.create_common_include_configurator()
		com_conf.name = 'kukukukukuk.h'
		com_conf.want_message = False
		self.failIf(com_conf.run(), "directory was returned for non-exist header." )
		
class CcConfigureTester(ConfigureTester):
	def __init__(self, methodName):
		self._tool_name = 'compiler_cc'
		self._object_type = 'cc'
		ConfigureTester.__init__(self, methodName)

	def test_valid_flag(self):
		# black-box test: valid flag
		self._populate_dictionary("""conf.check_tool('checks')
	if not conf.check_flags('-Werror'):
		Logs.fatal("invalid flag")
		""")
		self._write_files()
		self._test_configure()

	def test_invalid_flag(self):
		# black-box test: invalid flag
		self._populate_dictionary("""conf.check_tool('checks')
	if not conf.check_flags('KUKU'):
		Logs.fatal("invalid flag")
		""")
		self._write_files()
		self._test_configure(False)

class CxxConfigureTester(ConfigureTester):
	def __init__(self, methodName):
		self._tool_name = 'compiler_cxx'
		self._object_type = 'cxx'
		ConfigureTester.__init__(self, methodName)

	def test_valid_flag(self):
		# black-box test: valid flag
		self._populate_dictionary("""conf.check_tool('checks')
	if not conf.check_flags('-Werror', kind='cxx'):
		Logs.fatal("invalid flag")
		""")
		self._write_files()
		self._test_configure()

	def test_invalid_flag(self):
		# black-box test: invalid flag
		self._populate_dictionary("""conf.check_tool('checks')
	if not conf.check_flags('KUKU', kind='cxx'):
		Logs.fatal("invalid flag")
		""")
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
		
	def test_missing_test_conf_code(self):
		conf = self._setup_configure()
		com_conf = conf.create_test_configurator()
		self.failUnlessRaises(Configure.ConfigurationError, com_conf.run)

	def test_missing_compile_conf_code(self):
		conf = self._setup_configure()
		com_conf = conf.create_compile_configurator()
		self.failUnlessRaises(Configure.ConfigurationError, com_conf.run)

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
