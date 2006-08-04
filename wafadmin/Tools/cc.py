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
		self.cppflags=''

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


	def apply_obj_vars(self):
		trace('apply_obj_vars called for cppobj')
		cpppath_st       = self.env['CPPPATH_ST']
		lib_st           = self.env['LIB_ST']
		staticlib_st     = self.env['STATICLIB_ST']
		libpath_st       = self.env['LIBPATH_ST']
		staticlibpath_st = self.env['STATICLIBPATH_ST']

		if type(self.ccflags) is types.StringType:
			for i in self.ccflags.split():
				self.env.appendValue('CCFLAGS', i)
		else:
			# TODO: double-check
			self.env['CCFLAGS'] += self.ccflags

		if type(self.cppflags) is types.StringType:
			for i in self.cppflags.split():
				self.env.appendValue('CPPFLAGS', i)
		else:
			# TODO: double-check
			self.env['CPPFLAGS'] += self.cppflags

		# local flags come first
		# set the user-defined includes paths
		if not self._incpaths_lst: self.apply_incpaths()
		for i in self._bld_incpaths_lst:
			self.env.appendValue('_CCINCFLAGS', cpppath_st % i.bldpath(self.env))
			self.env.appendValue('_CCINCFLAGS', cpppath_st % i.srcpath(self.env))

		# set the library include paths
		for i in self.env['CPPPATH']:
			self.env.appendValue('_CCINCFLAGS', cpppath_st % i)
			#print self.env['_CCINCFLAGS']
			#print " appending include ",i
	
		# this is usually a good idea
		self.env.appendValue('_CCINCFLAGS', cpppath_st % '.')
		self.env.appendValue('_CCINCFLAGS', cpppath_st % self.env.variant())
		try:
			tmpnode = Params.g_build.m_curdirnode
			#tmpnode_mirror = Params.g_build.m_src_to_bld[tmpnode]
			self.env.appendValue('_CCINCFLAGS', cpppath_st % tmpnode.bldpath(self.env))
			self.env.appendValue('_CCINCFLAGS', cpppath_st % tmpnode.srcpath(self.env))
		except:
			pass

		for i in self.env['RPATH']:
			self.env.appendValue('LINKFLAGS', i)

		for i in self.env['LIBPATH']:
			self.env.appendValue('LINKFLAGS', libpath_st % i)

		for i in self.env['LIBPATH']:
			self.env.appendValue('LINKFLAGS', staticlibpath_st % i)

		if self.env['STATICLIB']:
			self.env.appendValue('LINKFLAGS', self.env['STATICLIB_MARKER'])
			for i in self.env['STATICLIB']:
				self.env.appendValue('LINKFLAGS', staticlib_st % i)

		if self.env['LIB']:
			self.env.appendValue('LINKFLAGS', self.env['SHLIB_MARKER'])
			for i in self.env['LIB']:
				self.env.appendValue('LINKFLAGS', lib_st % i)

# tool specific setup
# is called when a build process is started 
def setup(env):
	# register our object
	Object.register('cc', ccobj)

# no variable added, do nothing
def detect(conf):
	return 1

