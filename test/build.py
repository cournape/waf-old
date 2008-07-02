#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Tests building...
"""

import os, unittest, shutil, tempfile
import common_test

from Constants import *
import Options
import Utils
import Scripting
import Build
import Configure

class BuildTester(common_test.CommonTester):
	def __init__(self, methodName):
		common_test.CommonTester.__init__(self, methodName)

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

	def test_build_fails_on_cpp_syntax_err(self):
		# black-box test: error on build failure due to syntax error
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def build(bld):
	obj = bld.new_task_gen('cxx', 'program')
	obj.source = '%s'
	obj.name = 'kuku'

def configure(conf):
	conf.check_tool('g++')

def set_options(opt):
	pass
""" % self._source_file_path

		self._write_wscript(wscript_contents)
		
		# error in source file...
		self._write_source("int main() {fafwefwefgwe}")
		self._test_configure()
		
		# test that BuildError was raised
		self._test_build(False)
		
def run_tests(verbose=1):
	if verbose > 1: common_test.hide_output = False

	suite = unittest.TestLoader().loadTestsFromTestCase(BuildTester)
	unittest.TextTestRunner(verbosity=verbose).run(suite)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	run_tests()
