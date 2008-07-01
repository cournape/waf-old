#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Should be serve as common tester for all cc derivativers, currently:
msvc, g++, sunc++, gcc & suncc.
"""

import os, sys, shutil, tempfile, logging
import common_test

# allow importing from wafadmin dir.
sys.path.append(os.path.abspath(os.path.pardir))
from Constants import *

# The following string is a wscript for tests.
# Note the embedded strings that changed by self._test_dic: set_env, tool, objname, build_type
wscript_contents = """
blddir = 'build'
srcdir = '.'

def configure(conf):
	%(set_env)s
	conf.check_tool('%(tool)s')

def build(bld):
	obj = bld.new_task_gen('%(objname)s', '%(build_type)s')
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
	
	def _populate_dictionary(self, build_type, code, set_env='pass'):
		"""
		standard template for functions below - single (write) access point to dictionary. 
		"""
		self._test_dic['build_type'] 	= build_type
		self._test_dic['code'] 			= code
		self._test_dic['set_env'] 		= set_env
		
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
		
	def _setup_cpp_program_with_env(self, env_line):
		self._populate_dictionary('program', cpp_program_code, env_line)
		self._write_files()
		
	def _setup_c_program_with_env(self, env_line):
		self._populate_dictionary('program', c_program_code, env_line)
		self._write_files()

	def _write_wscript(self, contents = '', use_dic=True):
		wscript_file_path = os.path.join(self._test_dir_root, WSCRIPT_FILE)
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

	def _write_source(self):
		try:
			source_file = open( self._source_file_path, 'w' )
			source_file.write( self._test_dic['code'] )
		finally:
			source_file.close()
			
	def _write_files(self):
		self._write_wscript()
		self._write_source()

	def __init__(self, methodName):
		common_test.CommonTester.__init__(self, methodName)

	def setUp(self):

		# populate specific tool's dictionary
		self._test_dic = {}
		try:		
			self._test_dic['tool'] = self.tool_name
			self._test_dic['objname'] = self.object_name
		except AttributeError:
			logging.fatal("Testers that inherited ccroot have to define 'self.tool_name' and 'self.object_name'")

		# define & create temporary testing directories
		self._test_dir_root = tempfile.mkdtemp("", ".waf-testing_")
		self._srcdir = self._test_dir_root
		self._blddir = os.path.join( self._test_dir_root, "build" )
		self._source_file_path = os.path.join(self._srcdir, "test.c")
		self._wscript_file_path = os.path.join(self._test_dir_root, WSCRIPT_FILE)
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
#
#	--debug-level is unused option now...		   
#				
#	def test_invalid_debug_level1(self):
#		# make sure it fails on invalid option
#		self._setup_c_program()
#		self._test_configure( False, ["--debug-level=kuku"])
#
#	def test_invalid_debug_level2(self):
#		# make sure it fails on invalid option (only lower 'debug' works now
#		self._setup_c_program()
#		self._test_configure( False, ["--debug-level=DEBUG"])
		
	def tearDown(self):
		'''tearDown - deletes the directories and files created by the tests ran '''
		os.chdir(self._waf_root_dir)
		
		if os.path.isdir(self._test_dir_root):
			shutil.rmtree(self._test_dir_root)
