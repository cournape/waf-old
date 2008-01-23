#! /usr/bin/env python
# encoding: utf-8
# Matthias Jahn, 2007 (pmarat)
# Yinon Ehrlich, 2008

import os, sys, shutil, unittest
import common_test

# allow importing from wafadmin dir when ran from sub-directory 
sys.path.append(os.path.abspath(os.path.pardir))

try:
	import Params, Test
except ImportError:
	(curr_dir, curr_file) = os.path.split(__file__)
	print "Failed to import wafadmin modules."
	print "Either run 'waf check' from root waf directory, or run '%s' from '%s'" % (curr_file, curr_dir) 
	sys.exit(1)

class TestBuildDir(common_test.CommonTester):

	def __init__(self, methodName):
		''' initializes class attributes and run the base __init__'''

		# define directories
		# ------------------
		# waf						_waf_root_dir (defined by common_test)
		#		demos				__orig_demos_dir
		#		test_dir			__test_dir_root
		#				waf			__test_waf_dir
		#				demos		__test_demos_dir
		
		common_test.CommonTester.__init__(self, methodName)

		self.__orig_demos_dir=os.path.join(self._waf_root_dir, Test.DIRS.DEMOS)
		self.__test_dir_root = os.path.join(self._waf_root_dir, "test_dir") 
		self.__test_waf_dir = os.path.join(self.__test_dir_root, "waf")
		self.__test_demos_dir = os.path.join(self.__test_dir_root, Test.DIRS.DEMOS )
		
		# by default, original waf scripts is used by common_tester.
		# Here we override the default and use 'waf' from test directory.
		self._waf_exe = os.path.join(self.__test_waf_dir, "waf")
		
	def setUp(self):
		self.assert_(self.__test_waf_dir)
		
		# create test directories
		if os.path.isdir(self.__test_dir_root):
			shutil.rmtree(self.__test_dir_root)
		os.makedirs(self.__test_dir_root)

		os.mkdir(self.__test_waf_dir)

		os.chdir(self._waf_root_dir)
		self._copy("wafadmin", self.__test_waf_dir)
		self._copy("waf-light", self.__test_waf_dir)
		self._copy("wscript", self.__test_waf_dir)
		self._copy(self.__orig_demos_dir, self.__test_demos_dir )

		os.chdir(self.__test_waf_dir)

		# make sure 'waf' file is being created by waf-light
		self.assertEqual(0, self.call(["python", "waf-light", "--make-waf"]), "waf could not be created")
		self.assert_(os.path.isfile(self._waf_exe), "waf was not created")
		
		os.chdir(self.__test_demos_dir)


	def tearDown(self):
		'''tearDown - deletes the directories and files created by the tests ran '''
		if os.path.isdir(self.__test_dir_root):
			shutil.rmtree(self.__test_dir_root)
		if os.path.isdir(self.__test_waf_dir):
			shutil.rmtree(self.__test_waf_dir)
			
		os.chdir(self._waf_root_dir)

	def test_build1(self):
		# standard build without override build-dir
		os.chdir("cc")

		self._test_configure()
		self._test_build()
		self._test_run("build/default/src/test_c_program")
		self._test_distclean()

	def test_build2(self):
		# build with TestBuildDir override within the project root with command-line -blddir option
		os.chdir("cc")

		self._test_configure(True, ["--blddir=test_build2"])
		self._test_build()
		self._test_run("test_build2/default/src/test_c_program")
		self._test_distclean()

	def test_build3(self):
		# build with TestBuildDir override within the project root by configure within the self created buidldir 
		self._copy(os.path.join(self.__test_waf_dir,"waf"), os.path.join(self.__test_demos_dir,"cc"))
		os.chdir("cc")

		os.mkdir("test_build2")
		os.chdir("test_build2")
#		
		self.assertEqual(0, self.call(["python", "../waf", "configure"]), "build failed")
		self.assertEqual(0, self.call(["python", "../waf", "build"]), "configure failed")
		self._test_run("default/src/test_c_program")
		self.call(["touch", "test_file"]) #create a file to check the distclean
		#attention current dir will be completely removed including the  "test_file" file
		self.assertEqual(0, self.call(["python", "../waf", "distclean"]), "distclean failed")

	def test_build4(self):
		# build with TestBuildDir override outside the project root by configure within the self created buidldir
		self._copy(os.path.join(self.__test_waf_dir,"waf"), os.path.join(self.__test_demos_dir,"cc"))

		os.mkdir("test_build2")
		os.chdir("test_build2")
		file = open("test_file", 'wb')
		file.close() #this file must be accessible after distclean

		test_dir=os.getcwd()
		
		self.assertEqual(0, self.call(["python", 
			os.path.join(self.__test_demos_dir,"cc","waf"), "configure"]))
		self.assertEqual(0, self.call(["python", 
			"%s"%os.path.join(self.__test_demos_dir,"cc","waf"), "build"]))
		self._test_run("default/src/test_c_program")
		self.assertEqual(0, self.call(["python",
			"%s"%os.path.join(self.__test_demos_dir,"cc","waf"), "distclean"]))
		self.failIf(os.path.exists(test_dir), 
			"'%s' should not exists distclean did not work" % test_dir)

def run_tests(verbose=2):
	try:
		suite = unittest.TestLoader().loadTestsFromTestCase(TestBuildDir)
		unittest.TextTestRunner(verbosity=verbose).run(suite)
	except common_test.StartupError, e:
		Params.error( e.message )

if __name__ == '__main__':
	# test must be ran from waf's root directory
	os.chdir(os.path.pardir)
	os.chdir(os.path.pardir)
	run_tests()
