#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"base for all c/c++ programs and libraries"

import sys, re, os

import Action, Object, Params, Scan, Common, Utils, preproc
from Params import error, debug, fatal, warning

class DEBUG_LEVELS:
	ULTRADEBUG = "ultradebug"
	DEBUG = "debug"
	RELEASE = "release"
	OPTIMIZED = "optimized"
	CUSTOM = "custom"

	ALL = [ULTRADEBUG, DEBUG, RELEASE, OPTIMIZED, CUSTOM]

class c_scanner(Scan.scanner):
	"scanner for c/c++ files"
	def __init__(self):
		Scan.scanner.__init__(self)
		self.vars = ('CCDEFINES', 'CXXDEFINES')

	def scan(self, task, node):
		"look for .h the .cpp need"
		debug("_scan_preprocessor(self, node, env, path_lst)", 'ccroot')
		gruik = preproc.c_parser(nodepaths = task.path_lst, defines = task.defines)
		gruik.start(node, task.env())
		if Params.g_verbose:
			debug("nodes found for %s: %s %s" % (str(node), str(gruik.m_nodes), str(gruik.m_names)), 'deps')
			debug("deps found for %s: %s" % (str(node), str(gruik.deps)), 'deps')
		return (gruik.m_nodes, gruik.m_names)

g_c_scanner = c_scanner()
"scanner for c programs"

class ccroot(Object.task_gen):
	"Parent class for programs and libraries in languages c, c++ and moc (Qt)"
	def __init__(self, type='program', subtype=None):
		Object.task_gen.__init__(self)

		# TODO obsolete
		self.m_type = type

		# includes, seen from the current directory
		self.includes=''

		# list of directories to enable when scanning
		# #include directives in source files for automatic
		# dependency tracking.  If left empty, scanning the
		# whole project tree is enabled.  If non-empty, only
		# the indicated directories (which must be relative
		# paths), plus the directories in obj.includes, are
		# scanned for #includes.
		self.dependencies = ''

		self.defines=''
		self.rpaths=''

		self.uselib=''

		# new scheme: provide the names of the local libraries to link with
		# the objects found will be post()-ed
		self.uselib_local=''

		# add .o files produced by another task_gen class
		self.add_objects = ''

		# version number for shared libraries
		#self.vnum='1.2.3' #
		#self.soname='.so.3' # else soname is computed from vnum

		#self.program_chmod = 0755 # by default: 0755

		# do not forget to set the following variables in a subclass
		self.p_flag_vars = []
		self.p_type_vars = []

		# TODO ???
		self.m_type_initials = ''

		# these are kind of private, do not touch
		self.incpaths_lst=[]
		self.inc_paths = []
		self.scanner_defines = {}
		self.bld_incpaths_lst=[]

		self.subtype = subtype

		self.compiled_tasks = []
		self.link_task = None

		# characteristics of what we want to build: cc, cpp, program, staticlib, shlib, etc
		#self.features = ['program']
# helper used only here
def get_target_name(self, ext=None):
	name = self.target
	v = self.env

	prefix = v[self.m_type+'_PREFIX']
	if self.subtype+'_PREFIX' in v.m_table:
		prefix = v[self.subtype+'_PREFIX']

	suffix = v[self.m_type+'_SUFFIX']
	if self.subtype+'_SUFFIX' in v.m_table:
		suffix = v[self.subtype+'_SUFFIX']

	if ext: suffix = ext
	if not prefix: prefix=''
	if not suffix: suffix=''

	# Handle the case where the name contains a directory src/mylib
	k=name.rfind('/')
	if k == -1:
		return ''.join([prefix, name, suffix])
	else:
		return name[0:k+1] + ''.join([prefix, name[k+1:], suffix])
Object.gen_hook(get_target_name)

def apply_verif(self):
	if not hasattr(self, 'nochecks'):
		if not (self.source or self.add_objects):
			fatal('no source files specified for %s' % self)
		if not self.target and self.m_type != 'objects':
			fatal('no target for %s' % self)
Object.gen_hook(apply_verif)

def install(self):
	if not hasattr(self, 'link_task'): return
	if not (Params.g_commands['install'] or Params.g_commands['uninstall']): return

	dest_var    = self.inst_var
	dest_subdir = self.inst_dir
	if dest_var == 0: return

	if not dest_var:
		dest_var = self.env[self.subtype+'_INST_VAR']
		dest_subdir = self.env[self.subtype+'_INST_DIR']

	if self.m_type == 'program':
		try: mode = self.program_chmod
		except AttributeError: mode = 0755
		self.install_results(dest_var, dest_subdir, self.link_task, chmod=mode)
	elif self.m_type == 'shlib' or self.m_type == 'plugin':

		try: nums = self.vnum.split('.')
		except AttributeError: nums = []

		if nums and sys.platform != 'win32':
			libname = self.link_task.m_outputs[0].m_name

			name3 = libname+'.'+self.vnum
			name2 = libname+'.'+nums[0]
			name1 = libname

			filename = self.link_task.m_outputs[0].relpath_gen(Params.g_build.m_curdirnode)
			Common.install_as(dest_var, dest_subdir+'/'+name3, filename, env=self.env)
			Common.symlink_as(dest_var, name3, dest_subdir+'/'+name2)
			Common.symlink_as(dest_var, name2, dest_subdir+'/'+name1)
		else:
			self.install_results(dest_var, dest_subdir, self.link_task)
	else:
		self.install_results(dest_var, dest_subdir, self.link_task, chmod=self.chmod)
Object.gen_hook(install)

def apply_dependencies(self):
	if self.dependencies:
		dep_lst = (self.to_list(self.dependencies) + self.to_list(self.includes))
		self.inc_paths = []
		for directory in dep_lst:
			if os.path.isabs(directory):
				Params.fatal("Absolute paths not allowed in obj.dependencies")
				return

			node = self.path.find_dir_lst(Utils.split_path(directory))
			if not node:
				Params.fatal("node not found in ccroot:apply_dependencies " + str(directory), 'ccroot')
				return
			if node not in self.inc_paths:
				self.inc_paths.append(node)
	else:
		# by default, we include the whole project tree
		lst = [self.path]
		for obj in Object.g_allobjs:
			if obj.path not in lst:
				lst.append(obj.path)
		self.inc_paths = lst + self.incpaths_lst
Object.gen_hook(apply_dependencies)

def apply_incpaths(self):
	lst = []
	for i in self.to_list(self.uselib):
		if self.env['CPPPATH_'+i]:
			lst += self.to_list(self.env['CPPPATH_'+i])
	inc_lst = self.to_list(self.includes) + lst
	lst = self.incpaths_lst

	# add the build directory
	self.incpaths_lst.append(Params.g_build.m_bldnode)
	self.incpaths_lst.append(Params.g_build.m_srcnode)

	# now process the include paths
	tree = Params.g_build
	for dir in inc_lst:
		if os.path.isabs(dir):
			self.env.append_value('CPPPATH', dir)
			continue

		node = self.path.find_dir_lst(Utils.split_path(dir))
		if not node:
			debug("node not found in ccroot:apply_incpaths "+str(dir), 'ccroot')
			continue
		if not node in lst: lst.append(node)
		Params.g_build.rescan(node)
		self.bld_incpaths_lst.append(node)
	# now the nodes are added to self.incpaths_lst
Object.gen_hook(apply_incpaths)

def apply_type_vars(self):

	# the subtype, used for all sorts of evil things
	if not self.subtype:
		if self.m_type in 'program staticlib plugin'.split():
			self.subtype = self.m_type
		else:
			self.subtype = 'shlib'

	# if the subtype defines uselib to add, add them
	st = self.env[self.subtype+'_USELIB']
	if st: self.uselib = self.uselib + ' ' + st

	# each compiler defines variables like 'shlib_CXXFLAGS', 'shlib_LINKFLAGS', etc
	# so when we make a cppobj of the type shlib, CXXFLAGS are modified accordingly
	for var in self.p_type_vars:
		compvar = '_'.join([self.m_type, var])
		#print compvar
		value = self.env[compvar]
		if value: self.env.append_value(var, value)
Object.gen_hook(apply_type_vars)

def apply_link(self):
	# if we are only building .o files, tell which ones we built
	# FIXME see msvc.py
	# FIXME remove the "type" thing
	if self.m_type == 'objects':
		self.out_nodes = []
		app = self.out_nodes.append
		for t in self.compiled_tasks: app(t.m_outputs[0])
		return

	if self.m_type=='staticlib':
		linktask = self.create_task('ar_link_static', self.env)
	else:
		linktask = self.create_task(self.m_type_initials+'_link', self.env)
	outputs = [t.m_outputs[0] for t in self.compiled_tasks]
	linktask.set_inputs(outputs)
	linktask.set_outputs(self.path.find_build(get_target_name(self)))

	self.link_task = linktask
Object.gen_hook(apply_link)

def apply_lib_vars(self):
	env=self.env

	# 1. the case of the libs defined in the project (visit ancestors first)
	# the ancestors external libraries (uselib) will be prepended
	uselib = self.to_list(self.uselib)
	seen = []
	names = self.to_list(self.uselib_local) # consume the list of names
	while names:
		x = names[0]

		# visit dependencies only once
		if x in seen:
			names = names[1:]
			continue

		# object does not exist ?
		y = Object.name_to_obj(x)
		if not y:
			fatal('object not found in uselib_local: obj %s uselib %s' % (self.name, x))
			names = names[1:]
			continue

		# object has ancestors to process: add them to the end of the list
		if y.uselib_local:
			lst = y.to_list(y.uselib_local)
			for u in lst:
				if u in seen: continue
				names.append(u)

		# safe to process the current object
		if not y.m_posted: y.post()
		seen.append(x)

		if y.m_type == 'shlib':
			env.append_value('LIB', y.target)
		elif y.m_type == 'plugin':
			if sys.platform == 'darwin': env.append_value('PLUGIN', y.target)
			else: env.append_value('LIB', y.target)
		elif y.m_type == 'staticlib':
			env.append_value('STATICLIB', y.target)
		elif y.m_type == 'objects':
			pass
		else:
			error('%s has unknown object type %s, in apply_lib_vars, uselib_local.'
			      % (y.name, y.m_type))

		# add the link path too
		tmp_path = y.path.bldpath(self.env)
		if not tmp_path in env['LIBPATH']: env.prepend_value('LIBPATH', tmp_path)

		# set the dependency over the link task
		if y.link_task is not None:
			self.link_task.set_run_after(y.link_task)
			dep_nodes = getattr(self.link_task, 'dep_nodes', [])
			self.link_task.dep_nodes = dep_nodes + y.link_task.m_outputs

		# add ancestors uselib too
		# TODO potential problems with static libraries ?
		morelibs = y.to_list(y.uselib)
		for v in morelibs:
			if v in uselib: continue
			uselib = [v]+uselib
		names = names[1:]

	# 2. the case of the libs defined outside
	for x in uselib:
		for v in self.p_flag_vars:
			val = self.env[v+'_'+x]
			if val: self.env.append_value(v, val)
Object.gen_hook(apply_lib_vars)

def apply_objdeps(self):
	"add the .o files produced by some other object files in the same manner as uselib_local"
	if not self.link_task: return
 	seen = []
	names = self.to_list(self.add_objects)
	while names:
		x = names[0]

		# visit dependencies only once
		if x in seen:
			names = names[1:]
			continue

		# object does not exist ?
		y = Object.name_to_obj(x)
		if not y:
			error('object not found in add_objects: obj %s add_objects %s' % (self.name, x))
			names = names[1:]
			continue

		# object has ancestors to process first ? update the list of names
		if y.add_objects:
			added = 0
			lst = y.to_list(y.add_objects)
			lst.reverse()
			for u in lst:
				if u in seen: continue
				added = 1
				names = [u]+names
			if added: continue # list of names modified, loop

		# safe to process the current object
		if not y.m_posted: y.post()
		seen.append(x)

		self.link_task.m_inputs += y.out_nodes
Object.gen_hook(apply_objdeps)

def apply_obj_vars(self):
	lib_st           = self.env['LIB_ST']
	staticlib_st     = self.env['STATICLIB_ST']
	libpath_st       = self.env['LIBPATH_ST']
	staticlibpath_st = self.env['STATICLIBPATH_ST']

	self.addflags('CPPFLAGS', self.cppflags)

	app = self.env.append_unique

	for i in self.env['RPATH']:
		app('LINKFLAGS', i)

	for i in self.env['LIBPATH']:
		app('LINKFLAGS', libpath_st % i)

	for i in self.env['LIBPATH']:
		app('LINKFLAGS', staticlibpath_st % i)

	if self.env['STATICLIB']:
		self.env.append_value('LINKFLAGS', self.env['STATICLIB_MARKER'])
		k = [(staticlib_st % i) for i in self.env['STATICLIB']]
		app('LINKFLAGS', k)

	# fully static binaries ?
	if not self.env['FULLSTATIC']:
		if self.env['STATICLIB'] or self.env['LIB']:
			self.env.append_value('LINKFLAGS', self.env['SHLIB_MARKER'])

	app('LINKFLAGS', [lib_st % i for i in self.env['LIB']])
Object.gen_hook(apply_obj_vars)

def apply_vnum(self):
	"use self.vnum and self.soname to modify the command line (un*x)"
	try: vnum = self.vnum
	except AttributeError: return
	# this is very unix-specific
	if sys.platform != 'darwin' and sys.platform != 'win32':
		nums = self.vnum.split('.')
		try: name3 = self.soname
		except AttributeError: name3 = self.link_task.m_outputs[0].m_name+'.'+self.vnum.split('.')[0]
		self.env.append_value('LINKFLAGS', '-Wl,-h,'+name3)
Object.gen_hook(apply_vnum)

Object.declare_order('apply_type_vars', 'apply_incpaths', 'apply_dependencies', 'apply_core',
	'apply_link', 'apply_vnum', 'apply_lib_vars', 'apply_obj_vars', 'apply_objdeps', 'install')


# Small example on how to link object files as if they were source
# obj = bld.create_obj('cc')
# obj.add_obj_file('foo.o')
#
def process_obj_files(self):
	if not hasattr(self, 'obj_files'): return
	for x in self.obj_files:
		node = self.path.find_source(x)
		self.link_task.m_inputs.append(node)

def add_obj_file(self, file):
	if not hasattr(self, 'obj_files'): self.obj_files = []
	if not 'process_obj_files' in self.meths: self.meths.add('process_obj_files')
	self.obj_files.append(file)

Object.gen_hook(add_obj_file)
Object.gen_hook(process_obj_files)
Object.declare_order('apply_link', 'process_obj_files')

