#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"""
genobj is an abstract class for declaring targets:
  * creates tasks (consisting of a task, an environment, a list of source and list of target)
  * sets environment on the tasks (which are copies most of the time)
  * modifies environments as needed

 genobj cannot be used as it is, so you must create a subclass

subclassing
  * makes it possible to share environment copies for several objects at once (efficiency)
  * be careful to call Object.genobj.__init__(...) in the __init__ of your subclass

hooks
  * declare new kind of targets quickly (give a pattern ? and the action name)
  * several extensions are mapped to a single method
  * cf ccroot.py and flex.py for more details on this scheme
"""

import os, types
import Params, Task, Common, Node, Utils
from Params import debug, error, trace, fatal

g_allobjs=[]

def find_launch_node(node, lst):
	#if node.m_parent: print node, lst
	#else: print '/', lst
	if not lst: return node
	name=lst[0]
	if not name:     return find_launch_node(node, lst[1:])
	if name == '.':  return find_launch_node(node, lst[1:])
	if name == '..': return find_launch_node(node.m_parent, lst[1:])
	for d in node.m_dirs+node.m_files:
		if d.m_name == name:
			return find_launch_node(d, lst[1:])
	return None

def flush():
	"force all objects to post their tasks"

	bld = Params.g_build
	trace("delayed operation Object.flush() called")

	dir_lst = Params.g_launchdir.split(os.sep)
	root    = bld.m_root
	launch_dir_node = find_launch_node(root, dir_lst)
	if Params.g_options.compile_targets:
		compile_targets = Params.g_options.compile_targets.split(',')
	else:
		compile_targets = None

	for obj in bld.m_outstanding_objs:
		trace("posting object")

		if obj.m_posted: continue

		# compile only targets under the launch directory
		if launch_dir_node:
			objnode = obj.m_current_path
			if not (objnode is launch_dir_node or objnode.is_child_of(launch_dir_node)):
				continue
		if compile_targets:
			if obj.name and not (obj.name in compile_targets):
				trace("skipping because of name")
				continue
			if not obj.target in compile_targets:
				trace("skipping because of target")
				continue
		# post the object
		obj.post()

		trace("object posted")

def hook(objname, var, func):
	"Attach a new method to an object class (objname is the name of the class)"
	klass = g_allclasses[objname]
	klass.__dict__[var] = func
	try: klass.__dict__['all_hooks'].append(var)
	except: klass.__dict__['all_hooks'] = [var]

class genobj:
	def __init__(self, type):
		self.m_type  = type
		self.m_posted = 0
		self.m_current_path = Params.g_build.m_curdirnode # emulate chdir when reading scripts
		self.name = '' # give a name to the target (static+shlib with the same targetname ambiguity)

		# TODO if we are building something, we need to make sure the folder is scanned
		#if not Params.g_build.m_curdirnode in Params...

		# targets / sources
		self.source = ''
		self.target = ''

		# we use a simple list for the tasks TODO not used ?
		self.m_tasks = []

		# no default environment - in case if
		self.env = None

		# register ourselves - used at install time
		g_allobjs.append(self)

		# nodes that this object produces
		self.out_nodes = []

		# allow delayed operations on objects created (declarative style)
		# an object is then posted when another one is added
		# of course, you may want to post the object yourself first :)
		#flush()
		Params.g_build.m_outstanding_objs.append(self)

		if not type in self.get_valid_types():
			error("BUG genobj::init : invalid type given")

	def get_valid_types(self):
		return ['program', 'shlib', 'staticlib', 'other']

	def get_hook(self, ext):
		try:
			for i in self.__class__.__dict__['all_hooks']:
				if ext in self.env[i]:
					return self.__class__.__dict__[i]
		except:
			return None

	def post(self):
		"runs the code to create the tasks, do not subclass"
		if not self.env: self.env = Params.g_build.m_allenvs['default']
		if not self.name: self.name = self.target

		if self.m_posted:
			error("OBJECT ALREADY POSTED")
			return
		self.apply()
		self.m_posted=1

	def create_task(self, type, env=None, nice=10):
		"""the lower the nice is, the higher priority tasks will run at
		groups are sorted like this [2, 4, 5, 100, 200]
		the tasks with lower nice will run first
		if tasks have an odd priority number, they will be run only sequentially
		if tasks have an even priority number, they will be allowed to be run in parallel
		"""
		if env is None: env=self.env
		task = Task.Task(type, env, nice)
		self.m_tasks.append(task)
		return task

	def apply(self):
		"subclass me"
		fatal("subclass me!")

	# FIXME (ita)
	def get_bld_node(self, parent, filename):
		node = parent
		for name in filename.split('/'):
			found = 0
			if not found:
				for f in node.m_files:
					if f.m_name == name:
						node = f
						found = 1
						break
			if not found:
				for f in node.m_build:
					if f.m_name == name:
						node = f
						found = 1
						break
			if not found:
				for f in node.m_dirs:
					if f.m_name == name:
						node = f
						found = 1
						break
			if not found:
				# bld node does not exist, create it
				node2 = Node.Node(name, node)
				node.m_build.append(node2)
				node = node2
		return node

	def file_in(self, filename):
		return [ self.get_bld_node(self.m_current_path, filename) ]

	# an object is to be posted, even if only for install
	# the install function is called for uninstalling too
	def install(self):
		# subclass me
		pass

	def cleanup(self):
		# subclass me if necessary
		pass

	def install_results(self, var, subdir, task, chmod=0644):
		trace('install results called')
		current = Params.g_build.m_curdirnode
		# TODO what is the pythonic replacement for these three lines ?
		lst = []
		for node in task.m_outputs:
			lst.append( node.relpath_gen(current) )
		Common.install_files(var, subdir, lst, chmod=chmod)

	def clone(self, env):
		newobj = Utils.copyobj(self)

		if type(env) is types.StringType:
			newobj.env = Params.g_build.m_allenvs[env]
		else:
			newobj.env = env

		g_allobjs.append(newobj)
		Params.g_build.m_outstanding_objs.append(newobj)

		return newobj

	def to_list(self, value):
		"helper: returns a list"
		if type(value) is types.StringType: return value.split()
		else: return value

def flatten(env, var):
	try:
		v = env[var]
		if not v: debug("variable %s does not exist in env !" % var)

		if type(v) is types.ListType:
			return " ".join(v)
		else:
			return v
	except:
		fatal("variable %s does not exist in env !" % var)

def list_to_env_list(env, vars_list):
	" ['CXX', ..] -> [env['CXX'], ..]"
	def get_env_value(var):
		# TODO add a cache here ?
		#return env[var]
		try:
			v = env[var]
			if type(v) is types.ListType:
				return " ".join(v)
			else:
				return v
		except:
			debug("variable %s does not exist in env !" % var)
			return ''
	return map(get_env_value, vars_list)

def sign_env_vars(env, vars_list):
	lst = list_to_env_list(env, vars_list)
	return Params.h_list(lst)

# TODO there is probably a way to make this more simple
g_allclasses = {}
def register(name, classval):
	global g_allclasses
	if name in g_allclasses:
		trace('class exists in g_allclasses '+name)
		return
	g_allclasses[name] = classval

