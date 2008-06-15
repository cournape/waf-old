#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"Base for c programs/libraries"

import sys
import TaskGen, Params, Utils, Task
from logging import debug, fatal
import ccroot # <- do not remove
from TaskGen import taskgen, before, extension

g_cc_flag_vars = [
'FRAMEWORK', 'FRAMEWORKPATH',
'STATICLIB', 'LIB', 'LIBPATH', 'LINKFLAGS', 'RPATH',
'INCLUDE',
'CCFLAGS', 'CPPPATH', 'CPPFLAGS', 'CCDEFINES']

EXT_CC = ['.c']
CC_METHS = ['init_cc', 'apply_type_vars', 'apply_incpaths', 'apply_defines_cc',
'apply_core', 'apply_lib_vars', 'apply_obj_vars_cc']

TaskGen.bind_feature('cc', CC_METHS)

g_cc_type_vars = ['CCFLAGS', 'LINKFLAGS']

class cc_taskgen(ccroot.ccroot_abstract):
	def __init__(self, *kw):
		ccroot.ccroot_abstract.__init__(self, *kw)

@taskgen
@before('apply_type_vars')
def init_cc(self):
	if hasattr(self, 'p_flag_vars'): self.p_flag_vars = set(self.p_flag_vars).union(g_cc_flag_vars)
	else: self.p_flag_vars = g_cc_flag_vars

	if hasattr(self, 'p_type_vars'): self.p_type_vars = set(self.p_type_vars).union(g_cc_type_vars)
	else: self.p_type_vars = g_cc_type_vars

	if not self.env['CC_NAME']:
		fatal("At least one compiler (gcc, ..) must be selected")

@taskgen
def apply_obj_vars_cc(self):
	debug('apply_obj_vars_cc', 'ccroot')
	env = self.env
	app = env.append_unique
	cpppath_st = env['CPPPATH_ST']

	# local flags come first
	# set the user-defined includes paths
	for i in env['INC_PATHS']:
		app('_CCINCFLAGS', cpppath_st % i.bldpath(env))
		app('_CCINCFLAGS', cpppath_st % i.srcpath(env))

	# set the library include paths
	for i in env['CPPPATH']:
		app('_CCINCFLAGS', cpppath_st % i)

	# this is usually a good idea
	app('_CCINCFLAGS', cpppath_st % '.')
	app('_CCINCFLAGS', cpppath_st % env.variant())
	tmpnode = self.path
	app('_CCINCFLAGS', cpppath_st % tmpnode.bldpath(env))
	app('_CCINCFLAGS', cpppath_st % tmpnode.srcpath(env))

@taskgen
def apply_defines_cc(self):
	tree = Params.g_build
	self.defines = getattr(self, 'defines', [])
	lst = self.to_list(self.defines) + self.to_list(self.env['CCDEFINES'])
	milst = []

	# now process the local defines
	for defi in lst:
		if not defi in milst:
			milst.append(defi)

	# CCDEFINES_
	libs = self.to_list(self.uselib)
	for l in libs:
		val = self.env['CCDEFINES_'+l]
		if val: milst += val
	self.env['DEFLINES'] = ["%s %s" % (x[0], Utils.trimquotes('='.join(x[1:]))) for x in [y.split('=') for y in milst]]
	y = self.env['CCDEFINES_ST']
	self.env['_CCDEFFLAGS'] = [y%x for x in milst]

@extension(EXT_CC)
def c_hook(self, node):
	# create the compilation task: cpp or cc
	task = self.create_task('cc', self.env)
	try: obj_ext = self.obj_ext
	except AttributeError: obj_ext = '_%d.o' % self.idx

	task.defines  = self.scanner_defines

	task.m_inputs = [node]
	task.m_outputs = [node.change_ext(obj_ext)]
	self.compiled_tasks.append(task)

cc_str = '${CC} ${CCFLAGS} ${CPPFLAGS} ${_CCINCFLAGS} ${_CCDEFFLAGS} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
link_str = '${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT} ${LINKFLAGS} ${_LIBDIRFLAGS} ${_LIBFLAGS}'

cls = Task.simple_task_type('cc', cc_str, 'GREEN', ext_out='.o', ext_in='.c')
cls.scan = ccroot.scan
cls.scan_signature_queue = ccroot.scan_signature_queue
Task.simple_task_type('cc_link', link_str, color='YELLOW', ext_in='.o')

TaskGen.declare_order('apply_incpaths', 'apply_defines_cc', 'apply_core', 'apply_lib_vars', 'apply_obj_vars_cc', 'apply_obj_vars')

