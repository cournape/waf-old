#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"""
Running tasks in parallel is a simple problem, but in practice it is more complicated:
* dependencies discovered during the build (dynamic task creation)
* dependencies discovered after files are compiled
* the amount of tasks and dependencies (graph size) can be huge

This is why the dependency management is split on three different levels:
1. groups of tasks that run all after another group of tasks
2. groups of tasks that can be run in parallel
3. tasks that can run in parallel, but with possible unknown ad-hoc dependencies

The point #1 represents a strict sequential order between groups of tasks, for example a compiler is produced
and used to compile the rest, whereas #2 and #3 represent partial order constraints where #2 applies to the kind of task
and #3 applies to the task instances.

#1 is held by the task manager: ordered list of TaskGroups (see bld.add_group)
#2 is held by the task groups and the task types: precedence after/before (topological sort),
   and the constraints extracted from file extensions
#3 is held by the tasks individually (attribute run_after),
   and the scheduler (Runner.py) use Task::runnable_status to reorder the tasks

--

To try, use something like this in your code:
import Constants, Task
Task.algotype = Constants.MAXPARALLEL
Task.shuffle = True

--

There are two concepts with the tasks (individual units of change):
* dependency (if 1 is recompiled, recompile 2)
* order (run 2 after 1)

example 1: if t1 depends on t2 and t2 depends on t3 it is not necessary to make t1 depend on t3 (dependency is transitive)
example 2: if t1 depends on a node produced by t2, it is not immediately obvious that t1 must run after t2 (order is not obvious)

The role of the Task Manager is to give the tasks in order (groups of task that may be run in parallel one after the other)

"""

import os, types, shutil, sys, re, new, random, time
from Utils import md5
import Build, Runner, Utils, Node, Logs, Options
from Logs import debug, error, warn
from Constants import *

algotype = NORMAL
#algotype = JOBCONTROL
#algotype = MAXPARALLEL
shuffle = False

"""
Enable different kind of dependency algorithms:
1 make groups: first compile all cpps and then compile all links (NORMAL)
2 parallelize all (each link task run after its dependencies) (MAXPARALLEL)
3 like 1 but provide additional constraints for the parallelization (MAXJOBS)

In theory 1. will be faster than 2 for waf, but might be slower for builds
The scheme 2 will not allow for running tasks one by one so it can cause disk thrashing on huge builds

"""

class TaskManager(object):
	"""The manager is attached to the build object, it holds a list of TaskGroup"""
	def __init__(self):
		self.groups = []
		self.tasks_done = []

		self.current_group = 0

	def get_next_set(self):
		"""return the next set of tasks to execute
		the first parameter is the maximum amount of parallelization that may occur"""
		ret = None
		while not ret and self.current_group < len(self.groups):
			ret = self.groups[self.current_group].get_next_set()
			if ret: return ret
			else: self.current_group += 1
		return (None, None)

	def add_group(self, name=''):
		if not name:
			size = len(self.groups)
			name = 'group-%d' % size
		if not self.groups:
			self.groups = [TaskGroup(name)]
			return
		if not self.groups[0].tasks:
			warn('add_group: an empty group is already present')
			return
		self.groups = self.groups + [TaskGroup(name)]

	def add_task(self, task):
		if not self.groups: self.add_group('group-0')
		self.groups[-1].add_task(task)

	def total(self):
		total = 0
		if not self.groups: return 0
		for group in self.groups:
			total += len(group.tasks)
		return total

	def add_finished(self, tsk):
		self.tasks_done.append(tsk)
		# TODO we could install using threads here
		bld = Build.bld
		if Options.is_install and hasattr(tsk, 'install'):
			d = tsk.install
			env = tsk.env
			if type(d) is types.FunctionType:
				d(tsk)
			elif type(d) is types.StringType:
				if not env[d]: return
				lst = [a.relpath_gen(Build.bld.srcnode) for a in tsk.outputs]
				bld.install_files(env[d], '', lst, chmod=0644, env=env)
			else:
				if not d['var']: return
				lst = [a.relpath_gen(Build.bld.srcnode) for a in tsk.outputs]
				if d.get('src', 0): lst += [a.relpath_gen(Build.bld.srcnode) for a in tsk.inputs]
				# TODO ugly hack
				if d.get('as', ''):
					bld.install_as(d['var'], d['dir']+d['as'], lst[0], chmod=d.get('chmod', 0644), env=tsk.env)
				else:
					bld.install_files(d['var'], d['dir'], lst, chmod=d.get('chmod', 0644), env=env)

class TaskGroup(object):
	"the compilation of one group does not begin until the previous group has finished (in the manager)"
	def __init__(self, name):
		self.name = name
		self.tasks = [] # this list will be consumed

		self.cstr_groups = {} # tasks having equivalent constraints
		self.cstr_order = {} # partial order between the cstr groups
		self.temp_tasks = [] # tasks put on hold
		self.ready = 0

	def reset(self):
		"clears the state of the object (put back the tasks into self.tasks)"
		for x in self.cstr_groups:
			self.tasks += self.cstr_groups[x]
		self.tasks = self.temp_tasks + self.tasks
		self.temp_tasks = []
		self.cstr_groups = []
		self.cstr_order = {}
		self.ready = 0

	def prepare(self):
		"prepare the scheduling"
		self.ready = 1
		self.make_cstr_groups()
		self.extract_constraints()

	def get_next_set(self):
		"next list of tasks to execute using max job settings, returns (maxjobs, task_list)"
		global algotype, shuffle
		if algotype == NORMAL:
			tasks = self.tasks_in_parallel()
			maxj = sys.maxint
		elif algotype == JOBCONTROL:
			(maxj, tasks) = self.tasks_by_max_jobs()
		elif algotype == MAXPARALLEL:
			tasks = self.tasks_with_inner_constraints()
			maxj = sys.maxint
		else:
			raise Utils.WafError("unknown algorithm type %s" % (algotype))

		if not tasks: return ()
		if shuffle: random.shuffle(tasks)
		return (maxj, tasks)

	def make_cstr_groups(self):
		"unite the tasks that have similar constraints"
		self.cstr_groups = {}
		for x in self.tasks:
			h = x.hash_constraints()
			try: self.cstr_groups[h].append(x)
			except KeyError: self.cstr_groups[h] = [x]

	def add_task(self, task):
		try: self.tasks.append(task)
		except KeyError: self.tasks = [task]

	def set_order(self, a, b):
		try: self.cstr_order[a].add(b)
		except KeyError: self.cstr_order[a] = set([b,])

	def compare_exts(self, t1, t2):
		"extension production"
		x = "ext_in"
		y = "ext_out"
		in_ = t1.attr(x, ())
		out_ = t2.attr(y, ())
		for k in in_:
			if k in out_:
				return -1
		in_ = t2.attr(x, ())
		out_ = t1.attr(y, ())
		for k in in_:
			if k in out_:
				return 1
		return 0

	def compare_partial(self, t1, t2):
		"partial relations after/before"
		m = "after"
		n = "before"
		name = t2.__class__.__name__
		if name in t1.attr(m, ()): return -1
		elif name in t1.attr(n, ()): return 1
		name = t1.__class__.__name__
		if name in t2.attr(m, ()): return 1
		elif name in t2.attr(n, ()): return -1
		return 0

	def extract_constraints(self):
		"extract the parallelization constraints from the tasks with different constraints"
		keys = self.cstr_groups.keys()
		max = len(keys)
		#a = self.__class__
		# hopefully the lenght of this list is short
		for i in xrange(max):
			t1 = self.cstr_groups[keys[i]][0]
			for j in xrange(i + 1, max):
				t2 = self.cstr_groups[keys[j]][0]

				# add the constraints based on the comparisons
				val = (self.compare_exts(t1, t2)
					or self.compare_partial(t1, t2)
					)
				if val > 0:
					self.set_order(keys[i], keys[j])
				elif val < 0:
					self.set_order(keys[j], keys[i])

		#print "the constraint groups are:", self.cstr_groups, "and the constraints ", self.cstr_order
		# TODO extract constraints by file extensions on the actions

	def tasks_in_parallel(self):
		"(NORMAL) next list of tasks that may be executed in parallel"

		if not self.ready: self.prepare()

		#print [(a.name, cstrs[a].name) for a in cstrs]
		keys = self.cstr_groups.keys()

		unconnected = []
		remainder = []

		for u in keys:
			for k in self.cstr_order.values():
				if u in k:
					remainder.append(u)
					break
			else:
				unconnected.append(u)

		#print "unconnected tasks: ", unconnected, "tasks", [eq_groups[x] for x in unconnected]

		toreturn = []
		for y in unconnected:
			toreturn.extend(self.cstr_groups[y])

		# remove stuff only after
		for y in unconnected:
				try: self.cstr_order.__delitem__(y)
				except KeyError: pass
				self.cstr_groups.__delitem__(y)

		if not toreturn and remainder:
			raise Utils.WafError("circular order constraint detected %r" % remainder)

		#print "returning", toreturn
		return toreturn

	def tasks_by_max_jobs(self):
		"(JOBCONTROL) returns the tasks that can run in parallel with the max amount of jobs"
		if not self.ready: self.prepare()
		if not self.temp_tasks: self.temp_tasks = self.tasks_in_parallel()
		if not self.temp_tasks: return (None, None)

		maxjobs = sys.maxint
		ret = []
		remaining = []
		for t in self.temp_tasks:
			m = getattr(t, "maxjobs", getattr(self.__class__, "maxjobs", sys.maxint))
			if m > maxjobs:
				remaining.append(t)
			elif m < maxjobs:
				remaining += ret
				ret = [t]
				maxjobs = m
			else:
				ret.append(t)
		self.temp_tasks = remaining
		return (maxjobs, ret)

	def tasks_with_inner_constraints(self):
		"""(MAXPARALLEL) returns all tasks in this group, but add the constraints on each task instance
		as an optimization, it might be desirable to discard the tasks which do not have to run"""
		if not self.ready: self.prepare()

		if getattr(self, "done", None): return None

		for p in self.cstr_order:
			for v in self.cstr_order[p]:
				for m in self.cstr_groups[p]:
					for n in self.cstr_groups[v]:
						n.set_run_after(m)
		self.cstr_order = {}
		self.cstr_groups = {}
		self.done = 1
		return self.tasks[:] # make a copy

class store_task_type(type):
	"store the task types that have a name ending in _task into a map (remember the existing task types)"
	def __init__(cls, name, bases, dict):
		super(store_task_type, cls).__init__(name, bases, dict)
		name = cls.__name__

		if name.endswith('_task'):
			name = name.replace('_task', '')
			TaskBase.classes[name] = cls

class TaskBase(object):
	"""Base class for all Waf tasks

	The most important methods are (by usual order of call):
	1 runnable_status: ask the task if it should be run, skipped, or if we have to ask later
	2 __str__: string to display to the user
	3 run: execute the task
	4 post_run: after the task is run, update the cache about the task

	This class should be seen as an interface, it provides the very minimum necessary for the scheduler
	so it does not do much.

	For illustration purposes, TaskBase instances try to execute self.fun (if provided)
	"""

	__metaclass__ = store_task_type

	color = "GREEN"
	maxjobs = sys.maxint
	classes = {}
	stat = None

	def __init__(self, normal=1):
		self.hasrun = 0

		manager = Build.bld.task_manager
		if normal:
			manager.add_task(self)

	def __repr__(self):
		"used for debugging"
		return '\n\t{task: %s %s}' % (self.__class__.__name__, str(getattr(self, "fun", "")))

	def __str__(self):
		"string to display to the user"
		try: self.fun
		except AttributeError: return self.__class__.__name__ + '\n'
		else: return 'executing: %s\n' % self.fun.__name__

	def runnable_status(self):
		"RUN_ME SKIP_ME or ASK_LATER"
		return RUN_ME

	def run(self):
		"called if the task must run"
		try: fun = self.fun
		except: return 0
		return fun(self)

	def post_run(self):
		"update the dependency tree (node stats)"
		pass

	def display(self):
		"print either the description (using __str__) or the progress bar or the ide output"
		col1 = Logs.colors(self.color)
		col2 = Logs.colors.NORMAL

		if Options.options.progress_bar == 1:
			return Build.bld.progress_line(self.position[0], self.position[1], col1, col2)

		if Options.options.progress_bar == 2:
			try: ini = Build.bld.ini
			except AttributeError: ini = Build.bld.ini = time.time()
			ela = time.strftime('%H:%M:%S', time.gmtime(time.time() - ini))
			ins  = ','.join([n.name for n in task.inputs])
			outs = ','.join([n.name for n in task.outputs])
			return '|Total %s|Current %s|Inputs %s|Outputs %s|Time %s|\n' % (self.position[1], self.position[0], ins, outs, ela)

		total = self.position[1]
		n = len(str(total))
		fs = '[%%%dd/%%%dd] %%s%%s%%s' % (n, n)
		return fs % (self.position[0], self.position[1], col1, str(self), col2)

	def attr(self, att, default=None):
		"retrieve an attribute from the instance or from the class"
		return getattr(self, att, getattr(self.__class__, att, default))

	def hash_constraints(self):
		"identify a task type for all the constraints relevant for the scheduler: precedence, file production"
		sum = 0
		names = ('before', 'after', 'ext_in', 'ext_out')
		sum = hash((sum, self.__class__.__name__,))
		for x in names:
			sum = hash((sum, str(self.attr(x, sys.maxint)),))
		sum = hash((sum, self.__class__.maxjobs))
		return sum

	def format_error(self):
		if self.attr('error_msg'):
			# you can leave a message after the ....beep
			msg = self.attr('error_msg')
			if type(msg) is types.FunctionType:
				return msg(self)
			else:
				lst.append(msg)
		elif self.hasrun == CRASHED:
			try:
				return " -> task failed (err #%d): %r" % (tsk.err_code, tsk)
			except AttributeError:
				return " -> task failed: %r" % tsk
		elif tsk.hasrun == MISSING:
			return " -> missing files: %r" % tsk
		else:
			return ''

class Task(TaskBase):
	"""The parent class is quite limited, in this version:
	* file system interaction: input and output nodes
	* persistence: do not re-execute tasks that have already run
	* caching: same files can be saved and retrieved from a cache directory
	* dependencies:
	   implicit, like .c files depending on .h files
       explicit, like the input nodes or the dep_nodes
       environment variables, like the CXXFLAGS in self.env
	"""
	vars = []
	def __init__(self, env, normal=1):
		TaskBase.__init__(self, normal=normal)
		self.env = env

		# inputs and outputs are nodes
		# use setters when possible
		self.inputs  = []
		self.outputs = []

		self.deps_nodes = []
		self.run_after = []

		# Additionally, you may define the following
		#self.dep_vars  = 'PREFIX DATADIR'

	def __str__(self):
		"string to display to the user"
		env = self.env
		src_str = ' '.join([a.nice_path(env) for a in self.inputs])
		tgt_str = ' '.join([a.nice_path(env) for a in self.outputs])
		return '%s: %s -> %s\n' % (self.__class__.__name__, src_str, tgt_str)

	def __repr__(self):
		return "".join(['\n\t{task: ', self.__class__.__name__, " ", ",".join([x.name for x in self.inputs]), " -> ", ",".join([x.name for x in self.outputs]), '}'])

	def unique_id(self):
		"get a unique id: hash the node paths, the variant, the class, the function"
		x = getattr(self, 'uid', None)
		if x: return x

		m = md5()
		up = m.update
		up(self.env.variant())
		for x in self.inputs + self.outputs:
			up(x.abspath())
		up(self.__class__.__name__)
		up(Utils.h_fun(self.run))
		x = self.uid = m.digest()
		return x

	def set_inputs(self, inp):
		if type(inp) is types.ListType: self.inputs += inp
		else: self.inputs.append(inp)

	def set_outputs(self, out):
		if type(out) is types.ListType: self.outputs += out
		else: self.outputs.append(out)

	def set_run_after(self, task):
		"set (scheduler) order on another task"
		# TODO: handle list or object
		assert isinstance(task, TaskBase)
		self.run_after.append(task)

	def add_file_dependency(self, filename):
		"TODO user-provided file dependencies"
		node = Build.bld.current.find_resource(filename)
		self.deps_nodes.append(node)

	def signature(self):
		# compute the result one time, and suppose the scan_signature will give the good result
		try: return self.sign_all
		except AttributeError: pass

		m = md5()

		# explicit deps
		exp_sig = self.sig_explicit_deps()
		m.update(exp_sig)

		# implicit deps
		imp_sig = self.scan and self.sig_implicit_deps() or SIG_NIL
		m.update(imp_sig)

		# env vars
		var_sig = self.sig_vars()
		m.update(var_sig)

		# we now have the signature (first element) and the details (for debugging)
		ret = m.digest()
		self.cache_sig = (ret, exp_sig, imp_sig, var_sig)

		self.sign_all = ret
		return ret

	def runnable_status(self):
		"SKIP_ME RUN_ME or ASK_LATER"
		#return 0 # benchmarking

		if self.inputs and (not self.outputs):
			if not getattr(self.__class__, 'quiet', None):
				error("task is invalid : no inputs or outputs (override in a Task subclass?) %r" % self)

		for t in self.run_after:
			if not t.hasrun:
				return ASK_LATER

		env = self.env
		tree = Build.bld

		# tasks that have no inputs or outputs are run each time
		if not self.inputs and not self.outputs:
			self.dep_sig = SIG_NIL
			return RUN_ME

		# look at the previous signature first
		time = None
		for node in self.outputs:
			variant = node.variant(env)
			try:
				time = tree.node_sigs[variant][node.id]
			except KeyError:
				debug("task: task %r must run as the first node does not exist" % self)
				time = None
				break
		# if one of the nodes does not exist, try to retrieve them from the cache
		if time is None:
			try:
				new_sig = self.signature()
			except KeyError:
				debug("something is wrong, computing the task signature failed")
				return RUN_ME

			ret = self.can_retrieve_cache(new_sig)
			return ret and SKIP_ME or RUN_ME

		key = self.unique_id()
		try:
			prev_sig = tree.task_sigs[key][0]
		except KeyError:
			debug("task: task %r must run as it was never run before or the task code changed" % self)
			return RUN_ME

		#print "prev_sig is ", prev_sig
		new_sig = self.signature()

		# debug if asked to
		if Logs.zones: self.debug_why(tree.task_sigs[key])

		if new_sig != prev_sig:
			# try to retrieve the file from the cache
			ret = self.can_retrieve_cache(new_sig)
			return ret and SKIP_ME or RUN_ME

		return SKIP_ME

	def post_run(self):
		"called after a successful task run"
		tree = Build.bld
		env = self.env
		sig = self.signature()

		cnt = 0
		for node in self.outputs:
			variant = node.variant(env)
			#if node in tree.node_sigs[variant]:
			#	print "variant is ", variant
			#	print "self sig is ", Utils.view_sig(tree.node_sigs[variant][node])

			# check if the node exists ..
			os.stat(node.abspath(env))

			# important, store the signature for the next run
			tree.node_sigs[variant][node.id] = sig

			# We could re-create the signature of the task with the signature of the outputs
			# in practice, this means hashing the output files
			# this is unnecessary
			if Options.cache_global:
				ssig = sig.encode('hex')
				dest = os.path.join(Options.cache_global, ssig+'-'+str(cnt))
				try: shutil.copy2(node.abspath(env), dest)
				except IOError: warn('Could not write the file to the cache')
				cnt += 1

		tree.task_sigs[self.unique_id()] = self.cache_sig
		self.executed=1

	def can_retrieve_cache(self, sig):
		"""Retrieve build nodes from the cache - the file time stamps are updated
		for cleaning the least used files from the cache dir - be careful when overridding"""
		if not Options.cache_global: return None
		if Options.options.nocache: return None

		env = self.env
		sig = self.signature()

		cnt = 0
		for node in self.outputs:
			variant = node.variant(env)

			ssig = sig.encode('hex')
			orig = os.path.join(Options.cache_global, ssig+'-'+str(cnt))
			try:
				shutil.copy2(orig, node.abspath(env))
				# mark the cache file as used recently (modified)
				os.utime(orig, None)
			except (OSError, IOError):
				debug('task: failed retrieving file')
				return None
			else:
				cnt += 1
				Build.bld.node_sigs[variant][node.id] = sig
				if not Runner.g_quiet: Utils.pprint('GREEN', 'restored from cache %s' % node.bldpath(env))
		return 1

	def debug_why(self, old_sigs):
		"explains why a task is run"

		new_sigs = self.cache_sig
		def v(x):
			return x.encode('hex')

		msgs = ['Task must run', '* Source file or manual dependency', '* Implicit dependency', '* Environment variable']
		tmp = 'task: -> %s: %s %s'
		for x in xrange(len(msgs)):
			if (new_sigs[x] != old_sigs[x]):
				debug(tmp % (msgs[x], v(old_sigs[x]), v(new_sigs[x])))

	def sig_explicit_deps(self):
		tree = Build.bld
		m = md5()

		# the inputs
		for x in self.inputs:
			variant = x.variant(self.env)
			m.update(tree.node_sigs[variant][x.id])

		# additional nodes to depend on, if provided
		for x in getattr(self, 'dep_nodes', []):
			variant = x.variant(self.env)
			v = tree.node_sigs[variant][x.id]
			m.update(v)

		# manual dependencies, they can slow down the builds
		try:
			additional_deps = tree.deps_man
		except AttributeError:
			pass
		else:
			for x in self.inputs + self.outputs:
				try:
					d = additional_deps[x]
				except KeyError:
					continue
				if callable(d): d = d() # dependency is a function, call it
				m.update(d)

		return m.digest()

	def sig_vars(self):
		m = md5()
		tree = Build.bld
		env = self.env

		# dependencies on the environment vars
		fun = getattr(self.__class__, 'signature_hook', None)
		if fun: act_sig = self.__class__.signature_hook(self)
		else: act_sig = tree.sign_vars(env, self.__class__.vars)
		m.update(act_sig)

		# additional variable dependencies, if provided
		var_sig = SIG_NIL
		dep_vars = getattr(self, 'dep_vars', None)
		if dep_vars:
			var_sig = tree.sign_vars(env, dep_vars)
			m.update(var_sig)

		# additional variables to hash (command-line defines for example)
		for x in getattr(self.__class__, "vars", ()):
			k = env[x]
			if k:
				m.update(str(k))
				vars_sig = hash((var_sig, str(k)))

		return m.digest()

	#def scan(self, node):
	#	"""this method returns a tuple containing:
	#	* a list of nodes corresponding to real files
	#	* a list of names for files not found in path_lst
	#	the input parameters may have more parameters that the ones used below
	#	"""
	#	return ((), ())
	scan = None

	# compute the signature, recompute it if there is no match in the cache
	def sig_implicit_deps(self):
		"the signature obtained may not be the one if the files have changed, we do it in two steps"
		tree = Build.bld

		# get the task signatures from previous runs
		key = self.unique_id()
		prev_sigs = tree.task_sigs.get(key, ())
		if prev_sigs and prev_sigs[2] == self.compute_sig_implicit_deps():
			return prev_sigs[2]

		# no previous run or the signature of the dependencies has changed, rescan the dependencies
		(nodes, names) = self.scan()
		if Logs.verbose and Logs.zones:
			debug('deps: scanner for %s returned %s %s' % (str(self), str(nodes), str(names)))

		# store the dependencies in the cache
		tree = Build.bld
		tree.node_deps[self.unique_id()] = nodes
		tree.raw_deps[self.unique_id()] = names

		# recompute the signature and return it
		sig = self.compute_sig_implicit_deps()

		return sig

	def compute_sig_implicit_deps(self):
		"""it is intented for .cpp and inferred .h files
		there is a single list (no tree traversal)
		this is the hot spot so ... do not touch"""
		m = md5()
		upd = m.update

		tree = Build.bld
		tstamp = tree.node_sigs
		env = self.env

		for k in Build.bld.node_deps.get(self.unique_id(), ()):
			# unlikely but necessary if it happens
			try: tree.cache_scanned_folders[k.parent.id]
			except KeyError: tree.rescan(k.parent)

			if k.id & 3 == Node.FILE: upd(tstamp[0][k.id])
			else: upd(tstamp[env.variant()][k.id])

		return m.digest()

def funex(c):
	exec(c)
	return f

reg_act = re.compile(r"(?P<dollar>\$\$)|(?P<subst>\$\{(?P<var>\w+)(?P<code>.*?)\})", re.M)
def compile_fun(name, line):
	"""Compiles a string (once) into an function, eg:
	simple_action('c++', '${CXX} -o ${TGT[0]} ${SRC} -I ${SRC[0].parent.bldpath()}')

	The env variables (CXX, ..) on the task must not hold dicts (order)
	The reserved keywords TGT and SRC represent the task input and output nodes
	"""
	extr = []
	def repl(match):
		g = match.group
		if g('dollar'): return "$"
		elif g('subst'): extr.append((g('var'), g('code'))); return "%s"
		return None

	line = reg_act.sub(repl, line)

	parm = []
	dvars = []
	app = parm.append
	for (var, meth) in extr:
		if var == 'SRC':
			if meth: app('task.inputs%s' % meth)
			else: app('" ".join([a.srcpath(env) for a in task.inputs])')
		elif var == 'TGT':
			if meth: app('task.outputs%s' % meth)
			else: app('" ".join([a.bldpath(env) for a in task.outputs])')
		else:
			if not var in dvars: dvars.append(var)
			app("p('%s')" % var)
	if parm: parm = "%% (%s) " % (',\n\t\t'.join(parm))
	else: parm = ''

	c = '''
def f(task):
	env = task.env
	p = env.get_flat
	cmd = "%s" %s
	return Runner.exec_command(cmd)
''' % (line, parm)

	debug('action: %s' % c)
	return (funex(c), dvars)

def simple_task_type(name, line, color='GREEN', vars=[], ext_in=[], ext_out=[], before=[], after=[]):
	"""return a new Task subclass with the function run compiled from the line given"""
	(fun, dvars) = compile_fun(name, line)
	fun.code = line
	return task_type_from_func(name, fun, vars or dvars, color, ext_in, ext_out, before, after)

def task_type_from_func(name, func, vars=[], color='GREEN', ext_in=[], ext_out=[], before=[], after=[]):
	"""return a new Task subclass with the function run compiled from the line given"""
	params = {
		'run': func,
		'vars': vars,
		'color': color,
		'name': name,
		'ext_in': Utils.to_list(ext_in),
		'ext_out': Utils.to_list(ext_out),
		'before': Utils.to_list(before),
		'after': Utils.to_list(after),
	}

	cls = new.classobj(name, (Task,), params)
	TaskBase.classes[name] = cls
	return cls


