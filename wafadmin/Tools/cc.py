#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"Base for c programs/libraries"

from wafadmin import TaskGen, Build, Utils, Task, Errors
from wafadmin.Logs import debug
from wafadmin.Tools import ccroot
from wafadmin.TaskGen import feature, before, extension, after

g_cc_flag_vars = [
'CCDEPS', 'FRAMEWORK', 'FRAMEWORKPATH',
'STATICLIB', 'LIB', 'LIBPATH', 'LINKFLAGS', 'RPATH',
'CCFLAGS', 'CPPFLAGS', 'INCLUDES', 'DEFINES']

@feature('cc')
@before('apply_lib_vars')
@after('default_cc')
def init_cc(self):
	self.p_flag_vars = set(self.p_flag_vars).union(g_cc_flag_vars)

	if not self.env['CC_NAME']:
		# TODO move to the paranoid optional checks
		raise Errors.WafError("At least one compiler (gcc, ..) must be selected")

@extension('.c')
def c_hook(self, node):
	return self.create_compiled_task('cc', node)

cc_str = '${CC} ${CCFLAGS} ${CPPFLAGS} ${_INCFLAGS} ${_DEFFLAGS} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
class cc(Task.Task):
	color   = 'GREEN'
	run_str = cc_str
	vars    = ['CCDEPS']
	ext_in  = ['.c']
	ext_out = ['.o']
	scan    = ccroot.scan

link_str = '${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT[0].abspath()} ${LINKFLAGS}'
class cc_link(Task.Task):
	color   = 'YELLOW'
	run_str = link_str
	ext_in  = ['.o']
	ext_out = ['.bin']

