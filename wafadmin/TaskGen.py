#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"""
The class task_gen encapsulates the creation of task objects (low-level code)
The instances can have various parameters, but the creation of task nodes (Task.py)
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

WARNING: subclasses must reimplement the clone method
"""

import os, types, traceback, copy
import Params, Task, Utils
from logging import debug, error, fatal

typos = {
'sources':'source',
'targets':'target',
'include':'includes',
'define':'defines',
'importpath':'importpaths',
'install_var':'inst_var',
'install_subdir':'inst_dir',
'm_type_initials':'link',
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
	debug('task_gen: delayed operation TaskGen.flush() called')

	# post only objects below a particular folder (recursive make behaviour)
	launch_dir_node = tree.m_root.find_dir(Params.g_cwd_launch)
	if launch_dir_node.is_child_of(tree.m_bldnode):
		launch_dir_node = tree.m_srcnode
	if not launch_dir_node.is_child_of(tree.m_srcnode):
		launch_dir_node = tree.m_srcnode

	if Params.g_options.compile_targets:
		debug('task_gen: posting objects listed in compile_targets')

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
		debug('task_gen: posting objects (normal)')
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
	idx = {}

	def __init__(self, *kw, **kwargs):
		self.prec = {}
		"map precedence of function names to call"
		# so we will have to play with directed acyclic graphs
		# detect cycles, etc

		self.source = ''
		self.target = ''

		# list of methods to execute - in general one does not touch it by hand
		self.meths = set()

		# list of mappings extension -> function
		self.mappings = {}

		# list of features (see the documentation on traits)
		self.features = list(kw)

		# not always a good idea
		self.m_tasks = []

		self.chmod = 0644
		self._inst_var = ''
		self._inst_dir = ''

		if Params.g_install:
			self.inst_files = [] # lazy list of tuples representing the files to install

		# kind of private, beware of what you put in it, also, the contents are consumed
		self.allnodes = []

		self.env = Params.g_build.env.copy()

		self.m_posted = 0
		self.path = Params.g_build.path # emulate chdir when reading scripts
		self.name = '' # give a name to the target (static+shlib with the same targetname ambiguity)
		g_allobjs.append(self)


		# provide a unique id
		self.idx = task_gen.idx[self.path.id] = task_gen.idx.get(self.path.id, 0) + 1

		for key in kwargs:
			setattr(self, key, kwargs[key])

	def __str__(self):
		return ("<task_gen '%s' of type %s defined in %s>"
			% (self.name or self.target, self.__class__.__name__, str(self.path)))

	def __setattr__(self, name, attr):
		real = typos.get(name, name)
		if real != name:
			Params.warn('typo %s -> %s' % (name, real))
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
		debug('task_gen: install results called')
		if not task: return
		current = Params.g_build.path
		lst = [a.relpath_gen(current) for a in task.m_outputs]
		Params.g_build.install_files(var, subdir, lst, chmod=chmod, env=self.env)

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
		lst = self.to_list(self.source)

		# Validation: sources specified somehow
		# 	one can set self.source to None to avoid apply_core()
		if not lst is None:
			# sources can be supplied either by self.source or self.allnodes
			if len(lst) == 0 and not self.allnodes:
				fatal("no sources were specified for '%s'" % self.name)

		find_resource_lst = self.path.find_resource_lst

		for filename in lst:
			# if self.mappings or task_gen.mappings contains a file of the same name
			x = self.get_hook(filename)
			if x:
				x(self, filename)
			else:
				node = find_resource_lst(Utils.split_path(filename))
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
		keys = self.meths

		# add the methods listed in the features
		for x in self.features:
			keys.update(task_gen.traits.get(x, ()))

		# copy the precedence table
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

		if prec: fatal("graph has a cycle %s" % str(prec))
		out.reverse()
		self.meths = out

		if not out: out.append(self.apply_core.__name__)

		# then we run the methods in order
		debug('task_gen: posting %s %d' % (self, id(self)))
		for x in out:
			v = self.get_meth(x)
			debug('task_gen: -> %s (%d)' % (x, id(self)))
			v()

	def post(self):
		"runs the code to create the tasks, do not subclass"
		if not self.name: self.name = self.target

		if self.m_posted:
			error("OBJECT ALREADY POSTED")
			return
		self.apply()
		debug('task_gen: posted %s' % self.name)
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

	def create_task(self, name, env=None, nice=None):
		task = Task.g_task_types[name](env or self.env)
		if nice: task.prio = nice
		self.m_tasks.append(task)
		return task

	def find_sources_in_dirs(self, dirnames, excludes=[], exts=[]):
		"subclass if necessary"
		lst = []

		# validation: excludes and exts must be lists.
		# the purpose: make sure a confused user didn't wrote
		#  find_sources_in_dirs('a', 'b', 'c')
		# instead of find_sources_in_dirs('a b c')
		err_msg = "'%s' attribute must be a list.\n" \
		"Directories should be given either as a string separated by spaces, or as a list."
		not_a_list = lambda x: x and type(x) is not types.ListType
		if not_a_list(excludes):
			fatal(err_msg % 'excludes')
		if not_a_list(exts):
			fatal(err_msg % 'exts')

		#make sure dirnames is a list helps with dirnames with spaces
		dirnames = self.to_list(dirnames)

		ext_lst = exts or self.mappings.keys() + task_gen.mappings.keys()

		# FIXME the following two lines should be removed
		try: ext_lst += self.s_default_ext
		except AttributeError: pass

		for name in dirnames:
			anode = self.path.find_dir(name)

			# validation:
			# * don't use absolute path.
			# * don't use paths outside the source tree.
			if not anode or not anode.is_child_of(Params.g_build.m_srcnode):
				fatal("Unable to use '%s' - either because it's not a relative path" \
					 ", or it's not child of '%s'." % (name, Params.g_build.m_srcnode))

			Params.g_build.rescan(anode)

			for name in Params.g_build.cache_dir_contents[anode.id]:
				(base, ext) = os.path.splitext(name)
				if ext in ext_lst and not name in lst and not name in excludes:
					lst.append((anode.relative_path(self.path) or '.') + os.path.sep + name)

		lst.sort()
		self.source = self.to_list(self.source)
		if not self.source: self.source = lst
		else: self.source += lst

	def clone(self, env):
		""
		newobj = task_gen()
		for x in self.__dict__:
			if x in ["env"]:
				continue
			elif x in ["path", "features"]:
				setattr(newobj, x, getattr(self, x))
			else:
				setattr(newobj, x, copy.copy(getattr(self, x)))

		newobj.__class__ = self.__class__
		if type(env) is types.StringType:
			newobj.env = Params.g_build.m_allenvs[env].copy()
		else:
			newobj.env = env.copy()

		g_allobjs.append(newobj)

		return newobj

	def get_inst_var(self):
		"return a default parameter if provided"
		k = self._inst_var
		if k == 0: return k
		if not k: return getattr(self, "inst_var_default", k)
		return k

	def set_inst_var(self, val):
		self._inst_var = val

	inst_var = property(get_inst_var, set_inst_var)

	def get_inst_dir(self):
		"return a default parameter if provided"
		k = self._inst_dir
		if k == 0: return k
		if not k: return getattr(self, "inst_dir_default", k)
		return k

	def set_inst_dir(self, val):
		self._inst_dir = val

	inst_dir = property(get_inst_dir, set_inst_dir)

def declare_extension(var, func):
	try:
		for x in var:
			task_gen.mappings[x] = func
	except:
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

def declare_chain(name='', action='', ext_in='', ext_out='', reentrant=1, color='BLUE', install=0, before=[], after=[], decider=None):
	"""
	see Tools/flex.py for an example
	while i do not like such wrappers, some people really do
	"""

	if type(action) == types.StringType:
		act = Task.simple_task_type(name, action, color=color)
	else:
		act = Task.task_type_from_func(name, action, color=color)
		name = action.name
	act.ext_in = tuple(Utils.to_list(ext_in))
	act.ext_out = tuple(Utils.to_list(ext_out))
	act.before = Utils.to_list(before)
	act.after = Utils.to_list(after)

	def x_file(self, node):
		if decider:
			ext = decider(self, node)
		elif type(ext_out) == types.StringType:
			ext = ext_out

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

	declare_extension(act.ext_in, x_file)

def bind_feature(name, methods):
	lst = Utils.to_list(methods)
	try:
		l = task_gen.traits[name]
	except KeyError:
		l = set()
		task_gen.traits[name] = l
	l.update(lst)

"""
All the following decorators are registration decorators, i.e add an attribute to current class
 (task_gen and its derivatives), with same name as func, which points to func itself.
For example:
   @taskgen
   def sayHi(self):
        print "hi"
Now taskgen.sayHi() may be called
"""
def taskgen(func):
	setattr(task_gen, func.__name__, func)

def feature(*k):
	def deco(func):
		for name in k:
			try:
				l = task_gen.traits[name]
			except KeyError:
				l = set()
				task_gen.traits[name] = l
			l.update([func.__name__])
		return func
	return deco

def before(fun_name):
	def deco(func):
		try:
			if not func.__name__ in task_gen.prec[fun_name]: task_gen.prec[fun_name].append(func.__name__)
		except KeyError:
			task_gen.prec[fun_name] = [func.__name__]
		return func
	return deco

def after(fun_name):
	def deco(func):
		try:
			if not fun_name in task_gen.prec[func.__name__]: task_gen.prec[func.__name__].append(fun_name)
		except KeyError:
			task_gen.prec[func.__name__] = [fun_name]
		return func
	return deco

def extension(var):
	if type(var) is types.ListType:
		pass
	elif type(var) is types.StringType:
		var = [var]
	else:
		raise TypeError('declare extension takes either a list or a string %s' % str(var))

	def deco(func):
		for x in var:
			task_gen.mappings[x] = func
		task_gen.mapped[func.__name__] = func
		return func
	return deco

