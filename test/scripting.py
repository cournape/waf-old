#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Tests Scripting
"""

import os, unittest, shutil, tempfile
import tarfile
import common_test

from Constants import *
import Options
import Utils
import Scripting

class ScriptingTester(common_test.CommonTester):
	def __init__(self, methodName):
		common_test.CommonTester.__init__(self, methodName)

	def setUp(self):
		# define & create temporary testing directories
		self._test_dir_root = tempfile.mkdtemp("", ".waf-testing_")
		self._wscript_file_path = os.path.join(self._test_dir_root, WSCRIPT_FILE)
		os.chdir(self._test_dir_root)

	def tearDown(self):
		'''tearDown - deletes the directories and files created by the tests ran '''
		os.chdir(self._waf_root_dir)

		if os.path.isdir(self._test_dir_root):
			shutil.rmtree(self._test_dir_root)

	def test_reconfigure(self):
		# black-box test: reconfigure is done on build if lockfile is missing
		built_code = 'waf_waf_built'
		conf_code = 'waf_waf_configured'
		# black_box test: reconfigure when lock file is missing
		wscript_contents = """
blddir = 'build'
srcdir = '.'

import os
import Configure
Configure.autoconfig = True

def build(bld):
	open('%s', 'w')

def configure(conf):
	open('%s', 'w')
""" % (built_code, conf_code)

		self._write_wscript(wscript_contents, 0)
		self._test_configure()
		self.assert_(os.path.isfile(conf_code), "1st configure failed")
		print self._test_build()[1]
		self.assert_(os.path.isfile(built_code), "1st build failed")

		# this should cause reconfiguration.
		os.remove(Options.lockfile)

		os.remove(conf_code)
		os.remove(built_code)
		self._test_build()
		self.assert_(os.path.isfile(conf_code), "2nd configure skipped")
		self.assert_(os.path.isfile(built_code), "2nd build failed")

	def test_black_no_conf_no_clean(self):
		self._write_wscript("def set_options(opt): pass", 0)
		self._test_clean(False)

	def test_dist(self):
		# black-box test: dist works
		appname = 'waf_waf_dist_test'
		version = '30.4.5768'
		wscript_contents = """
%s = '%s'
%s = '%s'
""" % (APPNAME, appname, VERSION, version)

		self._write_wscript(wscript_contents, 0)
		self._test_dist()
		dist_file = appname+'-'+version + '.tar.' + Scripting.g_gz
		self.assert_(os.path.isfile(dist_file), "dist file doesn't exists")

	def test_user_define_dist(self):
		# black-box test: if user wrote dist() function it will be used
		wscript_contents = """
def dist():
	open('waf_waf_custom_dist.txt', 'w')
"""
		self._write_wscript(wscript_contents, 0)
		self._test_dist()
		self.assert_(os.path.isfile('waf_waf_custom_dist.txt'), "custom dist() was not used")

	def test_user_dist_hook(self):
		# black-box test: 
		# if user wrote dist_hook() function it will be used to add something to dist
		# to ease testing the function here creates a file
		wscript_contents = """
def dist_hook():
	open('waf_waf_custom_dist.txt', 'w')
"""
		self._write_wscript(wscript_contents, 0)
		self._test_dist()
		dist_file = 'noname-1.0.tar.' + Scripting.g_gz
		tar = tarfile.open(dist_file)
		self.assert_('noname-1.0/waf_waf_custom_dist.txt' in tar.getnames(), "custom dist_hook() was not used")

	def test_distcheck_fails(self):
		# black-box test: distcheck fails - missing srcdir
		self._write_wscript("def set_options(opt):	pass", 0)
		self._test_distcheck(False)

	def test_distcheck(self):
		# black-box test: distcheck works
		appname = 'waf_waf_dist_test'
		version = '30.4.5768'

		wscript_contents = """
srcdir = '.'
blddir = 'out'

%s = '%s'
%s = '%s'

def build(bld):
	lib = bld.new_task_gen('cxx', 'shlib')
	lib.source = 'dd.cpp'
	lib.target = 'dd'

def configure(conf):
	conf.check_tool('compiler_cxx')

def set_options(opt):
	opt.tool_options('compiler_cxx')
""" % (APPNAME, appname, VERSION, version)

		self._write_wscript(wscript_contents, 0)
		dd_file = open('dd.cpp', 'w')
		dd_file.writelines("int k=3;")
		dd_file.close()
		self._test_distcheck()
		dist_file = appname+'-'+version + '.tar.' + Scripting.g_gz
		self.assert_(os.path.isfile(dist_file), "dist file doesn't exists")

	def test_user_define_distcheck(self):
		# black-box test: if user wrote dist() function it will be used
		wscript_contents = """
srcdir = '.'
blddir = 'out'

def build(bld):
	lib = bld.new_task_gen('cxx', 'shlib')
	lib.source = 'dd.cpp'
	lib.target = 'dd'

def configure(conf):
	conf.check_tool('compiler_cxx')

def set_options(opt):
	opt.tool_options('compiler_cxx')

def distcheck():
	open('waf_waf_custom_dist.txt', 'w')
"""
		self._write_wscript(wscript_contents, 0)
		dd_file = open('dd.cpp', 'w')
		dd_file.writelines("int k=3;")
		dd_file.close()
		self._test_distcheck()
		self.assert_(os.path.isfile('waf_waf_custom_dist.txt'), "custom dist() was not used")

	def test_user_distcheck_hook(self):
		# black-box test:
		# if user wrote dist_hook() function it will be used to add something to dist
		# to ease testing the function here creates a file
		wscript_contents = """
srcdir = '.'
blddir = 'out'

def build(bld):
	lib = bld.new_task_gen('cxx', 'shlib')
	lib.source = 'dd.cpp'
	lib.target = 'dd'

def configure(conf):
	conf.check_tool('compiler_cxx')

def set_options(opt):
	opt.tool_options('compiler_cxx')

def dist_hook():
	open('waf_waf_custom_dist.txt', 'w')
"""
		self._write_wscript(wscript_contents, 0)
		dd_file = open('dd.cpp', 'w')
		dd_file.writelines("int k=3;")
		dd_file.close()
		self._test_distcheck()
		dist_file = 'noname-1.0.tar.' + Scripting.g_gz
		tar = tarfile.open(dist_file)
		self.assert_('noname-1.0/waf_waf_custom_dist.txt' in tar.getnames(), "custom dist_hook() was not used")

	def test_distcheck_fails_cannot_uninstall(self):
		# black-box test: distcheck fails if uninstall fails
		appname = 'waf_waf_dist_test'
		version = '30.4.5768'

		wscript_contents = """
srcdir = '.'
blddir = 'out'

%s = '%s'
%s = '%s'

def build(bld):
	open('duh', 'w')

def configure(conf):
	pass
""" % (APPNAME, appname, VERSION, version)

		self._write_wscript(wscript_contents, 0)
		self._test_distcheck(False)

	def test_distcheck_fails_conf_err(self):
		# black-box test: distcheck fails if conf fails
		appname = 'waf_waf_dist_test'
		version = '30.4.5768'

		wscript_contents = """
srcdir = '.'
blddir = 'out'

%s = '%s'
%s = '%s'
""" % (APPNAME, appname, VERSION, version)

		self._write_wscript(wscript_contents, 0)
		self._test_distcheck(False)

def run_tests(verbose=1):
	suite = unittest.TestLoader().loadTestsFromTestCase(ScriptingTester)
	#suite = unittest.TestLoader().loadTestsFromNames(["test_build_without_conf"], ScriptingTester)
	return unittest.TextTestRunner(verbosity=verbose).run(suite)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	options = common_test.get_args_options()
	run_tests(options.verbose)
