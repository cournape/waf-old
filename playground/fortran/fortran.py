#! /usr/bin/env python
# encoding: utf-8
import re
import sys
import os
import shutil

import Utils, Task, TaskGen
import ccroot # <- leave this
from TaskGen import feature, before, after, extension
from Configure import conftest, conf
import Build

from myconfig import MyBuildContext

#################################################### Task definitions

EXT_FC = ".f"
EXT_OBJ = ".o"

Task.simple_task_type('fortran',
	'${FC} ${FCFLAGS} ${FC_TGT_F}${TGT} ${FC_SRC_F}${SRC}',
	'GREEN',
	ext_out=EXT_OBJ,
	ext_in=EXT_FC)

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

#################################################### Task generators

# we reuse a lot of code from ccroot.py

FORTRAN = 'init_f default_cc apply_incpaths apply_type_vars apply_lib_vars add_extra_flags'.split()
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
	self.p_type_vars = ['CFLAGS', 'LINKFLAGS']

@feature('fortran')
@after('apply_incpaths')
def incflags_fortran(self):
	app = self.env.append_unique
	pat = self.env['FCPATH_ST']
	for x in self.env['INC_PATHS']:
		app('FCFLAGS', pat % x.bldpath(env))
		app('FCFLAGS', pat % x.srcpath(env))

@feature('fprogram', 'fshlib', 'fstaticlib')
@after('apply_core')
@before('apply_link', 'apply_lib_vars')
def apply_fortran_link(self):
	# override the normal apply_link with c or c++ - just in case cprogram is given too
	try: self.meths.remove('apply_link')
	except ValueError: pass

	def get_name():
		if 'fprogram' in self.features:
			return '%s'
		elif 'fshlib' in self.features:
			return 'lib%s.so'
		else:
			return 'lib%s.a'

	linktask = self.create_task('fortran_link')
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

# Get verbose flag of fortran linker
GCC_DRIVER_LINE = re.compile('^Driving:')
POSIX_STATIC_EXT = re.compile('\S+\.a')
POSIX_LIB_FLAGS = re.compile('-l\S+')

def _got_link_verbose_posix(lines):
    """Returns true if useful link options can be found in output.

    POSIX implementation.

    Expect lines to be a list of lines."""
    for line in lines:
		if not GCC_DRIVER_LINE.search(line):
			if POSIX_STATIC_EXT.search(line) or POSIX_LIB_FLAGS.search(line):
				return True
    return False

def _got_link_verbose(lines):
    """Return true if useful link option can be found in output."""
    if sys.platform == 'win32':
        raise NotImplementedError("FIXME: not implemented on win32")
    else:
        return _got_link_verbose_posix(lines)

@conf
def check_fortran_verbose(self, autoadd=True, *k, **kw):
	kw["compile_filename"] = "test.f"
	kw["code"] = """\
       PROGRAM MAIN
       END
	"""

	kw['compile_mode'] = 'fortran'
	kw['type'] = 'fprogram'
	kw['env'] = self.env.copy()
	kw['execute'] = 0

	kw['msg'] = kw.get('msg', 'Getting fortran link verbose flag')
	kw['errmsg'] = kw.get('errmsg', 'bad luck')

	self.check_message_1(kw['msg'])
	flags = ['-v', '--verbose', '-verbose', '-V']
	gotflag = False
	for flag in flags:
		kw['env']['LINKFLAGS'] = flag
		try:
			ret, out = self.mycompile_code(*k, **kw)
		except:
			ret = 1
			out = ""
			
		if ret == 0 and _got_link_verbose(out.splitlines()):
			gotflag = True
			break

	if gotflag:
		self.check_message_2('ok (%s)' % flag, 'GREEN')
		if autoadd:
			self.env["FC_VERBOSE_FLAG"] = flag	
	else:
		self.check_message_2(kw['errmsg'], 'YELLOW')

	return ret

# Get Fortran runtime libraries
import shlex

# linkflags which match those are ignored
LINKFLAGS_IGNORED = [r'-lang*', r'-lcrt[a-zA-Z0-9]*\.o', r'-lc$', r'-lSystem',
                     r'-libmil', r'-LIST:*', r'-LNO:*']
if os.name == 'nt':
    LINKFLAGS_IGNORED.extend([r'-lfrt*', r'-luser32',
            r'-lkernel32', r'-ladvapi32', r'-lmsvcrt',
            r'-lshell32', r'-lmingw', r'-lmoldname'])
else:
    LINKFLAGS_IGNORED.append(r'-lgcc*')

RLINKFLAGS_IGNORED = [re.compile(f) for f in LINKFLAGS_IGNORED]

def _match_ignore(line):
    """True if the line should be ignored."""
    if [i for i in RLINKFLAGS_IGNORED if i.match(line)]:
        return True
    else:
        return False

def parse_fortran_link(lines):
	"""Given the output of verbose link of Fortran compiler, this returns a
	list of flags necessary for linking using the standard linker."""
	# TODO: On windows ?
	final_flags = []
	for line in lines:
		if not GCC_DRIVER_LINE.match(line):
			_parse_flink_line(line, final_flags)
	return final_flags

SPACE_OPTS = re.compile('^-[LRuYz]$')
NOSPACE_OPTS = re.compile('^-[RL]')

def _parse_flink_line(line, final_flags):
    lexer = shlex.shlex(line, posix = True)
    lexer.whitespace_split = True

    t = lexer.get_token()
    tmp_flags = []
    while t:
        def parse(token):
            # Here we go (convention for wildcard is shell, not regex !)
            #   1 TODO: we first get some root .a libraries
            #   2 TODO: take everything starting by -bI:*
            #   3 Ignore the following flags: -lang* | -lcrt*.o | -lc |
            #   -lgcc* | -lSystem | -libmil | -LANG:=* | -LIST:* | -LNO:*)
            #   4 take into account -lkernel32
            #   5 For options of the kind -[[LRuYz]], as they take one argument
            #   after, the actual option is the next token 
            #   6 For -YP,*: take and replace by -Larg where arg is the old
            #   argument
            #   7 For -[lLR]*: take

            # step 3
            if _match_ignore(token):
                pass
            # step 4
            elif token.startswith('-lkernel32') and sys.platform == 'cygwin':
                tmp_flags.append(token)
            # step 5
            elif SPACE_OPTS.match(token):
                t = lexer.get_token()
                if t.startswith('P,'):
                    t = t[2:]
                for opt in t.split(os.pathsep):
                    tmp_flags.append('-L%s' % opt)
            # step 6
            elif NOSPACE_OPTS.match(token):
                tmp_flags.append(token)
            # step 7
            elif POSIX_LIB_FLAGS.match(token):
                tmp_flags.append(token)
            else:
                # ignore anything not explicitely taken into account
                pass

            t = lexer.get_token()
            return t
        t = parse(t)

    final_flags.extend(tmp_flags)
    return final_flags
@conf
def check_fortran_clib(self, autoadd=True, *k, **kw):
	# Get verbose flag
	try:
		flag = self.env["FC_VERBOSE_FLAG"]
		if len(flag) < 1:
			raise KeyError
	except KeyError:
		if self.check_fortran_verbose():
			return 1

	flag = self.env["FC_VERBOSE_FLAG"]

	kw["compile_filename"] = "test.f"
	kw["code"] = """\
       PROGRAM MAIN
       END
	"""

	kw['compile_mode'] = 'fortran'
	kw['type'] = 'fprogram'
	kw['env'] = self.env.copy()
	kw['execute'] = 0

	kw['msg'] = kw.get('msg', 'Getting fortran runtime link flags')
	kw['errmsg'] = kw.get('errmsg', 'bad luck')

	self.check_message_1(kw['msg'])
	kw['env']['LINKFLAGS'] = flag
	try:
		ret, out = self.mycompile_code(*k, **kw)
	except:
		ret = 1
		out = ""
			
	if ret == 0:
		flags = parse_fortran_link(out.splitlines())

	if ret == 0:
		self.check_message_2('ok (%s)' % " ".join(flags), 'GREEN')
		if autoadd:
			self.env["FC_CLIB_LDFLAGS"] = flag	
	else:
		self.check_message_2(kw['errmsg'], 'YELLOW')

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

# XXX: things which have nothing to do here...
@conftest
def mycompile_code(self, *k, **kw):
	"""Like compile_code, but return output of the compiler command as well as
	the return code."""
	test_f_name = kw['compile_filename']

	# create a small folder for testing
	dir = os.path.join(self.blddir, '.wscript-trybuild')

	# if the folder already exists, remove it
	try:
		shutil.rmtree(dir)
	except OSError:
		pass
	os.makedirs(dir)

	bdir = os.path.join(dir, 'testbuild')

	if not os.path.exists(bdir):
		os.makedirs(bdir)

	env = kw['env']

	dest = open(os.path.join(dir, test_f_name), 'w')
	dest.write(kw['code'])
	dest.close()

	back = os.path.abspath('.')

	bld = MyBuildContext()
	bld.log = self.log
	bld.all_envs.update(self.all_envs)
	bld.all_envs['default'] = env
	bld.lst_variants = bld.all_envs.keys()
	bld.load_dirs(dir, bdir)

	os.chdir(dir)

	bld.rescan(bld.srcnode)

	o = bld.new_task_gen(features=[kw['compile_mode'], kw['type']],
			source=test_f_name, target='testprog')

	for k, v in kw.iteritems():
		setattr(o, k, v)

	self.log.write("==>\n%s\n<==\n" % kw['code'])

	# compile the program
	try:
		bld.compile()
	except:
		ret = Utils.ex_stack()
	else:
		ret = 0

	# chdir before returning
	os.chdir(back)

	if ret:
		self.log.write('command returned %r' % ret)
		self.fatal(str(ret))

	# keep the name of the program to execute
	if kw['execute']:
		lastprog = o.link_task.outputs[0].abspath(env)

	return ret, bld.out

