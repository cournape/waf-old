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
blddir = '%(build)s'
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
		self._blddir = 'build'
		self._test_dic['build'] = self._blddir

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
		Options.options.prefix = Options.default_prefix
		return Configure.ConfigurationContext()

	def load_env(self, cache_file=''):
		if not cache_file:
			cache_file = os.path.join( self._blddir,  'c4che', 'default.cache.py' )
		return Environment.Environment(cache_file)

	def test_simple_configure(self):
		# regular configuration
		self._populate_dictionary('pass')
		self._write_files()
		self._test_configure()

	def test_config_header(self):
		# simple config header is written
		self._populate_dictionary( \
		"""conf.define('KUKU', 'riku')
	conf.write_config_header()""" )
		self._write_files()
		self._test_configure()
		config_file = os.path.join( self._blddir, 'default', 'config.h' )
		config_content = open( config_file ).readlines()
		self.assert_( "".join(config_content).find("""#define KUKU""") > 1, "missing DEFINE in the config header")

	def test_renamed_config_header(self):
		# renamed config header works too
		self._populate_dictionary( \
		"""conf.define('KUKU', 'riku')
	conf.write_config_header('blabla.h')""" )
		self._write_files()
		self._test_configure()
		config_file = os.path.join( self._blddir, 'default', 'blabla.h' )
		config_content = open( config_file ).readlines()
		self.assert_( "".join(config_content).find("""#define KUKU""") > 1, "missing DEFINE in the config header")

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

	def test_library_configurator(self):
		# black-box test: configurates a library
		self._populate_dictionary("""conf.check_cc(lib='z', mandatory=1)""")
		self._write_files()
		self._test_configure()

		env = self.load_env()
		self.assert_(env['LIB_Z']==['z'], "it seems that libz was not configured properly, run waf check -vv to see the exact error...")

	def test_invalid_flag(self):
		# black-box test: invalid flag
		self._populate_dictionary("""conf.check_cc(msg="checking for flag='blah'", ccflags='blah', mandatory=1)""")
		self._write_files()
		self._test_configure(False)

	def test_configure_header(self):
		# black-box test: finds a header file
		self._populate_dictionary("""conf.check_cc(header_name='time.h', mandatory=1)""")
		self._write_files()
		self._test_configure()

	def test_configure_header_specific_path(self):
		# black-box test: finds non-standard header file in specific path
		header_file = open('no_way_such_header_exists4141.h', 'w')
		header_file.close()
		self._populate_dictionary("""conf.check_cc(header_name='no_way_such_header_exists4141.h', includes=['%s'], mandatory=1)""" % os.getcwd())
		self._write_files()
		self._test_configure()

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
		# black-box + white-box test: configurates a library
		self._populate_dictionary("""conf.check_cxx(lib='z', mandatory=1)""")
		self._write_files()
		self._test_configure()

		env = self.load_env()
		self.assert_(env['LIB_Z']==['z'], "it seems that libz was not configured properly, run waf check -vv to see the exact error...")

	def test_remove_libpath_trailing_slash(self):
		# black-box test: removes trailing slash from LIBPATH variables
		self._populate_dictionary("""conf.check_cxx(lib='z', mandatory=1, libpath='/usr/lib/')""")
		self._write_files()
		self._test_configure()

		env = self.load_env()
		self.assert_(env['LIBPATH_Z']==['/usr/lib'], "it seems that libz was not configured properly, or the trailing slash was not removed. run waf check -vv to see the exact error...")

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
"""
		self._write_wscript(wscript_contents, use_dic=False)
		opt_obj = Options.Handler()
		opt_obj.parse_args()
		Options.options.prefix = Options.default_prefix
		Utils.set_main_module(self._wscript_file_path)
		conf = Configure.ConfigurationContext()
		self.failUnlessRaises(Utils.WscriptError, Scripting.configure, conf)

	def test_invalid_tool(self):
		# white_box test: tool not exists
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	conf.check_tool('no_way_such_a_tool_exists_gwerghergjekrhgker')
"""
		self._write_wscript(wscript_contents, use_dic=False)
		opt_obj = Options.Handler()
		opt_obj.parse_args()
		Options.options.prefix = Options.default_prefix
		Utils.set_main_module(self._wscript_file_path)
		conf = Configure.ConfigurationContext()
		self.failUnlessRaises(Utils.WscriptError, Scripting.configure, conf)

	def test_nothing_to_store(self):
		# white-box test: fails if all_envs are not defined.
		conf = self._setup_configure()
		conf.all_envs = None
		self.failUnlessRaises(Configure.ConfigurationError, conf.store)

	def test_configure_header(self):
		# black-box test: finds a header file
		self._populate_dictionary("""conf.check_cxx(header_name='time.h', mandatory=1)""")
		self._write_files()
		self._test_configure()

	def test_configure_header_specific_path(self):
		# black-box test: finds non-standard header file in specific path
		header_file = open('no_way_such_header_exists4141.h', 'w')
		header_file.close()
		self._populate_dictionary("""conf.check_cxx(header_name='no_way_such_header_exists4141.h', includes=['%s'], mandatory=1)""" % os.getcwd())
		self._write_files()
		self._test_configure()

def run_tests(verbose=1):
	cc_suite = unittest.TestLoader().loadTestsFromTestCase(CcConfigureTester)
	cpp_suite = unittest.TestLoader().loadTestsFromTestCase(CxxConfigureTester)
	all_tests = unittest.TestSuite((cc_suite, cpp_suite))
	return unittest.TextTestRunner(verbosity=verbose).run(all_tests)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	options = common_test.get_args_options()
	run_tests(options.verbose)
