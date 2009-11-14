#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
cxx_family_test:
a root tester for all c++ compilers tools, like g++, sunc++, msvc.
"""

import os
from ccroot_test import CcRootTester

class CxxFamilyTester(CcRootTester):
	def __init__(self, methodName):
		self.object_name	= 'cxx'
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

	def test_share_lib(self):
		# simple default share lib
		self._setup_cpp_share_lib()
		self._test_configure()
		self._test_build()

	def test_static_lib(self):
		# simple default static lib
		self._setup_cpp_static_lib()
		self._test_configure()
		self._test_build()

