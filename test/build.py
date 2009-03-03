#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Tests building...
"""

import os, unittest, shutil, tempfile
import common_test

from Constants import *
import Utils
import Build
import Options

class BuildTester(common_test.CommonTester):
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

	def test_build_fails_on_cpp_syntax_err(self):
		# black-box test: error on build failure due to syntax error
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def build(bld):
	obj = bld.new_task_gen('cxx', 'program')
	obj.source = '%s'
	obj.target = 'kuku'

def configure(conf):
	conf.check_tool('g++')
""" % self._source_file_path

		self._write_wscript(wscript_contents)

		# error in source file...
		self._write_source("int main() {fafwefwefgwe}")
		self._test_configure()

		# test that BuildError was raised
		self._test_build(False)

	def test_white_build_fails_blddir_is_srcdir(self):
		# white-box test: build fail if blddir == srcdir
		bld = Build.BuildContext()
		self.failUnlessRaises(Utils.WafError, bld.load_dirs, self._test_dir_root, self._test_dir_root)

	def test_incorrect_version(self):
		# white-box test: configured with old version
		Options.commands['configure'] = False

		bld = Build.BuildContext()
		bld.blddir = os.path.join(self._test_dir_root, 'b')

		# this will create the cachedir...
		self.failUnlessRaises(Utils.WafError, bld.load_dirs, bld.blddir, bld.blddir)
		os.makedirs(bld.cachedir)

		# create build cache file with OLD version
		cachefile = os.path.join(bld.cachedir, 'build.config.py')
		file = open(cachefile, 'w')
		file.writelines("version = 0.0")
		file.close()

		self.failUnlessRaises(Utils.WafError, bld.load)

	def test_black_build_fails_blddir_is_srcdir(self):
		# black-box test: build fail if blddir == srcdir
		my_wscript = """
blddir = srcdir = '.'
def configure(conf):
	pass

def build(bld):
	pass
"""
		self._write_wscript(my_wscript)
		self._test_configure()
		self._test_build(False)

	def test_rescan_fails_file_not_readable(self):
		# black-box test: rescan fails if file is not readable
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def build(bld):
	obj = bld.new_task_gen('cxx', 'program')
	obj.target = 'kuku'
	obj.find_sources_in_dirs('.')

def configure(conf):
	conf.check_tool('g++')
"""

		self._write_wscript(wscript_contents)
		self._write_source("int main() {return 0;}")

		self._test_configure()
		self._test_build()
		os.remove(self._source_file_path)
		os.makedirs(self._source_file_path)
		self._test_build(False)

	def test_target_not_found(self):
		# black-box test: fails if target not found
		wscript_contents = """
blddir = 'build'
srcdir = '.'

def build(bld):
	obj = bld.new_task_gen('cxx')
	obj.name = 'hh'
	obj.source = '%s'
	obj.uselib_local = 'ff'

def configure(conf):
	conf.check_tool('g++')
"""  % self._source_file_path

		self._write_wscript(wscript_contents)
		self._write_source("int main() {return 0;}")
		self._test_configure()
		self._test_build(False)

def run_tests(verbose=1):
	if verbose > 1: common_test.hide_output = False

	suite = unittest.TestLoader().loadTestsFromTestCase(BuildTester)
	unittest.TextTestRunner(verbosity=verbose).run(suite)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	run_tests(2)
