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

	def call_run(self):
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
			lst = [a.path_from(bld.srcnode) for a in self.outputs]
			perm = self.attr('chmod', O644)
			if self.attr('src'):
				# if src is given, install the sources too
				lst += [a.path_from(bld.srcnode) for a in self.inputs]
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
				if node.sig != new_sig:
					return RUN_ME
			except AttributeError:
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
			node.sig = sig

		bld.task_sigs[self.unique_id()] = self.cache_sig

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
			m.update(x.sig)

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
							v = v.sig
						except AttributeError: # make it fatal?
							v = ''
					elif hasattr(v, '__call__'):
						v = v() # dependency is a function, call it
					m.update(v)

		for x in self.deps_nodes:
			m.update(x.sig)

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
			except (AttributeError, OSError):
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
		env = self.env

		for k in bld.node_deps.get(self.unique_id(), []):
			# can do an optimization here
			k.parent.rescan()
			upd(k.sig) # should thow an AttributeError

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
	"""
	Task class decorator

	Set all task instances of this class to be executed whenever a build is started
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
	"""
	Task class decorator

	When a command is always run, it is possible that the output only change
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
		self.outputs[0].sig = Utils.h_file(self.outputs[0].abspath())
	cls.post_run = post_run
	return cls







def can_retrieve_cache(self):
	"""
	Retrieve build nodes from the cache
	update the file timestamps to help cleaning the least used entries from the cache
	additionally, set an attribute 'cached' to avoid re-creating the same cache files

	suppose there are files in cache/dir1/file1 and cache/dir2/file2
	first, read the timestamp of dir1
	then try to copy the files
	then look at the timestamp again, if it has changed, the data may have been corrupt (cache update by another process)
	should an exception occur, ignore the data
	"""

	env = self.env
	sig = self.signature()
	ssig = sig.encode('hex')

	# first try to access the cache folder for the task
	dname = os.path.join(Options.cache_global, ssig)
	try:
		t1 = os.stat(dname).st_mtime
	except OSError:
		return None

	for node in self.outputs:
		orig = os.path.join(dname, node.name)
		try:
			shutil.copy2(orig, node.abspath())
			# mark the cache file as used recently (modified)
			os.utime(orig, None)
		except (OSError, IOError):
			debug('task: failed retrieving file')
			return None

	# is it the same folder?
	try:
		t2 = os.stat(dname).st_mtime
	except OSError:
		return None

	if t1 != t2:
		return None

	for node in self.outputs:
		node.sig = sig
		if Options.options.progress_bar < 1:
			self.generator.bld.printout('restoring from cache %r\n' % node.bldpath(env))

	self.cached = True
	return True

def put_files_cache(self):

	# file caching, if possible
	# try to avoid data corruption as much as possible
	if getattr(self, 'cached', None):
		return None

	dname = os.path.join(Options.cache_global, ssig)
	tmpdir = tempfile.mkdtemp(prefix=Options.cache_global)

	try:
		shutil.rmtree(dname)
	except:
		pass

	try:
		for node in self.outputs:
			dest = os.path.join(tmpdir, node.name)
			shutil.copy2(node.abspath(), dest)
	except (OSError, IOError):
		try:
			shutil.rmtree(tmpdir)
		except:
			pass
	else:
		try:
			os.rename(tmpdir, dname)
		except OSError:
			try:
				shutil.rmtree(tmpdir)
			except:
				pass
		else:
			try:
				os.chmod(dname, O755)
			except:
				pass

def cache_outputs(cls):
	"""
	Task class decorator

	If Options.cache_global is defined and if the task instances produces output nodes,
	the files will be copied into a folder in the cache directory

	the files may also be retrieved from that folder, if it exists
	"""
	if not Options.cache_global or Options.options.nocache or not self.outputs:
		return None

	old = cls.run
	def run(self):
		return can_retrieve_cache(self) or old(self)
	cls.run = run

	old = cls.post_run
	def post_run(self):
		ret = old(self)
		put_files_cache(self)
		return ret
	cls.post_run = post_run

	return cls


