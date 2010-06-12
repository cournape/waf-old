#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"Base for c programs/libraries"

from wafadmin import TaskGen, Task
from wafadmin.Tools import ccroot

@TaskGen.extension('.c')
def c_hook(self, node):
	return self.create_compiled_task('cc', node)

class cc(Task.Task):
	color   = 'GREEN'
	run_str = '${CC} ${CCFLAGS} ${CPPFLAGS} ${_INCFLAGS} ${_DEFFLAGS} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
	vars    = ['CCDEPS']
	ext_in  = ['.h', '.c']
	scan    = ccroot.scan

class cc_link(Task.Task):
	color   = 'YELLOW'
	run_str = '${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT[0].abspath()} ${LINKFLAGS}'
	ext_in  = ['.o']
	ext_out = ['.bin']

