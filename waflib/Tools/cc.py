#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"Base for c programs/libraries"

from waflib import TaskGen, Task, Utils
from waflib.Tools import ccroot
from waflib.Tools.ccroot import link_task, static_link

@TaskGen.extension('.c')
def c_hook(self, node):
	return self.create_compiled_task('cc', node)

class cc(Task.Task):
	color   = 'GREEN'
	run_str = '${CC} ${CCFLAGS} ${CPPFLAGS} ${CPPPATH_ST:INCPATHS} ${DEFINES_ST:DEFINES} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
	vars    = ['CCDEPS']
	ext_in  = ['.h']
	scan    = ccroot.scan

class cprogram(link_task):
	run_str = '${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT[0].abspath()} ${LINKFLAGS}'
	ext_out = ['.bin']
	inst_to = '${BINDIR}'
	chmod   = Utils.O755

class cshlib(cprogram):
	inst_to = '${LIBDIR}'

class cstlib(static_link):
	pass

