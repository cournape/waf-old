#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, os.path, sys, cPickle, types

import Environment, Params, Runner, Object, Utils

from Deptree import Deptree
from Params import debug, error, trace, fatal

class Build:
	def __init__(self):
		self.m_configs  = []   # environments
		self.m_tree     = None # dependency tree
		self.m_dirs     = []   # folders in the dependency tree to scan
		self.m_rootdir  = ''   # root of the build, in case if the build is moved ?

		Params.g_build=self

		# the current directory from which the code is run
		# the folder changes everytime a sconscript is read
		self.m_curdirnode = None

		# map a name to an environment, the 'default' must be defined
		self.m_allenvs = {}

		self.m_bdir = ''

	def load(self, blddir):
		self.m_bdir = blddir
		self.m_rootdir = os.path.abspath('.')
		if sys.platform=='win32': self.m_rootdir=self.m_rootdir[2:]
		try:
			file = open( os.path.join(blddir, Params.g_dbfile), 'rb')
			self.m_tree = cPickle.load(file)
			file.close()
		except:
			self.m_tree = Deptree()
		# reset the flags of the tree
		self.m_tree.m_root.tag(0)

	def store(self):
		file = open(os.path.join(self.m_bdir, Params.g_dbfile), 'wb')
		cPickle.dump(self.m_tree, file, -1)
		file.close()

	def set_dirs(self, srcdir, blddir, scan='auto'):
		if len(srcdir) >= len(blddir)-1:
			fatal("build dir must be different from srcdir")

		self.load(blddir)

		self.set_bdir(blddir)
		self.set_srcdir(srcdir, scan)

	def set_bdir(self, path):
		trace("set_builddir")
		p = os.path.abspath(path)
		if sys.platform=='win32': p=p[2:]
		node = self.m_tree.ensure_directory(p)
		self.m_tree.m_bldnode = node
		Params.g_bldnode = node

	def set_srcdir(self, dir, scan='auto'):
		trace("set_srcdir")
		p = os.path.abspath(dir)
		if sys.platform=='win32': p=p[2:]
		node=self.m_tree.ensure_node_from_path(p)
		self.m_tree.m_srcnode = node
		Params.g_srcnode = node
		# position in the source tree when reading scripts
		self.m_curdirnode = node
		# stupid behaviour (will scan every project in the folder) but scandirs-free
		# we will see later for more intelligent behaviours (scan only folders that contain sources..)
		try:
			Params.g_excludes=Params.g_excludes+Utils.g_module.prunedirs
		except:
			pass
		if scan == 'auto':
			trace("autoscan in use")
			# avoid recursion
			def scan(node):
				if node is Params.g_bldnode: return []
				if node.m_name in Params.g_excludes: return []
				dir = os.sep.join( Params.g_srcnode.difflst(node) )
				self.m_tree.scanner_mirror(dir)
				return node.m_dirs
			mlst = scan(Params.g_srcnode)
			while mlst:
				el=mlst[0]
				mlst=mlst[1:]
				mlst += scan(el)

	# use this when autoscan is off
	def scandirs(self, paths):
		ldirs=paths.split()
		for sub_dir in ldirs:
			self.m_tree.scanner_mirror(sub_dir)

	def cleanup(self):
		self.m_tree.m_name2nodes = {}
		self.m_tree.m_flags      = {}
		#self.m_tree.m_src_to_bld = {}
		#self.m_tree.m_bld_to_src = {}

		#debug("setting some stat value to a bldnode")
		#curnode = self.m_tree.m_bldnode
		#curnode = curnode.find_node(['src', 'main.cpp'])
		#curnode.m_tstamp = os.stat(curnode.abspath()).st_mtime
		#curnode.debug_time()

	# usual computation types - dist and distclean might come here too
	def clean(self):
		trace("clean called")

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
			self.store()
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
		
	def add_subdirs(self, dirs):
		import Scripting
		if type(dirs) is types.ListType: lst = dirs
		else: lst = dirs.split()

		for d in lst:
			if not d: continue
			Scripting.add_subdir(d, self)

	def createObj(self, objname, *k, **kw):
		try:
			return Object.g_allclasses[objname](*k, **kw)
		except:
			print "error in createObj", objname
			raise

