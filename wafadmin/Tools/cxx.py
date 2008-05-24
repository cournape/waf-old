#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Base for c++ programs and libraries"

import sys
import TaskGen, Params, Action, Utils
from Params import debug, fatal
import ccroot # <- do not remove
from TaskGen import taskgen, before, extension

g_cpp_flag_vars = [
'FRAMEWORK', 'FRAMEWORKPATH',
'STATICLIB', 'LIB', 'LIBPATH', 'LINKFLAGS', 'RPATH',
'INCLUDE',
'CXXFLAGS', 'CCFLAGS', 'CPPPATH', 'CPPFLAGS', 'CXXDEFINES']
"main cpp variables"

EXT_CXX = ['.cpp', '.cc', '.cxx', '.C']
CXX_METHS = ['init_cxx', 'apply_type_vars', 'apply_incpaths', 'apply_defines_cxx',
'apply_core', 'apply_lib_vars', 'apply_obj_vars_cxx']

TaskGen.add_feature('cxx', CXX_METHS)

g_cpp_type_vars=['CXXFLAGS', 'LINKFLAGS']
class cpp_taskgen(ccroot.ccroot_abstract):
	def __init__(self, *k):
		ccroot.ccroot_abstract.__init__(self, *k)

		# it is called cpp for backward compatibility, in fact it is cxx
		self.features[0] = 'cxx'

@taskgen
@before('apply_type_vars')
def init_cxx(self):
	if not 'cc' in self.features:
		self.mappings['.c'] = TaskGen.task_gen.mappings['.cxx']

	if hasattr(self, 'p_flag_vars'): self.p_flag_vars = set(self.p_flag_vars).union(g_cpp_flag_vars)
	else: self.p_flag_vars = g_cpp_flag_vars

	if hasattr(self, 'p_type_vars'): self.p_type_vars = set(self.p_type_vars).union(g_cpp_type_vars)
	else: self.p_type_vars = g_cpp_type_vars

@taskgen
def apply_obj_vars_cxx(self):
	debug('apply_obj_vars_cxx', 'ccroot')
	env = self.env
	app = self.env.append_unique
	cxxpath_st = self.env['CPPPATH_ST']

	# local flags come first
	# set the user-defined includes paths
	for i in self.inc_paths:
		app('_CXXINCFLAGS', cxxpath_st % i.bldpath(env))
		app('_CXXINCFLAGS', cxxpath_st % i.srcpath(env))

	# set the library include paths
	for i in self.env['CPPPATH']:
		app('_CXXINCFLAGS', cxxpath_st % i)
		#print self.env['_CXXINCFLAGS']
		#print " appending include ",i

	# this is usually a good idea
	app('_CXXINCFLAGS', cxxpath_st % '.')
	app('_CXXINCFLAGS', cxxpath_st % self.env.variant())
	tmpnode = Params.g_build.m_curdirnode
	app('_CXXINCFLAGS', cxxpath_st % tmpnode.bldpath(env))
	app('_CXXINCFLAGS', cxxpath_st % tmpnode.srcpath(env))

@taskgen
def apply_defines_cxx(self):
	tree = Params.g_build
	self.defines = getattr(self, 'defines', [])
	lst = self.to_list(self.defines) + self.to_list(self.env['CXXDEFINES'])
	milst = []

	# now process the local defines
	for defi in lst:
		if not defi in milst:
			milst.append(defi)

	# CXXDEFINES_USELIB
	libs = self.to_list(self.uselib)
	for l in libs:
		val = self.env['CXXDEFINES_'+l]
		if val: milst += self.to_list(val)

	self.env['DEFLINES'] = ["%s %s" % (x[0], Utils.trimquotes('='.join(x[1:]))) for x in [y.split('=') for y in milst]]
	y = self.env['CXXDEFINES_ST']
	self.env['_CXXDEFFLAGS'] = [y%x for x in milst]

@extension(EXT_CXX)
def cxx_hook(self, node):
	# create the compilation task: cpp or cc
	task = self.create_task('cxx', self.env)
	try: obj_ext = self.obj_ext
	except AttributeError: obj_ext = '_%d.o' % self.idx

	task.m_scanner = ccroot.g_c_scanner
	task.path_lst = self.inc_paths
	task.defines  = self.scanner_defines

	task.m_inputs = [node]
	task.m_outputs = [node.change_ext(obj_ext)]
	self.compiled_tasks.append(task)

cxx_str = '${CXX} ${CXXFLAGS} ${CPPFLAGS} ${_CXXINCFLAGS} ${_CXXDEFFLAGS} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}'
link_str = '${LINK_CXX} ${CXXLNK_SRC_F}${SRC} ${CXXLNK_TGT_F}${TGT} ${LINKFLAGS} ${_LIBDIRFLAGS} ${_LIBFLAGS}'

Action.simple_action('cxx', cxx_str, color='GREEN', prio=100)
Action.simple_action('cxx_link', link_str, color='YELLOW', prio=111)

TaskGen.declare_order('apply_incpaths', 'apply_defines_cxx', 'apply_core', 'apply_lib_vars', 'apply_obj_vars_cxx', 'apply_obj_vars')

