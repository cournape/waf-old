#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"base for all c/c++ programs and libraries"

import os, sys, re, subprocess
from wafadmin import TaskGen, Task, Utils, Logs, Build, Options, Node, Errors
from wafadmin.Logs import error, debug, warn
from wafadmin.Utils import md5
from wafadmin.TaskGen import after, before, feature, taskgen_method
from wafadmin.Configure import conf
from wafadmin.Tools import preproc

import config_c # <- necessary for the configuration, do not touch

@conf
def get_cc_version(conf, cc, gcc=False, icc=False):
	"""get the compiler version"""
	cmd = cc + ['-dM', '-E', '-']
	try:
		p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		p.stdin.write(b'\n')
		out = p.communicate()[0].decode('utf-8')
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
		# The names given to DEST_OS must match what Utils.unversioned_sys_platform() returns.
		mp1 = {
			'__linux__'   : 'linux',
			'__GNU__'     : 'gnu',
			'__FreeBSD__' : 'freebsd',
			'__NetBSD__'  : 'netbsd',
			'__OpenBSD__' : 'openbsd',
			'__sun'       : 'sunos',
			'__hpux'      : 'hpux',
			'__sgi'       : 'irix',
			'_AIX'        : 'aix',
			'__CYGWIN__'  : 'cygwin',
			'__MSYS__'    : 'msys',
			'_UWIN'       : 'uwin',
			'_WIN64'      : 'win32',
			'_WIN32'      : 'win32',
			}

		for i in mp1:
			if isD(i):
				conf.env.DEST_OS = mp1[i]
				break
		else:
			if isD('__APPLE__') and isD('__MACH__'):
				conf.env.DEST_OS = 'darwin'
			elif isD('__unix__'): # unix must be tested last as it's a generic fallback
				conf.env.DEST_OS = 'generic'

		if isD('__ELF__'):
			conf.env.DEST_BINFMT = 'elf'

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
		for i in mp2:
			if isD(i):
				conf.env.DEST_CPU = mp2[i]
				break

		debug('ccroot: dest platform: ' + ' '.join([conf.env[x] or '?' for x in ('DEST_OS', 'DEST_BINFMT', 'DEST_CPU')]))
		conf.env['CC_VERSION'] = (k['__GNUC__'], k['__GNUC_MINOR__'], k['__GNUC_PATCHLEVEL__'])
	return k

# ============ the --as-needed flag should added during the configuration, not at runtime =========

@conf
def add_as_needed(conf):
	if conf.env.DEST_BINFMT == 'elf' and 'gcc' in (conf.env.CXX_NAME, conf.env.CC_NAME):
		conf.env.append_unique('LINKFLAGS', '--as-needed')

# =================================================================================================

def scan(self):
	"scanner for c and c++ tasks, uses the python-based preprocessor from the module preproc.py (task method)"
	debug('ccroot: _scan_preprocessor(self, node, env, path_lst)')

	node = self.inputs[0]
	(nodes, names) = preproc.get_deps(node, self.env, nodepaths = self.env['INC_PATHS'])
	if Logs.verbose:
		debug('deps: deps for %s: %r; unresolved %r' % (str(node), nodes, names))
	return (nodes, names)

@taskgen_method
def create_compiled_task(self, name, node):
	"""
	creates the compilation task: cc, cxx, asm, ...
	the task is appended to the list 'compiled_tasks' which is used by
	'apply_link'
	"""
	out = '%s.%d.o' % (node.name, self.idx)
	task = self.create_task(name, node, node.parent.find_or_declare(out))
	try:
		self.compiled_tasks.append(task)
	except AttributeError:
		self.compiled_tasks = [task]
	return task

@taskgen_method
def get_dest_binfmt(self):
	# The only thing we need for cross-compilation is DEST_BINFMT.
	# At some point, we may reach a case where DEST_BINFMT is not enough, but for now it's sufficient.
	# Currently, cross-compilation is auto-detected only for the gnu and intel compilers.
	if not self.env.DEST_BINFMT:
		# Infer the binary format from the os name.
		self.env.DEST_BINFMT = Utils.unversioned_sys_platform_to_binary_format(
			self.env.DEST_OS or Utils.unversioned_sys_platform())

@taskgen_method
def get_target_name(self):
	tp = 'program'
	for x in self.features:
		if x in ['cshlib', 'cstlib']:
			tp = x.lstrip('c')

	pattern = self.env[tp + '_PATTERN']
	if not pattern: pattern = '%s'

	dir, name = os.path.split(self.target)

	if self.get_dest_binfmt() == 'pe' and getattr(self, 'vnum', None) and 'cshlib' in self.features:
		# include the version in the dll file name,
		# the import lib file name stays unversionned.
		name = name + '-' + self.vnum.split('.')[0]

	return os.path.join(dir, pattern % name)

@feature('cc', 'cxx')
@before('process_source')
def default_cc(self):
	"""compiled_tasks attribute must be set before the '.c->.o' tasks can be created"""
	Utils.def_attrs(self,
		defines= '',
		rpaths = '',
		uselib = '',
		uselib_local = '',
		add_objects = '',
		p_flag_vars = [],
		compiled_tasks = [],
		link_task = None)

@feature('cc', 'cxx')
@after('apply_lib_vars')
def apply_defines(self):
	"""after uselib is set for DEFINES"""
	self.defines = getattr(self, 'defines', [])

	lst = self.to_list(self.defines) + self.to_list(self.env['DEFINES'])
	milst = []

	# now process the local defines
	for defi in lst:
		if not defi in milst:
			milst.extend(self.to_list(defi))

	# DEFINES_USELIB
	libs = self.to_list(self.uselib)
	for l in libs:
		val = self.env['DEFINES_'+l]
		if val:
			milst += self.to_list(val)

	self.env['DEFLINES'] = ['%s %s' % (x[0], Utils.trimquotes('='.join(x[1:]))) for x in [y.split('=') for y in milst]]
	y = self.env['DEFINES_ST']
	self.env['_DEFFLAGS'] = [y%x for x in milst]

@feature('cc', 'cxx', 'd', 'asm')
@after('apply_lib_vars', 'process_source')
def apply_incpaths(self):
	"""used by the scanner
	after processing the uselib for INCLUDES
	after process_source because some processing may add include paths
	"""

	paths = self.to_list(getattr(self, 'includes', []))
	for lib in self.to_list(self.uselib):
		for path in self.env['INCLUDES_' + lib]:
			paths.append(path)

	lst = []
	seen = set([])
	for path in paths:

		if path in seen:
			continue
		seen.add(path)

		if isinstance(path, Node.Node):
			lst.append(node)
		else:
			if os.path.isabs(path):
				lst.append(self.bld.root.make_node(path))
			else:
				if path[0] == '#':
					lst.append(self.bld.bldnode.make_node(path[1:]))
					lst.append(self.bld.srcnode.make_node(path[1:]))
				else:
					lst.append(self.path.get_bld().make_node(path))
					lst.append(self.path.make_node(path))

	self.env.append_value('INC_PATHS', lst)
	cpppath_st = self.env['CPPPATH_ST']
	self.env.append_unique('_INCFLAGS', [cpppath_st % x.abspath() for x in self.env['INC_PATHS']])

@feature('cprogram', 'cshlib', 'cstlib')
@after('process_source')
def apply_link(self):
	"""executes after process_source for collecting 'compiled_tasks'
	use a custom linker if specified (self.link='name-of-custom-link-task')"""
	link = getattr(self, 'link', None)
	if not link:
		if 'cstlib' in self.features: link = 'static_link'
		elif 'cxx' in self.features: link = 'cxx_link'
		else: link = 'cc_link'

	objs = [t.outputs[0] for t in self.compiled_tasks]
	out = self.path.find_or_declare(self.get_target_name())
	self.link_task = self.create_task(link, objs, out)

	if getattr(self, 'is_install', None):
		if not self.env.BINDIR:
			self.env.BINDIR = Utils.subst_vars('${PREFIX}/bin', self.env)
		if not self.env.LIBDIR:
			self.env.LIBDIR = Utils.subst_vars('${PREFIX}/lib${LIB_EXT}', self.env)

		if 'cprogram' in self.features or 'dprogram' in self.features:
			inst = '${BINDIR}'
		else:
			inst = '${LIBDIR}'
		self.install_task = bld.install_files(inst, out, env=self.env)

@feature('cc', 'cxx')
@after('apply_link', 'init_cc', 'init_cxx')
def apply_lib_vars(self):
	"""after apply_link because of 'link_task'
	after default_cc because of the attribute 'uselib'"""
	env = self.env

	# 0.
	# each compiler defines variables like 'shlib_CXXFLAGS', 'shlib_LINKFLAGS', etc
	# so when we make a task generator of the type shlib, CXXFLAGS are modified accordingly
	for x in self.features:
		if not x in ['cprogram', 'cstlib', 'cshlib']:
			continue
		x = x.lstrip('c')
		for var in ['CCFLAGS', 'CXXFLAGS', 'LINKFLAGS']:
			compvar = '%s_%s' % (x, var)
			self.env.append_value(var, self.env[compvar])

	# 1. the case of the libs defined in the project (visit ancestors first)
	# the ancestors external libraries (uselib) will be prepended
	self.uselib = self.to_list(self.uselib)
	names = self.to_list(self.uselib_local)
	get = self.bld.get_tgen_by_name
	seen = set([])
	tmp = Utils.deque(names) # consume a copy of the list of names
	while tmp:
		lib_name = tmp.popleft()
		# visit dependencies only once
		if lib_name in seen:
			continue

		y = get(lib_name)
		y.post()
		seen.add(lib_name)

		# object has ancestors to process (shared libraries): add them to the end of the list
		if getattr(y, 'uselib_local', None):
			lst = y.to_list(y.uselib_local)
			if 'cshlib' in y.features or 'cprogram' in y.features:
				lst = [x for x in lst if not 'cstlib' in get(x).features]
			tmp.extend(lst)

		# link task and flags
		if getattr(y, 'link_task', None):

			link_name = y.target[y.target.rfind(os.sep) + 1:]
			if 'cstlib' in y.features:
				env.append_value('STATICLIB', [link_name])
			elif 'cshlib' in y.features or 'cprogram' in y.features:
				# WARNING some linkers can link against programs
				env.append_value('LIB', [link_name])

			# the order
			self.link_task.set_run_after(y.link_task)

			# for the recompilation
			dep_nodes = getattr(self.link_task, 'dep_nodes', [])
			self.link_task.dep_nodes = dep_nodes + y.link_task.outputs

			# add the link path too
			tmp_path = y.link_task.outputs[0].parent.bldpath()
			if not tmp_path in env['LIBPATH']: env.prepend_value('LIBPATH', [tmp_path])

		# add ancestors uselib too - but only propagate those that have no staticlib
		for v in self.to_list(getattr(y, 'uselib', [])):
			if not env['STATICLIB_' + v]:
				if not v in self.uselib:
					self.uselib.insert(0, v)

		# if the library task generator provides 'export_incdirs', add to the include path
		# the export_incdirs must be a list of paths relative to the other library
		if getattr(y, 'export_incdirs', None):
			for x in self.to_list(y.export_incdirs):
				node = y.path.find_dir(x)
				if not node:
					raise Errors.WafError('object %r: invalid folder %r in export_incdirs' % (y.target, x))
				self.includes.append(node)

	# 2. the case of the libs defined outside
	for x in self.uselib:
		for v in self.p_flag_vars:
			val = self.env[v + '_' + x]
			if val: self.env.append_value(v, val)

@feature('cprogram', 'cstlib', 'cshlib', 'dprogram', 'dstlib', 'dshlib')
@after('init_cc', 'init_cxx', 'apply_link')
def apply_objdeps(self):
	"add the .o files produced by some other object files in the same manner as uselib_local"
	if not getattr(self, 'add_objects', None): return

	get = self.bld.get_tgen_by_name
	seen = []
	names = self.to_list(self.add_objects)
	while names:
		x = names[0]

		# visit dependencies only once
		if x in seen:
			names = names[1:]
			continue

		# object does not exist ?
		y = get(x)

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

@feature('cprogram', 'cshlib', 'cstlib')
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
		v.append_value('LINKFLAGS', [v['FULLSTATIC_MARKER']])

	for i in v['RPATH']:
		if i and rpath_st:
			app('LINKFLAGS', rpath_st % i)

	for i in v['LIBPATH']:
		app('LINKFLAGS', [libpath_st % i])
		app('LINKFLAGS', [staticlibpath_st % i])

	if v['STATICLIB']:
		v.append_value('LINKFLAGS', [v['STATICLIB_MARKER']])
		k = [(staticlib_st % i) for i in v['STATICLIB']]
		app('LINKFLAGS', k)

	# fully static binaries ?
	if not v['FULLSTATIC']:
		if v['STATICLIB'] or v['LIB']:
			v.append_value('LINKFLAGS', [v['SHLIB_MARKER']])

	app('LINKFLAGS', [lib_st % i for i in v['LIB']])

@after('apply_link')
def process_obj_files(self):
	if not hasattr(self, 'obj_files'):
		return
	for x in self.obj_files:
		node = self.path.find_resource(x)
		self.link_task.inputs.append(node)

@taskgen_method
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
@before('init_cxx', 'init_cc')
@before('apply_lib_vars', 'apply_obj_vars', 'apply_incpaths', 'init_cc')
def add_extra_flags(self):
	"""
	process additional task generator attributes such as cflags → CFLAGS, see c_attrs above
	case and plural insensitive
	before apply_obj_vars for processing the library attributes
	"""
	for x in self.__dict__.keys():
		y = x.lower()
		if y[-1] == 's':
			y = y[:-1]
		if c_attrs.get(y, None):
			self.env.append_unique(c_attrs[y], getattr(self, x))

# ============ the code above must not know anything about import libs ==========

@feature('cshlib', 'implib')
@after('apply_link', 'default_cc')
@before('apply_lib_vars', 'apply_objdeps')
def apply_implib(self):
	"""On mswindows, handle dlls and their import libs
	the .dll.a is the import lib and it is required for linking so it is installed too
	"""
	if not self.get_dest_binfmt() == 'pe':
		return

	bindir = self.install_path
	if not bindir: return

	# install the dll in the bin dir
	dll = self.link_task.outputs[0]
	self.bld.install_files(bindir, dll, self.env, self.chmod)

	# add linker flags to generate the import lib
	implib = self.env['implib_PATTERN'] % os.path.split(self.target)[1]

	implib = dll.parent.find_or_declare(implib)
	self.link_task.outputs.append(implib)
	self.implib_install_task = self.bld.install_as('${LIBDIR}/%s' % implib.name, implib, self.env)

	self.env.append_value('LINKFLAGS', (self.env['IMPLIB_ST'] % implib.bldpath()).split())

# ============ the code above must not know anything about vnum processing on unix platforms =========

@feature('cshlib', 'dshlib', 'vnum')
@after('apply_link')
def apply_vnum(self):
	"""
	libfoo.so is installed as libfoo.so.1.2.3
	create symlinks libfoo.so → libfoo.so.1.2.3 and libfoo.so.1 → libfoo.so.1.2.3
	"""
	if not getattr(self, 'vnum', '') or not 'cshlib' in self.features or os.name != 'posix' or self.get_dest_binfmt() not in ('elf', 'mac-o'):
		return

	link = self.link_task
	nums = self.vnum.split('.')
	node = link.outputs[0]

	libname = node.name
	if libname.endswith('.dylib'):
		name3 = libname.replace('.dylib', '.%s.dylib' % self.vnum)
		name2 = libname.replace('.dylib', '.%s.dylib' % nums[0])
	else:
		name3 = libname + '.' + self.vnum
		name2 = libname + '.' + nums[0]

	# add the so name for the ld linker - to disable, just unset env.SONAME_ST
	if self.env.SONAME_ST:
		v = self.env.SONAME_ST % name2
		self.env.append_value('LINKFLAGS', v.split())

	if not getattr(self, 'is_install', None):
		return

	path = getattr(self, 'install_path', None)
	if not path:
		return

	# the following task is just to enable execution from the build dir :-/
	tsk = self.create_task('vnum')
	tsk.set_inputs([node])
	tsk.set_outputs(node.parent.find_or_declare(name2))

	self.install_task.hasrun = Task.SKIP_ME
	bld = self.bld
	t1 = bld.install_as(path + os.sep + name3, node, env=self.env)
	t2 = bld.symlink_as(path + os.sep + name2, name3)
	t3 = bld.symlink_as(path + os.sep + libname, name3)
	self.vnum_install_task = (t1, t2, t3)

class vnum_task(Task.Task):
	color = 'CYAN'
	quient = True
	ext_in = ['.bin']
	def run(self):
		path = self.outputs[0].abspath()
		try:
			os.remove(path)
		except OSError:
			pass

		try:
			os.symlink(self.inputs[0].name, path)
		except OSError:
			return 1

# ============ aliases, let's see if people use them ==============

def sniff_features(**kw):
	"""look at the source files and return the features (mainly cc and cxx)"""
	has_c = False
	has_cxx = False
	s = Utils.to_list(kw['source'])
	for name in s:
		if name.endswith('.c'):
			has_c = True
		elif name.endswith('.cxx') or name.endswith('.cpp') or name.endswith('.c++'):
			has_cxx = True
	lst = []
	if has_c:
		lst.append('cc')
	if has_cxx:
		lst.append('cxx')
	return lst

def Program(bld, *k, **kw):
	"""alias for features='cc cprogram' bound to the build context"""
	if not 'features' in kw:
		kw['features'] = ['cprogram'] + sniff_features(**kw)
	return bld(*k, **kw)
Build.BuildContext.Program = Program

def Shlib(bld, *k, **kw):
	"""alias for features='cc cshlib' bound to the build context"""
	if not 'features' in kw:
		kw['features'] = ['cshlib'] + sniff_features(**kw)
	return bld(*k, **kw)
Build.BuildContext.Shlib = Shlib

def Stlib(bld, *k, **kw):
	"""alias for features='cc cstlib' bound to the build context"""
	if not 'features' in kw:
		kw['features'] = ['cstlib'] + sniff_features(**kw)
	return bld(*k, **kw)
Build.BuildContext.Stlib = Stlib

