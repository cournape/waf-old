#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"Base for c++ programs and libraries"

from wafadmin import TaskGen, Task, Utils
from wafadmin.Logs import debug
from wafadmin.Tools import ccroot
from wafadmin.TaskGen import feature, before, extension, after

g_cxx_flag_vars = [
'CXXDEPS', 'FRAMEWORK', 'FRAMEWORKPATH',
'STATICLIB', 'LIB', 'LIBPATH', 'LINKFLAGS', 'RPATH',
'CXXFLAGS', 'CCFLAGS', 'CPPFLAGS', 'INCLUDES', 'DEFINES']
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
		raise Errors.WafError("At least one compiler (g++, ..) must be selected")

@extension(*EXT_CXX)
def cxx_hook(self, node):
	return self.create_compiled_task('cxx', node)

cxx_str = '${CXX} ${CXXFLAGS} ${CPPFLAGS} ${_INCFLAGS} ${_DEFFLAGS} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}'
cls = Task.simple_task_type('cxx', cxx_str, color='GREEN', ext_out='.o', ext_in='.cxx')
cls.scan = ccroot.scan
cls.vars.append('CXXDEPS')

link_str = '${LINK_CXX} ${CXXLNK_SRC_F}${SRC} ${CXXLNK_TGT_F}${TGT[0].abspath()} ${LINKFLAGS}'
cls = Task.simple_task_type('cxx_link', link_str, color='YELLOW', ext_in='.o', ext_out='.bin')

