#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, types
import ccroot
import Action, Object, Params, Scan
from Params import debug, error, trace, fatal

g_cc_flag_vars = [
'FRAMEWORK', 'FRAMEWORKPATH',
'STATICLIB', 'LIB', 'LIBPATH', 'LINKFLAGS', 'RPATH',
'INCLUDE',
'CCFLAGS', 'CPPPATH', 'CPPLAGS']

cctypes=['shlib', 'program', 'staticlib']
g_cc_type_vars=['CCFLAGS', 'LINKFLAGS', 'obj_ext']
class ccobj(ccroot.ccroot):
	def __init__(self, type='program'):
		ccroot.ccroot.__init__(self, type)

		self.ccflags=''

		self._incpaths_lst=[]
		self._bld_incpaths_lst=[]

		self.p_shlib_deps_names=[]
		self.p_staticlib_deps_names=[]

		self.m_linktask=None
		self.m_deps_linktask=[]

		self.m_type_initials = 'cc'

		global g_cc_flag_vars
		self.p_flag_vars = g_cc_flag_vars

		global g_cc_type_vars
		self.p_type_vars = g_cc_type_vars

	def get_valid_types(self):
		return ['program', 'shlib', 'staticlib']

# tool specific setup
# is called when a build process is started 
def setup(env):
	# register our object
	Object.register('cc', ccobj)

# no variable added, do nothing
def detect(env):
	return 1

