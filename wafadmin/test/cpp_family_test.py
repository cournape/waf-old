#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
cpp_family_test:
a root tester for all c++ compilers tools, like g++, sunc++, msvc.
"""

import os
from ccroot_test import CcRootTester

class CppFamilyTester(CcRootTester):
	def __init__(self, methodName):
		self.object_name	= 'cpp'
		CcRootTester.__init__(self, methodName)

	def test_simple_program(self):
		# simple default cpp program
		self._setup_cpp_program()
		self._test_configure()
		self._test_build()
		self._test_run( os.path.join("build", "default", "hello") )

	def test_simple_object(self):
		# simple default cpp object of executable
		self._setup_cpp_objects()
		self._test_configure()
		self._test_build()

	def test_c_program(self):
		# simple default program - c program should be built with cpp too 
		self._setup_c_program()
		self._test_configure()
		self._test_build()
		self._test_run( os.path.join("build", "default", "hello") )

	def test_c_object(self):
		# simple default object - c objects should be built with cpp too 
		self._setup_c_objects()
		self._test_configure()
		self._test_build()

	def test_debug_flags(self):
		# simple debug cpp program, checks defined FLAGS
		self._setup_cpp_program()
		self._test_configure(True, ["--debug-level=debug"])
		self._same_env(dict(CXXFLAGS=['-Wall', '-g', '-DDEBUG']))

	def test_ultradebug_flags(self):
		# simple ultradebug cpp program, checks defined FLAGS
		self._setup_cpp_program()
		self._test_configure(True, ["--debug-level=ultradebug"])
		self._same_env(dict(CXXFLAGS=['-Wall', '-g3', '-O0', '-DDEBUG']))

	def test_optimized_flags(self):
		# simple optimized cpp program, checks defined FLAGS (should be the same as release)
		self._setup_cpp_program()
		self._test_configure(True, ["--debug-level=optimized"])
		self._same_env(dict(CXXFLAGS=['-Wall', '-O2']))

	def test_release_flags(self):
		# simple release cpp program, checks defined FLAGS
		self._setup_cpp_program()
		self._test_configure(True, ["--debug-level=release"])
		self._same_env(dict(CXXFLAGS=['-Wall', '-O2']))

	def test_default_flags(self):
		# simple default cpp program, checks defined FLAGS (should be the same as release)
		self._setup_cpp_program()
		self._test_configure()
		self._same_env(dict(CXXFLAGS=['-Wall', '-O2']))
		
	def test_empty_custom_flags(self):
		# simple default cpp program, checks defined FLAGS
		# (should be just the default -Wall, since CXXFLAGS_CUSTOM is not defined)
		self._setup_cpp_program()
		self._test_configure(True, ["--debug-level=custom"])
		self._same_env(dict(CXXFLAGS=['-Wall']))
		
	def test_customized_debug_level(self):
		# make sure that user can control the custom debug level
		# by setting the CXXFLAGS_CUSTOM.
		self._setup_cpp_program_with_env("conf.env['CXXFLAGS_CUSTOM'] = '-O9'")
		self._test_configure(True, ["--debug-level=custom"])
		self._same_env(dict(CXXFLAGS=['-Wall', '-O9']))
		
	def test_cxx_by_environ(self):
		# change the CXX environment variable, to something really stupid.
		# then make sure that configure failed (since cxx cannot be found...)
		
		try:
			original_cxx = os.environ.get('CXX')
			os.environ['CXX'] = 'kuku'
			self._setup_cpp_program()
			self._test_configure(False)
		finally:
			# restore os.environ, so subsequent tests won't fail...
			if not original_cxx:
				del os.environ['CXX']
			else:
				os.environ['CXX'] = original_cxx
