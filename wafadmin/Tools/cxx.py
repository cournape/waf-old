#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Base for c++ programs and libraries"

import TaskGen, Task, Utils
from Logs import debug
import ccroot # <- do not remove
from TaskGen import feature, before, extension, after

g_cxx_flag_vars = [
'CXXDEPS', 'FRAMEWORK', 'FRAMEWORKPATH',
'STATICLIB', 'LIB', 'LIBPATH', 'LINKFLAGS', 'RPATH',
'CXXFLAGS', 'CCFLAGS', 'CPPPATH', 'CPPFLAGS', 'DEFINES']
"main cpp variables"

EXT_CXX = ['.cpp', '.cc', '.cxx', '.C', '.c++']

g_cxx_type_vars=['CXXFLAGS', 'LINKFLAGS']

@feature('cxx')
@before('apply_type_vars')
@after('default_cc')
def init_cxx(self):
	if not 'cc' in self.features:
		self.mappings['.c'] = TaskGen.task_gen.mappings['.cxx']

	self.p_flag_vars = set(self.p_flag_vars).union(g_cxx_flag_vars)
	self.p_type_vars = set(self.p_type_vars).union(g_cxx_type_vars)

	if not self.env['CXX_NAME']:
		raise Utils.WafError("At least one compiler (g++, ..) must be selected")

@feature('cxx')
@after('apply_incpaths')
def apply_obj_vars_cxx(self):
	"""after apply_incpaths for INC_PATHS"""
	env = self.env
	app = env.append_unique
	cxxpath_st = env['CPPPATH_ST']

	# local flags come first
	# set the user-defined includes paths
	for i in env['INC_PATHS']:
		app('_CXXINCFLAGS', (cxxpath_st % i.path_from(self.bld.bldnode), cxxpath_st % i.path_from(self.bld.srcnode)))

	# set the library include paths
	for i in env['CPPPATH']:
		app('_CXXINCFLAGS', [cxxpath_st % i])

@extension(*EXT_CXX)
def cxx_hook(self, node):
	# create the compilation task: cpp or cc
	if getattr(self, 'obj_ext', None):
		obj_ext = self.obj_ext
	else:
		obj_ext = '_%d.o' % self.idx

	task = self.create_task('cxx', node, node.change_ext(obj_ext))
	try:
		self.compiled_tasks.append(task)
	except AttributeError:
		raise Utils.WafError('Have you forgotten to set the feature "cxx" on %s?' % str(self))
	return task

cxx_str = '${CXX} ${CXXFLAGS} ${CPPFLAGS} ${_CXXINCFLAGS} ${_DEFFLAGS} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}'
cls = Task.simple_task_type('cxx', cxx_str, color='GREEN', ext_out='.o', ext_in='.cxx')
cls.scan = ccroot.scan
cls.vars.append('CXXDEPS')

link_str = '${LINK_CXX} ${CXXLNK_SRC_F}${SRC} ${CXXLNK_TGT_F}${TGT[0].abspath()} ${LINKFLAGS}'
cls = Task.simple_task_type('cxx_link', link_str, color='YELLOW', ext_in='.o', ext_out='.bin')
cls.maxjobs = 1
cls.install = Utils.nada

