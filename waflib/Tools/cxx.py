#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"Base for c++ programs and libraries"

from waflib import TaskGen, Task
from waflib.Tools import ccroot

@TaskGen.extension('.cpp', '.cc', '.cxx', '.C', '.c++')
def cxx_hook(self, node):
	return self.create_compiled_task('cxx', node)

if not '.c' in TaskGen.task_gen.mappings:
	TaskGen.task_gen.mappings['.c'] = TaskGen.task_gen.mappings['.cpp']

cxx_str = '${CXX} ${CXXFLAGS} ${CPPFLAGS} ${_INCFLAGS} ${_DEFFLAGS} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}'
cxx = Task.task_factory('cxx', cxx_str, color='GREEN', ext_in=['.h'], scan=ccroot.scan)
cxx.vars.append('CXXDEPS')

link_str = '${LINK_CXX} ${CXXLNK_SRC_F}${SRC} ${CXXLNK_TGT_F}${TGT[0].abspath()} ${LINKFLAGS}'
cxx_link = Task.task_factory('cxx_link', link_str, color='YELLOW', ext_out='.bin')

