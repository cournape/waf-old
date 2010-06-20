#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

import re, shutil, os, sys, string, shlex
from waflib.Configure import conf
from waflib.TaskGen import feature, after, before
from waflib import Build, Utils

FC_FRAGMENT = '        program main\n        end     program main\n'

GCC_DRIVER_LINE = re.compile('^Driving:')
POSIX_STATIC_EXT = re.compile('\S+\.a')
POSIX_LIB_FLAGS = re.compile('-l\S+')

@conf
def check_fortran(self, *k, **kw):
	self.check_cc(
		fragment         = FC_FRAGMENT,
		compile_filename = 'test.f',
		features         = 'fc fcprogram_test',
		msg              = 'Compiling a simple fortran app')

@conf
def check_fortran_dummy_main(self, *k, **kw):
	"""For a given main , compile the code snippet with the C compiler, and
	link with the Fortran compiler

	TODO:
	- handling dialects (F77, F90, etc... -> needs core support first)
	- handling dependencies between config checks ?
	- fix dummy main check (AC_FC_DUMMY_MAIN vs AC_FC_MAIN)
	"""

	lst = ['MAIN__', '__MAIN', '_MAIN', 'MAIN_', 'MAIN']
	lst.extend([m.lower() for m in lst])
	lst.append('')

	self.start_msg('Detecting whether we need a dummy main')
	for main in lst:
		kw['fortran_main'] = main
		try:
			self.check_cc(
				fragment = 'int %s() { return 0; }\n' % (main or 'test'),
				features = 'cc fcprogram',
				mandatory = True
			)
			if not main:
				self.end_msg('no')
			else:
				self.end_msg('yes %s' % main)
			break
		except self.errors.ConfigurationError:
			pass
	else:
		self.end_msg('not found')
		self.fatal('could not detect whether fortran requires a dummy main, see the config.log')

@conf
def is_link_verbose(self, output):
	"""Return true if useful link option can be found in output."""
	if sys.platform == 'win32':
		raise NotImplementedError("FIXME: not implemented on win32")

	assert isinstance(output, str)
	for line in output.splitlines():
		if not GCC_DRIVER_LINE.search(line):
			if POSIX_STATIC_EXT.search(line) or POSIX_LIB_FLAGS.search(line):
				return True
	return False

@conf
def check_fortran_verbose_flag(self, *k, **kw):
	"""TODO incomplete"""

	self.start_msg('fortran link verbose flag')
	for x in ['-v', '--verbose', '-verbose', '-V']:
		try:
			self.check_cc(
				features = 'fc fcprogram',
				fragment = '        PROGRAM MAIN\n        END\n', # TODO why not use FC_FRAGMENT?
				compile_filename = 'test.f',
				fcflags = [x]
				)
		except:
			pass
		else:
			#print id(self.test_bld), type(self.test_bld)
			if self.is_link_verbose(self.test_bld.out):
				self.end_msg(x)
			break
	else:
		self.end_msg('failure')
		self.fatal('Could not obtain the fortran link verbose flag (see config.log)')

	self.env.FC_VERBOSE_FLAG = x
	return x

#------------------------------------
# Detecting fortran runtime libraries
#------------------------------------
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

#-------------------------
# Fortran mangling scheme
#-------------------------
# Helper to generate combinations of lists
def _RecursiveGenerator(*sets):
	"""Returns a generator that yields one tuple per element combination.
	  A set may be any iterable to which the not operator is applicable.
	"""
	if not sets: return
	def calc(sets):
		head, tail = sets[0], sets[1:]
		if not tail:
			for e in head:
				yield (e,)
		else:
			for e in head:
				for t in calc(tail):
					  yield (e,) + t
	return calc(sets)

@conf
def link_main_routines(self, *k, **kw):
	# This function tests one mangling scheme, defined by the correspondance
	# fortran name <-> C name. It works as follows:
	#	* build a fortran library subroutines with dummy functions
	#	* compile a C main program which calls the dummy functions, and link
	#	against the fortran library. If the link succeeds, it means the names
	#	as used in the C program matches the mangling scheme of the fortran
	#	compiler.
	routines_compile_mode = 'fortran'
	routines_type = 'fstaticlib'

	routines_f_name = "subroutines.f"
	routines_code = """\
      subroutine foobar()
      return
      end
      subroutine foo_bar()
      return
      end
"""

	main_compile_mode = 'cc'
	main_type = 'cprogram'
	main_f_name = "main.c"
	# XXX: handle dummy main...
	main_code = """\
      void %s(void);
      void %s(void);
      int main() {
      %s();
      %s();
      return 0;
      }
""" % (kw['dummy_func_under'], kw['dummy_func_nounder'],
		kw['dummy_func_under'], kw['dummy_func_nounder'])


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

	env = self.env.copy()

	dest = open(os.path.join(dir, routines_f_name), 'w')
	dest.write(routines_code)
	dest.close()

	dest = open(os.path.join(dir, main_f_name), 'w')
	dest.write(main_code)
	dest.close()

	back = os.path.abspath('.')

	bld = Build.BuildContext()
	bld.log = self.log
	bld.all_envs.update(self.all_envs)
	bld.all_envs['default'] = env
	bld.lst_variants = bld.all_envs.keys()
	bld.load_dirs(dir, bdir)

	os.chdir(dir)

	bld.rescan(bld.srcnode)

	routines_task = bld(
			features=[routines_compile_mode, routines_type],
			source=routines_f_name, target='subroutines')

	main_task = bld(
			features=[main_compile_mode, main_type],
			source=main_f_name, target='main')
	main_task.uselib_local = 'subroutines'
	env['LIB'] = ['subroutines']

	for k, v in kw.iteritems():
		setattr(routines_task, k, v)

	for k, v in kw.iteritems():
		setattr(main_task, k, v)

	self.log.write("==>\nsubroutines.f\n%s\n<==\n" % routines_code)
	self.log.write("==>\nmain.c\n%s\n<==\n" % main_code)

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

	return ret

@conf
def check_fortran_mangling(self, *k, **kw):
	# XXX: what's the best way to return a second result ?
	kw['msg'] = kw.get('msg', 'Getting fortran mangling scheme')
	kw['errmsg'] = kw.get('errmsg', 'Failed !')

	self.check_message_1(kw['msg'])

	# Order is 'optimized' for gfortran
	under = ['_', '']
	doubleunder = ['', '_']
	casefcn = ["lower", "upper"]
	gen = _RecursiveGenerator(under, doubleunder, casefcn)
	while True:
		try:
			u, du, c = gen.next()
			def make_mangler(u, du, c):
				return lambda n: getattr(string, c)(n) +\
								 u + (n.find('_') != -1 and du or '')
			mangler = make_mangler(u, du, c)
			kw['dummy_func_nounder'] = mangler("foobar")
			kw['dummy_func_under'] = mangler("foo_bar")
			try:
				ret = self.link_main_routines(*k, **kw)
			except self.errors.ConfigurationError, e:
				ret = 1
			if ret == 0:
				break
		except StopIteration:
			# We ran out, mangling scheme is unknown ...
			result = mangler = u = du = c = None
			break

	if mangler is None:
		self.check_message_2(kw['errmsg'], 'YELLOW')
		result = False
	else:
		self.check_message_2("ok ('%s', '%s', '%s-case')" % (u, du, c),
							 'GREEN')
		result = True
	return result, mangler

@conf
def fc_flags(conf):
	v = conf.env

	v['FC_SRC_F']    = ''
	v['FC_TGT_F']    = ['-c', '-o', '']
	v['FCINCPATH_ST']  = '-I%s'
	v['FCDEFINES_ST']  = '-D%s'

	if not v['LINK_FC']: v['LINK_FC'] = v['FC']
	v['FCLNK_SRC_F'] = ''
	v['FCLNK_TGT_F'] = ['-o', '']

	v['fcshlib_FCFLAGS']   = ['-fpic']
	v['fcshlib_LINKFLAGS'] = ['-shared']
	v['fcshlib_PATTERN']   = 'lib%s.so'

	v['fcstlib_PATTERN']   = 'lib%s.a'


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



