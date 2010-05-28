#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
Dependency tree holder

The class Build holds all the info related to a build:
* file system representation (tree of Node instances)
* various cached objects (task signatures, file scan results, ..)
"""

import os, sys, errno, re, gc, datetime, shutil
try: import cPickle
except: import pickle as cPickle
import Runner, TaskGen, Node, Utils, ConfigSet, Task, Logs, Options, Base, Configure

INSTALL = 1337
"""positive value '->' install"""

UNINSTALL = -1337
"""negative value '<-' uninstall"""

SAVED_ATTRS = 'root node_deps raw_deps task_sigs'.split()
"""Build class members to save"""

CFG_FILES = 'cfg_files'
"""files from the build directory to hash before starting the build"""

class BuildError(Base.WafError):
	"""error raised during the build"""
	def __init__(self, b=None, t=[]):
		self.bld = b
		self.tasks = t
		Base.WafError.__init__(self, self.format_error())

	def format_error(self):
		lst = ['Build failed']
		for tsk in self.tasks:
			txt = tsk.format_error()
			if txt: lst.append(txt)
		return '\n'.join(lst)

def check_dir(dir):
	"""
	Ensure that a directory exists. Equivalent to mkdir -p.
	@type  dir: string
	@param dir: Path to directory
	"""
	try:
		os.stat(dir)
	except OSError:
		try:
			os.makedirs(dir)
		except OSError as e:
			raise Base.WafError('Cannot create folder %r (original error: %r)' % (dir, e))

def group_method(fun):
	"""
	sets a build context method to execute after the current group has finished executing
	this is useful for installing build files:
	* calling install_files/install_as will fail if called too early
	* people do not want to define install method in their task classes
	"""
	def f(*k, **kw):
		if not k[0].is_install:
			return False

		postpone = True
		if 'postpone' in kw:
			postpone = kw['postpone']
			del kw['postpone']

		if postpone:
			if not self.groups: self.add_group()
			self.groups[self.current_group].post_funs.append((fun, k, kw))
			kw['cwd'] = k[0].path
		else:
			fun(*k, **kw)
	return f

class BuildContext(Base.Context):
	"""executes the build"""

	cmd = 'build'
	variant = ''

	def __init__(self, *k, **kw):
		super(BuildContext, self).__init__(kw.get('start', None))

		self.top_dir = kw.get('top_dir', Options.top_dir)

		# output directory - may be set until the nodes are considered
		self.out_dir = kw.get('out_dir', Options.out_dir)

		self.variant_dir = kw.get('variant_dir', self.out_dir)

		self.variant = kw.get('variant', None)
		if self.variant:
			self.variant_dir = os.path.join(self.out_dir, self.variant)

		self.cache_dir = kw.get('cache_dir', None)
		if not self.cache_dir:
			self.cache_dir = self.out_dir + os.sep + Configure.CACHE_DIR

		# bind the build context to the nodes in use
		# this means better encapsulation and no build context singleton
		class node_class(Node.Node):
			pass
		self.node_class = node_class
		self.node_class.__module__ = "Node"
		self.node_class.__name__ = "Nod3"
		self.node_class.bld = self

		# map names to environments, the 'default' must be defined
		self.all_envs = {}

		# ======================================= #
		# code for reading the scripts

		# the current directory from which the code is run
		# the folder changes everytime a wscript is read
		self.path = None

		# nodes
		self.root = None

		# ======================================= #
		# cache variables

		for v in 'task_sigs node_deps raw_deps'.split():
			setattr(self, v, {})

		# list of folders that are already scanned
		# so that we do not need to stat them one more time
		self.cache_dir_contents = {}

		self.all_task_gen = []
		self.task_gen_cache_names = {}
		self.log = None

		############ stuff below has not been reviewed

		# Manual dependencies.
		self.deps_man = Utils.defaultdict(list)

		self.groups = []
		self.tasks_done = []
		self.current_group = 0
		self.groups_names = {}
		self.error = False


	def __call__(self, *k, **kw):
		"""Creates a task generator"""
		kw['bld'] = self
		ret = TaskGen.task_gen(*k, **kw)
		self.add_task_gen(ret)
		self.all_task_gen.append(ret)
		return ret

	def __copy__(self):
		"""Build context copies are not allowed"""
		raise Base.WafError('build contexts are not supposed to be copied')

	def load_envs(self):
		"""load the data from the project directory into self.allenvs"""
		try:
			lst = Utils.listdir(self.cache_dir)
		except OSError as e:
			if e.errno == errno.ENOENT:
				raise Base.WafError('The project was not configured: run "waf configure" first!')
			else:
				raise

		if not lst:
			raise Base.WafError('The cache directory is empty: reconfigure the project')

		for file in lst:
			if file.endswith(Configure.CACHE_SUFFIX):
				env = ConfigSet.ConfigSet(os.path.join(self.cache_dir, file))
				name = file[:-len(Configure.CACHE_SUFFIX)]
				self.all_envs[name] = env

				for f in env[CFG_FILES]:
					newnode = self.path.find_or_declare(f)
					try:
						hash = Utils.h_file(newnode.abspath())
					except (IOError, AttributeError):
						Logs.error('cannot find %r' % f)
						hash = Utils.SIG_NIL
					newnode.sig = hash

	def make_root(self):
		"""Creates a node representing the filesystem root"""
		Node.Nod3 = self.node_class
		self.root = Node.Nod3('', None)

	def init_dirs(self, src, bld):
		"""Initializes the project directory and the build directory"""
		if not self.root:
			self.make_root()
		self.path = self.srcnode = self.root.find_dir(src)
		self.bldnode = self.root.make_node(bld)
		self.bldnode.mkdir()
		self.variant_dir = self.bldnode.abspath()
		if self.variant:
			self.variant_dir += os.sep + self.variant

		# TODO to cache or not to cache?
		self.bld2src = {id(self.bldnode): self.srcnode}
		self.src2bld = {id(self.srcnode): self.bldnode}

	def prepare(self):
		"""see Context.prepare"""
		self.is_install = 0

		self.load()

		self.init_dirs(self.top_dir, self.variant_dir)

		if not self.all_envs:
			self.load_envs()

	def run_user_code(self):
		"""Overridden from Base.Context"""
		self.execute_build()

	def execute_build(self):
		"""Executes the build, it is shared by install and uninstall"""

		self.recurse(self.curdir)
		self.pre_build()
		self.flush()
		try:
			self.compile()
		finally:
			if Options.options.progress_bar: print('')
			Logs.info("Waf: Leaving directory `%s'" % self.out_dir)
		self.post_build()

	def load(self):
		"Loads the cache from the disk (pickle)"
		try:
			env = ConfigSet.ConfigSet(os.path.join(self.cache_dir, 'build.config.py'))
		except (IOError, OSError):
			pass
		else:
			if env['version'] < Base.HEXVERSION:
				raise Base.WafError('Version mismatch! reconfigure the project')
			for t in env['tools']:
				self.setup(**t)

		try:
			gc.disable()
			f = data = None

			Node.Nod3 = self.node_class

			try:
				f = open(os.path.join(self.variant_dir, Base.DBFILE), 'rb')
			except (IOError, EOFError):
				# handle missing file/empty file
				pass

			if f:
				data = cPickle.load(f)
				for x in SAVED_ATTRS:
					setattr(self, x, data[x])
			else:
				Logs.debug('build: Build cache loading failed')

		finally:
			if f: f.close()
			gc.enable()

	def save(self):
		"Stores the cache on disk (pickle), see self.load"
		gc.disable()
		self.root.__class__.bld = None

		# some people are very nervous with ctrl+c so we have to make a temporary file
		Node.Nod3 = self.node_class
		db = os.path.join(self.variant_dir, Base.DBFILE)
		file = open(db + '.tmp', 'wb')
		data = {}
		for x in SAVED_ATTRS: data[x] = getattr(self, x)
		cPickle.dump(data, file)
		file.close()

		# do not use shutil.move
		try: os.unlink(db)
		except OSError: pass
		os.rename(db + '.tmp', db)
		self.root.__class__.bld = self
		gc.enable()

	# ======================================= #

	def compile(self):
		"""The cache file is not written if nothing was build at all (build is up to date)"""
		Logs.debug('build: compile called')

		def dw(on=True):
			if Options.options.progress_bar:
				if on: sys.stderr.write(Logs.colors.cursor_on)
				else: sys.stderr.write(Logs.colors.cursor_off)

		Logs.debug('build: executor starting')

		try:
			dw(on=False)
			self.start()
		except KeyboardInterrupt:
			dw()
			#if Runner.TaskConsumer.consumers:
			# TODO optimize
			self.save()
			raise
		except Exception:
			dw()
			# do not store anything, for something bad happened
			raise
		else:
			dw()
			#if self.: TODO speed up the no-op build here
			self.save()

		if self.error:
			raise BuildError(self, self.tasks_done)

	def setup(self, tool, tooldir=None, funs=None):
		"""Loads the waf tools used during the build (task classes, etc)"""
		if isinstance(tool, list):
			for i in tool: self.setup(i, tooldir)
			return

		module = Base.load_tool(tool, tooldir)
		if hasattr(module, "setup"): module.setup(self)

	def get_env(self):
		return self.env_of_name('default')
	def set_env(self, name, val):
		self.all_envs[name] = val

	env = property(get_env, set_env)

	def env_of_name(self, name):
		"""Configuration data access"""
		try:
			return self.all_envs[name]
		except KeyError:
			Logs.error('no such environment: '+name)
			return None


	def add_manual_dependency(self, path, value):
		"""Adds a dependency from a node object to a path (string or node)"""
		if isinstance(path, Node.Node):
			node = path
		elif os.path.isabs(path):
			node = self.root.find_resource(path)
		else:
			node = self.path.find_resource(path)
		self.deps_man[id(node)].append(value)

	def launch_node(self):
		"""returns the launch directory as a node object"""
		try:
			# private cache
			return self.p_ln
		except AttributeError:
			self.p_ln = self.root.find_dir(Options.launch_dir)
			return self.p_ln

	## the following methods are candidates for the stable apis ##

	def hash_env_vars(self, env, vars_lst):
		"""hash environment variables
		['CXX', ..] -> [env['CXX'], ..] -> md5()

		cached by build context
		"""

		# ccroot objects use the same environment for building the .o at once
		# the same environment and the same variables are used

		if not env.table:
			env = env.parent
			if not env:
				return Utils.SIG_NIL

		idx = str(id(env)) + str(vars_lst)
		try:
			cache = self.cache_env
		except AttributeError:
			cache = self.cache_env = {}
		else:
			try:
				return self.cache_env[idx]
			except KeyError:
				pass

		lst = [str(env[a]) for a in vars_lst]
		ret = Utils.h_list(lst)
		Logs.debug('envhash: %r %r', ret, lst)

		cache[idx] = ret

		return ret

	def name_to_obj(self, name):
		"""Retrieves a task generator from its name or its target name
		the name must be unique"""
		cache = self.task_gen_cache_names
		if not cache:
			# create the index lazily
			for x in self.all_task_gen:
				if x.name:
					cache[x.name] = x
				else:
					if isinstance(x.target, str):
						target = x.target
					else:
						target = ' '.join(x.target)
					if not cache.get(target, None):
						cache[target] = x
		return cache.get(name, None)

	def flush(self):
		"""tell the task generators to create the tasks"""

		# setting the timer here looks weird
		self.timer = Utils.Timer()

		# force the initialization of the mapping name->object in flush
		# name_to_obj can be used in userland scripts, in that case beware of incomplete mapping
		self.task_gen_cache_names = {}
		self.name_to_obj('')

		Logs.debug('build: delayed operation TaskGen.flush() called')

		if Options.options.compile_targets:
			Logs.debug('task_gen: posting task generators %r', Options.options.compile_targets)

			to_post = []
			min_grp = 0
			for name in Options.options.compile_targets.split(','):
				tg = self.name_to_obj(name)

				if not tg:
					raise Base.WafError('target %r does not exist' % name)

				m = self.group_idx(tg)
				if m > min_grp:
					min_grp = m
					to_post = [tg]
				elif m == min_grp:
					to_post.append(tg)

			Logs.debug('group: Forcing up to group %s for target %s', self.group_name(min_grp), Options.options.compile_targets)

			# post all the task generators in previous groups
			for i in xrange(len(self.groups)):
				self.current_group = i
				if i == min_grp:
					break
				g = self.groups[i]
				Logs.debug('group: Forcing group %s', self.group_name(g))
				for tg in g.tasks_gen:
					Logs.debug('group: Posting %s', t.name or t.target)
					tg.post()

			# then post the task generators listed in compile_targets in the last group
			for tg in to_post:
				tg.post()

		else:
			Logs.debug('task_gen: posting task generators (normal)')
			for i in range(len(self.groups)):
				g = self.groups[i]
				self.current_group = i
				for tg in g.tasks_gen:
					# TODO limit the task generators to the one below the folder of ... (ita)
					tg.post()

	def progress_line(self, state, total, col1, col2):
		"""Compute the progress bar"""
		n = len(str(total))

		Utils.rot_idx += 1
		ind = Utils.rot_chr[Utils.rot_idx % 4]

		pc = (100.*state)/total
		eta = str(self.timer)
		fs = "[%%%dd/%%%dd][%%s%%2d%%%%%%s][%s][" % (n, n, ind)
		left = fs % (state, total, col1, pc, col2)
		right = '][%s%s%s]' % (col1, eta, col2)

		cols = Logs.get_term_cols() - len(left) - len(right) + 2*len(col1) + 2*len(col2)
		if cols < 7: cols = 7

		ratio = int((cols*state)/total) - 1

		bar = ('='*ratio+'>').ljust(cols)
		msg = Utils.indicator % (left, bar, right)

		return msg

	def exec_command(self, cmd, **kw):
		"""'runner' zone is printed out for waf -v, see wafadmin/Options.py"""
		Logs.debug('runner: system command -> %s' % cmd)
		if self.log:
			self.log.write('%s\n' % cmd)
			kw['log'] = self.log

		# ensure that a command is always frun from somewhere
		try:
			if not kw.get('cwd', None):
				kw['cwd'] = self.cwd
		except AttributeError:
			self.cwd = kw['cwd'] = self.variant_dir

		return Utils.exec_command(cmd, **kw)

	def printout(self, s):
		"""for printing stuff TODO remove?"""
		f = self.log or sys.stderr
		f.write(s)
		#f.flush()

	def pre_recurse(self, name_or_mod, path, nexdir):
		"""from the context class"""
		if not hasattr(self, 'oldpath'):
			self.oldpath = []
		self.oldpath.append(self.path)
		self.path = self.root.find_dir(nexdir)
		return {'bld': self, 'ctx': self}

	def post_recurse(self, name_or_mod, path, nexdir):
		"""from the context path"""
		self.path = self.oldpath.pop()

	def pre_build(self):
		"""executes the user-defined methods before the build starts"""
		if hasattr(self, 'pre_funs'):
			for m in self.pre_funs:
				m(self)

	def post_build(self):
		"""executes the user-defined methods after the build is complete"""
		if hasattr(self, 'post_funs'):
			for m in self.post_funs:
				m(self)

	def add_pre_fun(self, meth):
		"""binds a method to be executed after the scripts are read and before the build starts"""
		try: self.pre_funs.append(meth)
		except AttributeError: self.pre_funs = [meth]

	def add_post_fun(self, meth):
		"""binds a method to be executed immediately after the build is complete"""
		try: self.post_funs.append(meth)
		except AttributeError: self.post_funs = [meth]


	def group_name(self, g):
		"""name for the group g (utility)"""
		if not isinstance(g, BuildGroup):
			g = self.groups[g]
		for x in self.groups_names:
			if id(self.groups_names[x]) == id(g):
				return x
		return ''

	def group_idx(self, tg):
		"""group the task generator tg is in"""
		se = id(tg)
		for i in range(len(self.groups)):
			g = self.groups[i]
			for t in g.tasks_gen:
				if id(t) == se:
					return i
		return None

	def get_next_set(self):
		"""return the next set of tasks to execute
		the first parameter is the maximum amount of parallelization that may occur"""

		while self.current_group < len(self.groups):
			ret = self.groups[self.current_group].get_next_set()
			if ret:
				return ret
			else:
				self.groups[self.current_group].process_install()
				self.current_group += 1
		return []

	def add_group(self, name=None, move=True):
		#if self.groups and not self.groups[0].tasks:
		#	error('add_group: an empty group is already present')
		if name and name in self.groups_names:
			Logs.error('add_group: name %s already present' % name)
		g = BuildGroup()
		self.groups_names[name] = g
		self.groups.append(g)
		if move:
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
		if not self.groups:
			self.add_group()
		self.groups[self.current_group].tasks_gen.append(tgen)

	def add_task(self, task):
		if not self.groups:
			self.add_group()
		self.groups[self.current_group].tasks.append(task)

	def total(self):
		total = 0
		for group in self.groups:
			for tg in group.tasks_gen:
				total += len(tg.tasks)
		return total

	def add_finished(self, tsk):
		self.tasks_done.append(tsk)
		bld = tsk.generator.bld
		return # TODO
		if bld.is_install:
			f = None
			if 'install' in tsk.__dict__:
				f = tsk.__dict__['install']
				# install=0 to prevent installation
				if f: f(tsk)
			else:
				tsk.install()

	def start(self):
		self.generator = Runner.Parallel(self)
		self.generator.start() # vroom
		self.error = self.generator.error


	def install_files(self, *k, **kw):
		pass

	def install_as(self, *k, **kw):
		pass

	def symlink_as(self, *k, **kw):
		pass

class BuildGroup(object):
	"""all the tasks from one group must be done before going to the next group"""
	def __init__(self):
		self.tasks = [] # this list will be consumed
		self.tasks_gen = []

		self.cstr_groups = Utils.defaultdict(list) # tasks having equivalent constraints
		self.cstr_order = Utils.defaultdict(set) # partial order between the cstr groups
		self.temp_tasks = [] # tasks put on hold
		self.post_funs = []

	def reset(self):
		"clears the state of the object (put back the tasks into self.tasks)"
		for x in self.cstr_groups:
			self.tasks += self.cstr_groups[x]
		self.tasks = self.temp_tasks + self.tasks
		self.temp_tasks = []
		self.cstr_groups = Utils.defaultdict(list)
		self.cstr_order = Utils.defaultdict(set)

	def process_install(self):
		for (f, k, kw) in self.post_funs:
			f(*k, **kw)

	def make_cstr_groups(self):
		"join the tasks that have similar constraints"
		self.cstr_groups = Utils.defaultdict(list)
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

	def get_next_set(self):
		"next list of tasks that may be executed in parallel"

		if not getattr(self, 'ready_iter', None):

			# if the constraints are set properly (ext_in/ext_out, before/after)
			# the method set_file_constraints is not necessary (can be 15% penalty on no-op rebuilds)
			#
			# the constraint extraction thing is splitting the tasks by groups of independent tasks that may be parallelized
			# this is slightly redundant with the task manager groups
			#
			# if the tasks have only files, set_file_constraints is required but extract_constraints is not necessary
			#
			for tg in self.tasks_gen:
				# insert the task objects
				self.tasks.extend(tg.tasks)

			self.set_file_constraints(self.tasks)
			self.make_cstr_groups()
			self.extract_constraints()

			self.ready_iter = True

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

		if not toreturn:
			self.ready_iter = False
			if remainder:
				raise Base.WafError("Circular order constraint detected %r" % remainder)

		return toreturn

	def set_file_constraints(self, tasks):
		"will set the run_after constraints on all tasks (may cause a slowdown with lots of tasks)"
		ins = {}
		outs = {}
		for x in tasks:
			for a in getattr(x, 'inputs', []):
				try:
					ins[id(a)].append(x)
				except KeyError:
					ins[id(a)] = [x]
			for a in getattr(x, 'outputs', []):
				try:
					outs[id(a)].append(x)
				except KeyError:
					outs[id(a)] = [x]

		links = set(ins.keys()).intersection(outs.keys())
		for k in links:
			for a in ins[k]:
				for b in outs[k]:
					a.set_run_after(b)

# The classes below are stubs that integrate functionality from Scripting.py
# for now. TODO: separate more functionality from the build context.

class InstallContext(BuildContext):
	"""installs the targets on the system"""
	cmd = 'install'

	def __init__(self, start=None):
		super(InstallContext, self).__init__(start)

		# list of targets to uninstall for removing the empty folders after uninstalling
		self.uninstall = []

		self.is_install = INSTALL

	def run_user_code(self):
		"""see Context.run_user_code"""
		self.is_install = INSTALL
		self.execute_build()
		self.install()

	def do_install(self, src, tgt, chmod=Utils.O644):
		"""returns true if the file was effectively installed or uninstalled, false otherwise"""
		if self.is_install > 0:
			if not Options.options.force:
				# check if the file is already there to avoid a copy
				try:
					st1 = os.stat(tgt)
					st2 = os.stat(src)
				except OSError:
					pass
				else:
					# same size and identical timestamps -> make no copy
					if st1.st_mtime >= st2.st_mtime and st1.st_size == st2.st_size:
						return False

			srclbl = src.replace(self.srcnode.abspath()+os.sep, '')
			Logs.info("* installing %s as %s" % (srclbl, tgt))

			# following is for shared libs and stale inodes (-_-)
			try: os.remove(tgt)
			except OSError: pass

			try:
				shutil.copy2(src, tgt)
				os.chmod(tgt, chmod)
			except IOError:
				try:
					os.stat(src)
				except (OSError, IOError):
					Logs.error('File %r does not exist' % src)
				raise Base.WafError('Could not install the file %r' % tgt)
			return True

		elif self.is_install < 0:
			Logs.info("* uninstalling %s" % tgt)

			self.uninstall.append(tgt)

			try:
				os.remove(tgt)
			except OSError as e:
				if e.errno != errno.ENOENT:
					if not getattr(self, 'uninstall_error', None):
						self.uninstall_error = True
						Logs.warn('build: some files could not be uninstalled (retry with -vv to list them)')
					if Logs.verbose > 1:
						Logs.warn('could not remove %s (error code %r)' % (e.filename, e.errno))
			return True

	def get_install_path(self, path, env=None):
		"installation path prefixed by the destdir, the variables like in '${PREFIX}/bin' are substituted"
		if not env: env = self.env
		destdir = Options.options.destdir
		path = path.replace('/', os.sep)
		destpath = Utils.subst_vars(path, env)
		if destdir:
			destpath = os.path.join(destdir, destpath.lstrip(os.sep))
		return destpath

	def install(self):
		"""Called for both install and uninstall"""
		Logs.debug('build: install called')

		self.flush()

		# remove empty folders after uninstalling
		if self.is_install < 0:
			lst = []
			for x in self.uninstall:
				dir = os.path.dirname(x)
				if not dir in lst: lst.append(dir)
			lst.sort()
			lst.reverse()

			nlst = []
			for y in lst:
				x = y
				while len(x) > 4:
					if not x in nlst: nlst.append(x)
					x = os.path.dirname(x)

			nlst.sort()
			nlst.reverse()
			for x in nlst:
				try: os.rmdir(x)
				except OSError: pass

	def install_files(self, path, files, env=None, chmod=Utils.O644, relative_trick=False, cwd=None):
		"""To install files only after they have been built, put the calls in a method named
		post_build on the top-level wscript

		The files must be a list and contain paths as strings or as Nodes

		The relative_trick flag can be set to install folders, use bld.path.ant_glob() with it
		"""
		if env:
			assert isinstance(env, ConfigSet.ConfigSet), "invalid parameter"
		else:
			env = self.env

		if not path: return []

		if not cwd:
			cwd = self.path

		lst = Utils.to_list(files)

		if not getattr(lst, '__iter__', False):
			lst = [lst]

		destpath = self.get_install_path(path, env)

		check_dir(destpath)

		installed_files = []
		for filename in lst:
			if isinstance(filename, str) and os.path.isabs(filename):
				alst = Utils.split_path(filename)
				destfile = os.path.join(destpath, alst[-1])
			else:
				if isinstance(filename, Node.Node):
					nd = filename
				else:
					nd = cwd.find_resource(filename)
				if not nd:
					raise Base.WafError("Unable to install the file %r (not found in %s)" % (filename, cwd))

				if relative_trick:
					destfile = os.path.join(destpath, filename)
					check_dir(os.path.dirname(destfile))
				else:
					destfile = os.path.join(destpath, nd.name)

				filename = nd.abspath()

			if self.do_install(filename, destfile, chmod):
				installed_files.append(destfile)
		return installed_files

	def install_as(self, path, srcfile, env=None, chmod=Utils.O644, cwd=None):
		"""
		srcfile may be a string or a Node representing the file to install

		returns True if the file was effectively installed, False otherwise
		"""
		if env:
			assert isinstance(env, ConfigSet.ConfigSet), "invalid parameter"
		else:
			env = self.env

		if not path:
			raise Base.WafError("where do you want to install %r? (%r?)" % (srcfile, path))

		if not cwd:
			cwd = self.path

		destpath = self.get_install_path(path, env)

		dir, name = os.path.split(destpath)
		check_dir(dir)

		# the source path
		if isinstance(srcfile, Node.Node):
			src = srcfile.abspath()
		else:
			src = srcfile
			if not os.path.isabs(srcfile):
				node = cwd.find_resource(srcfile)
				if not node:
					raise Base.WafError("Unable to install the file %r (not found in %s)" % (srcfile, cwd))
				src = node.abspath()

		return self.do_install(src, destpath, chmod)

	def symlink_as(self, path, src, env=None, cwd=None):
		"""example:  bld.symlink_as('${PREFIX}/lib/libfoo.so', 'libfoo.so.1.2.3') """

		if sys.platform == 'win32':
			# well, this *cannot* work
			return

		if not path:
			raise Base.WafError("where do you want to install %r? (%r?)" % (src, path))

		tgt = self.get_install_path(path, env)

		dir, name = os.path.split(tgt)
		check_dir(dir)

		if self.is_install > 0:
			link = False
			if not os.path.islink(tgt):
				link = True
			elif os.readlink(tgt) != src:
				link = True

			if link:
				try: os.remove(tgt)
				except OSError: pass
				Logs.info('* symlink %s (-> %s)' % (tgt, src))
				os.symlink(src, tgt)
			return 0

		else: # UNINSTALL
			try:
				Logs.info('* removing %s' % (tgt))
				os.remove(tgt)
				return 0
			except OSError:
				return 1

	install_as = group_method(install_as)
	install_files = group_method(install_files)
	symlink_as = group_method(symlink_as)


class UninstallContext(InstallContext):
	"""removes the targets installed"""
	cmd = 'uninstall'
	def run_user_code(self):
		"""see Context.run_user_code"""
		self.is_install = UNINSTALL

		try:
			# do not execute any tasks
			def runnable_status(self):
				return SKIP_ME
			setattr(Task.Task, 'runnable_status_back', Task.Task.runnable_status)
			setattr(Task.Task, 'runnable_status', runnable_status)
			self.execute_build()
			self.install()
		finally:
			setattr(Task.Task, 'runnable_status', Task.Task.runnable_status_back)

class CleanContext(BuildContext):
	"""cleans the project"""
	cmd = 'clean'
	def run_user_code(self):
		"""see Context.run_user_code"""
		self.recurse(self.curdir)
		try:
			self.clean()
		finally:
			self.save()

	def clean(self):
		Logs.debug('build: clean called')

		# TODO clean could remove the files except the ones listed in env[CFG_FILES]

		# forget about all the nodes
		self.root.children = {}

		for v in 'node_deps task_sigs raw_deps'.split():
			setattr(self, v, {})

class ListContext(BuildContext):
	"""lists the targets to execute"""

	cmd = 'list'
	def run_user_code(self):
		"""see Context.run_user_code"""
		self.recurse(self.curdir)
		self.pre_build()
		self.flush()
		self.name_to_obj('')
		lst = list(self.task_gen_cache_names.keys())
		lst.sort()
		for k in lst:
			Logs.pprint('GREEN', k)

