#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Tests task generator...
"""

import os, unittest, shutil, tempfile
import common_test

from Constants import *
import Build
import Options
import Environment
import TaskGen
import Utils

class TaskGenTester(common_test.CommonTester):
	def __init__(self, methodName):
		common_test.CommonTester.__init__(self, methodName)

	def setUp(self):
		# define & create temporary testing directories
		self._test_dir_root = tempfile.mkdtemp("", ".waf-testing_")
		self._wscript_file_path = os.path.join(self._test_dir_root, WSCRIPT_FILE)
		self._source_file_path = "test.cpp"
		os.chdir(self._test_dir_root)

	def tearDown(self):
		'''tearDown - deletes the directories and files created by the tests ran '''
		os.chdir(self._waf_root_dir)
		
		if os.path.isdir(self._test_dir_root):
			shutil.rmtree(self._test_dir_root)

	def _write_wscript(self, contents):
		self._write_file(self._wscript_file_path, contents)

	def _write_source(self, contents):
		self._write_file(self._source_file_path, contents)

	def _write_file(self, file_path, contents):
		try:
			wscript_file = open(file_path, 'w')
			wscript_file.write(contents)
		finally:
			wscript_file.close()

	def test_black_no_sources_specified(self):
		# black-box test: fails if source not specified
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def build(bld):
	obj = bld.new_task_gen('cxx')
	obj.name = 'fsfgws'

def configure(conf):
	conf.check_tool('g++')

def set_options(opt):
	pass
""" 

		self._write_wscript(wscript_contents)

		self._test_configure()
		self._test_build(False)

	def test_white_no_sources_specified(self):
		# white-box test: no sources were specified
		Options.commands['configure'] = False
		env = Environment.Environment()		
		bld = Build.bld = Build.Build()
		bld.set_env('default', env)
		blddir = os.path.join(self._test_dir_root, 'b')
		bld.load_dirs(self._test_dir_root, blddir)
		
		obj = TaskGen.task_gen()
		self.failUnlessRaises(Utils.WafError, obj.apply_core)

	def test_source_not_found(self):
		# black-box test: fails if source not found
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def build(bld):
	obj = bld.new_task_gen('cxx')
	obj.name = 'hh'
	obj.source = 'fwefwe.cpp'

def configure(conf):
	conf.check_tool('g++')

def set_options(opt):
	pass
""" 

		self._write_wscript(wscript_contents)

		self._test_configure()
		self._test_build(False)
		
	def make_bld(self):
		Options.commands['configure'] = False
		env = Environment.Environment()		
		bld = Build.bld = Build.Build()
		bld.set_env('default', env)
		blddir = os.path.join(self._test_dir_root, 'b')
		bld.load_dirs(self._test_dir_root, blddir)

	def test_missing_mapping(self):
		# no mapping for extension
		self.make_bld()
		obj = TaskGen.task_gen()
		obj.source = self._source_file_path
		self._write_source("int main() {return 0;}")
		self.failUnlessRaises(Utils.WafError, obj.apply_core)

	def test_validate_find_srcs_excs(self):
		# find sources in dirs 'excludes' must be a list
		self.make_bld()
		obj = TaskGen.task_gen()
		self.failUnlessRaises(Utils.WafError, obj.find_sources_in_dirs, 'a', 'excludes=b')

	def test_validate_find_srcs_exts(self):
		# find sources in dirs 'exts' must be a list
		self.make_bld()
		obj = TaskGen.task_gen()
		self.failUnlessRaises(Utils.WafError, obj.find_sources_in_dirs, 'a', 'exts=b')

	def test_validate_find_srcs_absolute(self):
		# find sources in dirs cannot get absoulte paths
		self.make_bld()
		obj = TaskGen.task_gen()
		self.failUnlessRaises(Utils.WafError, obj.find_sources_in_dirs, self._test_dir_root)

	def test_validate_extension_decorator(self):
		self.failUnlessRaises(Utils.WafError, TaskGen.extension, 1)

	def test_validate_declare_extension(self):
		self.failUnlessRaises(Utils.WafError, TaskGen.declare_extension, 1, None)

def run_tests(verbose=1):
	if verbose > 1: common_test.hide_output = False

	suite = unittest.TestLoader().loadTestsFromTestCase(TaskGenTester)
	unittest.TextTestRunner(verbosity=verbose).run(suite)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	run_tests(2)
