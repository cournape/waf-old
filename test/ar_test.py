#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2009

# Python built-in modules
import os, sys, unittest, tempfile, shutil

# This will allow to import Waf modules
import common_test

# Waf modules
import Constants

wscript_contents = """
blddir = 'build'
srcdir = '.'

def build(bld):
	# no taskgen with such name...
	obj = bld.new_task_gen('cxx', 'staticlib', source='%(sources)s', target='dummy')

def configure(conf):
	conf.check_tool('g++')
"""

class ArTester(common_test.CommonTester):
	def __init__(self, methodName):
		common_test.CommonTester.__init__(self, methodName)
		# populate specific tool's dictionary
		self._test_dic = {}

	def setUp(self):
		# define & create temporary testing directories
		self._test_dir_root = tempfile.mkdtemp("", ".waf-testing_")
		os.chdir(self._test_dir_root)
		self._wscript_file_path = os.path.join(self._test_dir_root, Constants.WSCRIPT_FILE)


	def tearDown(self):
		'''tearDown - deletes the directories and files created by the tests ran '''
		os.chdir(self._waf_root_dir)

		if os.path.isdir(self._test_dir_root):
			shutil.rmtree(self._test_dir_root)

	def test_old_file_get_removed_from_static_lib(self):
		# will work on POSIX only...
		lib_path = os.path.join(self._test_dir_root, 'build', 'default', 'libdummy.a')

		# black_box test: removing old object files from archive
		# (actually: deletes the archive...)
		self._write_file('babu.cpp', 'int x=1;\n')
		self._write_file('dada.cpp', 'int y=2;\n')
		self._test_dic['sources'] = 'babu.cpp dada.cpp'
		self._write_wscript(wscript_contents)
		self._test_configure()

		# first build - both object files should be in the archive
		stdout = self._build_and_ar(lib_path)
		self.assert_(stdout.split() == ['babu_1.o', 'dada_1.o'], "object files were not found in archive")

		# second build - after removing one of the source files,
		# its object file should NOT be in the archive.
		self._test_dic['sources'] = 'babu.cpp'
		self._write_wscript(wscript_contents)
		stdout = self._build_and_ar(lib_path)
		self.assert_(stdout.split() == ['babu_1.o'], "missing/redundant object in archive")

	def _build_and_ar(self, lib_path):
		self._test_build()
		(ret, stdout, stderr) = self.call(['ar', 't', '%s' % lib_path])
		self.assert_(ret == 0, "'ar t' fails... (%s)" % stderr)
		return stdout

def run_tests(verbose=1):
	try:
		suite = unittest.TestLoader().loadTestsFromTestCase(ArTester)
		# use the next line to run only specific tests:
#		suite = unittest.TestLoader().loadTestsFromName("test_simple_program", CxxTester)
		return unittest.TextTestRunner(verbosity=verbose).run(suite)
	except common_test.StartupError, e:
		Logs.error(e)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	options = common_test.get_args_options()
	run_tests(options.verbose)
