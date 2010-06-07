#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"Base for c++ programs and libraries"

from wafadmin import TaskGen, Task
from wafadmin.Tools import ccroot

@TaskGen.extension('.cpp', '.cc', '.cxx', '.C', '.c++')
def cxx_hook(self, node):
	return self.create_compiled_task('cxx', node)

cxx_str = '${CXX} ${CXXFLAGS} ${CPPFLAGS} ${_INCFLAGS} ${_DEFFLAGS} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}'
cls = Task.simple_task_type('cxx', cxx_str, color='GREEN', ext_out='.o', ext_in='.cxx', scan=ccroot.scan)
cls.vars.append('CXXDEPS')

link_str = '${LINK_CXX} ${CXXLNK_SRC_F}${SRC} ${CXXLNK_TGT_F}${TGT[0].abspath()} ${LINKFLAGS}'
cls = Task.simple_task_type('cxx_link', link_str, color='YELLOW', ext_in='.o', ext_out='.bin')

