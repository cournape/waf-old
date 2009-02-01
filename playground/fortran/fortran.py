#! /usr/bin/env python
# encoding: utf-8
import Utils, Task, TaskGen
import ccroot # <- leave this
import config_fortran # <- leave this
from TaskGen import feature, before, after, extension
from Configure import conftest, conf
import Build

# TODO:
#   - handle pre-processed files (FORTRANPPCOM in scons)
#   - handle modules
#   - handle multiple dialects
#   - windows...

#################################################### Task definitions

EXT_FC = ".f"
EXT_FCPP = ".F"
EXT_OBJ = ".o"

Task.simple_task_type('fortran',
	'${FC} ${FCFLAGS} ${_CCINCFLAGS} ${FC_TGT_F}${TGT} ${FC_SRC_F}${SRC}',
	'GREEN',
	ext_out=EXT_OBJ,
	ext_in=EXT_FC)

# Task to compile fortran source which needs to be preprocessed by cpp first
Task.simple_task_type('fortranpp',
	'${FC} ${FCFLAGS} ${CPPFLAGS} ${_CCINCFLAGS} ${_CCDEFFLAGS} ${FC_TGT_F}${TGT} ${FC_SRC_F}${SRC} ',
	'GREEN',
	ext_out=EXT_OBJ,
	ext_in=EXT_FCPP)

Task.simple_task_type('fortran_link',
	'${FC} ${FCLNK_SRC_F}${SRC} ${FCLNK_TGT_F}${TGT} ${LINKFLAGS}',
	color='YELLOW', ext_in=EXT_OBJ)

@extension(EXT_FC)
def fortran_hook(self, node):
	obj_ext = '_%d.o' % self.idx

	task = self.create_task('fortran')
	task.inputs = [node]
	task.outputs = [node.change_ext(obj_ext)]
	self.compiled_tasks.append(task)
	return task

@extension(EXT_FCPP)
def fortranpp_hook(self, node):
	obj_ext = '_%d.o' % self.idx

	task = self.create_task('fortranpp')
	task.inputs = [node]
	task.outputs = [node.change_ext(obj_ext)]
	self.compiled_tasks.append(task)
	return task

#################################################### Task generators

# we reuse a lot of code from ccroot.py

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
	# the kinds of variables we depend on
	self.p_flag_vars = 'FC FCFLAGS RPATH LINKFLAGS'.split()
	self.p_type_vars = ['FCFLAGS', 'LINKFLAGS']

@feature('fortran')
@after('apply_incpaths')
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

#################################################### Configuration

@conf
def check_fortran(self, *k, **kw):
	if not 'compile_filename' in kw:
		kw['compile_filename'] = 'test.f'
	if 'fragment' in kw:
		kw['code'] = kw['fragment']
	if not 'code' in kw:
		kw['code'] = '''        program main
        end     program main
'''

	if not 'compile_mode' in kw:
		kw['compile_mode'] = 'fortran'
	if not 'type' in kw:
		kw['type'] = 'fprogram'
	if not 'env' in kw:
		kw['env'] = self.env.copy()
	kw['execute'] = kw.get('execute', None)

	kw['msg'] = kw.get('msg', 'Compiling a simple fortran app')
	kw['okmsg'] = kw.get('okmsg', 'ok')
	kw['errmsg'] = kw.get('errmsg', 'bad luck')

	self.check_message_1(kw['msg'])
	ret = self.run_c_code(*k, **kw) == 0
	if not ret:
		self.check_message_2(kw['errmsg'], 'YELLOW')
	else:
		self.check_message_2(kw['okmsg'], 'GREEN')

	return ret

#################################################### Add some flags on some feature

@feature('flink_with_c++')
@after('apply_core')
@before('apply_link', 'apply_lib_vars', 'apply_fortran_link')
def apply_special_link(self):
	linktask = self.create_task('fortran_link')
	outputs = [t.outputs[0] for t in self.compiled_tasks]
	linktask.set_inputs(outputs)
	linktask.set_outputs(self.path.find_or_declare("and_without_target"))
	linktask.chmod = self.chmod
	self.link_task = linktask

@feature('flink_with_c++')
@before('apply_lib_vars')
@after('default_cc')
def add_some_uselib_vars(self):
	#if sys.platform == ...
	self.uselib += ' DEBUG'
