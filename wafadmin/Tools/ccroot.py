#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"base for all c/c++ programs and libraries"

import os, sys, re
import TaskGen, Task, Utils, preproc, Logs, Build, Options
from Logs import error, debug, warn
from Utils import md5
from TaskGen import taskgen, after, before, feature
from Constants import *
try:
	from cStringIO import StringIO
except ImportError:
	from io import StringIO

import config_c # <- necessary for the configuration, do not touch

USE_TOP_LEVEL = False

def get_cc_version(conf, cc, gcc=False, icc=False):

	cmd = cc + ['-dM', '-E', '-']
	try:
		p = Utils.pproc.Popen(cmd, stdin=Utils.pproc.PIPE, stdout=Utils.pproc.PIPE, stderr=Utils.pproc.PIPE)
		p.stdin.write('\n')
		out = p.communicate()[0]
	except:
		conf.fatal('could not determine the compiler version %r' % cmd)

	# PY3K: do not touch
	out = str(out)

	if gcc:
		if out.find('__INTEL_COMPILER') >= 0:
			conf.fatal('The intel compiler pretends to be gcc')
		if out.find('__GNUC__') < 0:
			conf.fatal('Could not determine the compiler type')

	if icc and out.find('__INTEL_COMPILER') < 0:
		conf.fatal('Not icc/icpc')

	k = {}
	if icc or gcc:
		out = out.split('\n')
		import shlex

		for line in out:
			lst = shlex.split(line)
			if len(lst)>2:
				key = lst[1]
				val = lst[2]
				k[key] = val

		def isD(var):
			return var in k

		def isT(var):
			return var in k and k[var] != '0'

		# Some documentation is available at http://predef.sourceforge.net

		mp1 = {
			'__linux__'   :'linux',
			'__FreeBSD__' :'freebsd',
			'__NetBSD__'  :'netbsd',
			'__OpenBSD__' :'openbsd',
			'__GNU__'     :'hurd',
			'_aix'        :'aix',
			'__hpux'      :'hpux',
			'__sgi'       :'irix',
			'__sun'       :'solaris',
			'__CYGWIN__'  :'cygwin',
			'__MSYS__'    :'msys',
			'_UWIN'       :'uwin',
			'_WIN32'      :'windows',
			}

		conf.env.DEST_OS = 'unknown'
		for i in mp1:
			if isD(i):
				conf.env.DEST_OS = mp1[i]
				break
		else:
			if isD('__APPLE__') and isD('__MACH__'):
				conf.env.DEST_OS = 'darwin'
			elif isD('__unix__'): # unix must be tested last as it's a generic fallback
				conf.env.DEST_OS = 'unix'

		if isD('__ELF__'):
			conf.env.DEST_BINFMT = 'elf'
		elif conf.env.DEST_OS == 'darwin':
			conf.env.DEST_BINFMT = 'mac-o'
		elif conf.env.DEST_OS in ('windows', 'cygwin', 'msys', 'uwin'):
			conf.env.DEST_BINFMT = 'pe'
		else:
			conf.env.DEST_BINFMT = 'unknown'

		mp2 = {
				'__x86_64__'  : 'x86_64',
				'__i386__'    : 'x86',
				'__ia64__'    : 'ia',
				'__mips__'    : 'mips',
				'__sparc__'   : 'sparc',
				'__alpha__'   : 'alpha',
				'__arm__'     : 'arm',
				'__hppa__'    : 'hppa',
				'__powerpc__' : 'powerpc',
				}
		conf.env.DEST_CPU = 'unknown'
		for i in mp2:
			if isD(i):
				conf.env.DEST_CPU = mp2[i]
				break

		debug('ccroot: dest platform: %(DEST_OS)s %(DEST_BINFMT)s %(DEST_CPU)s' % conf.env.table)
		conf.env['CC_VERSION'] = (k['__GNUC__'], k['__GNUC_MINOR__'], k['__GNUC_PATCHLEVEL__'])
	return k

class DEBUG_LEVELS:
	ULTRADEBUG = "ultradebug"
	DEBUG = "debug"
	RELEASE = "release"
	OPTIMIZED = "optimized"
	CUSTOM = "custom"

	ALL = [ULTRADEBUG, DEBUG, RELEASE, OPTIMIZED, CUSTOM]

def scan(self):
	"look for .h the .cpp need"
	debug('ccroot: _scan_preprocessor(self, node, env, path_lst)')

	# TODO waf 1.6 - assume the default input has exactly one file

	if len(self.inputs) == 1:
		node = self.inputs[0]
		(nodes, names) = preproc.get_deps(node, self.env, nodepaths = self.env['INC_PATHS'])
		if Logs.verbose:
			debug('deps: deps for %s: %r; unresolved %r' % (str(node), nodes, names))
		return (nodes, names)

	all_nodes = []
	all_names = []
	seen = []
	for node in self.inputs:
		(nodes, names) = preproc.get_deps(node, self.env, nodepaths = self.env['INC_PATHS'])
		if Logs.verbose:
			debug('deps: deps for %s: %r; unresolved %r' % (str(node), nodes, names))
		for x in nodes:
			if id(x) in seen: continue
			seen.append(id(x))
			all_nodes.append(x)
		for x in names:
			if not x in all_names:
				all_names.append(x)
	return (all_nodes, all_names)

class ccroot_abstract(TaskGen.task_gen):
	"Parent class for programs and libraries in languages c, c++ and moc (Qt)"
	def __init__(self, *k, **kw):
		# COMPAT remove in waf 1.6 TODO
		if len(k) > 1:
			k = list(k)
			if k[1][0] != 'c':
				k[1] = 'c' + k[1]
		TaskGen.task_gen.__init__(self, *k, **kw)

def get_target_name(self):
	tp = 'program'
	for x in self.features:
		if x in ['cshlib', 'cstaticlib']:
			tp = x.lstrip('c')

	pattern = self.env[tp + '_PATTERN']
	if not pattern: pattern = '%s'

	dir, name = os.path.split(self.target)

	if self.env.DEST_BINFMT == 'pe' and getattr(self, 'vnum', None) and 'cshlib' in self.features:
		# include the version in the dll file name,
		# the import lib file name stays unversionned.
		name = name + '-' + self.vnum.split('.')[0]

	return os.path.join(dir, pattern % name)

@feature('cc', 'cxx')
@before('apply_core')
def default_cc(self):
	"""compiled_tasks attribute must be set before the '.c->.o' tasks can be created"""
	Utils.def_attrs(self,
		includes = '',
		defines= '',
		rpaths = '',
		uselib = '',
		uselib_local = '',
		add_objects = '',
		p_flag_vars = [],
		p_type_vars = [],
		compiled_tasks = [],
		link_task = None)

	if not self.env.DEST_OS:
		try:
			self.env.DEST_OS = {
				'linux2': 'linux',
				'win32': 'windows',
				# TODO etc
			}[sys.platform]
		except KeyError:
			self.env.DEST_OS = 'unknown'

		if self.env.DEST_OS in ('windows', 'cygwin', 'msys', 'uwin'):
			self.env.DEST_BINFMT = 'pe'
		elif self.env.DEST_OS == 'darwin':
			self.env.DEST_BINFMT = 'mac-o'
		else:
			self.env.DEST_BINFMT = 'unknown'

	if not self.env.BINDIR: self.env.BINDIR = self.env['${PREFIX}/bin']
	if not self.env.LIBDIR: self.env.LIBDIR = self.env['${PREFIX}/lib${LIB_EXT}']

@feature('cprogram', 'dprogram', 'cstaticlib', 'dstaticlib', 'cshlib', 'dshlib')
def apply_verif(self):
	"""no particular order, used for diagnostic"""
	if not (self.source or getattr(self, 'add_objects', None)):
		raise Utils.WafError('no source files specified for %s' % self)
	if not self.target:
		raise Utils.WafError('no target for %s' % self)

# TODO reference the d programs, shlibs in d.py, not here

@feature('cprogram', 'dprogram')
@before('apply_core')
def vars_target_cprogram(self):
	self.default_install_path = self.env.BINDIR
	self.default_chmod = O755

@feature('cstaticlib', 'dstaticlib')
@before('apply_core')
def vars_target_cstaticlib(self):
	self.default_install_path = self.env.LIBDIR

@feature('cshlib', 'dshlib')
@before('apply_core')
def vars_target_cshlib(self):
	if self.env.DEST_BINFMT == 'pe':
		#   set execute bit on libs to avoid 'permission denied' (issue 283)
		self.default_chmod = O755
		self.default_install_path = self.env.BINDIR
	else:
		self.default_install_path = self.env.LIBDIR

@feature('cprogram', 'dprogram', 'cstaticlib', 'dstaticlib', 'cshlib', 'dshlib')
@after('apply_objdeps', 'apply_link')
def install_target_cstaticlib(self):
	self.link_task.install_path = self.install_path

@feature('cshlib', 'dshlib')
@after('apply_link')
def install_target_cshlib(self):
	"""execute after the link task (apply_link)"""

	if self.env.DEST_BINFMT == 'pe' or os.name != 'posix' or not getattr(self, 'vnum', ''):
		return

	bld = self.bld
	nums = self.vnum.split('.')

	path = self.install_path
	if not path: return
	libname = self.link_task.outputs[0].name

	if libname.endswith('.dylib'):
		name3 = libname.replace('.dylib', '.%s.dylib' % task.vnum)
		name2 = libname.replace('.dylib', '.%s.dylib' % nums[0])
	else:
		name3 = libname + '.' + self.vnum
		name2 = libname + '.' + nums[0]

	filename = self.link_task.outputs[0].abspath(self.env)
	bld.install_as(os.path.join(path, name3), filename, env=self.env)
	bld.symlink_as(os.path.join(path, name2), name3)
	bld.symlink_as(os.path.join(path, libname), name3)

	self.link_task.install = None

@feature('cc', 'cxx')
@after('apply_type_vars', 'apply_lib_vars', 'apply_core')
def apply_incpaths(self):
	"""used by the scanner
	after processing the uselib for CPPPATH
	after apply_core because some processing may add include paths
	"""
	lst = []
	# TODO move the uselib processing out of here
	for lib in self.to_list(self.uselib):
		for path in self.env['CPPPATH_' + lib]:
			if not path in lst:
				lst.append(path)
	if preproc.go_absolute:
		for path in preproc.standard_includes:
			if not path in lst:
				lst.append(path)

	for path in self.to_list(self.includes):
		if not path in lst:
			if preproc.go_absolute or not os.path.isabs(path):
				lst.append(path)
			else:
				self.env.prepend_value('CPPPATH', path)

	for path in lst:
		node = None
		if os.path.isabs(path):
			if preproc.go_absolute:
				node = self.bld.root.find_dir(path)
		elif path[0] == '#':
			node = self.bld.srcnode
			if len(path) > 1:
				node = node.find_dir(path[1:])
		else:
			node = self.path.find_dir(path)

		if node:
			self.env.append_value('INC_PATHS', node)

	# TODO WAF 1.6
	if USE_TOP_LEVEL:
		self.env.append_value('INC_PATHS', self.bld.srcnode)

@feature('cc', 'cxx')
@after('init_cc', 'init_cxx')
@before('apply_lib_vars')
def apply_type_vars(self):
	"""before apply_lib_vars because we modify uselib
	after init_cc and init_cxx because web need p_type_vars
	"""
	for x in self.features:
		if not x in ['cprogram', 'cstaticlib', 'cshlib']:
			continue
		x = x.lstrip('c')

		# if the type defines uselib to add, add them
		st = self.env[x + '_USELIB']
		if st: self.uselib = self.uselib + ' ' + st

		# each compiler defines variables like 'shlib_CXXFLAGS', 'shlib_LINKFLAGS', etc
		# so when we make a task generator of the type shlib, CXXFLAGS are modified accordingly
		for var in self.p_type_vars:
			compvar = '%s_%s' % (x, var)
			#print compvar
			value = self.env[compvar]
			if value: self.env.append_value(var, value)

@feature('cprogram', 'cshlib', 'cstaticlib')
@after('apply_core')
def apply_link(self):
	"""executes after apply_core for collecting 'compiled_tasks'
	use a custom linker if specified (self.link='name-of-custom-link-task')"""
	link = getattr(self, 'link', None)
	if not link:
		if 'cstaticlib' in self.features: link = 'ar_link_static'
		elif 'cxx' in self.features: link = 'cxx_link'
		else: link = 'cc_link'

		if getattr(self, 'vnum', '') and 'cshlib' in self.features:
			if self.env.DEST_BINFMT != 'pe':
				link = 'vnum_' + link

	tsk = self.create_task(link)
	outputs = [t.outputs[0] for t in self.compiled_tasks]
	tsk.set_inputs(outputs)
	tsk.set_outputs(self.path.find_or_declare(get_target_name(self)))
	tsk.chmod = self.chmod

	self.link_task = tsk

@feature('cc', 'cxx')
@after('apply_link', 'init_cc', 'init_cxx')
def apply_lib_vars(self):
	"""after apply_link because of 'link_task'
	after default_cc because of the attribute 'uselib'"""
	env = self.env

	# 1. the case of the libs defined in the project (visit ancestors first)
	# the ancestors external libraries (uselib) will be prepended
	uselib = self.to_list(self.uselib)
	names = self.to_list(self.uselib_local)

	seen = []
	tmp = names[:] # consume a copy of the list of names
	while tmp:
		lib_name = tmp.pop(0)
		# visit dependencies only once
		if lib_name in seen:
			continue

		y = self.name_to_obj(lib_name)
		if not y:
			raise Utils.WafError('object %r was not found in uselib_local (required by %r)' % (lib_name, self.name))
		y.post()
		seen.append(lib_name)

		# object has ancestors to process (shared libraries): add them to the end of the list
		if getattr(y, 'uselib_local', None):
			lst = y.to_list(y.uselib_local)
			tmp.extend(lst)

		# link task and flags
		if getattr(y, 'link_task', None):

			link_name = y.target[y.target.rfind(os.sep) + 1:]
			if 'cstaticlib' in y.features:
				if not lib_name in names:
					continue
				env.append_value('STATICLIB', link_name)
			elif 'cshlib' in y.features or 'cprogram' in y.features:
				# WARNING some linkers can link against programs
				env.append_value('LIB', link_name)

			# the order
			self.link_task.set_run_after(y.link_task)

			# for the recompilation
			dep_nodes = getattr(self.link_task, 'dep_nodes', [])
			self.link_task.dep_nodes = dep_nodes + y.link_task.outputs

			# add the link path too
			tmp_path = y.link_task.outputs[0].parent.bldpath(self.env)
			if not tmp_path in env['LIBPATH']: env.prepend_value('LIBPATH', tmp_path)

		# add ancestors uselib too
		# WARNING providing STATICLIB_FOO in env will result in broken builds
		# TODO waf 1.6 prevent this behaviour somehow
		for v in self.to_list(y.uselib):
			if v in uselib: continue
			uselib = [v] + uselib

		# if the library task generator provides 'export_incdirs', add to the include path
		# the export_incdirs must be a list of paths relative to the other library
		if getattr(y, 'export_incdirs', None):
			for x in self.to_list(y.export_incdirs):
				node = y.path.find_dir(x)
				if not node:
					raise Utils.WafError('object %r: invalid folder %r in export_incdirs' % (y.target, x))
				self.env.append_unique('INC_PATHS', node)

	# 2. the case of the libs defined outside
	for x in uselib:
		for v in self.p_flag_vars:
			val = self.env[v + '_' + x]
			if val: self.env.append_value(v, val)

@feature('cprogram', 'cstaticlib', 'cshlib')
@after('apply_obj_vars', 'apply_vnum', 'apply_link')
def apply_objdeps(self):
	"add the .o files produced by some other object files in the same manner as uselib_local"
	if not getattr(self, 'add_objects', None): return

	seen = []
	names = self.to_list(self.add_objects)
	while names:
		x = names[0]

		# visit dependencies only once
		if x in seen:
			names = names[1:]
			continue

		# object does not exist ?
		y = self.name_to_obj(x)
		if not y:
			raise Utils.WafError("object '%s' was not found in uselib_local (required by add_objects '%s')" % (x, self.name))

		# object has ancestors to process first ? update the list of names
		if getattr(y, 'add_objects', None):
			added = 0
			lst = y.to_list(y.add_objects)
			lst.reverse()
			for u in lst:
				if u in seen: continue
				added = 1
				names = [u]+names
			if added: continue # list of names modified, loop

		# safe to process the current object
		y.post()
		seen.append(x)

		for t in y.compiled_tasks:
			self.link_task.inputs.extend(t.outputs)

@feature('cprogram', 'cshlib', 'cstaticlib')
@after('apply_lib_vars')
def apply_obj_vars(self):
	"""after apply_lib_vars for uselib"""
	v = self.env
	lib_st           = v['LIB_ST']
	staticlib_st     = v['STATICLIB_ST']
	libpath_st       = v['LIBPATH_ST']
	staticlibpath_st = v['STATICLIBPATH_ST']
	rpath_st         = v['RPATH_ST']

	app = v.append_unique

	if v['FULLSTATIC']:
		v.append_value('LINKFLAGS', v['FULLSTATIC_MARKER'])

	for i in v['RPATH']:
		if i and rpath_st:
			app('LINKFLAGS', rpath_st % i)

	for i in v['LIBPATH']:
		app('LINKFLAGS', libpath_st % i)
		app('LINKFLAGS', staticlibpath_st % i)

	if v['STATICLIB']:
		v.append_value('LINKFLAGS', v['STATICLIB_MARKER'])
		k = [(staticlib_st % i) for i in v['STATICLIB']]
		app('LINKFLAGS', k)

	# fully static binaries ?
	if not v['FULLSTATIC']:
		if v['STATICLIB'] or v['LIB']:
			v.append_value('LINKFLAGS', v['SHLIB_MARKER'])

	app('LINKFLAGS', [lib_st % i for i in v['LIB']])

@feature('cshlib')
@after('apply_link')
@before('apply_lib_vars')
def apply_vnum(self):
	"""use self.vnum and self.soname to modify the command line (un*x)
	before adding the uselib and uselib_local LINKFLAGS (apply_lib_vars)
	"""
	if self.env.DEST_BINFMT == 'elf':
		# this is very unix-specific
		try:
			nums = self.vnum.split('.')
		except AttributeError:
			pass
		else:
			try: name3 = self.soname
			except AttributeError: name3 = self.link_task.outputs[0].name + '.' + nums[0]
			self.link_task.outputs.append(self.link_task.outputs[0].parent.find_or_declare(name3))
			self.env.append_value('LINKFLAGS', (self.env['SONAME_ST'] % name3).split())

@after('apply_link')
def process_obj_files(self):
	if not hasattr(self, 'obj_files'): return
	for x in self.obj_files:
		node = self.path.find_resource(x)
		self.link_task.inputs.append(node)

@taskgen
def add_obj_file(self, file):
	"""Small example on how to link object files as if they were source
	obj = bld.create_obj('cc')
	obj.add_obj_file('foo.o')"""
	if not hasattr(self, 'obj_files'): self.obj_files = []
	if not 'process_obj_files' in self.meths: self.meths.append('process_obj_files')
	self.obj_files.append(file)

c_attrs = {
'cxxflag' : 'CXXFLAGS',
'cflag' : 'CCFLAGS',
'ccflag' : 'CCFLAGS',
'linkflag' : 'LINKFLAGS',
'ldflag' : 'LINKFLAGS',
'lib' : 'LIB',
'libpath' : 'LIBPATH',
'staticlib': 'STATICLIB',
'staticlibpath': 'STATICLIBPATH',
'rpath' : 'RPATH',
'framework' : 'FRAMEWORK',
'frameworkpath' : 'FRAMEWORKPATH'
}

@feature('cc', 'cxx')
@before('init_cxx', 'init_cc') # TODO not certain why
@before('apply_lib_vars', 'apply_obj_vars', 'apply_incpaths', 'init_cc')
def add_extra_flags(self):
	"""case and plural insensitive
	before apply_obj_vars for processing the library attributes
	"""
	for x in self.__dict__.keys():
		y = x.lower()
		if y[-1] == 's':
			y = y[:-1]
		if c_attrs.get(y, None):
			self.env.append_unique(c_attrs[y], getattr(self, x))

def link_vnum(self):
	"""special case for versioned libraries on unix platforms"""
	clsname = self.__class__.__name__.replace('vnum_', '')
	out = self.outputs
	self.outputs = out[1:]
	ret = Task.TaskBase.classes[clsname].__dict__['run'](self)
	self.outputs = out
	if ret:
		return ret
	try:
		os.remove(self.outputs[0].abspath(self.env))
	except OSError:
		pass
	try:
		os.symlink(self.outputs[1].name, self.outputs[0].bldpath(self.env))
	except:
		return 1

# ============ the code above must not know anything about import libs ==========

@feature('cshlib')
@before('apply_link')
def set_link_task(self):
	if not self.env.DEST_BINFMT == 'pe':
		return
	if not getattr(self, 'link', None):
		self.link = 'dll_cc_link'
		if 'cxx' in self.features:
			self.link = 'dll_cxx_link'

@feature('no_implib')
@before('apply_implib')
def disable_implib(self):
	if 'cshlib' not in self.features:
		raise Utils.WafError('feature "no_implib" requires "cshlib"')
	# There does not seem to be a way not to generate the import lib on msvc.
	if self.env.CC_NAME != 'msvc':
		self.meths.remove('apply_implib')

@feature('cshlib')
@after('apply_link')
@before('apply_lib_vars', 'apply_objdeps')
def apply_implib(self):
	"""On mswindows, handle dlls and their import libs
	the .dll.a is the import lib and it is required for linking so it is installed too
	"""
	if not self.env.DEST_BINFMT == 'pe':
		return

	# disable the normal installation
	self.link_task.install = None

	bindir = self.install_path
	if not bindir: return

	# install the dll in the bin dir
	dll = self.link_task.outputs[0]
	self.bld.install_as(bindir + os.sep + dll.name, dll, self.env, self.chmod)

	# add linker flags to generate the import lib
	dll = self.link_task.outputs[0]
	implib = self.env['implib_PATTERN'] % os.path.split(self.target)[1]
	no_implib = 'no_implib' in self.features
	if no_implib:
		# There does not seem to be a way not to generate the import lib on msvc,
		# so if the 'no_implib' feature was specified, we set a filename that the linker won't find.
		implib += '.disabled'

	implib = dll.parent.find_or_declare(implib)
	if not no_implib:
		self.link_task.outputs.append(implib)
	else:
		# install the import lib in the lib dir
		node = self.link_task.outputs[1]
		self.bld.install_as('${LIBDIR}/%s' % node.name, node, self.env)

	self.env.append_value('LINKFLAGS', (self.env['IMPLIB_ST'] % implib.bldpath(self.env)).split())

