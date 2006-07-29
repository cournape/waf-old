#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

# common builders and actions

import os, types
import ccroot
import Action, Object, Params, Scan
from Params import debug, error, trace, fatal

# main c/cpp variables
g_cpp_flag_vars = [
'FRAMEWORK', 'FRAMEWORKPATH',
'STATICLIB', 'LIB', 'LIBPATH', 'LINKFLAGS', 'RPATH',
'INCLUDE',
'CXXFLAGS', 'CCFLAGS', 'CPPPATH', 'CPPLAGS']

cpptypes=['shlib', 'program', 'staticlib']
g_cpp_type_vars=['CXXFLAGS', 'LINKFLAGS', 'obj_ext']
class cppobj(ccroot.ccroot):
	def __init__(self, type='program'):
		ccroot.ccroot.__init__(self, type)

		self.cxxflags=''
		self.cppflags=''
		self.ccflags=''

		self._incpaths_lst=[]
		self._bld_incpaths_lst=[]

		self.p_shlib_deps_names=[]
		self.p_staticlib_deps_names=[]

		self.m_linktask=None
		self.m_deps_linktask=[]

		self.m_type_initials = 'cpp'

		global g_cpp_flag_vars
		self.p_flag_vars = g_cpp_flag_vars

		global g_cpp_type_vars
		self.p_type_vars = g_cpp_type_vars

	def get_valid_types(self):
		return ['program', 'shlib', 'staticlib']

# tool specific setup
# is called when a build process is started 
def setup(env):
	# register our object
	Object.register('cpp', cppobj)

# no variable added, do nothing
def detect(conf):
	return 1

