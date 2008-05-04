#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
cc_family_test:
a root tester for all c-compilers tools, like gcc, suncc, msvc.
"""

import os
from ccroot_test import CcRootTester

class CcFamilyTester(CcRootTester):
	def __init__(self, methodName):
		self.object_name	= 'cc'
		CcRootTester.__init__(self, methodName)

	def test_simple_cpp_program_fails(self):
		# simple default cpp program, should fail !
		self._setup_cpp_program()
		self._test_configure()
		self._test_build(False) # test for failure

	def test_simple_cpp_object_fails(self):
		# simple default cpp object of executable, should fail !
		self._setup_cpp_objects()
		self._test_configure()
		self._test_build(False) # test for failure

	def test_c_program(self):
		# simple default program 
		self._setup_c_program()
		self._test_configure()
		self._test_build()
		self._test_run( os.path.join("build", "default", "hello") )

	def test_c_object(self):
		# simple default object 
		self._setup_c_objects()
		self._test_configure()
		self._test_build()

	def test_debug_flags(self):
		# simple debug cpp program, checks defined FLAGS
		self._setup_c_program()
		self._test_configure(True,["--debug-level=debug"])
		self._same_env(dict(CCFLAGS=['-Wall', '-g', '-DDEBUG']))

	def test_ultradebug_flags(self):
		# simple ultradebug cpp program, checks defined FLAGS
		self._setup_c_program()
		self._test_configure(True,["--debug-level=ultradebug"])
		self._same_env(dict(CCFLAGS=['-Wall', '-g3', '-O0', '-DDEBUG']))

	def test_optimized_flags(self):
		# simple optimized cpp program, checks defined FLAGS (should be the same as release)
		self._setup_c_program()
		self._test_configure(True,["--debug-level=optimized"])
		self._same_env(dict(CCFLAGS=['-Wall', '-O2']))

	def test_release_flags(self):
		# simple release cpp program, checks defined FLAGS
		self._setup_c_program()
		self._test_configure(True,["--debug-level=release"])
		self._same_env(dict(CCFLAGS=['-Wall', '-O2']))

	def test_default_flags(self):
		# simple default cpp program, checks defined FLAGS (should be the same as release)
		self._setup_c_program()
		self._test_configure()
		self._same_env(dict(CCFLAGS=['-Wall', '-O2']))

	def test_customized_debug_level(self):
		# make sure that user can control the custom debug level
		# by setting the CCFLAGS_CUSTOM.
		self._setup_c_program_with_env("conf.env['CCFLAGS_CUSTOM'] = '-O9'")
		self._test_configure(True, ["--debug-level=custom"])
		self._same_env(dict(CCFLAGS=['-O9']))

	def test_cc_by_environ(self):
		
		try:
			original_cxx = os.environ.get('CC')
			os.environ['CC'] = 'kuku'
			self._setup_cpp_program()
			self._test_configure(False)
		finally:
			# restore os.environ, so subsequent tests won't fail...
			if not original_cxx:
				del os.environ['CC']
			else:
				os.environ['CC'] = original_cxx
