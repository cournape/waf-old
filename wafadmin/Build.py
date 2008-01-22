#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Dependency tree holder"

import os, sys, cPickle, types, imp
import Params, Runner, Object, Node, Task, Scripting, Utils, Environment, Task
from Params import debug, error, fatal, warning

SAVED_ATTRS = 'm_root m_srcnode m_bldnode m_tstamp_variants m_depends_on m_raw_deps m_sig_cache'.split()
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

		# dependency tree
		self._init_data()

		# ======================================= #
		# globals

		# map a name to an environment, the 'default' must be defined
		self.m_allenvs = {}

		# there should be only one build dir in use at a time
		Params.g_build = self

		# ======================================= #
		# code for reading the scripts

		# project build directory - do not reset() from load_dirs() or _init_data()
		self.m_bdir = ''

		# the current directory from which the code is run
		# the folder changes everytime a wscript is read
		self.m_curdirnode = None

		# temporary holding the subdirectories containing scripts - look in Scripting.py
		self.m_subdirs=[]

		# ======================================= #
		# cache variables

		# local cache for absolute paths - m_abspath_cache[variant][node]
		self.m_abspath_cache = {}

		# local cache for relative paths
		# two nodes - hashtable of hashtables - g_relpath_cache[child][parent])
		self._relpath_cache = {}

		# list of folders that are already scanned
		# so that we do not need to stat them one more time
		self.m_scanned_folders  = []

		# file contents
		self._cache_node_content = {}

		# list of targets to uninstall for removing the empty folders after uninstalling
		self.m_uninstall = []

		# ======================================= #
		# tasks and objects

		# build dir variants (release, debug, ..)
		for name in ['default', 0]:
			for v in 'm_tstamp_variants m_depends_on m_sig_cache m_raw_deps m_abspath_cache'.split():
				var = getattr(self, v)
				if not name in var: var[name] = {}

		# TODO used by xmlwaf
		self.pushed = []

	def _init_data(self):
		debug("init data called", 'build')

		# filesystem root - root name is Params.g_rootname
		self.m_root            = Node.Node('', None)

		# source directory
		self.m_srcnode         = None
		# build directory
		self.m_bldnode         = None

		# TODO: this code does not look too good
		# nodes signatures: self.m_tstamp_variants[variant_name][node] = signature_value
		self.m_tstamp_variants = {}

		# one node has nodes it depends on, tasks cannot be stored
		# self.m_depends_on[variant][node] = [node1, node2, ..]
		self.m_depends_on      = {}

		# results of a scan: self.m_raw_deps[variant][node] = [filename1, filename2, filename3]
		# for example, find headers in c files
		self.m_raw_deps        = {}

		self.m_sig_cache       = {}

		self.task_manager      = Task.TaskManager()

	# load existing data structures from the disk (stored using self._store())
	def _load(self):
		try:
			file = open(os.path.join(self.m_bdir, Params.g_dbfile), 'rb')
			dto = cPickle.load(file)
			dto.update_build(self)
			file.close()
		except IOError:
			debug("resetting the build object (dto failed)", 'build')
			self._init_data()
		if Params.g_verbose>2: self.dump()

	# store the data structures on disk, retrieve with self._load()
	def _store(self):
		file = open(os.path.join(self.m_bdir, Params.g_dbfile), 'wb')
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
			for x in node.m_build_lookup:
				nd = node.m_build_lookup[x]
				for env in self.m_allenvs.values():
					pt = nd.abspath(env)
					# do not remove config files
					if pt in env['waf_config_files']: continue
					try: os.remove(pt)
					except OSError: pass
			for x in node.m_dirs_lookup:
				nd = node.m_dirs_lookup[x]
				clean_rec(nd)
		clean_rec(self.m_srcnode)

	def compile(self):
		debug("compile called", 'build')

		os.chdir(self.m_bdir)

		Object.flush()

		if Params.g_verbose>2: self.dump()

		self.task_manager.flush()
		if Params.g_options.jobs <= 1: executor = Runner.Serial(self)
		else: executor = Runner.Parallel(self, Params.g_options.jobs)
		# TODO clean
		self.generator = executor

		def dw():
			if Params.g_options.progress_bar: sys.stdout.write(Params.g_cursor_on)

		debug("executor starting", 'build')
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
			Utils.test_full()
			raise BuildError(self, self.task_manager.tasks_done)

		if Params.g_verbose>2: self.dump()
		os.chdir(self.m_srcnode.abspath())

	def install(self):
		"this function is called for both install and uninstall"
		debug("install called", 'build')

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
		lst = Utils.to_list(dirs)
		for d in lst:
			if not d: continue
			Scripting.add_subdir(d, self)

	def create_obj(self, objname, *k, **kw):
		try: return Object.g_allclasses[objname](*k, **kw)
		except KeyError: raise KeyError("'%s' is not a valid build tool -> %s" % (objname, [x for x in Object.g_allclasses]))

	def load_envs(self):
		cachedir = Params.g_cachedir
		try:
			lst = os.listdir(cachedir)
		except OSError:
			fatal('The project was not configured: run "waf configure" first!')
		if not lst:
			fatal('The cache directory is empty: reconfigure the project')
		for file in lst:
			if not file.endswith('.cache.py'): continue
			env = Environment.Environment()
			env.load(os.path.join(cachedir, file))
			name = file.split('.')[0]

			self.m_allenvs[name] = env
			for t in env['tools']: self.setup(**t)

		self._initialize_variants()

		for env in self.m_allenvs.values():
			for f in env['dep_files']:
				newnode = self.m_srcnode.find_build(f, create=1)
				try:
					hash = Params.h_file(newnode.abspath(env))
				except IOError:
					error("cannot find "+f)
					hash = Params.sig_nil
				except AttributeError:
					error("cannot find "+f)
					hash = Params.sig_nil
				self.m_tstamp_variants[env.variant()][newnode] = hash

	def setup(self, tool, tooldir=None):
		"setup tools for build process"
		if type(tool) is types.ListType:
			for i in tool: self.setup(i)
			return

		if not tooldir: tooldir = Params.g_tooldir
		#print "setting up ", tool, self

		file = None
		key = str((tool, tooldir))
		module = g_modcache.get(key, None)
		if not module:
			file,name,desc = imp.find_module(tool, tooldir)
			module = imp.load_module(tool,file,name,desc)
			g_modcache[key] = module
		if hasattr(module, "setup"): module.setup(self)
		if file: file.close()


	def _initialize_variants(self):
		debug("init variants", 'build')

		lstvariants = []
		for env in self.m_allenvs.values():
			if not env.variant() in lstvariants:
				lstvariants.append(env.variant())
		self._variants = lstvariants

		debug("list of variants is "+str(lstvariants), 'build')

		for name in lstvariants+[0]:
			for v in 'm_tstamp_variants m_depends_on m_raw_deps m_abspath_cache'.split():
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
			if srcdir == blddir or os.path.abspath(srcdir)==os.path.abspath(blddir):
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
		debug("srcnode is %s and srcdir %s" % (str(self.m_srcnode), srcdir), 'build')

		self.m_curdirnode = self.m_srcnode

		self.m_bldnode = self.ensure_dir_node_from_path(self.m_bdir)

		# create this build dir if necessary
		try: os.makedirs(blddir)
		except OSError: pass

		self._initialize_variants()

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
				found = Node.Node(dirname, curnode)
				curnode.append_dir(found)
			curnode = found
		return curnode

	def prescan(self):
		self.rescan_recursively(self.m_srcnode)

	def rescan_recursively(self, src_dir_node):
		self.rescan(src_dir_node)
		tbl = src_dir_node.m_dirs_lookup
		for x in tbl:
			self.rescan_recursively(tbl[x])

	def rescan(self, src_dir_node):
		""" first list the files in the src dir and update the nodes
		    - for each variant build dir (multiple build dirs):
		        - list the files in the build dir, update the nodes

		this makes (n bdirs)+srdir to scan (at least 2 folders)
		so we might want to do it in parallel in some future
		"""

		# do not rescan over and over again
		if src_dir_node.hash_value in self.m_scanned_folders: return

		# do not rescan the nodes above srcnode
		if src_dir_node.height() < self.m_srcnode.height(): return

		#debug("rescanning "+str(src_dir_node), 'build')

		# list the files in the src directory, adding the signatures
		files = self.scan_src_path(src_dir_node, src_dir_node.abspath(), src_dir_node.files())
		#debug("files found in folder are "+str(files), 'build')
		src_dir_node.m_files_lookup={}
		for i in files:	src_dir_node.m_files_lookup[i.m_name]=i

		# list the files in the build dirs
		# remove the existing timestamps if the build files are removed

		# first obtain the differences between srcnode and src_dir_node
		#lst = self.m_srcnode.difflst(src_dir_node)
		h1 = self.m_srcnode.height()
		h2 = src_dir_node.height()

		lst=[]
		child = src_dir_node
		while h2 > h1:
			lst.append(child.m_name)
			child=child.m_parent
			h2-=1
		lst.reverse()

		for variant in self._variants:
			sub_path = os.path.join(self.m_bldnode.abspath(), variant , *lst)
			try:
				files = self.scan_path(src_dir_node, sub_path, src_dir_node.m_build_lookup.values(), variant)
				src_dir_node.m_build_lookup={}
				for i in files: src_dir_node.m_build_lookup[i.m_name]=i
			except OSError:
				#debug("osError on " + sub_path, 'build')

				# listdir failed, remove all sigs of nodes
				dict = self.m_tstamp_variants[variant]
				for node in src_dir_node.m_build_lookup.values():
					if node in dict:
						dict.__delitem__(node)
				os.makedirs(sub_path)
				src_dir_node.m_build_lookup={}
		self.m_scanned_folders.append(src_dir_node.hash_value)

	# ======================================= #
	def scan_src_path(self, i_parent_node, i_path, i_existing_nodes):

		try:
			# read the dir contents, ignore the folders in it
			l_names_read = os.listdir(i_path)
		except OSError:
			warning("OSError exception in scan_src_path()  i_path=%s" % str(i_path) )
			return None

		debug("folder contents "+str(l_names_read), 'build')

		# there are two ways to obtain the partitions:
		# 1 run the comparisons two times (not very smart)
		# 2 reduce the sizes of the list while looping

		l_names = l_names_read
		l_nodes = i_existing_nodes
		l_kept  = []

		for node in l_nodes:
			i     = 0
			name  = node.m_name
			l_len = len(l_names)
			while i < l_len:
				if l_names[i] == name:
					l_kept.append(node)
					break
				i += 1
			if i < l_len:
				del l_names[i]

		# Now:
		# l_names contains the new nodes (or files)
		# l_kept contains only nodes that actually exist on the filesystem
		for node in l_kept:
			try:
				# update the time stamp
				self.m_tstamp_variants[0][node] = Params.h_file(node.abspath())
			except IOError:
				fatal("a file is readonly or has become a dir "+node.abspath())

		debug("new files found "+str(l_names), 'build')

		l_path = i_path + os.sep
		for name in l_names:
			try:
				# throws IOError if not a file or if not readable
				st = Params.h_file(l_path + name)
			except IOError:
				continue
			l_child = Node.Node(name, i_parent_node)
			self.m_tstamp_variants[0][l_child] = st
			l_kept.append(l_child)
		return l_kept

	def scan_path(self, i_parent_node, i_path, i_existing_nodes, i_variant):
		"""in this function we do not add timestamps but we remove them
		when the files no longer exist (file removed in the build dir)"""

		# read the dir contents, ignore the folders in it
		l_names_read = os.listdir(i_path)

		# there are two ways to obtain the partitions:
		# 1 run the comparisons two times (not very smart)
		# 2 reduce the sizes of the list while looping

		l_names = l_names_read
		l_nodes = i_existing_nodes
		l_rm    = []

		for node in l_nodes:
			i     = 0
			name  = node.m_name
			l_len = len(l_names)
			while i < l_len:
				if l_names[i] == name:
					break
				i += 1
			if i < l_len:
				del l_names[i]
			else:
				l_rm.append(node)

		# remove the stamps of the nodes that no longer exist in the build dir
		for node in l_rm:

			#print "\nremoving the timestamp of ", node, node.m_name
			#print node.m_parent.m_build
			#print l_names_read
				#print l_names

			if node in self.m_tstamp_variants[i_variant]:
				self.m_tstamp_variants[i_variant].__delitem__(node)
		return l_nodes

	def dump(self):
		"for debugging"
		def printspaces(count):
			if count>0: return printspaces(count-1)+"-"
			return ""
		def recu(node, count):
			accu = printspaces(count)
			accu+= "> "+node.m_name+" (d)\n"
			for child in node.files():
				accu+= printspaces(count)
				accu+= '-> '+child.m_name+' '

				for variant in self.m_tstamp_variants:
					#print "variant %s"%variant
					var = self.m_tstamp_variants[variant]
					#print var
					if child in var:
						accu+=' [%s,%s] ' % (str(variant), Params.vsig(var[child]))

				accu+='\n'
				#accu+= ' '+str(child.m_tstamp)+'\n'
				# TODO #if node.files()[file].m_newstamp != node.files()[file].m_oldstamp: accu += "\t\t\t(modified)"
				#accu+= node.files()[file].m_newstamp + "< >" + node.files()[file].m_oldstamp + "\n"
			for child in node.m_build_lookup.values():
				accu+= printspaces(count)
				accu+= '-> '+child.m_name+' (b) '

				for variant in self.m_tstamp_variants:
					#print "variant %s"%variant
					var = self.m_tstamp_variants[variant]
					#print var
					if child in var:
						accu+=' [%s,%s] ' % (str(variant), Params.vsig(var[child]))

				accu+='\n'
				#accu+= ' '+str(child.m_tstamp)+'\n'
				# TODO #if node.files()[file].m_newstamp != node.files()[file].m_oldstamp: accu += "\t\t\t(modified)"
				#accu+= node.files()[file].m_newstamp + "< >" + node.files()[file].m_oldstamp + "\n"
			for dir in node.dirs(): accu += recu(dir, count+1)
			return accu

		Params.pprint('CYAN', recu(self.m_root, 0) )
		Params.pprint('CYAN', 'size is '+str(self.m_root.size_subtree()))

		#keys = self.m_name2nodes.keys()
		#for k in keys:
		#	print k, '\t\t', self.m_name2nodes[k]


	def pushdir(self, dir):
		node = self.m_curdirnode.ensure_node_from_lst(Utils.split_path(dir))
		self.pushed = [self.m_curdirnode]+self.pushed
		self.m_curdirnode = node

	def popdir(self):
		self.m_curdirnode = self.pushed.pop(0)

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
		Object.flush()
		Task.g_tasks.add_group(name)

	def add_manual_dependency(self, path, value):
		h = getattr(self, 'deps_man', {})
		node = self.m_curdirnode.find_source(path)
		if not node: node = self.m_curdirnode.find_build(path, create=1)

		h[node] = value
		self.deps_man = h

	def set_sig_cache(self, key, val):
		self.m_sig_cache[key] = val

	def get_sig_cache(self, key):
		try:
			return self.m_sig_cache[key]
		except KeyError:
			s = Params.sig_nil
			return [s, s, s, s, s]

