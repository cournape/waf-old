#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"""
Dependency tree holder

The class Build holds all the info related to a build:
* file system representation (tree of Node instances)
* various cached objects (task signatures, file scan results, ..)

There is only one Build object at a time (Params.g_build singleton)
"""

import os, sys, cPickle, types, imp, errno, re
import Params, Runner, Object, Node, Scripting, Utils, Environment, Task
from Params import debug, error, fatal, warning
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
			if tsk.m_hasrun == Runner.crashed:
				try:
					lst.append(" -> task failed (err #%d): %s" % (tsk.err_code, str(tsk.m_outputs)))
				except AttributeError:
					lst.append(" -> task failed:" % str(tsk.m_outputs))
			elif tsk.m_hasrun == Runner.missing:
				lst.append(" -> missing files: %s" % str(tsk.m_outputs))
		return '\n'.join(lst)

class BuildDTO(object):
	"holds the data to store using cPickle"
	def __init__(self):
		pass
	def init(self, bdobj):
		global SAVED_ATTRS
		for a in SAVED_ATTRS:
			setattr(self, a, getattr(bdobj, a))
	def update_build(self, bdobj):
		global SAVED_ATTRS
		for a in SAVED_ATTRS:
			setattr(bdobj, a, getattr(self, a))

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
		self.m_curdirnode = None

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
			dto = cPickle.load(file)
			dto.update_build(self)
			file.close()
		except IOError:
			debug("resetting the build object (dto failed)", 'build')
			self._init_data()

	# store the data structures on disk, retrieve with self._load()
	def _store(self):
		file = open(os.path.join(self.m_bdir, DBFILE), 'wb')
		dto = BuildDTO()
		dto.init(self)
		cPickle.dump(dto, file, -1) # remove the '-1' for unoptimized version
		file.close()

	# ======================================= #

	def save(self):
		self._store()

	def clean(self):
		debug("clean called", 'build')
		def clean_rec(node):
			for x in node.childs:
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
		clean_rec(self.m_srcnode)

	def compile(self):
		debug("compile called", 'build')

		os.chdir(self.m_bdir)


		"""
		import cProfile, pstats
		cProfile.run("import Object; Object.flush()", 'profi.txt')
		p = pstats.Stats('profi.txt')
		p.sort_stats('cumulative').print_stats(80)
		"""
		Object.flush()
		#"""

		if Params.g_verbose>2: self.dump()

		self.task_manager.flush()
		if Params.g_options.jobs <= 1: executor = Runner.Serial(self)
		else: executor = Runner.Parallel(self, Params.g_options.jobs)
		self.generator = executor

		def dw():
			if Params.g_options.progress_bar: sys.stdout.write(Params.g_cursor_on)

		debug('executor starting', 'build')
		try:
			if Params.g_options.progress_bar: sys.stdout.write(Params.g_cursor_off)
			ret = executor.start()
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

		if Params.g_verbose>2: self.dump()
		os.chdir(self.m_srcnode.abspath())

	def install(self):
		"this function is called for both install and uninstall"
		debug('install called', 'build')

		Object.flush()
		for obj in Object.g_allobjs:
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

	def create_obj(self, *k, **kw):
		cls_name = k[0]
		try: cls = Object.task_gen.classes[cls_name]
		except KeyError: raise KeyError('%s is not a valid build tool -> %s' % (cls_name, [x for x in Object.task_gen.classes]))
		else: return cls(*k, **kw)

	def load_envs(self):
		cachedir = Params.g_cachedir
		try:
			if not os.path.isdir(cachedir):
				e = OSError()
				e.errno = errno.ENOENT
				raise e
			lst = os.listdir(cachedir)
		except OSError, e:
			if e.errno == errno.ENOENT:
				fatal('The project was not configured: run "waf configure" first!')
			else:
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
					hash = Params.h_file(newnode.abspath(env))
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
				self.m_curdirnode = self.m_srcnode
				return

		self.m_srcnode = self.ensure_dir_node_from_path(srcdir)
		debug("srcnode is %s and srcdir %s" % (str(self.m_srcnode.m_name), srcdir), 'build')

		self.m_curdirnode = self.m_srcnode

		self.m_bldnode = self.ensure_dir_node_from_path(self.m_bdir)

		# create this build dir if necessary
		try: os.makedirs(blddir)
		except OSError: pass

		self.init_variants()

	def ensure_dir_node_from_path(self, abspath):
		"return a node corresponding to an absolute path, creates nodes if necessary"
		debug('ensure_dir_node_from_path %s' % (abspath), 'build')
		plst = Utils.split_path(abspath)
		curnode = self.m_root # root of the tree
		for dirname in plst:
			if not dirname: continue
			if dirname == '.': continue
			found = curnode.get_dir(dirname, None)
			if not found:
				found = Node.Node(dirname, curnode, Node.DIR)
			curnode = found
		return curnode

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

		## scanning the root node does not work in win32;
		## additionally it does not seem to be needed.
		if src_dir_node is not self.m_root:
			## list the files in the src directory, adding the signatures
			self.scan_src_path(src_dir_node, src_dir_node.abspath())
		# list the files in the build dirs
		# remove the existing timestamps if the build files are removed

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
					src_dir_node.childs.__delitem__(node.m_name)
				os.makedirs(sub_path)

	# ======================================= #
	def scan_src_path(self, i_parent_node, i_path):

		try:
			# read the dir contents, ignore the folders in it
			if not os.path.isdir(i_path):
				e = OSError()
				e.errno = errno.ENOENT
				raise e
			listed_files = set(os.listdir(i_path))
		except OSError:
			warning("OSError exception in scan_src_path()  i_path=%r" % i_path)
			return None

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
				cache[node.id] = Params.h_file(i_path + os.sep + node.m_name)
			except IOError:
				fatal("a file is readonly or has become a dir "+node.abspath())

		# TODO remove the src nodes of deleted files

	def scan_path(self, i_parent_node, i_path, i_variant):
		"""in this function we do not add timestamps but we remove them
		when the files no longer exist (file removed in the build dir)"""

		i_existing_nodes = [x for x in i_parent_node.childs.values() if x.id & 3 == Node.BUILD]

		if not os.path.isdir(i_path):
			e = OSError()
			e.errno = errno.ENOENT
			raise e
		listed_files = set(os.listdir(i_path))
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
			print node, count
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
							accu += ' [%s,%s] ' % (str(variant), Params.view_sig(var[child.id]))
							accu += str(child.id)

					accu+='\n'
				elif tp == Node.BUILD:
					accu+= count * '-'
					accu+= '-> '+child.m_name+' (b) '

					for variant in self.m_tstamp_variants:
						var = self.m_tstamp_variants[variant]
						if child.id in var:
							accu+=' [%s,%s] ' % (str(variant), Params.view_sig(var[child.id]))
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
			error('no such environment'+name)
			return None

	def env(self, name='default'):
		return self.env_of_name(name)

	def add_group(self, name=''):
		Object.flush(all=0)
		self.task_manager.add_group(name)

	def add_manual_dependency(self, path, value):
		h = getattr(self, 'deps_man', {})
		node = self.m_curdirnode.find_resource(path)
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

