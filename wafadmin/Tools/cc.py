#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"Base for c programs/libraries"

import Object, Params, Action, Utils
from Params import debug
import ccroot # <- do not remove

import sys
# backwards compatibility for python 2.3
if sys.hexversion < 0x020400f0: from sets import Set as set

g_cc_flag_vars = [
'FRAMEWORK', 'FRAMEWORKPATH',
'STATICLIB', 'LIB', 'LIBPATH', 'LINKFLAGS', 'RPATH',
'INCLUDE',
'CCFLAGS', 'CPPPATH', 'CPPFLAGS', 'CCDEFINES']

EXT_CC = ['.c', '.cc']
CC_METHS = ['init_cc', 'apply_type_vars', 'apply_incpaths', 'apply_dependencies', 'apply_defines_cc',
'apply_core', 'apply_link', 'apply_vnum', 'apply_lib_vars', 'apply_obj_vars_cc', 'apply_obj_vars',
'apply_objdeps', 'install_target']

Object.add_trait('cc', CC_METHS)

g_cc_type_vars = ['CCFLAGS', 'LINKFLAGS']

# TODO get rid of this
class ccobj(ccroot.ccroot):
	def __init__(self, type='program', subtype=None):
		ccroot.ccroot.__init__(self, type, subtype)
		self.m_type_initials = 'cc'

		self.ccflags=''
		self.cppflags=''

		self.features.append('cc')

		global g_cc_type_vars
		self.p_type_vars = g_cc_type_vars

def init_cc(self):
	if hasattr(self, 'p_flag_vars'): self.p_flag_vars = set(self.p_flag_vars).union(g_cc_flag_vars)
	else: self.p_flag_vars = g_cc_flag_vars

	if hasattr(self, 'p_type_vars'):	self.p_type_vars = set(self.p_type_vars).union(g_cc_type_vars)
	else: self.p_type_vars = g_cc_type_vars
Object.gen_hook(init_cc)

def apply_obj_vars_cc(self):
	debug('apply_obj_vars_cc', 'ccroot')
	env = self.env
	app = env.append_unique
	cpppath_st = self.env['CPPPATH_ST']

	self.addflags('CCFLAGS', self.ccflags)

	# local flags come first
	# set the user-defined includes paths
	for i in self.bld_incpaths_lst:
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
Object.gen_hook(apply_obj_vars_cc)

def apply_defines_cc(self):
	tree = Params.g_build
	lst = self.to_list(self.defines)+self.to_list(self.env['CCDEFINES'])
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
Object.gen_hook(apply_defines_cc)

def c_hook(self, node):
	# create the compilation task: cpp or cc
	task = self.create_task('cc', self.env)
	obj_ext = '_%s.o' % self.m_type[:2]

	task.m_scanner = ccroot.g_c_scanner
	task.path_lst = self.inc_paths
	task.defines  = self.scanner_defines

	task.m_inputs = [node]
	task.m_outputs = [node.change_ext(obj_ext)]
	self.compiled_tasks.append(task)

cc_str = '${CC} ${CCFLAGS} ${CPPFLAGS} ${_CCINCFLAGS} ${_CCDEFFLAGS} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
link_str = '${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT} ${LINKFLAGS} ${_LIBDIRFLAGS} ${_LIBFLAGS}'

Action.simple_action('cc', cc_str, 'GREEN', prio=100)
Action.simple_action('cc_link', link_str, color='YELLOW', prio=111)

Object.register('cc', ccobj)
Object.declare_extension(EXT_CC, c_hook)

Object.declare_order('init_cc', 'apply_type_vars')
Object.declare_order('apply_dependencies', 'apply_defines_cc', 'apply_core', 'apply_lib_vars', 'apply_obj_vars_cc', 'apply_obj_vars')

