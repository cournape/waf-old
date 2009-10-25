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

	def _write_source(self, contents):
		self._write_file(self._source_file_path, contents)

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

		self._write_wscript(wscript_contents, 0)

		# error in source file...
		self._write_source("int main() {fafwefwefgwe}")
		self._test_configure()

		# test that BuildError was raised
		self._test_build(False)

	def test_white_build_fails_blddir_is_srcdir(self):
		# white-box test: build fail if blddir == srcdir
		bld = Build.BuildContext()
		blddir = os.path.join(self._test_dir_root, 'blddir')
		self.failUnlessRaises(Utils.WafError, bld.load_dirs, blddir, blddir)

	def test_incorrect_version(self):
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

	def test_black_configure_fails_blddir_is_srcdir(self):
		# black-box test: configure fail if blddir == '.'
		my_wscript = """
blddir = srcdir = '.'
def configure(conf):
	pass

def build(bld):
	pass
"""
		self._write_wscript(my_wscript, 0)
		self._test_configure(False)

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

		self._write_wscript(wscript_contents, 0)
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

		self._write_wscript(wscript_contents, 0)
		self._write_source("int main() {return 0;}")
		self._test_configure()
		self._test_build(False)

	def test_rebuild_after_removing_dir(self):
		# black-box test: waf should not fail if a directory was removed -
		# both from file system and from previous call to add_subdirs

		# dirs & files in toy_project:
		# .
		#      main.cpp
		#      paper
		#           paper.cpp
		#      stone
		#           stone.cpp
		main_wscript = '''
blddir = 'build'
srcdir = '.'

def configure(conf):
	conf.check_tool('g++')

def build(bld):
	bld.new_task_gen('cxx', 'program', source='main.cpp', target='app')
	bld.add_subdirs(%s)
'''
		self._create_source_dir('stone paper')
		self._write_file('main.cpp', 'int main() {return 0;}\n')
		self._write_wscript(main_wscript % "'stone paper'", 0)
		self._test_configure()
		self._test_build()
		# 1st rebuild is OK
		self._test_build()

		# delete stone from filesystem and wscript
		self._write_wscript(main_wscript % "'paper'", 0)
		shutil.rmtree('stone')

		# rewrite paper, without the '#include stone'
		self._create_source_dir('paper', add_includes=False)
		# rebuild again - this build should NOT fail !
		self._test_build()

	def _create_source_dir(self, names, add_includes=True):
		# for each name in names,
		# will create a source dir named 'name' with:
		# 'name.cpp', 'name.h' and wscript.
		# The cpp wil #include all headers of other 'names'.
		names = Utils.to_list(names)
		for name in names:
			Utils.check_dir(name)
			includes = ''
			if add_includes and len(names) > 1:
				for other_name in [f for f in names if f != name]:
					includes += '#include "%s/%s.h"\n' % \
						(other_name, other_name)
			self._write_file(os.path.join(name, '%s.cpp'%name),
				'%sint %s() {return 1;}\n'% (includes, name))
			self._write_file(os.path.join(name, '%s.h'%name),
				'int %s();\n'% name)
			self._write_file(os.path.join(name, 'wscript_build'),
				 '''
lib = bld.new_task_gen('cxx', 'staticlib', source='%s.cpp', target='%s')
lib.includes = ['..']
''' % (name, name))

def run_tests(verbose=1):
	suite = unittest.TestLoader().loadTestsFromTestCase(BuildTester)
	return unittest.TextTestRunner(verbosity=verbose).run(suite)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	options = common_test.get_args_options()
	run_tests(options.verbose)
