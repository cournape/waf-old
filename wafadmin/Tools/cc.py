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

		global g_cc_flag_vars
		self.p_flag_vars = g_cc_flag_vars

		global g_cc_type_vars
		self.p_type_vars = g_cc_type_vars

	def get_valid_types(self):
		return ['program', 'shlib', 'staticlib']

	def apply(self):
		trace("apply called for cobj")
		if not self.m_type in self.get_valid_types(): fatal('Trying to build a c file of unknown type')

		self.apply_lib_vars()
		self.apply_type_vars()
		self.apply_obj_vars()
		self.apply_incpaths()

		obj_ext = self.env[self.m_type+'_obj_ext'][0]

		# get the list of folders to use by the scanners
                # all our objects share the same include paths anyway
                tree = Params.g_build.m_tree
                dir_lst = { 'path_lst' : self._incpaths_lst }

		lst = self.source.split()
		for filename in lst:

			node = self.m_current_path.find_node( filename.split(os.sep) )
			if not node:
				error("source not found "+filename)
				print "source not found", self.m_current_path
				sys.exit(1)

			base, ext = os.path.splitext(filename)

			fun = None
			try:
				fun = self.env['handlers_ccobj_'+ext]
				#print "fun is", 'handlers_ccobj_'+ext, fun
			except:
				pass

			if fun:
				fun(self, node)
				continue

			if tree.needs_rescan(node):
				tree.rescan(node, Scan.c_scanner, dir_lst)

			# create the task for the cc file
			cctask = self.create_task('cc', self.env)

			cctask.m_scanner = Scan.c_scanner
			cctask.m_scanner_params = dir_lst

			cctask.m_inputs  = self.file_in(filename)
			cctask.m_outputs = self.file_in(base+obj_ext)
			self.p_compiletasks.append(cctask)

		# and after the cc objects, the remaining is the link step
		# link in a lower priority (101) so it runs alone (default is 10)
		if self.m_type=='staticlib': linktask = self.create_task('cc_link_static', self.env, ccroot.g_prio_link)
		else:                        linktask = self.create_task('cc_link', self.env, ccroot.g_prio_link)
		ccoutputs = []
		for t in self.p_compiletasks: ccoutputs.append(t.m_outputs[0])
		linktask.m_inputs  = ccoutputs 
		linktask.m_outputs = self.file_in(self.get_target_name())

		self.m_linktask = linktask

		if self.m_type != 'program':	
			latask = self.create_task('fakelibtool', self.env, 200)
			latask.m_inputs = linktask.m_outputs
			latask.m_outputs = self.file_in(self.get_target_name('.la'))
			self.m_latask = latask

		self.apply_libdeps()

# tool specific setup
# is called when a build process is started 
def setup(env):
	print "setup for cc"
	# prevent other modules from loading us more than once
	if 'cc' in Params.g_tools: return
	Params.g_tools.append('cc')

	# register our object
	Object.register('cc', ccobj)

# no variable added, do nothing
def detect(env):
	return 1

