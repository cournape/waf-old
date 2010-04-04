#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"""
Task manager -> Task groups -> Tasks
"""

import os, shutil, sys, re, random, datetime
from collections import defaultdict
from Utils import md5
import Build, Runner, Utils, Node, Logs, Options
from Logs import debug, warn, error
from Constants import *
from Base import WafError

COMPILE_TEMPLATE_SHELL = '''
def f(task):
	env = task.env
	wd = getattr(task, 'cwd', None)
	p = env.get_flat
	cmd = \'\'\' %s \'\'\' % s
	return task.exec_command(cmd, cwd=wd)
'''

COMPILE_TEMPLATE_NOSHELL = '''
def f(task):
	env = task.env
	wd = getattr(task, 'cwd', None)
	def to_list(xx):
		if isinstance(xx, str): return [xx]
		return xx
	lst = []
	%s
	lst = [x for x in lst if x]
	return task.exec_command(lst, cwd=wd)
'''


class TaskManager(object):
	"""The manager is attached to the build object, it holds a list of TaskGroup"""
	def __init__(self):
		self.groups = []
		self.tasks_done = []
		self.current_group = 0
		self.groups_names = {}

	def get_next_set(self):
		"""return the next set of tasks to execute
		the first parameter is the maximum amount of parallelization that may occur"""
		ret = None
		while not ret and self.current_group < len(self.groups):
			ret = self.groups[self.current_group].get_next_set()
			if ret: return ret
			else:
				self.groups[self.current_group].process_install()
				self.current_group += 1
		return (None, None)

	def add_group(self, name=None, set=True):
		#if self.groups and not self.groups[0].tasks:
		#	error('add_group: an empty group is already present')
		g = TaskGroup()

		if name and name in self.groups_names:
			error('add_group: name %s already present' % name)
		self.groups_names[name] = g
		self.groups.append(g)
		if set:
			self.current_group = len(self.groups) - 1

	def set_group(self, idx):
		if isinstance(idx, str):
			g = self.groups_names[idx]
			for x in range(len(self.groups)):
				if id(g) == id(self.groups[x]):
					self.current_group = x
		else:
			self.current_group = idx

	def add_task_gen(self, tgen):
		if not self.groups: self.add_group()
		self.groups[self.current_group].tasks_gen.append(tgen)

	def add_task(self, task):
		if not self.groups: self.add_group()
		self.groups[self.current_group].tasks.append(task)

	def total(self):
		total = 0
		if not self.groups: return 0
		for group in self.groups:
			total += len(group.tasks)
		return total

	def add_finished(self, tsk):
		self.tasks_done.append(tsk)
		bld = tsk.generator.bld
		if bld.is_install:
			f = None
			if 'install' in tsk.__dict__:
				f = tsk.__dict__['install']
				# install=0 to prevent installation
				if f: f(tsk)
			else:
				tsk.install()

class TaskGroup(object):
	"the compilation of one group does not begin until the previous group has finished (in the manager)"
	def __init__(self):
		self.tasks = [] # this list will be consumed
		self.tasks_gen = []

		self.cstr_groups = defaultdict(list) # tasks having equivalent constraints
		self.cstr_order = defaultdict(set) # partial order between the cstr groups
		self.temp_tasks = [] # tasks put on hold
		self.ready = 0
		self.post_funs = []

	def reset(self):
		"clears the state of the object (put back the tasks into self.tasks)"
		for x in self.cstr_groups:
			self.tasks += self.cstr_groups[x]
		self.tasks = self.temp_tasks + self.tasks
		self.temp_tasks = []
		self.cstr_groups = defaultdict(list)
		self.cstr_order = defaultdict(set)
		self.ready = 0

	def process_install(self):
		for (f, k, kw) in self.post_funs:
			f(*k, **kw)

	def prepare(self):
		"prepare the scheduling"
		self.ready = 1
		extract_outputs(self.tasks)
		self.make_cstr_groups()
		self.extract_constraints()

	def get_next_set(self):
		"next list of tasks to execute using max job settings, returns (maxjobs, task_list)"
		return self.tasks_in_parallel()

	def make_cstr_groups(self):
		"unite the tasks that have similar constraints"
		self.cstr_groups = defaultdict(list)
		for x in self.tasks:
			h = x.hash_constraints()
			self.cstr_groups[h].append(x)

	def set_order(self, a, b):
		self.cstr_order[a].add(b)

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
		if name in Utils.to_list(t1.attr(m, ())): return -1
		elif name in Utils.to_list(t1.attr(n, ())): return 1
		name = t1.__class__.__name__
		if name in Utils.to_list(t2.attr(m, ())): return 1
		elif name in Utils.to_list(t2.attr(n, ())): return -1
		return 0

	def extract_constraints(self):
		"extract the parallelization constraints from the tasks with different constraints"
		keys = list(self.cstr_groups.keys())
		max = len(keys)
		# hopefully the length of this list is short
		for i in range(max):
			t1 = self.cstr_groups[keys[i]][0]
			for j in range(i + 1, max):
				t2 = self.cstr_groups[keys[j]][0]

				# add the constraints based on the comparisons
				val = (self.compare_exts(t1, t2)
					or self.compare_partial(t1, t2)
					)
				if val > 0:
					self.set_order(keys[i], keys[j])
				elif val < 0:
					self.set_order(keys[j], keys[i])

	def tasks_in_parallel(self):
		"(NORMAL) next list of tasks that may be executed in parallel"

		if not self.ready: self.prepare()

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

		toreturn = []
		for y in unconnected:
			toreturn.extend(self.cstr_groups[y])

		# remove stuff only after
		for y in unconnected:
				try: self.cstr_order.__delitem__(y)
				except KeyError: pass
				self.cstr_groups.__delitem__(y)

		if not toreturn and remainder:
			raise WafError("Circular order constraint detected %r" % remainder)

		return toreturn

class store_task_type(type):
	"store the task types that have a name ending in _task into a map (remember the existing task types)"
	def __init__(cls, name, bases, dict):
		super(store_task_type, cls).__init__(name, bases, dict)
		name = cls.__name__

		if name.endswith('_task'):
			name = name.replace('_task', '')
			TaskBase.classes[name] = cls

class TaskBase(object, metaclass=store_task_type):
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

	color = "GREEN"
	maxjobs = MAXJOBS
	classes = {}
	stat = None

	def __init__(self, *k, **kw):
		self.hasrun = NOT_RUN

		try:
			self.generator = kw['generator']
		except KeyError:
			self.generator = self

		if kw.get('normal', 1):
			self.generator.bld.task_manager.add_task(self)

	def __repr__(self):
		"used for debugging"
		return '\n\t{task: %s %s}' % (self.__class__.__name__, str(getattr(self, "fun", "")))

	def __str__(self):
		"string to display to the user"
		if hasattr(self, 'fun'):
			return 'executing: %s\n' % self.fun.__name__
		return self.__class__.__name__ + '\n'

	def exec_command(self, *k, **kw):
		"use this for executing commands from tasks"
		return self.generator.bld.exec_command(*k, **kw)

	def runnable_status(self):
		"RUN_ME SKIP_ME or ASK_LATER"
		return RUN_ME

	def can_retrieve_cache(self):
		return False

	def call_run(self):
		if self.can_retrieve_cache():
			return 0
		return self.run()

	def run(self):
		"called if the task must run"
		if hasattr(self, 'fun'):
			return self.fun(self)
		return 0

	def post_run(self):
		"update the dependency tree (node stats)"
		pass

	def display(self):
		"print either the description (using __str__) or the progress bar or the ide output"
		col1 = Logs.colors(self.color)
		col2 = Logs.colors.NORMAL

		if Options.options.progress_bar == 1:
			return self.generator.bld.progress_line(self.position[0], self.position[1], col1, col2)

		if Options.options.progress_bar == 2:
			ela = str(self.generator.bld.timer)
			try:
				ins  = ','.join([n.name for n in self.inputs])
			except AttributeError:
				ins = ''
			try:
				outs = ','.join([n.name for n in self.outputs])
			except AttributeError:
				outs = ''
			return '|Total %s|Current %s|Inputs %s|Outputs %s|Time %s|\n' % (self.position[1], self.position[0], ins, outs, ela)

		total = self.position[1]
		n = len(str(total))
		fs = '[%%%dd/%%%dd] %%s%%s%%s' % (n, n)
		return fs % (self.position[0], self.position[1], col1, str(self), col2)

	def attr(self, att, default=None):
		"retrieve an attribute from the instance or from the class (microoptimization here)"
		ret = getattr(self, att, self)
		if ret is self: return getattr(self.__class__, att, default)
		return ret

	def hash_constraints(self):
		"identify a task type for all the constraints relevant for the scheduler: precedence, file production"
		a = self.attr
		sum = hash((self.__class__.__name__,
			str(a('before', '')),
			str(a('after', '')),
			str(a('ext_in', '')),
			str(a('ext_out', '')),
			self.__class__.maxjobs))
		return sum

	def format_error(self):
		"error message to display to the user (when a build fails)"
		if getattr(self, "err_msg", None):
			return self.err_msg
		elif self.hasrun == CRASHED:
			try:
				return " -> task failed (err #%d): %r" % (self.err_code, self)
			except AttributeError:
				return " -> task failed: %r" % self
		elif self.hasrun == MISSING:
			return " -> missing files: %r" % self
		else:
			return ''

	def install(self):
		"""
		installation is performed by looking at the task attributes:
		* install_path: installation path like "${PREFIX}/bin"
		* filename: install the first node in the outputs as a file with a particular name, be certain to give os.sep
		* chmod: permissions
		"""
		bld = self.generator.bld
		d = self.attr('install')

		if self.attr('install_path'):
			lst = [a.relpath_gen(bld.srcnode) for a in self.outputs]
			perm = self.attr('chmod', O644)
			if self.attr('src'):
				# if src is given, install the sources too
				lst += [a.relpath_gen(bld.srcnode) for a in self.inputs]
			if self.attr('filename'):
				dir = self.install_path.rstrip(os.sep) + os.sep + self.attr('filename')
				bld.install_as(dir, lst[0], self.env, perm)
			else:
				bld.install_files(self.install_path, lst, self.env, perm)

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
	def __init__(self, *k, **kw):
		TaskBase.__init__(self, *k, **kw)
		self.env = kw['env']

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
		if self.outputs: sep = ' -> '
		else: sep = ''
		return '%s: %s%s%s\n' % (self.__class__.__name__.replace('_task', ''), src_str, sep, tgt_str)

	def __repr__(self):
		return "".join(['\n\t{task: ', self.__class__.__name__, " ", ",".join([x.name for x in self.inputs]), " -> ", ",".join([x.name for x in self.outputs]), '}'])

	def unique_id(self):
		"get a unique id: hash the node paths, the class, the function"
		try:
			return self.uid
		except AttributeError:
			"this is not a real hot zone, but we want to avoid surprizes here"
			m = md5()
			up = m.update
			up(self.__class__.__name__.encode())
			p = None
			for x in self.inputs + self.outputs:
				if p != x.parent.id:
					p = x.parent.id
					up(x.parent.abspath().encode())
				up(x.name.encode())
			self.uid = m.digest()
			return self.uid

	def set_inputs(self, inp):
		if isinstance(inp, list): self.inputs += inp
		else: self.inputs.append(inp)

	def set_outputs(self, out):
		if isinstance(out, list): self.outputs += out
		else: self.outputs.append(out)

	def set_run_after(self, task):
		"set (scheduler) order on another task"
		# TODO: handle list or object
		assert isinstance(task, TaskBase)
		self.run_after.append(task)

	def add_file_dependency(self, filename):
		"TODO user-provided file dependencies"
		node = self.generator.bld.path.find_resource(filename)
		self.deps_nodes.append(node)

	def signature(self):
		# compute the result one time, and suppose the scan_signature will give the good result
		try: return self.cache_sig[0]
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
		return ret

	def runnable_status(self):
		"SKIP_ME RUN_ME or ASK_LATER"
		#return 0 # benchmarking

		if self.inputs and (not self.outputs):
			if not getattr(self.__class__, 'quiet', None):
				warn("invalid task (no inputs OR outputs): override in a Task subclass or set the attribute 'quiet' %r" % self)

		for t in self.run_after:
			if not t.hasrun:
				return ASK_LATER

		env = self.env
		bld = self.generator.bld

		# first compute the signature
		try:
			new_sig = self.signature()
		except KeyError:
			debug("task: something is wrong, computing the task %r signature failed" % self)
			return RUN_ME

		# compare the signature to a signature computed previously
		key = self.unique_id()
		try:
			prev_sig = bld.task_sigs[key][0]
		except KeyError:
			debug("task: task %r must run as it was never run before or the task code changed" % self)
			return RUN_ME

		# compare the signatures of the outputs
		for node in self.outputs:
			try:
				if bld.node_sigs[node.id] != new_sig:
					return RUN_ME
			except KeyError:
				debug("task: task %r must run as the output nodes do not exist" % self)
				return RUN_ME

		# debug if asked to
		if Logs.verbose: self.debug_why(bld.task_sigs[key])

		if new_sig != prev_sig:
			return RUN_ME
		return SKIP_ME

	def post_run(self):
		"called after a successful task run"
		bld = self.generator.bld
		env = self.env
		sig = self.signature()

		cnt = 0
		for node in self.outputs:
			# check if the node exists ..
			try:
				os.stat(node.abspath())
			except OSError:
				self.hasrun = MISSING
				self.err_msg = '-> missing file: %r' % node.abspath()
				raise WafError

			# important, store the signature for the next run
			bld.node_sigs[node.id] = sig

			# We could re-create the signature of the task with the signature of the outputs
			# in practice, this means hashing the output files
			# this is unnecessary
			if Options.cache_global:
				ssig = sig.encode('hex')
				dest = os.path.join(Options.cache_global, '%s_%d_%s' % (ssig, cnt, node.name))
				try: shutil.copy2(node.abspath(), dest)
				except IOError: warn('Could not write the file to the cache')
				cnt += 1

		bld.task_sigs[self.unique_id()] = self.cache_sig

	def can_retrieve_cache(self):
		"""Retrieve build nodes from the cache - the file time stamps are updated
		for cleaning the least used files from the cache dir - be careful when overridding"""
		if not Options.cache_global: return None
		if Options.options.nocache: return None
		if not self.outputs: return None

		env = self.env
		sig = self.signature()

		cnt = 0
		for node in self.outputs:

			ssig = sig.encode('hex')
			orig = os.path.join(Options.cache_global, '%s_%d_%s' % (ssig, cnt, node.name))
			try:
				shutil.copy2(orig, node.abspath(env))
				# mark the cache file as used recently (modified)
				os.utime(orig, None)
			except (OSError, IOError):
				debug('task: failed retrieving file')
				return None
			else:
				cnt += 1

		for node in self.outputs:
			self.generator.bld.node_sigs[node.id] = sig
			self.generator.bld.printout('restoring from cache %r\n' % node.bldpath())

		return 1

	def debug_why(self, old_sigs):
		"explains why a task is run"

		new_sigs = self.cache_sig
		def v(x):
			return x.encode('hex')

		debug("Task %r" % self)
		msgs = ['Task must run', '* Source file or manual dependency', '* Implicit dependency', '* Configuration data variable']
		tmp = 'task: -> %s: %s %s'
		for x in range(len(msgs)):
			if (new_sigs[x] != old_sigs[x]):
				debug(tmp % (msgs[x], v(old_sigs[x]), v(new_sigs[x])))

	def sig_explicit_deps(self):
		bld = self.generator.bld
		m = md5()

		# the inputs
		for x in self.inputs + getattr(self, 'dep_nodes', []):
			x.parent.rescan()
			m.update(bld.node_sigs[x.id])

		# manual dependencies, they can slow down the builds
		if bld.deps_man:
			additional_deps = bld.deps_man
			for x in self.inputs + self.outputs:
				try:
					d = additional_deps[x.id]
				except KeyError:
					continue

				for v in d:
					if isinstance(v, Node.Node):
						v.parent.rescan()
						try:
							v = bld.node_sigs[v.id]
						except KeyError: # make it fatal?
							v = ''
					elif hasattr(v, '__call__'):
						v = v() # dependency is a function, call it
					m.update(v)

		for x in self.deps_nodes:
			v = bld.node_sigs[x.id]
			m.update(v)

		return m.digest()

	def sig_vars(self):
		m = md5()
		bld = self.generator.bld
		env = self.env

		# dependencies on the environment vars
		act_sig = bld.hash_env_vars(env, self.__class__.vars)
		m.update(act_sig)

		# additional variable dependencies, if provided
		dep_vars = getattr(self, 'dep_vars', None)
		if dep_vars:
			m.update(bld.hash_env_vars(env, dep_vars))

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

		bld = self.generator.bld

		# get the task signatures from previous runs
		key = self.unique_id()
		prev_sigs = bld.task_sigs.get(key, ())
		if prev_sigs:
			try:
				# for issue #379
				if prev_sigs[2] == self.compute_sig_implicit_deps():
					return prev_sigs[2]
			except (KeyError, OSError):
				pass

		# no previous run or the signature of the dependencies has changed, rescan the dependencies
		(nodes, names) = self.scan()
		if Logs.verbose:
			debug('deps: scanner for %s returned %s %s' % (str(self), str(nodes), str(names)))

		# store the dependencies in the cache
		bld.node_deps[key] = nodes
		bld.raw_deps[key] = names

		# recompute the signature and return it
		sig = self.compute_sig_implicit_deps()

		return sig

	def compute_sig_implicit_deps(self):
		"""it is intended for .cpp and inferred .h files
		there is a single list (no tree traversal)
		this is the hot spot so ... do not touch"""
		m = md5()
		upd = m.update

		bld = self.generator.bld
		tstamp = bld.node_sigs
		env = self.env

		for k in bld.node_deps.get(self.unique_id(), []):
			# can do an optimization here
			k.parent.rescan()

			# if the parent folder is removed, a KeyError will be thrown
			if k.id & 3 == 2: # Node.FILE:
				upd(tstamp[k.id])
			else:
				upd(tstamp[k.id])

		return m.digest()

def funex(c):
	dc = {}
	exec(c, dc)
	return dc['f']

reg_act = re.compile(r"(?P<backslash>\\)|(?P<dollar>\$\$)|(?P<subst>\$\{(?P<var>\w+)(?P<code>.*?)\})", re.M)
def compile_fun_shell(name, line):
	"""Compiles a string (once) into a function, eg:
	simple_task_type('c++', '${CXX} -o ${TGT[0]} ${SRC} -I ${SRC[0].parent.bldpath()}')

	The env variables (CXX, ..) on the task must not hold dicts (order)
	The reserved keywords TGT and SRC represent the task input and output nodes

	quick test:
	bld.new_task_gen(source='wscript', rule='echo "foo\\${SRC[0].name}\\bar"')
	"""

	extr = []
	def repl(match):
		g = match.group
		if g('dollar'): return "$"
		elif g('backslash'): return '\\\\'
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
			else: app('" ".join([a.bldpath() for a in task.outputs])')
		else:
			if not var in dvars: dvars.append(var)
			app("p('%s')" % var)
	if parm: parm = "%% (%s) " % (',\n\t\t'.join(parm))
	else: parm = ''

	c = COMPILE_TEMPLATE_SHELL % (line, parm)

	debug('action: %s' % c)
	return (funex(c), dvars)

def compile_fun_noshell(name, line):

	extr = []
	def repl(match):
		g = match.group
		if g('dollar'): return "$"
		elif g('subst'): extr.append((g('var'), g('code'))); return "<<|@|>>"
		return None

	line2 = reg_act.sub(repl, line)
	params = line2.split('<<|@|>>')

	buf = []
	dvars = []
	app = buf.append
	for x in range(len(extr)):
		params[x] = params[x].strip()
		if params[x]:
			app("lst.extend(%r)" % params[x].split())
		(var, meth) = extr[x]
		if var == 'SRC':
			if meth: app('lst.append(task.inputs%s)' % meth)
			else: app("lst.extend([a.srcpath(env) for a in task.inputs])")
		elif var == 'TGT':
			if meth: app('lst.append(task.outputs%s)' % meth)
			else: app("lst.extend([a.bldpath() for a in task.outputs])")
		else:
			app('lst.extend(to_list(env[%r]))' % var)
			if not var in dvars: dvars.append(var)

	if extr:
		if params[-1]:
			app("lst.extend(%r)" % params[-1].split())

	fun = COMPILE_TEMPLATE_NOSHELL % "\n\t".join(buf)
	debug('action: %s' % fun)
	return (funex(fun), dvars)

def compile_fun(name, line, shell=None):
	"commands can be launched by the shell or not"
	if line.find('<') > 0 or line.find('>') > 0 or line.find('&&') > 0:
		shell = True
	#else:
	#	shell = False

	if shell is None:
		if sys.platform == 'win32':
			shell = False
		else:
			shell = True

	if shell:
		return compile_fun_shell(name, line)
	else:
		return compile_fun_noshell(name, line)

def simple_task_type(name, line, color='GREEN', vars=[], ext_in=[], ext_out=[], before=[], after=[], shell=None):
	"""return a new Task subclass with the function run compiled from the line given"""
	(fun, dvars) = compile_fun(name, line, shell)
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

	cls = type(Task)(name, (Task,), params)
	TaskBase.classes[name] = cls
	return cls

def always_run(cls):
	"""Set all task instances of this class to be executed whenever a build is started
	The task signature is calculated, but the result of the comparation between
	task signatures is bypassed
	"""
	old = cls.runnable_status
	def always(self):
		old(self)
		return RUN_ME
	cls.runnable_status = always
	return cls

def update_outputs(cls):
	"""When a command is always run, it is possible that the output only change
	sometimes. By default the build node have as a hash the signature of the task
	which may not change. With this, the output nodes (produced) are hashed,
	and the hashes are set to the build nodes

	This may avoid unnecessary recompilations, but it uses more resources
	(hashing the output files) so it is not used by default
	"""
	old_post_run = cls.post_run
	def post_run(self):
		old_post_run(self)
		bld = self.outputs[0].__class__.bld
		bld.node_sigs[self.outputs[0].id] = Utils.h_file(self.outputs[0].abspath())
	cls.post_run = post_run
	return cls

def extract_outputs(tasks):
	ins = {}
	outs = {}
	for x in tasks:
		for a in getattr(x, 'inputs', []):
			try: ins[a.id].append(x)
			except KeyError: ins[a.id] = [x]
		for a in getattr(x, 'outputs', []):
			try: outs[a.id].append(x)
			except KeyError: outs[a.id] = [x]

	links = set(ins.keys()).intersection(outs.keys())
	for k in links:
		for a in ins[k]:
			for b in outs[k]:
				a.set_run_after(b)

