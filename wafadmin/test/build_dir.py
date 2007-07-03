#! /usr/bin/env python
# encoding: utf-8
# Matthias Jahn, 2007 (pmarat)

import os, sys, shutil, pproc
import unittest

waf_dir=None
build_dir_root=None
demos_dir=None
root_dir=None

def copy(source, target):
	if str.find(sys.platform, 'linux') != -1:
		_call(["cp", "-la", source, target])
	elif os.name=="posix":
		_call(["cp", "-a", source, target])
	else:
		shutil.copytree(source, target)

def _call(*option):
	"subprocess call method with silent stdout"
	kwargs = dict()
	kwargs['stdout'] = pproc.PIPE
	return pproc.call( *option, **kwargs)

class build_dir(unittest.TestCase):
	def setUp(self):
		global waf_dir, build_dir_root, demos_dir, root_dir
		if not waf_dir:
			self.assert_(os.path.isfile("waf-light"), "please run test with 'waf-light check'")
			self.assert_(os.path.isdir("demos"), "you need also demos dir from waf distribution")
			root_dir=os.getcwd()
			demos_dir=os.path.abspath("demos")
			build_dir_root=os.path.abspath(os.path.join("tests", "test_build_dir"))
			if os.path.isdir(build_dir_root):
				shutil.rmtree(build_dir_root)
			os.makedirs(build_dir_root)
			waf_dir=os.path.join(build_dir_root, "waf")
			os.mkdir(waf_dir)
			copy("wafadmin", "%s/"%waf_dir)
			copy("waf-light", "%s/"%waf_dir)
			copy("wscript", "%s/"%waf_dir)
			copy("configure", "%s/"%waf_dir)
			os.chdir(waf_dir)
			self.assert_(not _call(["./waf-light", "--make-waf"]), "waf could not be created")
			self.assert_(os.path.isfile("waf"), "waf is not created in current dir")
	def test_build1(self):
		self.assert_(waf_dir)
		print "\n**standard build without overided builddir:"
		copy("%s" % os.path.join(demos_dir,"cc"), "%s/"%build_dir_root)
		copy("%s" % os.path.join(waf_dir,"waf"), "%s/"%os.path.join(build_dir_root,"cc/"))
		copy("%s" % os.path.join(waf_dir,"configure"), "%s/"%os.path.join(build_dir_root,"cc/"))
		os.chdir(os.path.join(build_dir_root,"cc/"))
		self.assert_(not _call(["./configure"]))
		self.assert_(not _call(["make"]))
		self.assert_(not _call(["build/default/src/test_c_program"]))
		self.assert_(not _call(["make", "distclean"]))

	def test_build2(self):
		self.assert_(waf_dir)
		print "\n**build with build_dir overide within the project root \
		\nwith commandline -blddir option:"
		os.chdir(os.path.join(build_dir_root,"cc/"))
		self.assert_(not _call(["./configure", "--blddir=test_build2"]))
		self.assert_(not _call(["make"]))
		self.assert_(not _call(["test_build2/default/src/test_c_program"]))
		self.assert_(not _call(["make", "distclean"]))

	def test_build3(self):
		self.assert_(waf_dir)
		print "\n**build with build_dir overide within the project root \
		\nby configure within the self created buidldir:"
		os.chdir(os.path.join(build_dir_root,"cc/"))
		os.mkdir("test_build2")
		os.chdir("test_build2")
		self.assert_(not _call(["../configure"]))
		self.assert_(not _call(["make"]))
		self.assert_(not _call(["default/src/test_c_program"]))
		_call(["touch", "test_file"]) #create a file to check the distclean
		#attention current dir will be completly removed including the  "test_file" file
		self.assert_(not _call(["make", "distclean"]))
		os.chdir(os.path.join(build_dir_root,"cc/"))
	
	def test_build4(self):
		self.assert_(waf_dir)
		print "\n**build with build_dir overide outside the project root \
		\nby configure within the self created buidldir:"
		os.chdir("..")
		os.mkdir("test_build2")
		os.chdir("test_build2")
		_call(["touch", "test_file"]) #this file must be accesable after distclean
		test_dir=os.getcwd()
		os.mkdir("test_build2")
		os.chdir("test_build2")
		self.assert_(not _call(["%s"%os.path.join(build_dir_root,"cc","configure")]))
		self.assert_(not _call(["make"]))
		self.assert_(not _call(["default/src/test_c_program"]))
		self.assert_(not _call(["make", "distclean"]))
		os.chdir(test_dir)
		self.assert_(os.path.isfile("test_file"), "test_file did not exists distclean did not work")
		os.chdir(os.path.join(build_dir_root,"cc/"))

def run_tests():
	suite = unittest.TestLoader().loadTestsFromTestCase(build_dir)
	unittest.TextTestRunner(verbosity=2).run(suite)
	os.chdir(root_dir)

if __name__ == '__main__':
	run_tests()
