#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"""
The class task_gen encapsulates the creation of task objects (low-level code)
The instances can have various parameters, but the creation of task nodes
is delayed. To achieve this, various methods are called from the method "apply"

The class task_gen contains lots of methods, and a configuration table:
* the methods to call (self.meths) can be specified dynamically (removing, adding, ..)
* the order of the methods (self.prec or by default task_gen.prec) is configurable
* new methods can be inserted dynamically without pasting old code

Additionally, task_gen provides the method apply_core
* file extensions are mapped to methods: def meth(self, name_or_node)
* if a mapping is not found in self.mappings, it is searched in task_gen.mappings
* when called, the functions may modify self.allnodes to re-add source to process
* the mappings can map an extension or a filename (see the code below)

WARNING 1 subclasses must reimplement the clone method to avoid problems with 'deepcopy'
WARNING 2 find a new name for this file (naming it 'Object' was never a good idea)
"""

import os, types, traceback, sys, copy
import Params, Task, Common, Node, Utils, Action
from Params import debug, error, fatal

typos = {
'sources':'source',
'targets':'target',
'include':'includes',
'define':'defines',
'importpath':'importpaths',
'install_var':'inst_var',
'install_subdir':'inst_dir',
}

g_allobjs = []
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
		launch_dir_node = tree.m_srcnode
	if not launch_dir_node.is_child_of(tree.m_srcnode):
		launch_dir_node = tree.m_srcnode

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

class register_obj(type):
	"""no decorators for classes, so we use a metaclass
	we store into task_gen.classes the classes that inherit task_gen
	and whose names end in 'obj'
	"""
	def __init__(cls, name, bases, dict):
		super(register_obj, cls).__init__(name, bases, dict)
		name = cls.__name__
		if name != 'task_gen' and not name.endswith('_abstract'):
			task_gen.classes[name.replace('_taskgen', '')] = cls

class task_gen(object):
	"""
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

	Additionally, a 'traits' static attribute is provided:
	* this list contains methods
	* the methods can remove or add methods from self.meths
	Example1: the attribute 'staticlib' is set on an instance
	a method set in the list of traits is executed when the
	instance is posted, it finds that flag and adds another method for execution
	Example2: a method set in the list of traits finds the msvc
	compiler (from self.env['MSVC']==1); more methods are added to self.meths
	"""

	__metaclass__ = register_obj
	mappings = {}
	mapped = {}
	prec = {}
	traits = {}
	classes = {}

	def __init__(self, *kw):
		self.prec = {}
		"map precedence of function names to call"
		# so we will have to play with directed acyclic graphs
		# detect cycles, etc

		self.source = ''
		self.target = ''

		# list of methods to execute - in general one does not touch it by hand
		self.meths = set(['apply_core'])

		# list of mappings extension -> function
		self.mappings = {}

		# list of features (see the documentation on traits)
		self.features = list(kw)

		# not always a good idea
		self.m_tasks = []

		self.chmod = 0644
		self.inst_var = 0 # 0 to prevent installation
		self.inst_dir = ''

		if Params.g_install:
			self.inst_files = [] # lazy list of tuples representing the files to install

		# kind of private, beware of what you put in it, also, the contents are consumed
		self.allnodes = []

		self.env = Params.g_build.m_allenvs['default'].copy()

		self.m_posted = 0
		self.path = Params.g_build.m_curdirnode # emulate chdir when reading scripts
		self.name = '' # give a name to the target (static+shlib with the same targetname ambiguity)
		g_allobjs.append(self)

	def __str__(self):
		return ("<task_gen '%s' of type %s defined in %s>"
			% (self.name or self.target, self.__class__.__name__, str(self.path)))

	def __setattr__(self, name, attr):
		real = typos.get(name, name)
		if real != name:
			Params.warning('typo %s -> %s' % (name, real))
			if Params.g_verbose > 0:
				traceback.print_stack()
		object.__setattr__(self, real, attr)

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

	def install(self):
		# FIXME
		# ambiguity with the install functions
		# it is often better to install the targets right after they are up-to_date
		# but this means attaching the install to the task objects
		if not Params.g_install: return
		for (name, var, dir, chmod) in self.inst_files:
			print name, var, dir, chmod

	# TODO ugly code
	def install_results(self, var, subdir, task, chmod=0644):
		debug('install results called', 'object')
		if not task: return
		current = Params.g_build.m_curdirnode
		lst = [a.relpath_gen(current) for a in task.m_outputs]
		Common.install_files(var, subdir, lst, chmod=chmod, env=self.env)

	def meth_order(self, *k):
		"this one adds the methods to the list of methods"
		assert(len(k) > 1)
		n = len(k) - 1
		for i in xrange(n):
			f1 = k[i]
			f2 = k[i+1]
			try: self.prec[f2].append(f1)
			except: self.prec[f2] = [f1]
			if not f1 in self.meths: self.meths.append(f1)
			if not f2 in self.meths: self.meths.append(f2)

	def apply_core(self):
		# get the list of folders to use by the scanners
		# all our objects share the same include paths anyway
		tree = Params.g_build
		lst = self.to_list(self.source)
		find_source_lst = self.path.find_source_lst

		for filename in lst:
			# if self.mappings or task_gen.mappings contains a file of the same name
			x = self.get_hook(filename)
			if x:
				x(self, filename)
			else:
				node = find_source_lst(Utils.split_path(filename))
				if not node: fatal("source not found: %s in %s" % (filename, str(self.path)))
				self.allnodes.append(node)

		for node in self.allnodes:
			# self.mappings or task_gen.mappings map the file extension to a function
			filename = node.m_name
			k = max(0, filename.rfind('.'))
			x = self.get_hook(filename[k:])

			if not x:
				raise TypeError, "Do not know how to process %s in %s, mappings are %s" % \
					(str(node), str(self.__class__), str(self.__class__.mappings))
			x(self, node)

	def apply(self):
		"order the methods to execute using self.prec or task_gen.prec"
		dct = self.__class__.__dict__
		keys = self.meths

		# add the methods listed in the features
		for x in self.features:
			keys.update(task_gen.traits.get(x, ()))

		# copy the precedence table with the keys in self.meths
		prec = {}
		prec_tbl = self.prec or task_gen.prec
		for x in prec_tbl:
			if x in keys:
				prec[x] = prec_tbl[x]

		# elements disconnected
		tmp = []
		for a in prec:
			for x in prec.values():
				if a in x: break
			else:
				tmp.append(a)

		# topological sort
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
		self.meths = out

		# then we run the methods in order
		for x in out:
			v = self.get_meth(x)
			debug("apply "+x, 'task_gen')
			v()

	def post(self):
		"runs the code to create the tasks, do not subclass"
		if not self.name: self.name = self.target

		if self.m_posted:
			error("OBJECT ALREADY POSTED")
			return
		self.apply()
		debug("posted %s" % self.name, 'object')
		self.m_posted = 1

	def get_hook(self, ext):
		try: return self.mappings[ext]
		except KeyError:
			try: return task_gen.mappings[ext]
			except KeyError: return None

	def get_meth(self, name):
		try:
			return getattr(self, name)
		except AttributeError:
			raise AttributeError, "tried to retrieve %s which is not a valid method" % name

	def create_task(self, type, env=None, nice=None):
		task = Task.Task(type, env or self.env)
		if nice: task.prio = nice
		self.m_tasks.append(task)
		return task

	def find_sources_in_dirs(self, dirnames, excludes=[], exts=[]):
		"subclass if necessary"
		lst = []
		excludes = self.to_list(excludes)
		#make sure dirnames is a list helps with dirnames with spaces
		dirnames = self.to_list(dirnames)

		ext_lst = exts or self.mappings.keys() + task_gen.mappings.keys()

		# FIXME the following two lines should be removed
		try: ext_lst += self.s_default_ext
		except AttributeError: pass

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

def declare_extension(var, func):
	if type(var) is types.ListType:
		for x in var:
			task_gen.mappings[x] = func
	elif type(var) is types.StringType:
		task_gen.mappings[var] = func
	else:
		raise TypeError('declare extension takes either a list or a string %s' % str(var))
	task_gen.mapped[func.__name__] = func

def declare_order(*k):
	assert(len(k) > 1)
	n = len(k) - 1
	for i in xrange(n):
		f1 = k[i]
		f2 = k[i+1]
		try:
			if not f1 in task_gen.prec[f2]: task_gen.prec[f2].append(f1)
		except:
			task_gen.prec[f2] = [f1]

def declare_chain(name='', action='', ext_in=[], ext_out='', reentrant=1, color='BLUE', prio=40, install=0):
	"""
	see Tools/flex.py for an example
	while i do not like such wrappers, some people really do
	"""

	if type(action) == types.StringType:
		Action.simple_action(name, action, color=color, prio=prio)
	else:
		name = action.name

	def x_file(self, node):
		if type(ext_out) == types.StringType:
			ext = ext_out
		else:
			ext = ext_out(self, node)

		if type(ext) == types.StringType:
			out_source = node.change_ext(ext)
			if reentrant:
				self.allnodes.append(out_source)
		elif type(ext) == types.ListType:
			out_source = [node.change_ext(x) for x in ext]
			if reentrant:
				for i in xrange(reentrant):
					self.allnodes.append(out_source[i])
		else:
			fatal("do not know how to process %s" % str(ext))

		tsk = self.create_task(name)
		tsk.set_inputs(node)
		tsk.set_outputs(out_source)

		if Params.g_install and install:
			tsk.install = install

	declare_extension(ext_in, x_file)

def add_feature(name, methods):
	lst = Utils.to_list(methods)
	try:
		l = task_gen.traits[name]
	except KeyError:
		l = set()
		task_gen.traits[name] = l
	l.update(lst)

# decorators follow

def taskgen(f):
	setattr(task_gen, f.__name__, f)

def feature(name):
	def deco(f):
		#print name, f
		try:
			l = task_gen.traits[name]
		except KeyError:
			l = set()
			task_gen.traits[name] = l
		l.update([f.__name__])
		return f
	return deco

def before(fun_name):
	def deco(f):
		try:
			if not f.__name__ in task_gen.prec[fun_name]: task_gen.prec[fun_name].append(f.__name__)
		except KeyError:
			task_gen.prec[fun_name] = [f.__name__]
		return f
	return deco

def after(fun_name):
	def deco(f):
		try:
			if not fun_name in task_gen.prec[f.__name__]: task_gen.prec[f.__name__].append(fun_name)
		except KeyError:
			task_gen.prec[f.__name__] = [fun_name]
		return f
	return deco

def extension(var):
	if type(var) is types.ListType:
		pass
	elif type(var) is types.StringType:
		var = [var]
	else:
		raise TypeError('declare extension takes either a list or a string %s' % str(var))

	def deco(f):
		for x in var:
			task_gen.mappings[x] = f
		task_gen.mapped[f.__name__] = f
		return f
	return deco

