#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

import re

from waflib import Utils, Task, TaskGen, Logs
from waflib.Tools import ccroot
from waflib.extras import fc_cfg, fc_scan
from waflib.TaskGen import feature, before, after, extension
from waflib.Configure import conf

ccroot.USELIB_VARS['fc'] = set(['FCFLAGS', 'DEFINES'])
ccroot.USELIB_VARS['fcprogram_test'] = ccroot.USELIB_VARS['fcprogram'] = set(['LINKFLAGS'])
ccroot.USELIB_VARS['fcshlib'] = set(['LINKFLAGS'])
ccroot.USELIB_VARS['fcstlib'] = set(['LINKFLAGS'])

@feature('fcprogram', 'fcshlib', 'fcstlib', 'fcprogram_test')
def dummy(self):
	pass

# FIXME what was this for??????
#def fortran_compile(task):
#	env = task.env
#	def tolist(xx):
#		if isinstance(xx, str):
#			return [xx]
#		return xx
#	cmd = []
#	cmd.extend(tolist(env["FC"]))
#	cmd.extend(tolist(env["FCFLAGS"]))
#	cmd.extend(tolist(env["_FCINCFLAGS"]))
#	cmd.extend(tolist(env["_FCMODOUTFLAGS"]))
#	for a in task.outputs:
#		cmd.extend(tolist(env["FC_TGT_F"] + tolist(a.bldpath(env))))
#	for a in task.inputs:
#		cmd.extend(tolist(env["FC_SRC_F"]) + tolist(a.srcpath(env)))
#	cmd = [x for x in cmd if x]
#	cmd = [cmd]
#
#	ret = task.exec_command(*cmd)
#	return ret

@TaskGen.extension('.f')
def fc_hook(self, node):
	return self.create_compiled_task('fc', node)

class fc(Task.Task):
	color = 'GREEN'
	run_str = '${FC} ${FCFLAGS} ${FCINCPATH_ST:INCPATHS} ${FCDEFINES_ST:DEFINES} ${_FCMODOUTFLAGS} ${FC_TGT_F}${TGT} ${FC_SRC_F}${SRC}'
	vars = ["FORTRANMODPATHFLAG"]
	scan = fc_scan.scan

@extension('.F')
def fcpp_hook(self, node):
	return self.create_compiled_task('fcpp', node)

class fcpp(Task.Task):
	# FIXME why another task? what's the problem?
	color = 'GREEN'
	run_str = '${FC} ${FCFLAGS} ${FCINCPATH_ST:INCPATHS} ${FCDEFINES_ST:DEFINES} ${FC_TGT_F}${TGT} ${FC_SRC_F}${SRC}'

class fcprogram(ccroot.link_task):
	color = 'YELLOW'
	run_str = '${FC} ${FCLNK_SRC_F}${SRC} ${FCLNK_TGT_F}${TGT} ${LINKFLAGS}'
	inst_to = '${BINDIR}'

class fcshlib(fcprogram):
	inst_to = '${LIBDIR}'

class fcprogram_test(fcprogram):
	"""custom link task to obtain the compiler outputs"""

	def runnable_status(self):
		"""make sure the link task is always executed"""
		ret = super(fcprogram_test, self).runnable_status()
		if ret == Task.SKIP_ME:
			ret = Task.RUN_ME
		return ret

	def exec_command(self, cmd, **kw):
		"""store the compiler std our/err onto the build context, to bld.out + bld.err"""
		bld = self.generator.bld

		kw['shell'] = isinstance(cmd, str)
		kw['stdout'] = kw['stderr'] = Utils.subprocess.PIPE
		kw['cwd'] = bld.variant_dir
		bld.out = bld.err = ''

		if bld.log:
			bld.log.write('command: %s\n' % cmd)

		try:
			proc = Utils.subprocess.Popen(cmd, **kw)
			(bld.out, bld.err) = proc.communicate()
		except OSError:
			return -1

		if bld.log:
			if bld.out:
				bld.log.write("out: %s\n" % bld.out)
			if bld.err:
				bld.log.write("err: %s\n" % bld.err)

		return proc.returncode

class fcstlib(ccroot.static_link):
	"""just use ar normally"""
	pass # do not remove the pass statement

#################################################### Task generators

# we reuse a lot of code from ccroot.py
"""
FORTRAN = 'init_f default_cc apply_incpaths apply_defines_cc apply_type_vars apply_lib_vars add_extra_flags apply_obj_vars_cc'.split()
FPROGRAM = 'apply_verif vars_target_cprogram install_target_cstaticlib apply_objdeps apply_obj_vars '.split()
FSHLIB = 'apply_verif vars_target_cstaticlib install_target_cstaticlib install_target_cshlib apply_objdeps apply_obj_vars apply_vnum'.split()
FSTATICLIB = 'apply_verif vars_target_cstaticlib install_target_cstaticlib apply_objdeps apply_obj_vars '.split()

TaskGen.bind_feature('fortran', FORTRAN)
TaskGen.bind_feature('fprogram', FPROGRAM)
TaskGen.bind_feature('fshlib', FSHLIB)
TaskGen.bind_feature('fstaticlib', FSTATICLIB)

TaskGen.declare_order('init_f', 'apply_lib_vars')
TaskGen.declare_order('default_cc', 'apply_core')

@feature('fortran')
@before('apply_type_vars')
@after('default_cc')
def init_f(self):
	# PATH flags:
	#	- CPPPATH: same as C, for pre-processed fortran files
	#	- FORTRANMODPATH: where to look for modules (.mod)
	#	- FORTRANMODOUTPATH: where to *put* modules (.mod)
	self.p_flag_vars = ['FC', 'FCFLAGS', 'RPATH', 'LINKFLAGS',
			'FORTRANMODPATH', 'CPPPATH', 'FORTRANMODOUTPATH', '_CCINCFLAGS']
	self.p_type_vars = ['FCFLAGS', 'LINKFLAGS']
"""

"""
@feature('fortran')
@after('apply_incpaths', 'apply_obj_vars_cc')
def apply_fortran_type_vars(self):
	for x in self.features:
		if not x in ['fprogram', 'fstaticlib', 'fshlib']:
			continue
		x = x.lstrip('f')

		# if the type defines uselib to add, add them
		st = self.env[x + '_USELIB']
		if st: self.uselib = self.uselib + ' ' + st

		# each compiler defines variables like 'shlib_FCFLAGS', 'shlib_LINKFLAGS', etc
		# so when we make a task generator of the type shlib, FCFLAGS are modified accordingly
		for var in self.p_type_vars:
			compvar = '%s_%s' % (x, var)
			value = self.env[compvar]
			if value: self.env.append_value(var, value)

	# Put module and header search paths into _FCINCFLAGS
	app = self.env.append_unique
	for i in self.env["FORTRANMODPATH"]:
		app('_FCINCFLAGS', self.env['FCPATH_ST'] % i)

	for i in self.env["_CCINCFLAGS"]:
		app('_FCINCFLAGS', i)

	#opath = self.env["FORTRANMODOUTPATH"]
	#if not opath:
	#	self.env["_FCMODOUTFLAGS"] = self.env["FORTRANMODFLAG"] + opath
	#	app('_FCINCFLAGS', self.env['FCPATH_ST'] % opath)
	#else:
	#	# XXX: assume that compiler put .mod in cwd by default
	#	app('_FCINCFLAGS', self.env['FCPATH_ST'] % self.bld.bdir)

@feature('fprogram', 'fshlib', 'fstaticlib')
@after('apply_core')
@before('apply_link', 'apply_lib_vars')
def apply_fortran_link(self):
	# override the normal apply_link with c or c++ - just in case cprogram is given too
	try: self.meths.remove('apply_link')
	except ValueError: pass

	link = 'fortran_link'
	if 'fstaticlib' in self.features:
		link = 'ar_link_static'

	def get_name():
		if 'fprogram' in self.features:
			return '%s'
		elif 'fshlib' in self.features:
			return 'lib%s.so'
		else:
			return 'lib%s.a'

	linktask = self.create_task(link)
	outputs = [t.outputs[0] for t in self.compiled_tasks]
	linktask.set_inputs(outputs)
	linktask.set_outputs(self.path.find_or_declare(get_name() % self.target))
	linktask.chmod = self.chmod

	self.link_task = linktask
"""


#################################################### Configuration


