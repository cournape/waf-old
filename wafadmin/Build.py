#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"""
Dependency tree holder

The class Build holds all the info related to a build:
* file system representation (tree of Node instances)
* various cached objects (task signatures, file scan results, ..)

There is only one Build object at a time (Params.g_build singleton)
"""

import os, sys, cPickle, types, imp, errno, re, glob
import Params, Runner, TaskGen, Node, Scripting, Utils, Environment, Task, Install
from logging import debug, error, fatal
from Constants import *

SAVED_ATTRS = 'm_root m_srcnode m_bldnode m_tstamp_variants node_deps raw_deps bld_sigs id_nodes'.split()
"Build class members to save"

g_modcache = {}
"Cache for the tools (modules), re-importing raises errors"

class BuildError(Exception):
	def __init__(self, b=None, t=[]):
		self.bld = b
		self.tasks = t
		self.ret = 1
	def get_message(self):
		lst = ['Build failed']
		for tsk in self.tasks:
			if tsk.m_hasrun == CRASHED:
				try:
					lst.append(" -> task failed (err #%d): %s" % (tsk.err_code, str(tsk.m_outputs)))
				except AttributeError:
					lst.append(" -> task failed:" % str(tsk.m_outputs))
			elif tsk.m_hasrun == MISSING:
				lst.append(" -> missing files: %s" % str(tsk.m_outputs))
		return '\n'.join(lst)

class Build(object):
	"holds the dependency tree"
	def __init__(self):

		# there should be only one build dir in use at a time
		Params.g_build = self

		# instead of hashing the nodes, we assign them a unique id when they are created
		self.id_nodes = 0

		# initialize the filesystem representation
		self._init_data()

		# map names to environments, the 'default' must be defined
		self.m_allenvs = {}

		# ======================================= #
		# code for reading the scripts

		# project build directory - do not reset() from load_dirs() or _init_data()
		self.m_bdir = ''

		# the current directory from which the code is run
		# the folder changes everytime a wscript is read
		self.path = None

		# temporary holding the subdirectories containing scripts - look in Scripting.py
		self.m_subdirs = []

		# ======================================= #
		# cache variables

		# local cache for absolute paths - m_abspath_cache[variant][node]
		self.m_abspath_cache = {}

		# list of folders that are already scanned
		# so that we do not need to stat them one more time
		self.m_scanned_folders = {}

		# list of targets to uninstall for removing the empty folders after uninstalling
		self.m_uninstall = []

		# ======================================= #
		# tasks and objects

		# build dir variants (release, debug, ..)
		for v in 'm_tstamp_variants node_deps bld_sigs raw_deps m_abspath_cache'.split():
			var = {}
			setattr(self, v, var)

		self.cache_dir_contents = {}

	def _init_data(self):
		debug("init data called", 'build')

		# filesystem root - root name is Params.g_rootname
		self.m_root = Node.Node('', None, Node.DIR)

		self.m_srcnode = None # src directory
		self.m_bldnode = None # bld directory

		self.task_manager = Task.TaskManager()

	# load existing data structures from the disk (stored using self._store())
	def _load(self):
		cachedir = Params.g_cachedir
		code = ''
		try:
			file = open(os.path.join(cachedir, 'build.config.py'), 'r')
			code = file.read()
			file.close()
		except (IOError, OSError):
			# TODO load the pickled file and the environments better
			pass
		else:
			re_imp = re.compile('^(#)*?([^#=]*?)\ =\ (.*?)$', re.M)
			for m in re_imp.finditer(code):
				g = m.group
				if g(2) == 'version':
					if eval(g(3)) < HEXVERSION:
						Params.fatal('Version mismatch! reconfigure the project')
				elif g(2) == 'tools':
					lst = eval(g(3))
					for t in lst:
						self.setup(**t)

		try:
			file = open(os.path.join(self.m_bdir, DBFILE), 'rb')
			data = cPickle.load(file)
			for x in SAVED_ATTRS: setattr(self, x, data[x])
			file.close()
		except IOError:
			debug("Build cache loading failed (cleaning)", 'build')
			self._init_data()

	# store the data structures on disk, retrieve with self._load()
	def _store(self):
		file = open(os.path.join(self.m_bdir, DBFILE), 'wb')
		data = {}
		for x in SAVED_ATTRS: data[x] = getattr(self, x)
		cPickle.dump(data, file, -1) # remove the '-1' for unoptimized version
		file.close()

	# ======================================= #

	def save(self):
		self._store()

	def clean(self):
		debug("clean called", 'build')
		# FIXME this will not work for files created during the configuration dep_files
		def clean_rec(node):
			for x in node.childs.keys():
				nd = node.childs[x]

				tp = nd.id & 3
				if tp == Node.DIR:
					clean_rec(nd)
				elif tp == Node.BUILD:
					for env in self.m_allenvs.values():
						pt = nd.abspath(env)
						if pt in env['waf_config_files']: continue
						try: os.remove(pt)
						except OSError: pass
					node.childs.__delitem__(x)
		clean_rec(self.m_srcnode)

		for v in 'm_tstamp_variants node_deps bld_sigs raw_deps m_abspath_cache'.split():
			var = {}
			setattr(self, v, var)

	def compile(self):
		debug("compile called", 'build')

		os.chdir(self.m_bdir)


		"""
		import cProfile, pstats
		cProfile.run("import TaskGen; TaskGen.flush()", 'profi.txt')
		p = pstats.Stats('profi.txt')
		p.sort_stats('cumulative').print_stats(80)
		"""
		TaskGen.flush()
		#"""

		if Params.g_verbose>2: self.dump()

		self.generator = Runner.get_instance(self, Params.g_options.jobs)

		def dw(on=True):
			if Params.g_options.progress_bar:
				if on: sys.stdout.write(Params.g_cursor_on)
				else: sys.stdout.write(Params.g_cursor_off)

		debug('executor starting', 'build')
		try:
			dw(on=False)
			ret = self.generator.start()
		except KeyboardInterrupt, e:
			dw()
			os.chdir(self.m_srcnode.abspath())
			self._store()
			Params.pprint('RED', 'Build interrupted')
			if Params.g_verbose > 1: raise
			else: sys.exit(68)
		except Exception, e:
			dw()
			# do not store anything, for something bad happened
			raise
		else:
			dw()
			self._store()

		if ret:
			os.chdir(self.m_srcnode.abspath())
			Utils.test_full()
			raise BuildError(self, self.task_manager.tasks_done)

		if Params.g_verbose > 2: self.dump()
		os.chdir(self.m_srcnode.abspath())

	def install(self):
		"this function is called for both install and uninstall"
		debug('install called', 'build')

		TaskGen.flush()
		for obj in TaskGen.g_allobjs:
			if obj.m_posted: obj.install()

		# remove empty folders after uninstalling
		if Params.g_commands['uninstall']:
			lst = []
			for x in self.m_uninstall:
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

	def add_subdirs(self, dirs):
		for dir in Utils.to_list(dirs):
			if dir: Scripting.add_subdir(dir, self)

	def new_task_gen(self, *k, **kw):
		if len(k) == 0: return TaskGen.task_gen()
		cls_name = k[0]
		try: cls = TaskGen.task_gen.classes[cls_name]
		except KeyError: raise KeyError('%s is not a valid task generator -> %s' %
			(cls_name, [x for x in TaskGen.task_gen.classes]))
		else: return cls(*k, **kw)

	def load_envs(self):
		cachedir = Params.g_cachedir
		try:
			lst = Utils.listdir(cachedir)
		except OSError, e:
			if e.errno == errno.ENOENT:
				fatal('The project was not configured: run "waf configure" first!')
			else:
				# TODO: deal with network error and other OS errors.
				raise

		if not lst:
			fatal('The cache directory is empty: reconfigure the project')

		for file in lst:
			if file.endswith(CACHE_SUFFIX):
				env = Environment.Environment()
				env.load(os.path.join(cachedir, file))
				name = file.split('.')[0]

				self.m_allenvs[name] = env

		self.init_variants()

		for env in self.m_allenvs.values():
			for f in env['dep_files']:
				newnode = self.m_srcnode.find_or_declare(f)
				try:
					hash = Utils.h_file(newnode.abspath(env))
				except (IOError, AttributeError):
					error("cannot find "+f)
					hash = SIG_NIL
				self.m_tstamp_variants[env.variant()][newnode.id] = hash

	def setup(self, tool, tooldir=None, funs=None):
		"setup tools for build process"
		if type(tool) is types.ListType:
			for i in tool: self.setup(i, tooldir)
			return

		if not tooldir: tooldir = Params.g_tooldir

		file = None
		key = str((tool, tooldir))
		module = g_modcache.get(key, None)
		if not module:
			file,name,desc = imp.find_module(tool, tooldir)
			module = imp.load_module(tool,file,name,desc)
			g_modcache[key] = module
		if hasattr(module, "setup"): module.setup(self)
		if file: file.close()

	def init_variants(self):
		debug("init variants", 'build')

		lstvariants = []
		for env in self.m_allenvs.values():
			if not env.variant() in lstvariants:
				lstvariants.append(env.variant())
		self._variants = lstvariants

		debug("list of variants is "+str(lstvariants), 'build')

		for name in lstvariants+[0]:
			for v in 'm_tstamp_variants node_deps raw_deps m_abspath_cache'.split():
				var = getattr(self, v)
				if not name in var:
					var[name] = {}

	# ======================================= #
	# node and folder handling

	# this should be the main entry point
	def load_dirs(self, srcdir, blddir, isconfigure=None):
		"this functions should be the start of everything"

		# there is no reason to bypass this check
		try:
			if srcdir == blddir or os.path.abspath(srcdir) == os.path.abspath(blddir):
				fatal("build dir must be different from srcdir ->"+str(srcdir)+" ->"+str(blddir))
		except OSError:
			pass

		# set the source directory
		if not os.path.isabs(srcdir):
			srcdir = os.path.join(os.path.abspath('.'),srcdir)

		# set the build directory it is a path, not a node (either absolute or relative)
		if not os.path.isabs(blddir):
			self.m_bdir = os.path.abspath(blddir)
		else:
			self.m_bdir = blddir

		if not isconfigure:
			self._load()
			if self.m_srcnode:
				self.path = self.m_srcnode
				return

		self.m_srcnode = self.m_root.ensure_dir_node_from_path(srcdir)
		debug("srcnode is %s and srcdir %s" % (str(self.m_srcnode.m_name), srcdir), 'build')

		self.path = self.m_srcnode

		self.m_bldnode = self.m_root.ensure_dir_node_from_path(self.m_bdir)

		# create this build dir if necessary
		try: os.makedirs(blddir)
		except OSError: pass

		self.init_variants()

	def rescan(self, src_dir_node):
		""" first list the files in the src dir and update the nodes
		    - for each variant build dir (multiple build dirs):
		        - list the files in the build dir, update the nodes

		this makes (n bdirs)+srdir to scan (at least 2 folders)
		so we might want to do it in parallel in some future
		"""

		# FIXME use sets with intersection and union
		# do not rescan over and over again
		if self.m_scanned_folders.get(src_dir_node.id, None): return
		self.m_scanned_folders[src_dir_node.id] = 1

		#debug("rescanning "+str(src_dir_node), 'build')

		# TODO undocumented hook
		if hasattr(self, 'repository'): self.repository(src_dir_node)

		# list the files in the build dirs
		# remove the existing timestamps if the build files are removed
		if sys.platform == "win32" and not src_dir_node.m_name:
			return
		self.scan_src_path(src_dir_node, src_dir_node.abspath())

		# first obtain the differences between srcnode and src_dir_node
		#lst = self.m_srcnode.difflst(src_dir_node)
		h1 = self.m_srcnode.height()
		h2 = src_dir_node.height()

		lst = []
		child = src_dir_node
		while h2 > h1:
			lst.append(child.m_name)
			child = child.m_parent
			h2 -= 1
		lst.reverse()

		for variant in self._variants:
			sub_path = os.path.join(self.m_bldnode.abspath(), variant , *lst)
			try:
				self.scan_path(src_dir_node, sub_path, variant)
			except OSError:
				#debug("osError on " + sub_path, 'build')
				# listdir failed, remove all sigs of nodes
				# TODO more things to remove?
				dict = self.m_tstamp_variants[variant]
				for node in src_dir_node.childs.values():
					if node.id in dict:
						dict.__delitem__(node.id)

					# avoid deleting the build dir node
					if node.id != Params.g_build.m_bldnode.id:
						src_dir_node.childs.__delitem__(node.m_name)
				os.makedirs(sub_path)

	# ======================================= #
	def scan_src_path(self, i_parent_node, i_path):
		"""
		@param i_parent_node [Node]: parent node of path to scan.
		@param i_path [string]: path to folder to scan.
		@param i_existing_nodes: nodes already scanned ?"""

		listed_files = set(Utils.listdir(i_path))

		self.cache_dir_contents[i_parent_node.id] = listed_files
		debug("folder contents "+str(listed_files), 'build')

		node_names = set([x.m_name for x in i_parent_node.childs.values() if x.id & 3 == Node.FILE])
		cache = self.m_tstamp_variants[0]

		# nodes to keep
		to_keep = listed_files & node_names
		for x in to_keep:
			node = i_parent_node.childs[x]
			try:
				# do not call node.abspath here
				cache[node.id] = Utils.h_file(i_path + os.sep + node.m_name)
			except IOError:
				fatal("a file is readonly or has become a dir "+node.abspath())

		# remove both nodes and signatures
		to_remove = node_names - listed_files
		if to_remove:
			# infrequent scenario
			cache = self.m_tstamp_variants[0]
			for name in to_remove:
				nd = i_parent_node.childs[name]
				if nd.id in cache:
					cache.__delitem__(nd.id)
				i_parent_node.childs.__delitem__(name)

	def scan_path(self, i_parent_node, i_path, i_variant):
		"""in this function we do not add timestamps but we remove them
		when the files no longer exist (file removed in the build dir)"""

		i_existing_nodes = [x for x in i_parent_node.childs.values() if x.id & 3 == Node.BUILD]

		listed_files = set(Utils.listdir(i_path))
		node_names = set([x.m_name for x in i_existing_nodes])
		remove_names = node_names - listed_files

		# remove the stamps of the build nodes that no longer exist on the filesystem
		ids_to_remove = [x.id for x in i_existing_nodes if x.m_name in remove_names]
		cache = self.m_tstamp_variants[i_variant]
		for nid in ids_to_remove:
			if nid in cache:
				cache.__delitem__(nid)

	def dump(self):
		"for debugging"
		def recu(node, count):
			accu = count * '-'
			accu += "> %s (d) %d \n" % (node.m_name, node.id)

			for child in node.childs.values():
				tp = child.get_type()
				if tp == Node.FILE:
					accu += count * '-'
					accu += '-> '+child.m_name+' '

					for variant in self.m_tstamp_variants:
						var = self.m_tstamp_variants[variant]
						if child.id in var:
							accu += ' [%s,%s] ' % (str(variant), var[child.id].encode('hex'))
							accu += str(child.id)

					accu+='\n'
				elif tp == Node.BUILD:
					accu+= count * '-'
					accu+= '-> '+child.m_name+' (b) '

					for variant in self.m_tstamp_variants:
						var = self.m_tstamp_variants[variant]
						if child.id in var:
							accu+=' [%s,%s] ' % (str(variant), var[child.id].encode('hex'))
							accu += str(child.id)

					accu+='\n'
				elif tp == Node.DIR:
					accu += recu(child, count+1)
			return accu

		Params.pprint('CYAN', recu(self.m_root, 0) )
		Params.pprint('CYAN', 'size is '+str(self.m_root.size_subtree()))

	def env_of_name(self, name):
		if not name:
			error('env_of_name called with no name!')
			return None
		try:
			return self.m_allenvs[name]
		except KeyError:
			error('no such environment: '+name)
			return None

	def get_env(self):
		return self.env_of_name('default')
	def set_env(self, name, val):
		self.m_allenvs[name] = val

	env = property(get_env, set_env)

	def add_group(self, name=''):
		TaskGen.flush(all=0)
		self.task_manager.add_group(name)

	def add_manual_dependency(self, path, value):
		h = getattr(self, 'deps_man', {})
		if os.path.isabs(path):
			node = self.m_root.find_resource(path)
		else:
			node = self.path.find_resource(path)
		h[node] = value
		self.deps_man = h

	def set_sig_cache(self, key, val):
		self.bld_sigs[key] = val

	def get_sig_cache(self, key):
		try:
			return self.bld_sigs[key]
		except KeyError:
			s = SIG_NIL
			return (s, s, s, s, s)

	def launch_node(self):
		try:
			return self._launch_node
		except AttributeError:
			self._launch_node = self.m_root.find_dir(Params.g_cwd_launch)
			return self._launch_node

	def glob(self, pattern, relative=True):
		"files matching the pattern, seen from the current folder"
		path = Params.g_build.path.abspath()
		files = [self.m_root.find_resource(x) for x in glob.glob(path+os.sep+pattern)]
		if relative:
			files = [x.relpath(self.path) for x in files if x]
		else:
			files = [x.abspath() for x in files if x]
		return files

	# with this we do not need to import the Install module

	#def install_files(var, subdir, files, env=None, chmod=0644):
	def install_files(self, *k, **kw):
		return Install.install_files(*k, **kw)

	#def install_as(var, destfile, srcfile, env=None, chmod=0644):
	def install_as(self, *k, **kw):
		return Install.install_as(*k, **kw)

	#def symlink_as(var, src, dest, env=None):
	def symlink_as(self, *k, **kw):
		return Install.symlink_as(*k, **kw)

