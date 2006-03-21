#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os
import os.path
import sys
import cPickle
from Deptree import Deptree

import Environment
import Params
import Runner
import Object

def trace(msg):
	Params.trace(msg, 'Build')
def debug(msg):
	Params.debug(msg, 'Build')
def error(msg):
	Params.error(msg, 'Build')
def fatal(msg):
	Params.fatal(msg, 'Build')

class Build:
	def __init__(self):
		self.m_configs  = []   # environments
		self.m_tree     = None # dependency tree
		self.m_dirs     = []   # folders in the dependency tree to scan
		self.m_rootdir  = ''   # root of the build, in case if the build is moved ?
		self.m_prune    = []

		Params.g_build=self

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

	def set_default_env(self, filename):
		# update the hashtable to set the build_dir
		env = Environment.Environment()
		if not filename:
			error('passing a null filename to set_default_env')
			return
		if not env.load(filename):
			print "the cache file was not found"
			#fatal("no cache file found or corrupted. You should run 'waf configure'")
		
		env.setup(env['tools'])
		Params.g_default_env = env.copy()
		#debug(Params.g_default_env)

	def set_srcdir(self, dir, scan='auto'):
		trace("set_srcdir")
		p = os.path.abspath(dir)
		if sys.platform=='win32': p=p[2:]
		node=self.m_tree.ensure_node_from_path(p)
		self.m_tree.m_srcnode = node
		Params.g_srcnode = node
		# position in the source tree when reading scripts
		Params.g_curdirnode = node
		# stupid behaviour (will scan every project in the folder) but scandirs-free
		# we will see later for more intelligent behaviours (scan only folders that contain sources..)
		Params.g_excludes=Params.g_excludes+self.m_prune
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
		generator = Runner.JobGenerator(self.m_tree)
		if Params.g_maxjobs <=1: executor = Runner.Serial(generator)
		else:                    executor = Runner.Parallel(generator, Params.g_maxjobs)
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

	def install(self):
		trace("install called")
		for obj in Object.g_allobjs:
			obj.install()
		
	def add_subdir(self, dir):
		import Scripting
		Scripting.add_subdir(dir)

