#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Tests Scripting
"""

import os, unittest, shutil, tempfile
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

	def _write_wscript(self, contents):
		wscript_file_path = self._wscript_file_path
		try:
			wscript_file = open( wscript_file_path, 'w' )
			wscript_file.write(contents)
		finally:
			wscript_file.close()

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

def set_options(opt):
	pass
""" % (built_code, conf_code)

		self._write_wscript(wscript_contents)
		self._test_configure()
		self.assert_(os.path.isfile(conf_code), "1st configure failed")
		self._test_build()
		self.assert_(os.path.isfile(built_code), "1st build failed")
		
		# this should cause reconfiguration.
		os.remove(Options.lockfile)
		
		os.remove(conf_code)
		os.remove(built_code)
		self._test_build()
		self.assert_(os.path.isfile(conf_code), "2nd configure skipped")
		self.assert_(os.path.isfile(built_code), "2nd build failed")
	
	def test_build_without_conf(self):
		# white-box test: make sure that waf aborts on build without configure
		Options.commands['configure'] = False
		Options.commands['clean'] = False
		self.failUnlessRaises(Utils.WafError, Scripting.main)
		
		# cleanup: don't harm other tests
		del Options.commands['configure']
		del Options.commands['clean']
		
	def test_white_no_conf_no_clean(self):
		# white-box test: make sure that waf aborts on build without configure
		Options.commands['clean'] = True
		Options.commands['configure'] = False
		self.failUnlessRaises(Utils.WafError, Scripting.main)
		
		# cleanup: don't harm other tests
		del Options.commands['clean']
		del Options.commands['configure']
		
	def test_black_no_conf_no_clean(self):
		self._write_wscript("def set_options(opt): pass")
		self._test_clean(False)

def run_tests(verbose=1):
	if verbose > 1: common_test.hide_output = False

	suite = unittest.TestLoader().loadTestsFromTestCase(ScriptingTester)
	unittest.TextTestRunner(verbosity=verbose).run(suite)

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	run_tests()
