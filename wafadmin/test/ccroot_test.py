#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Should be serve as common tester for all cc derivativers, currently:
msvc, g++, sunc++, gcc & suncc.
"""

import os, sys, shutil, tempfile
import common_test

# allow importing from wafadmin dir when ran from sub-directory 
sys.path.append(os.path.abspath(os.path.pardir))
import Params, Environment, Options
from Constants import *

wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	conf.check_tool('%(tool)s')

def build(bld):
	obj = bld.create_obj('%(objname)s', '%(build_type)s')
	obj.code = '''%(code)s'''
	obj.source = 'test.c'
	obj.target = 'hello'

def set_options(opt):
	opt.tool_options('%(tool)s')
"""

cpp_program_code = """
#include <iostream>
int main()
{
	std::cout << "hi";
	return 0;
}
"""

c_program_code = """
#include <stdio.h>
int main()
{
	printf("hi");
	return 0;
}
"""

lib_code = """
int getIt()
{
	return 2;
}
"""

class CcRootTester(common_test.CommonTester):

	# utilities functions:
	
	def _populate_dictionary(self, build_type, code):
		"""
		standard template for functions below - single (write) access point to dictionary. 
		"""
		self._test_dic['build_type'] = build_type
		self._test_dic['code'] = code
		
	def _setup_cpp_program(self):
		self._populate_dictionary('program', cpp_program_code)
		self._write_files()
		
	def _setup_c_program(self):
		self._populate_dictionary('program', c_program_code)
		self._write_files()
		
	def _setup_share_lib(self):
		self._populate_dictionary('shlib', lib_code)
		self._write_files()
	
	def _setup_static_lib(self):
		self._populate_dictionary('staticlib', lib_code)
		self._write_files()
	
	def _setup_cpp_objects(self):
		self._populate_dictionary('objects', cpp_program_code)
		self._write_files()
		
	def _setup_c_objects(self):
		self._populate_dictionary('objects', c_program_code)
		self._write_files()

	def _setup_lib_objects(self):
		self._populate_dictionary('objects', lib_code)
		self._write_files()
		
	def __write_wscript(self):
		wscript_file_path = os.path.join(self._test_dir_root, WSCRIPT_FILE)
		try:
			wscript_file = open( wscript_file_path, 'w' )
			wscript_file.write( wscript_contents % self._test_dic )
		finally:
			wscript_file.close()
			
	def __write_source(self):
		try:
			source_file = open( self._source_file_path, 'w' )
			source_file.write( self._test_dic['code'] )
		finally:
			source_file.close()
			
	def _write_files(self):
		self.__write_wscript()
		self.__write_source()
		
	def _same_env(self, expected_env, env_name='default'):
		"""
		All parameters decided upon configure are written to cache, then read on build. 
		This function checks that the written environment has the same values for keys given by expected_env
		@param expected_env [dictionary]: a dictionary that contains
					one or more key-value pairs to compare to stored environment
		@return: True if values the same,
				False otherwise
		"""
		if expected_env is None or not expected_env:
			raise ValueError("env must contains at least one key-value pair")
		else:
#			# Environment uses arguments defined by Options 
			opt_obj = Options.Handler()
			opt_obj.parse_args()
			
			stored_env = Environment.Environment()
			stored_env_path = os.path.join(self._blddir, CACHE_DIR, env_name+CACHE_SUFFIX)
			stored_env.load( stored_env_path )
			for key in expected_env:
				self.assertEqual( stored_env[key], expected_env[key], 
								"values of '%s' differ: expected = '%s', stored = '%s'" 
								% (key,expected_env[key], stored_env[key]))
	
	def __init__(self, methodName):
		common_test.CommonTester.__init__(self, methodName)

	def setUp(self):

		# populate specific tool's dictionary
		self._test_dic = {}
		try:		
			self._test_dic['tool'] = self.tool_name
			self._test_dic['objname'] = self.object_name
		except AttributeError:
			Params.fatal("Testers that inherited ccroot have to define 'self.tool_name' and 'self.object_name'")

		# define & create temporary testing directpries
		self._test_dir_root = tempfile.mkdtemp("", ".waf-testing_")
		self._srcdir = self._test_dir_root
		self._blddir = os.path.join( self._test_dir_root, "build" )
		self._source_file_path = os.path.join(self._srcdir, "test.c")
		os.chdir(self._test_dir_root)

	def test_common_object(self):
		# simple default cpp object of library
		self._setup_lib_objects()
		self._test_configure()
		self._test_build()

	def test_share_lib(self):
		# simple default share lib
		self._setup_share_lib()
		self._test_configure()
		self._test_build()

	def test_static_lib(self):
		# simple default static lib
		self._setup_static_lib()
		self._test_configure()
		self._test_build()
		
	def test_invalid_debug_level1(self):
		# make sure it fails on invalid option
		self._setup_c_program()
		self._test_configure( False, ["--debug-level=kuku"])

	def test_invalid_debug_level2(self):
		# make sure it fails on invalid option (only lower 'debug' works now
		self._setup_c_program()
		self._test_configure( False, ["--debug-level=DEBUG"])
		
	def tearDown(self):
		'''tearDown - deletes the directories and files created by the tests ran '''
		if os.path.isdir(self._test_dir_root):
			shutil.rmtree(self._test_dir_root)
			
		os.chdir(self._waf_root_dir)