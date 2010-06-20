#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

"""
fortran configuration helpers
"""

import re, shutil, os, sys, string, shlex
from waflib.Configure import conf
from waflib.TaskGen import feature, after, before
from waflib import Build, Utils

FC_FRAGMENT = '        program main\n        end     program main\n'
FC_FRAGMENT2 = '        PROGRAM MAIN\n        END\n' # what's the actual difference between these?

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

@conf
def check_fortran(self, *k, **kw):
	"""see if the compiler works by compiling a fragment"""
	self.check_cc(
		fragment         = FC_FRAGMENT,
		compile_filename = 'test.f',
		features         = 'fc fcprogram',
		msg              = 'Compiling a simple fortran app')

# ------------------------------------------------------------------------

@conf
def check_fortran_dummy_main(self, *k, **kw):
	"""
	Guess if a main function is needed by compiling a code snippet with
	the C compiler and link with the Fortran compiler

	TODO: (DC)
	- handling dialects (F77, F90, etc... -> needs core support first)
	- fix dummy main check (AC_FC_DUMMY_MAIN vs AC_FC_MAIN)

	TODO: what does the above mean? (ita)
	"""

	if not self.env.CC:
		self.fatal('A c compiler is required for check_fortran_dummy_main')

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

# ------------------------------------------------------------------------

GCC_DRIVER_LINE = re.compile('^Driving:')
POSIX_STATIC_EXT = re.compile('\S+\.a')
POSIX_LIB_FLAGS = re.compile('-l\S+')

@conf
def is_link_verbose(self, txt):
	"""Return True if 'useful' link options can be found in txt"""
	if sys.platform == 'win32':
		raise NotImplementedError("FIXME: not implemented on win32")

	assert isinstance(txt, str)
	for line in txt.splitlines():
		if not GCC_DRIVER_LINE.search(line):
			if POSIX_STATIC_EXT.search(line) or POSIX_LIB_FLAGS.search(line):
				return True
	return False

@conf
def check_fortran_verbose_flag(self, *k, **kw):
	"""
	check what kind of -v flag works, then set it to env.FC_VERBOSE_FLAG
	"""
	self.start_msg('fortran link verbose flag')
	for x in ['-v', '--verbose', '-verbose', '-V']:
		try:
			self.check_cc(
				features = 'fc fcprogram_test',
				fragment = FC_FRAGMENT2,
				compile_filename = 'test.f',
				linkflags = [x],
				mandatory=True
				)
		except self.errors.ConfigurationError:
			pass
		else:
			# output is on stderr
			if self.is_link_verbose(self.test_bld.err):
				self.end_msg(x)
				break
	else:
		self.end_msg('failure')
		self.fatal('Could not obtain the fortran link verbose flag (see config.log)')

	self.env.FC_VERBOSE_FLAG = x
	return x

# ------------------------------------------------------------------------

# linkflags which match those are ignored
LINKFLAGS_IGNORED = [r'-lang*', r'-lcrt[a-zA-Z0-9]*\.o', r'-lc$', r'-lSystem', r'-libmil', r'-LIST:*', r'-LNO:*']
if os.name == 'nt':
	LINKFLAGS_IGNORED.extend([r'-lfrt*', r'-luser32', r'-lkernel32', r'-ladvapi32', r'-lmsvcrt', r'-lshell32', r'-lmingw', r'-lmoldname'])
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
	"""private"""
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
	"""
	Obtain flags for linking with the c library
	if this check works, add uselib='CLIB' to your task generators
	"""
	if not self.env.FC_VERBOSE_FLAG:
		self.fatal('env.FC_VERBOSE_FLAG is not set: execute check_fortran_verbose_flag?')

	self.start_msg('Getting fortran runtime link flags')
	try:
		self.check_cc(
			fragment = FC_FRAGMENT2,
			compile_filename = 'test.f',
			features = 'fc fcprogram_test',
			linkflags = [self.env.FC_VERBOSE_FLAG]
		)
	except:
		self.end_msg(False)
		if kw.get('mandatory', True):
			conf.fatal('Could not find the c library flags')
	else:
		out = self.test_bld.err
		flags = parse_fortran_link(out.splitlines())
		self.end_msg('ok (%s)' % ' '.join(flags))
		self.env.CLIB_LINKFLAGS = flags
		return flags
	return []

# ------------------------------------------------------------------------

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

