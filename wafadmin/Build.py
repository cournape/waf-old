#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"""
Dependency tree holder

The class Build holds all the info related to a build:
* file system representation (tree of Node instances)
* various cached objects (task signatures, file scan results, ..)
"""

import os, sys, errno, re, gc, datetime, shutil
try: import cPickle
except: import pickle as cPickle
import Runner, TaskGen, Node, Scripting, Utils, ConfigSet, Task, Logs, Options, Configure
from Logs import debug, error, info
from Constants import *
from Base import WafError, Context, load_tool

SAVED_ATTRS = 'root node_deps raw_deps task_sigs'.split()
"Build class members to save"

class BuildError(WafError):
	def __init__(self, b=None, t=[]):
		self.bld = b
		self.tasks = t
		self.ret = 1
		WafError.__init__(self, self.format_error())

	def format_error(self):
		lst = ['Build failed']
		for tsk in self.tasks:
			txt = tsk.format_error()
			if txt: lst.append(txt)
		return '\n'.join(lst)

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

		# TODO waf 1.6 in theory there should be no reference to the TaskManager internals here
		if postpone:
			m = k[0].task_manager
			if not m.groups: m.add_group()
			m.groups[m.current_group].post_funs.append((fun, k, kw))
			kw['cwd'] = k[0].path
		else:
			fun(*k, **kw)
	return f

class BuildContext(Context):
	"""executes the build"""

	cmd = 'build'

	def __init__(self, start=None):
		super(BuildContext, self).__init__(start)

		if not getattr(self, 'top_dir', None):
			self.top_dir = Options.top_dir

		# output directory - may be set until the nodes are considered
		if not getattr(self, 'out_dir', None):
			self.out_dir = Options.out_dir

		try:
			self.variant_dir = os.path.join(self.out_dir, self.variant)
		except AttributeError:
			self.variant_dir = self.out_dir

		if not getattr(self, 'cache_dir', None):
			self.cache_dir = self.out_dir + os.sep + CACHE_DIR

		# the manager will hold the tasks
		self.task_manager = Runner.TaskManager()

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

		# list of targets to uninstall for removing the empty folders after uninstalling
		self.uninstall = []

		for v in 'task_sigs node_deps raw_deps'.split():
			setattr(self, v, {})

		# list of folders that are already scanned
		# so that we do not need to stat them one more time
		self.cache_dir_contents = {}

		self.all_task_gen = []
		self.task_gen_cache_names = {}
		self.log = None

		self.is_install = None

		############ stuff below has not been reviewed

		# Manual dependencies.
		self.deps_man = Utils.DefaultDict(list)

	def __call__(self, *k, **kw):
		"""Creates a task generator"""
		kw['bld'] = self
		return TaskGen.task_gen(*k, **kw)

	def __copy__(self):
		"""no build context copies"""
		raise WafError('build contexts are not supposed to be copied')

	def load_envs(self):
		try:
			lst = Utils.listdir(self.cache_dir)
		except OSError as e:
			if e.errno == errno.ENOENT:
				raise WafError('The project was not configured: run "waf configure" first!')
			else:
				raise

		if not lst:
			raise WafError('The cache directory is empty: reconfigure the project')

		for file in lst:
			if file.endswith(CACHE_SUFFIX):
				env = ConfigSet.ConfigSet(os.path.join(self.cache_dir, file))
				name = file[:-len(CACHE_SUFFIX)]
				self.all_envs[name] = env

				for f in env[CFG_FILES]:
					newnode = self.path.find_or_declare(f)
					try:
						hash = Utils.h_file(newnode.abspath(env))
					except (IOError, AttributeError):
						error("cannot find %r" % f)
						hash = SIG_NIL
					newnode.sig = hash

	def make_root(self):
		Node.Nod3 = self.node_class
		self.root = Node.Nod3('', None)

	def init_dirs(self, src, bld):
		if not self.root:
			self.make_root()
		self.path = self.srcnode = self.root.find_dir(src)
		self.bldnode = self.root.make_node(bld)
		self.bldnode.mkdir()

		# TODO to cache or not to cache?
		self.bld2src = {id(self.bldnode): self.srcnode}
		self.src2bld = {id(self.srcnode): self.bldnode}

	def prepare(self):
		self.is_install = 0

		self.load()

		self.init_dirs(self.top_dir, self.variant_dir)

		if not self.all_envs:
			self.load_envs()

	def run_user_code(self):
		self.execute_build()

	def execute_build(self):
		"""shared by install and uninstall"""

		self.recurse(self.curdir)
		self.pre_build()
		self.flush()
		try:
			self.compile()
		finally:
			if Options.options.progress_bar: print('')
			info("Waf: Leaving directory `%s'" % self.out_dir)
		self.post_build()

	def load(self):
		"load the cache from the disk"
		try:
			env = ConfigSet.ConfigSet(os.path.join(self.cache_dir, 'build.config.py'))
		except (IOError, OSError):
			pass
		else:
			if env['version'] < HEXVERSION:
				raise WafError('Version mismatch! reconfigure the project')
			for t in env['tools']:
				self.setup(**t)

		try:
			gc.disable()
			f = data = None

			Node.Nod3 = self.node_class

			try:
				f = open(os.path.join(self.variant_dir, DBFILE), 'rb')
			except (IOError, EOFError):
				# handle missing file/empty file
				pass

			if f:
				data = cPickle.load(f)
				for x in SAVED_ATTRS:
					setattr(self, x, data[x])
			else:
				debug('build: Build cache loading failed')

		finally:
			if f: f.close()
			gc.enable()

	def save(self):
		"store the cache on disk, see self.load"
		gc.disable()
		self.root.__class__.bld = None

		# some people are very nervous with ctrl+c so we have to make a temporary file
		Node.Nod3 = self.node_class
		db = os.path.join(self.variant_dir, DBFILE)
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
		debug('build: compile called')

		self.generator = Runner.Parallel(self, Options.options.jobs)

		def dw(on=True):
			if Options.options.progress_bar:
				if on: sys.stderr.write(Logs.colors.cursor_on)
				else: sys.stderr.write(Logs.colors.cursor_off)

		debug('build: executor starting')

		try:
			dw(on=False)
			self.generator.start()
		except KeyboardInterrupt:
			dw()
			if Runner.TaskConsumer.consumers:
				self.save()
			raise
		except Exception:
			dw()
			# do not store anything, for something bad happened
			raise
		else:
			dw()
			if Runner.TaskConsumer.consumers:
				self.save()

		if self.generator.error:
			raise BuildError(self, self.task_manager.tasks_done)

	def install(self):
		"this function is called for both install and uninstall"
		debug('build: install called')

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

	def setup(self, tool, tooldir=None, funs=None):
		"setup tools for build process"
		if isinstance(tool, list):
			for i in tool: self.setup(i, tooldir)
			return

		module = load_tool(tool, tooldir)
		if hasattr(module, "setup"): module.setup(self)

	# ======================================= #
	# node and folder handling

	# ======================================= #

	def get_env(self):
		return self.env_of_name('default')
	def set_env(self, name, val):
		self.all_envs[name] = val

	env = property(get_env, set_env)

	def add_manual_dependency(self, path, value):
		if isinstance(path, Node.Node):
			node = path
		elif os.path.isabs(path):
			node = self.root.find_resource(path)
		else:
			node = self.path.find_resource(path)
		self.deps_man[id(node)].append(value)

	def launch_node(self):
		"""return the launch directory as a node"""
		# p_ln is kind of private, but public in case if
		try:
			return self.p_ln
		except AttributeError:
			self.p_ln = self.root.find_dir(Options.launch_dir)
			return self.p_ln

	## the following methods are candidates for the stable apis ##

	def add_group(self, *k):
		self.task_manager.add_group(*k)

	def set_group(self, *k, **kw):
		self.task_manager.set_group(*k, **kw)

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
				return SIG_NIL

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
		debug('envhash: %r %r', ret, lst)

		cache[idx] = ret

		return ret

	def name_to_obj(self, name):
		"""retrieve a task generator from its name or its target name
		remember that names must be unique"""
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

		self.timer = Utils.Timer()
		# force the initialization of the mapping name->object in flush
		# name_to_obj can be used in userland scripts, in that case beware of incomplete mapping
		self.task_gen_cache_names = {}
		self.name_to_obj('')

		debug('build: delayed operation TaskGen.flush() called')

		if Options.options.compile_targets:
			debug('task_gen: posting task generators %r', Options.options.compile_targets)

			mana = self.task_manager

			to_post = []
			min_grp = 0
			for name in Options.options.compile_targets.split(','):
				tg = self.name_to_obj(name)

				if not tg:
					raise WafError('target %r does not exist' % name)

				m = mana.group_idx(tg)
				if m > min_grp:
					min_grp = m
					to_post = [tg]
				elif m == min_grp:
					to_post.append(tg)

			debug('group: Forcing up to group %s for target %s', mana.group_name(min_grp), Options.options.compile_targets)

			# post all the task generators in previous groups
			for i in xrange(len(mana.groups)):
				mana.current_group = i
				if i == min_grp:
					break
				g = mana.groups[i]
				debug('group: Forcing group %s', mana.group_name(g))
				for t in g.tasks_gen:
					debug('group: Posting %s', t.name or t.target)
					t.post()

			# then post the task generators listed in compile_targets in the last group
			for t in to_post:
				t.post()

		else:
			debug('task_gen: posting task generators (normal)')
			for i in range(len(self.task_manager.groups)):
				g = self.task_manager.groups[i]
				self.task_manager.current_group = i
				for tg in g.tasks_gen:
					# TODO limit the task generators to the one below the folder of ... (ita)
					tg.post()

	def env_of_name(self, name):
		try:
			return self.all_envs[name]
		except KeyError:
			error('no such environment: '+name)
			return None

	def progress_line(self, state, total, col1, col2):
		n = len(str(total))

		Utils.rot_idx += 1
		ind = Utils.rot_chr[Utils.rot_idx % 4]

		pc = (100.*state)/total
		eta = str(self.timer) #Utils.get_elapsed_time(ini)
		fs = "[%%%dd/%%%dd][%%s%%2d%%%%%%s][%s][" % (n, n, ind)
		left = fs % (state, total, col1, pc, col2)
		right = '][%s%s%s]' % (col1, eta, col2)

		cols = Logs.get_term_cols() - len(left) - len(right) + 2*len(col1) + 2*len(col2)
		if cols < 7: cols = 7

		ratio = int((cols*state)/total) - 1

		bar = ('='*ratio+'>').ljust(cols)
		msg = Utils.indicator % (left, bar, right)

		return msg

	def do_install(self, src, tgt, chmod=O644):
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
			info("* installing %s as %s" % (srclbl, tgt))

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
					error('File %r does not exist' % src)
				raise WafError('Could not install the file %r' % tgt)
			return True

		elif self.is_install < 0:
			info("* uninstalling %s" % tgt)

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

	def install_files(self, path, files, env=None, chmod=O644, relative_trick=False, cwd=None):
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

		Utils.check_dir(destpath)

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
					raise WafError("Unable to install the file %r (not found in %s)" % (filename, cwd))

				if relative_trick:
					destfile = os.path.join(destpath, filename)
					Utils.check_dir(os.path.dirname(destfile))
				else:
					destfile = os.path.join(destpath, nd.name)

				filename = nd.abspath()

			if self.do_install(filename, destfile, chmod):
				installed_files.append(destfile)
		return installed_files

	def install_as(self, path, srcfile, env=None, chmod=O644, cwd=None):
		"""
		srcfile may be a string or a Node representing the file to install

		returns True if the file was effectively installed, False otherwise
		"""
		if env:
			assert isinstance(env, ConfigSet.ConfigSet), "invalid parameter"
		else:
			env = self.env

		if not path:
			raise WafError("where do you want to install %r? (%r?)" % (srcfile, path))

		if not cwd:
			cwd = self.path

		destpath = self.get_install_path(path, env)

		dir, name = os.path.split(destpath)
		Utils.check_dir(dir)

		# the source path
		if isinstance(srcfile, Node.Node):
			src = srcfile.abspath()
		else:
			src = srcfile
			if not os.path.isabs(srcfile):
				node = cwd.find_resource(srcfile)
				if not node:
					raise WafError("Unable to install the file %r (not found in %s)" % (srcfile, cwd))
				src = node.abspath()

		return self.do_install(src, destpath, chmod)

	def symlink_as(self, path, src, env=None, cwd=None):
		"""example:  bld.symlink_as('${PREFIX}/lib/libfoo.so', 'libfoo.so.1.2.3') """

		if sys.platform == 'win32':
			# well, this *cannot* work
			return

		if not path:
			raise WafError("where do you want to install %r? (%r?)" % (src, path))

		tgt = self.get_install_path(path, env)

		dir, name = os.path.split(tgt)
		Utils.check_dir(dir)

		if self.is_install > 0:
			link = False
			if not os.path.islink(tgt):
				link = True
			elif os.readlink(tgt) != src:
				link = True

			if link:
				try: os.remove(tgt)
				except OSError: pass
				info('* symlink %s (-> %s)' % (tgt, src))
				os.symlink(src, tgt)
			return 0

		else: # UNINSTALL
			try:
				info('* removing %s' % (tgt))
				os.remove(tgt)
				return 0
			except OSError:
				return 1

	def exec_command(self, cmd, **kw):
		# 'runner' zone is printed out for waf -v, see wafadmin/Options.py
		debug('runner: system command -> %s' % cmd)
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
		f = self.log or sys.stderr
		f.write(s)
		#f.flush()


	def pre_recurse(self, name_or_mod, path, nexdir):
		if not hasattr(self, 'oldpath'):
			self.oldpath = []
		self.oldpath.append(self.path)
		self.path = self.root.find_dir(nexdir)
		return {'bld': self, 'ctx': self}

	def post_recurse(self, name_or_mod, path, nexdir):
		self.path = self.oldpath.pop()

	###### user-defined behaviour

	def pre_build(self):
		if hasattr(self, 'pre_funs'):
			for m in self.pre_funs:
				m(self)

	def post_build(self):
		if hasattr(self, 'post_funs'):
			for m in self.post_funs:
				m(self)

	def add_pre_fun(self, meth):
		try: self.pre_funs.append(meth)
		except AttributeError: self.pre_funs = [meth]

	def add_post_fun(self, meth):
		try: self.post_funs.append(meth)
		except AttributeError: self.post_funs = [meth]

	install_as = group_method(install_as)
	install_files = group_method(install_files)
	symlink_as = group_method(symlink_as)

# The classes below are stubs that integrate functionality from Scripting.py
# for now. TODO: separate more functionality from the build context.

class InstallContext(BuildContext):
	"""installs the targets on the system"""
	cmd = 'install'
	def run_user_code(self):
		self.is_install = INSTALL
		self.execute_build()
		self.install()

class UninstallContext(InstallContext):
	"""removes the targets installed"""
	cmd = 'uninstall'
	def run_user_code(self):
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
		self.recurse(self.curdir)
		try:
			self.clean()
		finally:
			self.save()

	def clean(self):
		debug('build: clean called')

		# TODO clean could remove the files except the ones listed in env[CFG_FILES]

		# forget about all the nodes
		self.root.children = {}

		for v in 'node_deps task_sigs raw_deps'.split():
			setattr(self, v, {})

class ListContext(BuildContext):
	"""lists the targets to execute"""

	cmd = 'list'
	def run_user_code(self):
		self.recurse(self.curdir)
		self.pre_build()
		self.flush()
		self.name_to_obj('')
		lst = list(self.task_gen_cache_names.keys())
		lst.sort()
		for k in lst:
			Logs.pprint('GREEN', k)

