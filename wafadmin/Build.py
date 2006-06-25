#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, os.path, sys, cPickle, types

import Environment, Params, Runner, Object, Utils

from Deptree import Deptree
from Params import debug, error, trace, fatal


class BuildDTO:
	def __init__(self, bdobj):
		self.m_root        = bdobj.m_root
		self.m_bldnode     = bdobj.m_bldnode
		self.m_srcnode     = bdobj.m_srcnode
		self.m_src_to_bld  = bdobj.m_src_to_bld
		self.m_bld_to_src  = bdobj.m_bld_to_src
		self.m_depends_on  = bdobj.m_depends_on
		self.m_deps_tstamp = bdobj.m_deps_tstamp
		self.m_raw_deps    = bdobj.m_raw_deps
		self.m_sigs        = bdobj.m_sigs
	def update_build(self, bdobj):
		bdobj.m_root        = self.m_root
		bdobj.m_bldnode     = self.m_bldnode
		bdobj.m_srcnode     = self.m_srcnode
		bdobj.m_src_to_bld  = self.m_src_to_bld
		bdobj.m_bld_to_src  = self.m_bld_to_src
		bdobj.m_depends_on  = self.m_depends_on
		bdobj.m_deps_tstamp = self.m_deps_tstamp
		bdobj.m_raw_deps    = self.m_raw_deps
		bdobj.m_sigs        = self.m_sigs

class Build:
	def __init__(self):

		# ======================================= #
		# dependency tree

		# filesystem root - root name is Params.g_rootname
		self.m_root = Node.Node('', None)

		self.m_name2nodes  = {}             # access nodes quickly
		self.m_bldnode     = None
		self.m_srcnode     = None           # source directory

		# get bld nodes from src nodes quickly
		self.m_src_to_bld  = {}
		# get src nodes from bld nodes quickly
		self.m_bld_to_src  = {}

		# one node has nodes it depends on, tasks cannot be stored
		# node -> [node; node; node ..] - all dependencies
		# m_depends_on[node] = [node1, node2, ..]
		self.m_depends_on  = {}

		# m_deps_tstamp[node] = represents the timestamp for the node last scan
		self.m_deps_tstamp = {}

		# results of a scan: self.m_raw_deps[node] = [filename1, filename2, filename3]
		# for example, find headers in c files
		self.m_raw_deps    = {}


		# signatures for nodes that are created in the builddir
		self.m_sigs        = {}

		# give flags to nodes (eg: existing->1, not existing->0)
		self._flags        = {}

		# ======================================= #
		# globals

		# map a name to an environment, the 'default' must be defined
		self.m_allenvs = {}

		# there should be only one build dir in use at a time
		Params.g_build = self

		# ======================================= #
		# code for reading the scripts

		# project build directory
		self.m_bdir = ''

		# the current directory from which the code is run
		# the folder changes everytime a wscript is read
		self.m_curdirnode = None

		# temporary holding the subdirectories containing scripts
		self.m_subdirs=[]

		# ======================================= #
		# cache variables

		# local cache for absolute paths
		self._abspath_cache = {}

		# local cache for relative paths
		# two nodes - hashtable of hashtables - g_relpath_cache[child][parent])
		self._relpath_cache = {}

		# cache for height of the node (amount of folders from the root)
		self._height_cache = {}

		# list of folders that are already scanned
		# so that we do not need to stat them one more time
		self._scanned_folders  = []

		# file contents
		self._cache_node_content = {}

		# ======================================= #
		# tasks and objects

		# objects that are not posted and objects already posted
		# -> delay task creation
		self.m_outstanding_objs = []
		self.m_posted_objs      = []



		#self.m_tree     = None # dependency tree
		#self.m_dirs     = []   # folders in the dependency tree to scan

		# NO WAY
		#self.m_rootdir  = ''   # root of the build, in case if the build is moved ?

	# load existing data structures from the disk (stored using self._store())
	def _load(self):
		try:
			file = open(os.path.join(self.m_bdir, Params.g_dbfile), 'rb')
			dto = cPickle.load(file)
			dto.update_build(self)
			file.close()
		except:
			debug("loading a new deptree (previous attempt failed)")
			self.m_tree = Deptree()
		# reset the flags of the tree
		self.m_tree.m_root.tag(0)

	# store the data structures on disk, retrieve with self._load()
	def _store(self):
		file = open(os.path.join(self.m_bdir, Params.g_dbfile), 'wb')
		cPickle.dump(BuildDTO(self), file, -1)
		file.close()

	# ======================================= #

	def save(self):
		self._cleanup()
		self._store()

	# TODO: is this really useful ?
	# usual computation types - dist and distclean might come here too
	def clean(self):
		trace("clean called")

	# keep
	def compile(self):
		trace("compile called")

		os.chdir( self.m_tree.m_bldnode.abspath() )

		Object.flush()
		if Params.g_maxjobs <=1:
			generator = Runner.JobGenerator(self.m_tree)
			executor = Runner.Serial(generator)
		else:
			executor = Runner.Parallel(self.m_tree, Params.g_maxjobs)

		trace("executor starting")
		try:
			ret = executor.start()
		except KeyboardInterrupt:
			os.chdir( self.m_tree.m_srcnode.abspath() )
			self._store()
			raise
		#finally:
		#	os.chdir( self.m_tree.m_srcnode.abspath() )

		os.chdir( self.m_tree.m_srcnode.abspath() )
		return ret

	# this function is called for both install and uninstall
	def install(self):
		trace("install called")
		Object.flush()
		for obj in Object.g_allobjs: obj.install()

	# keep
	def add_subdirs(self, dirs):
		import Scripting
		if type(dirs) is types.ListType: lst = dirs
		else: lst = dirs.split()

		for d in lst:
			if not d: continue
			Scripting.add_subdir(d, self)

	# keep
	def create_obj(self, objname, *k, **kw):
		try:
			return Object.g_allclasses[objname](*k, **kw)
		except:
			print "error in create_obj", objname
			raise

	# ======================================= #
	# node and folder handling

	# this should be the main entry point
	def load_dirs(self, srcdir, blddir, scan='auto'):
		# this functions should be the start
		# there is no reason to bypass this check
		if os.path.samefile(srcdir, blddir):
			fatal("build dir must be different from srcdir ->"+str(srcdir)+" ->"+str(blddir))


		self._set_srcdir(srcdir)
		node = self.m_tree.ensure_node_from_path(p)
		self.m_tree.m_srcnode = node
		self.m_curdirnode = node


		# mkdir blddir ?
		self.m_bdir = blddir
		self._load()


		self._set_blddir(blddir)
		self._duplicate_srcdir(srcdir, scan)

	# ======================================= #
	# TODO


	# tell if a node has changed, to update the cache
	def needs_rescan(self, node):
		#print "needs_rescan for ", node, node.m_tstamp
		try:
			if self.m_deps_tstamp[node] == node.m_tstamp:
				#print "no need to rescan", node.m_tstamp
				return 0
		except:
			pass
		return 1

	# Fast node access - feed an internal dictionary (to keep between runs -> TODO not sure)
	def store_node(self, node):
		nn=node.m_name
		try:
			# prevent silly errors
			if node in self.m_name2nodes[nn]: print "BUG: name2nodes already contains node!", nn
			else: self.m_name2nodes[nn].append(node)
		except:
			self.m_name2nodes[nn] = [node]


	## IMPORTANT - for debugging
	def dump(self):
		def printspaces(count):
			if count>0: return printspaces(count-1)+"-"
			return ""
		def recu(node, count):
			accu = printspaces(count)
			accu+= "> "+node.m_name+" (d)\n"
			for child in node.m_files:
				accu+= printspaces(count)
				accu+= '> '+child.m_name+' '
				accu+= ' '+str(child.m_tstamp)+'\n'
				# TODO #if node.m_files[file].m_newstamp != node.m_files[file].m_oldstamp: accu += "\t\t\t(modified)"
				#accu+= node.m_files[file].m_newstamp + "< >" + node.m_files[file].m_oldstamp + "\n"
			for dir in node.m_dirs: accu += recu(dir, count+1)
			return accu

		Params.pprint('CYAN', recu(self.m_root, 0) )
		Params.pprint('CYAN', 'size is '+str(self.m_root.size()))

		#keys = self.m_name2nodes.keys()
		#for k in keys:
		#	print k, '\t\t', self.m_name2nodes[k]




	# ======================================= #
	# obsolete code

	# TODO obsolete
	def _set_blddir(self, path):
		trace("set_builddir")
		if path[0]=="/":
			lst = path.split('/')
			truc = lst[len(lst)-1]
			Params.g_excludes.append(truc)

		p = os.path.abspath(path)
		if sys.platform=='win32': p=p[2:]
		node = self.m_tree.ensure_directory(p)
		self.m_tree.m_bldnode = node

	# TODO obsolete
	def _set_srcdir(self, dir):
		""" Inform the Build object of the srcdir."""
		trace("set_srcdir")
		p = os.path.abspath(dir)
		if sys.platform=='win32': p=p[2:]

		node = self.m_tree.ensure_node_from_path(p)
		self.m_tree.m_srcnode = node
		# position in the source tree when reading scripts
		self.m_curdirnode = node
		

	# TODO OBSOLETE
	def _duplicate_srcdir(self, dir, scan='auto'):
		trace("duplicate_srcdir")
		srcnode = self.m_tree.m_srcnode

		# stupid behaviour (will scan every project in the folder) but scandirs-free
		# we will see later for more intelligent behaviours (scan only folders that contain sources..)
		try:
			Params.g_excludes=Params.g_excludes+Utils.g_module.prunedirs
		except:
			pass

		if scan == 'auto':
			trace("autoscan in use")
			# This function actually dupes the dirs with 'scanner_mirror'
			def scan(node):
				if node is Params.g_build.m_tree.m_bldnode: return []
				if node.m_name in Params.g_excludes: return []
				dir = os.sep.join(srcnode.difflst(node))
				self.m_tree.scanner_mirror(dir)
				return node.m_dirs
			mlst = scan(srcnode)
			while mlst:
				el=mlst[0]
				mlst=mlst[1:]
				mlst += scan(el)
		else:
			dirs = []
			for tgt in self.m_subdirs:
				dirs.append( os.sep.join(srcnode.difflst(tgt[0]) ) )
			self.scandirs( dirs )
			

