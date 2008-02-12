#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"""
genobj is an abstract class for declaring targets:
  - creates tasks (consisting of a task, an environment, a list of source and list of target)
  - sets environment on the tasks (which are copies most of the time)
  - modifies environments as needed
  - genobj cannot be used as it is, so you must create a subclass

subclassing
  - makes it possible to share environment copies for several objects at once (efficiency)
  - be careful to call Object.genobj.__init__(...) in the __init__ of your subclass
  - examples are ccroot, ocamlobj, ..

hooks
  - declare new kind of targets quickly (give a pattern ? and the action name)
  - several extensions are mapped to a single method
  - they do not work with all objects (work with ccroot)
  - cf bison.py and flex.py for more details on this scheme

WARNING subclasses must reimplement the clone method to avoid problems with 'deepcopy'
"""

import copy
import os, types
import Params, Task, Common, Node, Utils
from Params import debug, error, fatal

g_allobjs=[]
"contains all objects, provided they are created (not in distclean or in dist)"
#TODO part of the refactoring to eliminate the static stuff (Utils.reset)

g_name_to_obj = {}

def name_to_obj(name):
	global g_name_to_obj
	if not g_name_to_obj:
		for x in g_allobjs:
			if x.name:
				g_name_to_obj[x.name] = x
			elif not x.target in g_name_to_obj.keys():
				g_name_to_obj[x.target] = x
	return g_name_to_obj.get(name, None)

def flush(all=1):
	"object instances under the launch directory create the tasks now"
	global g_allobjs
	global g_name_to_obj

	# force the initialization of the mapping name->object in flush
	# name_to_obj can be used in userland scripts, in that case beware of incomplete mapping
	g_name_to_obj = {}
	name_to_obj(None)

	tree = Params.g_build
	debug("delayed operation Object.flush() called", 'object')

	# post only objects below a particular folder (recursive make behaviour)
	launch_dir_node = tree.m_root.find_dir(Params.g_cwd_launch)
	if launch_dir_node.is_child_of(tree.m_bldnode):
		launch_dir_node=tree.m_srcnode

	if Params.g_options.compile_targets:
		debug('posting objects listed in compile_targets', 'object')

		# ensure the target names exist, fail before any post()
		targets_objects = {}
		for target_name in Params.g_options.compile_targets.split(','):
			# trim target_name (handle cases when the user added spaces to targets)
			target_name = target_name.strip()
			targets_objects[target_name] = name_to_obj(target_name)
			if all and not targets_objects[target_name]: fatal("target '%s' does not exist" % target_name)

		for target_obj in targets_objects.values():
			if target_obj and not target_obj.m_posted:
				target_obj.post()
	else:
		debug('posting objects (normal)', 'object')
		for obj in g_allobjs:
			if launch_dir_node and not obj.path.is_child_of(launch_dir_node): continue
			if not obj.m_posted: obj.post()

class genobj(object):
	def __init__(self, type):
		self.m_posted = 0
		self.path = Params.g_build.m_curdirnode # emulate chdir when reading scripts
		self.name = '' # give a name to the target (static+shlib with the same targetname ambiguity)

		# targets / sources
		self.source = ''
		self.target = ''

		# collect all tasks in a list - a few subclasses need it
		self.m_tasks = []

		# no default environment - in case if
		self.env = None

		if not type in self.get_valid_types():
			error("'%s' is not a valid type (error in %s)" % (type, self))
		self.m_type  = type

		# allow delayed operations on objects created (declarative style)
		# an object is then posted when another one is added
		# Objects can be posted manually, but this can break a few things, use with care
		# used at install time too
		g_allobjs.append(self)

	def __str__(self):
		return ("<genobj '%s' of type %s defined in %s>"
			% (self.name or self.target,
			   self.__class__.__name__, str(self.path)))

	def get_valid_types(self):
		return ['program', 'shlib', 'staticlib', 'plugin', 'objects', 'other']

	def get_hook(self, ext):
		env = self.env
		cls = self.__class__
		x = []
		while 1:
			try:
				cls.all_hooks
			except AttributeError:
				try: cls = cls.__bases__[0]
				except IndexError: return None
			else:
				for i in cls.all_hooks:
					if ext in env[i]:
						try:
							return cls.__dict__[i]
						except KeyError:
							break
				try: cls = cls.__bases__[0]
				except IndexError: return None
		return None

	def __setattr__(self, name, attr):
		if   name == 'sources': raise AttributeError, 'typo: self.sources -> self.source'
		elif name == 'targets': raise AttributeError, 'typo: self.targets -> self.target'
		elif name == 'include': raise AttributeError, 'typo: self.include -> self.includes'
		elif name == 'define':  raise AttributeError, 'typo: self.define -> self.defines'
		elif name == 'install_var':  raise AttributeError, 'typo: self.install_var -> self.inst_var'
		elif name == 'install_subdir':  raise AttributeError, 'typo: self.install_subdir -> self.inst_dir'
		object.__setattr__(self, name, attr)

	def post(self):
		"runs the code to create the tasks, do not subclass"
		if not self.env: self.env = Params.g_build.m_allenvs['default']
		if not self.name: self.name = self.target

		if self.m_posted:
			error("OBJECT ALREADY POSTED")
			return
		self.apply()
		debug("posted %s" % self.name, 'object')
		self.m_posted=1

	def create_task(self, type, env=None, nice=None):
		"""the lower the nice is, the higher priority tasks will run at
		groups are sorted in ascending order [2, 3, 4], the tasks with lower nice will run first
		if tasks have an odd priority number, they will be run only sequentially
		if tasks have an even priority number, they will be allowed to be run in parallel
		"""
		if env is None: env=self.env
		task = Task.Task(type, env)
		if not (nice is None): task.prio = nice
		self.m_tasks.append(task)
		return task

	def apply(self):
		"Subclass me"
		fatal("subclass me!")

	def install(self):
		"subclass me"
		pass

	def cleanup(self):
		"subclass me if necessary"
		pass

	def install_results(self, var, subdir, task, chmod=0644):
		debug('install results called', 'object')
		if not task: return
		current = Params.g_build.m_curdirnode
		lst = [a.relpath_gen(current) for a in task.m_outputs]
		Common.install_files(var, subdir, lst, chmod=chmod, env=self.env)

	def clone(self, env):
		newobj = copy.deepcopy(self)
		newobj.path = self.path

		if type(env) is types.StringType:
			newobj.env = Params.g_build.m_allenvs[env]
		else:
			newobj.env = env

		g_allobjs.append(newobj)

		return newobj

	def to_list(self, value):
		"helper: returns a list"
		if type(value) is types.StringType: return value.split()
		else: return value

	def find_sources_in_dirs(self, dirnames, excludes=[]):
		"subclass if necessary"
		lst=[]
		excludes = self.to_list(excludes)
		#make sure dirnames is a list helps with dirnames with spaces
		dirnames = self.to_list(dirnames)

		# FIXME temporary - see also qt4.py
		ext_lst = []
		cls = self.__class__
		while 1:
			try:
				cls.all_hooks
			except AttributeError:
				try: cls = cls.__bases__[0]
				except IndexError: break
			else:
				for i in cls.all_hooks:
					ext_lst += self.env[i]
				try: cls = cls.__bases__[0]
				except IndexError: break
		try:
			ext_lst += self.s_default_ext
		except AttributeError:
			pass

		for name in dirnames:
			anode = self.path.ensure_node_from_lst(Utils.split_path(name))
			Params.g_build.rescan(anode)

			for file in anode.files():
				(base, ext) = os.path.splitext(file.m_name)
				if ext in ext_lst:
					s = file.relpath(self.path)
					if not s in lst:
						if s in excludes: continue
						lst.append(s)

		lst.sort()
		self.source = self.to_list(self.source)
		if not self.source: self.source = lst
		else: self.source += lst

class task_gen(object):
	"""
	TODO: This class is not used yet - it is part of the ccroot class reorganization

	Most methods are of the form 'def meth(self):' without any parameters
	there are many of them, and they do many different things:
	* task creation
	* task results installation
	* environment modification
	* attribute addition/removal

	The inheritance approach is complicated
	* mixing several languages at once
	* subclassing is needed even for small changes
	* inserting new methods is complicated

	This new class uses a configuration table:
	* adding new methods easily
	* obtaining the order in which to call the methods
	* postponing the method calls (post() -> apply)
	"""

	mappings = {}

	def __init__(self):
		self.prec = {}
		"map precedence of function names to call"
		# so we will have to play with directed acyclic graphs
		# detect cycles, etc

		self.source = ''
		self.target = ''

		# list of methods to execute
		self.meths = []

		# not always a good idea
		self.m_tasks = []

		self.chmod = 0644
		self.inst_var = '' # 0 to prevent installation
		self.inst_dir = ''

		self.mappings = {}

		self.env = None
		self.m_posted = 0
		self.path = Params.g_build.m_curdirnode # emulate chdir when reading scripts
		self.name = '' # give a name to the target (static+shlib with the same targetname ambiguity)
		g_allobjs.append(self)

	def __str__(self):
		return ("<genobj '%s' of type %s defined in %s>"
			% (self.name or self.target,
			   self.__class__.__name__, str(self.path)))

	def to_list(self, value):
		"helper: returns a list"
		if type(value) is types.StringType: return value.split()
		else: return value

	def addflags(self, var, value):
		"utility function add self.cxxflags -> env['CXXFLAGS']"
		self.env.append_value(var, self.to_list(value))

	def add_method(self, name):
		"add a method to execute"
		# TODO adding functions ?
		self.meths.append(name)

	def set_order(self, f1, f2):
		try: self.prec[f2].append(f1)
		except: self.prec[f2] = [f1]
		if not f1 in self.meths: self.meths.append(f1)
		if not f2 in self.meths: self.meths.append(f2)

	def apply_core(self):
		# get the list of folders to use by the scanners
		# all our objects share the same include paths anyway
		tree = Params.g_build
		self.allnodes = []
		lst = self.to_list(self.source)
		find_source_lst = self.path.find_source_lst
		for filename in lst:
			# FIXME TODO allow hooks by name or partial match, like for mixing ocaml + c or other things
			node = find_source_lst(Utils.split_path(filename))
			if not node: fatal("source not found: %s in %s" % (filename, str(self.path)))
			self.allnodes.append(node)

		while self.allnodes:
			node = self.allnodes.pop()
			# Extract the extension and look for a handler hook.
			filename = node.m_name
			k = max(0, filename.rfind('.'))
			x = self.get_hook(filename[k:])

			if not x:
				print self.__class__.mappings
				raise TypeError, "Do not know how to process %s in %s" % (str(node), str(self.__class__))
			x(self, node)

	def apply(self):
		"use hook_table to create the tasks"
		dct = self.__class__.__dict__
		keys = self.meths

		# copy the precence table with the keys in self.meths
		prec = {}
		for x in self.prec:
			if x in keys:
				prec[x] = self.prec[x]

		# list of elements coming first (without dependency)
		tmp = []
		for a in prec:
			for x in prec.values():
				if a in x: break
			else:
				tmp.append(a)

		# then the topological sort
		out = []
		while tmp:
			e = tmp.pop()
			if e in keys: out.append(e)
			try:
				nlst = prec[e]
			except KeyError:
				pass
			else:
				del prec[e]
				for x in nlst:
					for y in prec:
						if x in prec[y]:
							break
					else:
						tmp.append(x)

		if prec: fatal("graph has a cycle" % str(prec))
		out.reverse()

		# then we run the methods in order
		for x in out:
			v = self.get_meth(x)
			debug("apply "+x, 'task_gen')
			v()

	def post(self):
		"runs the code to create the tasks, do not subclass"
		if not self.env: self.env = Params.g_build.m_allenvs['default']
		if not self.name: self.name = self.target

		if self.m_posted:
			error("OBJECT ALREADY POSTED")
			return
		self.apply()
		debug("posted %s" % self.name, 'object')
		self.m_posted=1

	def get_hook(self, ext):
		map = self.mappings
		for x in self.mappings:
			if x == ext:
				return map[x]

		map = task_gen.mappings
		for x in map:
			if x == ext:
				return map[x]

		return None

	def get_meth(self, name):
		try:
			return getattr(self, name)
		except AttributeError:
			raise AttributeError, "tried to retrieve %s which is not a valid method" % name

	def create_task(self, type, env=None, nice=None):
		if env is None: env=self.env
		task = Task.Task(type, env)
		if not (nice is None): task.prio = nice
		self.m_tasks.append(task)
		return task

	def find_sources_in_dirs(self, dirnames, excludes=[]):
		"subclass if necessary"
		lst=[]
		excludes = self.to_list(excludes)
		#make sure dirnames is a list helps with dirnames with spaces
		dirnames = self.to_list(dirnames)

		# FIXME temporary - see also qt4.py
		ext_lst = []
		cls = self.__class__
		while 1:
			try:
				cls.all_hooks
			except AttributeError:
				try: cls = cls.__bases__[0]
				except IndexError: break
			else:
				for i in cls.all_hooks:
					ext_lst += self.env[i]
				try: cls = cls.__bases__[0]
				except IndexError: break
		try:
			ext_lst += self.s_default_ext
		except AttributeError:
			pass

		for name in dirnames:
			anode = self.path.ensure_node_from_lst(Utils.split_path(name))
			Params.g_build.rescan(anode)

			for file in anode.files():
				(base, ext) = os.path.splitext(file.m_name)
				if ext in ext_lst:
					s = file.relpath(self.path)
					if not s in lst:
						if s in excludes: continue
						lst.append(s)

		lst.sort()
		self.source = self.to_list(self.source)
		if not self.source: self.source = lst
		else: self.source += lst

	def clone(self, env):
		newobj = copy.deepcopy(self)
		newobj.path = self.path

		if type(env) is types.StringType:
			newobj.env = Params.g_build.m_allenvs[env]
		else:
			newobj.env = env

		g_allobjs.append(newobj)

		return newobj

def gen_hook(name, meth):
	setattr(task_gen, name, meth)

# OBSOLETE
def hook(clsname, var, func):
	"Attach a new method to a genobj class"
	klass = g_allclasses[clsname]
	setattr(klass, var, func)
	try: klass.all_hooks.append(var)
	except AttributeError: klass.all_hooks = [var]

def declare_extension(var, func):
	if type(var) is types.ListType:
		for x in var:
			task_gen.mappings[x] = func
	elif type(var) is types.StringType:
		task_gen.mappings[var] = func
	else:
		raise TypeError('declare extension takes either a list or a string %s' % str(var))

g_cache_max={}
def sign_env_vars(env, vars_list):
	" ['CXX', ..] -> [env['CXX'], ..]"

	# ccroot objects use the same environment for building the .o at once
	# the same environment and the same variables are used
	s = str([env.m_idx]+vars_list)
	try: return g_cache_max[s]
	except KeyError: pass

	lst = [env.get_flat(a) for a in vars_list]
	ret = Params.h_list(lst)
	if Params.g_zones: debug("%s %s" % (Params.vsig(ret), str(lst)), 'envhash')

	# next time
	g_cache_max[s] = ret
	return ret

g_allclasses = {}
def register(name, classval):
	global g_allclasses
	g_allclasses[name] = classval

