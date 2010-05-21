#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"Base for c programs/libraries"

import os
import TaskGen, Build, Utils, Task
from Logs import debug
import ccroot
from TaskGen import feature, before, extension, after

g_cc_flag_vars = [
'CCDEPS', 'FRAMEWORK', 'FRAMEWORKPATH',
'STATICLIB', 'LIB', 'LIBPATH', 'LINKFLAGS', 'RPATH',
'CCFLAGS', 'CPPFLAGS', 'INCLUDES', 'DEFINES']

EXT_CC = ['.c']

g_cc_type_vars = ['CCFLAGS', 'LINKFLAGS']

@feature('cc')
@before('apply_type_vars')
@after('default_cc')
def init_cc(self):
	self.p_flag_vars = set(self.p_flag_vars).union(g_cc_flag_vars)
	self.p_type_vars = set(self.p_type_vars).union(g_cc_type_vars)

	if not self.env['CC_NAME']:
		raise Utils.WafError("At least one compiler (gcc, ..) must be selected")

@extension(*EXT_CC)
def c_hook(self, node):
	return self.create_compiled_task('cc', node)

cc_str = '${CC} ${CCFLAGS} ${CPPFLAGS} ${_INCFLAGS} ${_DEFFLAGS} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
cls = Task.simple_task_type('cc', cc_str, 'GREEN', ext_out='.o', ext_in='.c')
cls.scan = ccroot.scan
cls.vars.append('CCDEPS')

link_str = '${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT[0].abspath()} ${LINKFLAGS}'
cls = Task.simple_task_type('cc_link', link_str, color='YELLOW', ext_in='.o', ext_out='.bin')
cls.install = Utils.nada

