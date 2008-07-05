#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"base for all c/c++ programs and libraries"

import os, sys, re
import TaskGen, Utils, preproc, Logs, Build, Options
from Logs import error, debug, fatal, warn
from Utils import md5
from TaskGen import taskgen, after, before, feature
from Constants import *

import config_c # <- necessary for the configuration, do not touch

get_version_re = re.compile('\d+\.\d+(\.?\d+)*')
def get_cc_version(conf, cc, version_var):
	v = conf.env
	output = os.popen('%s -dumpversion' % cc).read()
	if output:
		match = get_version_re.search(output)
		if match:
			v[version_var] = match.group(0)
			conf.check_message('compiler', 'version', 1, v[version_var])
			return v[version_var]
	warn('could not determine the compiler version')

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
	all_nodes = []
	all_names = []
	seen = []
	for node in self.inputs:
		gruik = preproc.c_parser(nodepaths = self.env['INC_PATHS'], defines = self.defines)
		gruik.start(node, self.env)
		if Logs.verbose:
			debug('deps: nodes found for %s: %s %s' % (str(node), str(gruik.m_nodes), str(gruik.m_names)))
			debug('deps: deps found for %s: %s' % (str(node), str(gruik.deps)))
		for x in gruik.m_nodes:
			if id(x) in seen: continue
			seen.append(id(x))
			all_nodes.append(x)
		for x in gruik.m_names:
			if not x in all_names:
				all_names.append(x)
	return (all_nodes, gruik.m_names)

class ccroot_abstract(TaskGen.task_gen):
	"Parent class for programs and libraries in languages c, c++ and moc (Qt)"
	def __init__(self, *k, **kw):
		TaskGen.task_gen.__init__(self, *k)

		# TODO m_type is obsolete
		if len(k)>1: self.m_type = k[1]
		else: self.m_type = ''
		if self.m_type:
			self.features.append('c' + self.m_type)

		# includes, seen from the current directory
		self.includes=''

		self.defines = ''
		self.rpaths = ''

		self.uselib = ''

		# new scheme: provide the names of the local libraries to link with
		# the objects found will be post()-ed
		self.uselib_local=''

		# add .o files produced by another task_gen class (task generator names)
		self.add_objects = ''

		# version number for shared libraries
		#self.vnum='1.2.3' #
		#self.soname='.so.3' # else soname is computed from vnum

		#self.program_chmod = 0755 # by default: 0755

		# do not forget to set the following variables in a subclass
		self.p_flag_vars = []
		self.p_type_vars = []

		#self.link = '' # optional: kind of link to apply (ar, cc, cxx, ..)

		self.scanner_defines = {}

		self.compiled_tasks = []
		self.link_task = None

		# characteristics of what we want to build: cc, cpp, program, staticlib, shlib, etc
		#self.features = ['program']

	def clone(self, env):
		new_obj = TaskGen.task_gen.clone(self, env)
		variant = '_' + self.env.variant()

		if self.name: new_obj.name = self.name + variant
		else: new_obj.name = self.target + variant
		new_obj.uselib_local = [x + variant for x in Utils.to_list(self.uselib_local) ]
		return new_obj

def get_target_name(self):
	name = self.target
	pattern = self.env[self.m_type+'_PATTERN']
	if not pattern: pattern = '%s'

	# name can be src/mylib
	k = name.rfind('/')
	return name[0:k+1] + pattern % name[k+1:]

@taskgen
def apply_verif(self):
	if not 'objects' in self.features:
		if not self.source:
			fatal('no source files specified for %s' % self)
		if not self.target:
			fatal('no target for %s' % self)

def install_shlib(task):
	nums = task.vnum.split('.')

	inst_var = task.inst_var
	inst_dir = task.inst_dir

	libname = task.outputs[0].m_name

	name3 = libname+'.'+task.vnum
	name2 = libname+'.'+nums[0]
	name1 = libname

	filename = task.outputs[0].abspath(task.env)
	bld = Build.bld
	bld.install_as(inst_var, os.path.join(inst_dir, name3), filename, env=task.env)
	bld.symlink_as(inst_var, name3, os.path.join(inst_dir, name2))
	bld.symlink_as(inst_var, name3, os.path.join(inst_dir, name1))

# TODO reference the d programs, shlibs in d.py, not here

@taskgen
@feature('cprogram', 'dprogram')
@before('apply_core')
def vars_target_cprogram(self):
	self.inst_var_default = 'PREFIX'
	self.inst_dir_default = 'bin'

@taskgen
@feature('cstaticlib', 'dstaticlib')
@before('apply_core')
def vars_target_cstaticlib(self):
	self.inst_var_default = 'PREFIX'
	self.inst_dir_default = 'lib'

@taskgen
@feature('cshlib', 'dshlib')
@before('apply_core')
def vars_target_cshlib(self):
	self.inst_var_default = 'PREFIX'
	self.inst_dir_default = 'lib'

@taskgen
@feature('cprogram', 'dprogram')
@after('apply_objdeps')
def install_target_cprogram(self):
	if not Options.is_install: return
	try: mode = self.program_chmod
	except AttributeError: mode = 0755
	self.link_task.install = {'var':self.inst_var,'dir':self.inst_dir,'chmod':mode}

@taskgen
@feature('cstaticlib', 'dstaticlib')
@after('apply_objdeps')
def install_target_cstaticlib(self):
	if not Options.is_install: return
	self.link_task.install = {'var':self.inst_var,'dir':self.inst_dir}

@taskgen
@feature('cshlib', 'dshlib')
@after('apply_objdeps')
def install_target_cshlib(self):
	if not Options.is_install: return
	if getattr(self, 'vnum', '') and sys.platform != 'win32':
		tsk = self.link_task
		tsk.vnum = getattr(self, 'vnum', '')
		tsk.inst_var = self.inst_var
		tsk.inst_dir = self.inst_dir
		tsk.install = install_shlib
	else:
		self.link_task.install = {'var':self.inst_var,'dir':self.inst_dir}

@taskgen
@after('apply_type_vars')
def apply_incpaths(self):
	lst = []
	for i in self.to_list(self.uselib):
		if self.env['CPPPATH_'+i]:
			lst += self.to_list(self.env['CPPPATH_'+i])
	self.includes = getattr(self, 'includes', [])
	inc_lst = self.to_list(self.includes) + lst
	if preproc.go_absolute:
		inc_lst.extend(preproc.standard_includes)
	lst = []

	tree = Build.bld
	for dir in inc_lst:
		node = 0
		if os.path.isabs(dir):
			if preproc.go_absolute:
				node = Build.bld.m_root.find_dir(dir)
		else:
			node = self.path.find_dir(dir)

		if node is None:
			error("node not found in ccroot:apply_incpaths "+str(dir))
		elif node:
			if not node in lst: lst.append(node)
			Build.bld.rescan(node)
	self.env['INC_PATHS'] = self.env['INC_PATHS'] + lst
	# now the nodes are added to self.incpaths_lst

@taskgen
def apply_type_vars(self):
	# if the type defines uselib to add, add them
	st = self.env[self.m_type+'_USELIB']
	if st: self.uselib = self.uselib + ' ' + st

	# each compiler defines variables like 'shlib_CXXFLAGS', 'shlib_LINKFLAGS', etc
	# so when we make a cppobj of the type shlib, CXXFLAGS are modified accordingly
	for var in self.p_type_vars:
		compvar = '_'.join([self.m_type, var])
		#print compvar
		value = self.env[compvar]
		if value: self.env.append_value(var, value)

@taskgen
@feature('cprogram', 'cshlib', 'cstaticlib')
@after('apply_core')
def apply_link(self):
	# use a custom linker if specified (self.link)
	link = getattr(self, 'link', None)
	if not link:
		if 'cstaticlib' in self.features: link = 'ar_link_static'
		elif 'cxx' in self.features: link = 'cxx_link'
		else: link = 'cc_link'
	linktask = self.create_task(link)
	outputs = [t.outputs[0] for t in self.compiled_tasks]
	linktask.set_inputs(outputs)
	linktask.set_outputs(self.path.find_or_declare(get_target_name(self)))

	self.link_task = linktask

@taskgen
@after('apply_vnum')
def apply_lib_vars(self):
	env = self.env

	# 1. the case of the libs defined in the project (visit ancestors first)
	# the ancestors external libraries (uselib) will be prepended
	uselib = self.to_list(self.uselib)
	seen = []
	names = [] + self.to_list(self.uselib_local) # consume a copy of the list of names
	while names:
		x = names.pop(0)
		# visit dependencies only once
		if x in seen:
			continue

		# object does not exist ?
		y = Build.bld.name_to_obj(x)
		if not y:
			fatal("object '%s' was not found in uselib_local (required by '%s')" % (x, self.name))

		# object has ancestors to process: add them to the end of the list
		if y.uselib_local:
			lst = y.to_list(y.uselib_local)
			for u in lst:
				if not u in seen:
					names.append(u)

		# safe to process the current object
		if not y.m_posted: y.post()
		seen.append(x)

		if 'cshlib' in y.features:
			env.append_value('LIB', y.target)
		elif 'cstaticlib' in y.features:
			env.append_value('STATICLIB', y.target)

		# add the link path too
		tmp_path = y.path.bldpath(self.env)
		if not tmp_path in env['LIBPATH']: env.prepend_value('LIBPATH', tmp_path)

		# set the dependency over the link task
		if y.link_task is not None:
			self.link_task.set_run_after(y.link_task)
			dep_nodes = getattr(self.link_task, 'dep_nodes', [])
			self.link_task.dep_nodes = dep_nodes + y.link_task.outputs

		# add ancestors uselib too
		morelibs = y.to_list(y.uselib)
		for v in morelibs:
			if v in uselib: continue
			uselib = [v]+uselib

		# if the library task generator provides 'export_incdirs', add to the include path
		# if no one uses this feature, it will be removed
		if getattr(y, 'export_incdirs', None):
			cpppath_st = self.env['CPPPATH_ST']
			app = self.env.append_unique
			for x in self.to_list(y.export_incdirs):
				node = y.path.find_dir(x)
				if not node: fatal('object %s: invalid folder %s in export_incdirs' % (y.target, x))
				if not node in self.env['INC_PATHS']: self.env['INC_PATHS'].append(node)

	# 2. the case of the libs defined outside
	for x in uselib:
		for v in self.p_flag_vars:
			val = self.env[v+'_'+x]
			if val: self.env.append_value(v, val)

@taskgen
@feature('cprogram', 'cshlib', 'cstaticlib')
@after('apply_obj_vars')
@after('apply_vnum')
def apply_objdeps(self):
	"add the .o files produced by some other object files in the same manner as uselib_local"
 	seen = []
	names = self.to_list(self.add_objects)
	while names:
		x = names[0]

		# visit dependencies only once
		if x in seen:
			names = names[1:]
			continue

		# object does not exist ?
		y = Build.bld.name_to_obj(x)
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

		self.link_task.inputs += y.out_nodes

@taskgen
@feature('cprogram', 'cshlib', 'cstaticlib')
@after('apply_lib_vars')
def apply_obj_vars(self):
	lib_st           = self.env['LIB_ST']
	staticlib_st     = self.env['STATICLIB_ST']
	libpath_st       = self.env['LIBPATH_ST']
	staticlibpath_st = self.env['STATICLIBPATH_ST']

	app = self.env.append_unique

	if self.env['FULLSTATIC']:
		self.env.append_value('LINKFLAGS', self.env['FULLSTATIC_MARKER'])

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

@taskgen
@feature('cprogram', 'cshlib', 'cstaticlib')
@after('apply_link')
def apply_vnum(self):
	"use self.vnum and self.soname to modify the command line (un*x)"
	try: vnum = self.vnum
	except AttributeError: return
	# this is very unix-specific
	if sys.platform != 'darwin' and sys.platform != 'win32':
		nums = self.vnum.split('.')
		try: name3 = self.soname
		except AttributeError: name3 = self.link_task.outputs[0].m_name+'.'+self.vnum.split('.')[0]
		self.env.append_value('LINKFLAGS', '-Wl,-h,'+name3)

@taskgen
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
	if not 'process_obj_files' in self.meths: self.meths.add('process_obj_files')
	self.obj_files.append(file)

@taskgen
@feature('objects')
@after('apply_core')
def make_objects_available(self):
	"""when we do not link; make the .o files available
	if we are only building .o files, tell which ones we built"""
	self.out_nodes = []
	app = self.out_nodes.append
	for t in self.compiled_tasks: app(t.outputs[0])

c_attrs = {
'cxxflag' : 'CXXFLAGS',
'cflag' : 'CCFLAGS',
'ccflag' : 'CCFLAGS',
'linkflag' : 'LINKFLAGS',
'ldflag' : 'LINKFLAGS',
'rpath' : 'RPATH',
}

@taskgen
@feature('cc', 'cxx')
@before('init_cxx')
@before('init_cc')
def add_extra_flags(self):
	"insentive for the case and for the plurals"
	for x in self.__dict__.keys():
		y = x.lower()
		if y[-1] == 's':
			y = y[:-1]
		if c_attrs.get(y, None):
			self.env.append_unique(c_attrs[y], getattr(self, x))

