#! /usr/bin/env python
# encoding: utf-8
# Matthias Jahn, 2007 (pmarat)

import os, shutil, pproc
import unittest

waf_dir=None
build_dir_root=None
demos_dir=None
root_dir=None

def l_call(*option):
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
			l_call(["cp", "-la", "wafadmin", "%s/"%waf_dir])
			l_call(["cp", "-la", "waf-light", "%s/"%waf_dir])
			l_call(["cp", "-la", "wscript", "%s/"%waf_dir])
			l_call(["cp", "-la", "configure", "%s/"%waf_dir])
			os.chdir(waf_dir)
			self.assert_(not l_call(["./waf-light", "--make-waf"]), "waf could not be created")
			self.assert_(os.path.isfile("waf"), "waf is not created in current dir")
	def test_build1(self):
		self.assert_(waf_dir)
		print "\n**standard build without overided builddir:"
		l_call(["cp", "-la", "%s" % os.path.join(demos_dir,"cc"), "%s/"%build_dir_root])
		l_call(["cp", "-la", "%s" % os.path.join(waf_dir,"waf"), "%s/"%os.path.join(build_dir_root,"cc/")])
		l_call(["cp", "-la", "%s" % os.path.join(waf_dir,"configure"), "%s/"%os.path.join(build_dir_root,"cc/")])
		os.chdir(os.path.join(build_dir_root,"cc/"))
		self.assert_(not l_call(["./configure"]))
		self.assert_(not l_call(["make"]))
		self.assert_(not l_call(["build/default/src/test_c_program"]))
		self.assert_(not l_call(["make", "distclean"]))

	def test_build2(self):
		self.assert_(waf_dir)
		print "\n**build with build_dir overide within the project root \
		\nwith commandline -blddir option:"
		os.chdir(os.path.join(build_dir_root,"cc/"))
		self.assert_(not l_call(["./configure", "--blddir=test_build2"]))
		self.assert_(not l_call(["make"]))
		self.assert_(not l_call(["test_build2/default/src/test_c_program"]))
		self.assert_(not l_call(["make", "distclean"]))

	def test_build3(self):
		self.assert_(waf_dir)
		print "\n**build with build_dir overide within the project root \
		\nby configure within the self created buidldir:"
		os.chdir(os.path.join(build_dir_root,"cc/"))
		os.mkdir("test_build2")
		os.chdir("test_build2")
		self.assert_(not l_call(["../configure"]))
		self.assert_(not l_call(["make"]))
		self.assert_(not l_call(["default/src/test_c_program"]))
		l_call(["touch", "test_file"]) #create a file to check the distclean
		#attention current dir will be completly removed including the  "test_file" file
		self.assert_(not l_call(["make", "distclean"]))
		os.chdir(os.path.join(build_dir_root,"cc/"))
	
	def test_build4(self):
		self.assert_(waf_dir)
		print "\n**build with build_dir overide outside the project root \
		\nby configure within the self created buidldir:"
		os.chdir("..")
		os.mkdir("test_build2")
		os.chdir("test_build2")
		l_call(["touch", "test_file"]) #this file must be accesable after distclean
		test_dir=os.getcwd()
		os.mkdir("test_build2")
		os.chdir("test_build2")
		self.assert_(not l_call(["%s"%os.path.join(build_dir_root,"cc","configure")]))
		self.assert_(not l_call(["make"]))
		self.assert_(not l_call(["default/src/test_c_program"]))
		self.assert_(not l_call(["make", "distclean"]))
		os.chdir(test_dir)
		self.assert_(os.path.isfile("test_file"), "test_file did not exists distclean did not work")
		os.chdir(os.path.join(build_dir_root,"cc/"))

def run_tests():
	suite = unittest.TestLoader().loadTestsFromTestCase(build_dir)
	unittest.TextTestRunner(verbosity=2).run(suite)
	os.chdir(root_dir)

if __name__ == '__main__':
	run_tests()
