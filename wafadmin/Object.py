#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

# genobj is an abstract class for declaring targets:
#   * creates tasks (consisting of a task, an environment, a list of source and list of target)
#   * sets environment on the tasks (which are copies most of the time)
#   * modifies environments as needed
# 
# genobj cannot be used as it is, so you must create a subclass
#
# subclassing
#   * makes it possible to share environment copies for several objects at once (efficiency)
#   * be careful to call Object.genobj.__init__(...) in the init of your subclass
#
# composition
#   * makes it possible to declare new kind of targets quickly (give a pattern ? and the action name)
#   * is not really flexible, but lightweight
#   * cf cppobj for more details on this scheme

import os, shutil, types
import Action, Params, Environment, Runner, Task, Common
from Params import debug, error, trace, fatal

g_allobjs=[]

# call flush for every group of object to process
def flush():
	trace("delayed operation called")
	while len(Params.g_outstanding_objs)>0:
		trace("posting object")

		obj=Params.g_outstanding_objs.pop()
		obj.post()
		Params.g_posted_objs.append(obj)

		trace("object posted")

class genobj:
	def __init__(self, type):
		self.m_type  = type
		self.m_posted = 0
		self.m_current_path = Params.g_build.m_curdirnode # emulate chdir when reading scripts
		self.name = '' # give a name to the target

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

		# allow delayed operations on objects created (declarative style)
		# an object is then posted when another one is added
		# of course, you may want to post the object yourself first :)
		#flush()
		Params.g_outstanding_objs.append(self)

		if not type in self.get_valid_types():
			error("BUG genobj::init : invalid type given")

	def get_valid_types(self):
		return ['program', 'shlib', 'staticlib', 'other']

	# runs the code to create the tasks
	def post(self):
		if not self.env: self.env = Params.g_build.m_allenvs['default']

		if self.m_posted:
			error("OBJECT ALREADY POSTED")
			return
		self.apply()
		self.m_posted=1

	# probably important ?
	def to_real_file(self, file):
		# append the builddir to the file name, calls object to .. :)
		pass

	# the following function is used to modify the environments of the tasks
	def setForAll(self, var, val):
		for task in self.m_tasks:
			task.setvar(var, val)
	# the following function is used to modify the environments of the tasks
	def prependAll(self, var, val):
		for task in self.m_tasks:
			task.prependvar(var, val)
	# the following function is used to modify the environments of the tasks
	def appendAll(self, var, val):
		for task in self.m_tasks:
			task.appendvar(var, val)

	# the lower the nice is, the higher priority tasks will run at
	# groups are sorted like this [2, 4, 5, 100, 200]
	# the tasks with lower nice will run first
	# if tasks have an odd priority number, they will be run only sequentially
	# if tasks have an even priority number, they will be allowed to be run in parallel
	def create_task(self, type, env, nice=10):
		task = Task.Task(type, env, nice)
		self.m_tasks.append(task)
		return task

	# creates the tasks, override this method
	def apply(self):
		# subclass me
		trace("nothing to do")

	def get_mirror_node(self, node, filename):
		tree=Params.g_build.m_tree
		return tree.mirror_file(node, filename)

	def file_in(self, filename):
		return [ self.get_mirror_node(self.m_current_path, filename) ]

	# an object is to be posted, even if only for install
	# the install function is called for uninstalling too
	def install(self):
		# subclass me
		pass

	def install_results(self, var, subdir, task):
		trace('install results called')
		current = Params.g_build.m_curdirnode
		# TODO what is the pythonic replacement for these three lines ?
		lst = []
		for node in task.m_outputs:
			lst.append( node.relpath_gen(current) )
		Common.install_files(var, subdir, lst)
		
# ['CXX', ..] -> [env['CXX'], ..]
def list_to_env_list(env, vars_list):
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
	#lst = list_to_env_list(env, vars_list)
	#val = reduce( lambda a,b : Params.h_string(b)+Params.h_string(a), lst )
	#return val
	lst = list_to_env_list(env, vars_list)
	return Params.h_list(lst)

def reset():
	global g_register
	g_register={}
	g_allobjs=[]

# The main functor 
# build objects without having to add tons of import statements

g_allclasses = {}
def createObj(objname, *k, **kw):
	try:
		return g_allclasses[objname](*k, **kw)
	except:
		print "error in createObj", objname
		raise

def register(name, classval):
	global g_allclasses
	if name in g_allclasses: print "there is a problem in Object:register: class exists ", name
	g_allclasses[name] = classval

