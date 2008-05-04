#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Tests Configure.py
"""

# TODO: most of Configure functions and features are not tested here yet...

import os, sys, unittest, shutil, tempfile
import common_test

# allow importing from wafadmin dir when ran from sub-directory 
sys.path.append(os.path.abspath(os.path.pardir))

from Constants import *
import Options
import Configure

# The following string is a wscript for tests.
# Note the embedded string that changed by more_config
wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	conf.check_tool('g++')
	%(more_config)s

def build(bld):
	obj = bld.create_obj('cpp', 'program')
	obj.source = 'test.cpp'
	obj.target = 'test'

def set_options(opt):
	opt.tool_options('g++')
"""

cpp_program_code = """
int main()
{
	return 0;
}
"""

class ConfigureTester(common_test.CommonTester):
	def __init__(self, methodName):
		common_test.CommonTester.__init__(self, methodName)
		self._test_dic = {}
		self._blddir = 'build' # has to be the same as in wscript above

	def setUp(self):
		# define & create temporary testing directories
		self._test_dir_root = tempfile.mkdtemp("", ".waf-testing_")
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

	def _write_wscript(self):
		wscript_file_path = os.path.join(self._test_dir_root, WSCRIPT_FILE)
		try:
			wscript_file = open( wscript_file_path, 'w' )
			wscript_file.write( wscript_contents % self._test_dic )
		finally:
			wscript_file.close()

	def _write_source(self):
		try:
			source_file = open( self._source_file_path, 'w' )
			source_file.write( cpp_program_code )
		finally:
			source_file.close()

	def _write_files(self):
		self._write_wscript()
		self._write_source()
		
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
		self.assert_( com_conf.run(), "directory was not returned." )

	def test_common_include4(self):
		# white-box test: make sure it returns False/empty string for non-exist header
		conf = self._setup_configure()
		com_conf = conf.create_common_include_configurator()
		com_conf.name = 'kukukukukuk.h'
		self.failIf(com_conf.run(), "directory was returned for non-exist header." )

def run_tests(verbose=2):
	suite = unittest.TestLoader().loadTestsFromTestCase(ConfigureTester)
	# use the next line to run only specific tests: 
#	suite = unittest.TestLoader().loadTestsFromNames(["test_common_include2"], ConfigureTester)
	unittest.TextTestRunner(verbosity=verbose).run(suite)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	os.chdir(os.path.pardir)
	run_tests()