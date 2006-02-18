#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os
from stat import *
import Deptree
import Params

# local cache for absolute paths
g_abspath_cache = {}

# local cache for relative paths
# two nodes - hashtable of hashtables - g_relpath_cache[child][parent])
g_relpath_cache = {}

# cache for height of the node
g_height_cache = {}

def trace(msg):
	Params.trace(msg, 'Node')
def debug(msg):
	Params.debug(msg, 'Node')
def error(msg):
	Params.error(msg, 'Node')

class Node:
	def __init__(self, name, parent):

		self.m_name     = name
		self.m_parent   = parent

		# contents of this node (filesystem structure)
		self.m_dirs     = []
		self.m_files    = []

		# debugging only - a node is supposed to represent exactly one folder
		#if os.sep in name: print "error in name ? "+name

		# timestamp or hash of the file (string hash or md5) - we will use the timestamp by default
		self.m_tstamp   = None

		# IMPORTANT:
		# Some would-be class properties are stored in Deptree: nodes to depend on, signature, flags, ..
		# In fact, unused class members increase the .dblite file size sensibly with lots of objects 
		#   eg: the m_tstamp is used for every node, while the signature is computed only for build files

	def __str__(self):
		return "<%s>"%self.abspath()

	def __repr__(self):
		return "<%s>"%self.abspath()

	# tells if this node triggers a rebuild
	def haschanged(self):
		return (self.m_oldstamp != self.m_newstamp)

	# size of the subtree
	def size(self):
		l_size=1
		for i in self.m_dirs: l_size += i.size()
		l_size += len(self.m_files)
		return l_size

	def get_sig(self):
		try: return Params.g_build.m_tree.m_sigs[self]
		except: return self.m_tstamp

	# uses a cache, so calling height should have no overhead
	def height(self):
		try:
			return g_height_cache[self]
		except:
			if not self.m_parent: val=0
			else:                 val=1+self.m_parent.height()
			g_height_cache[self]=val
			return val

	# flag a subtree
	def tag(self, val):
		for i in self.m_files:
			i.m_flag = val
		for i in self.m_dirs:
			i.m_flag = val
			i.tag(val)

	def child_of_name(self, name):
		for d in self.m_dirs:
			trace('child of name '+d.m_name)
			if d.m_name == name:
				return d
		# perhaps we should throw an exception
		return None

	# list of file names that separate a node from a child
	def difflst(self, child):
		if not child: error('Node difflst takes a non-null parameter!')
		lst=[]
		node = child
		while child != self:
			lst.append(child.m_name)
			child=child.m_parent
		lst.reverse()
		return lst

	## ------------ TODO : the following may need to be improved
	# list of paths up to the root
	# cannot remember where it is used (ita)
	def path_list(self):
		if not self.m_parent: return []
		return self.m_parent.pathlist().append(self.m_name)


	# returns a list that can be reduced to the absolute path
	# make sure to reverse it (used by abspath)
	def pathlist2(self):
		if not self.m_parent: return [Params.g_rootname]
		return [self.m_name, os.sep]+self.m_parent.pathlist2()

	# absolute path
	def abspath(self):
		## 1. stupid method
		# if self.m_parent is None: return ''
		# return self.m_parent.abspath()+os.sep+self.m_name
		#
		## 2. without a cache
		# return ''.join( self.pathlist2() )
		#
		## 3. with the cache
		try:
			return g_abspath_cache[self]
		except:
			lst=self.pathlist2()
			lst.reverse()
			val=''.join(lst)
			g_abspath_cache[self]=val
			return val

	# TODO : make it procedural, not recursive
	# find a node given an existing node and a list like ['usr', 'local', 'bin']
	def find_node(self, lst):
		#print self, lst
		if not lst: return self
		name=lst[0]

		if name == '.':  return self.find_node( lst[1:] )
		if name == '..': return self.m_parent.find_node( lst[1:] )

		for d in self.m_dirs+self.m_files:
			if d.m_name == name:
				return d.find_node( lst[1:] )

		trace('find_node returns nothing '+str(self)+' '+str(lst))
		return None


	## ===== BEGIN relpath-related methods  ===== ##

	# returns the list of names to the node
	# make sure to reverse it (used by relpath)
	def pathlist3(self, node):
		if self is node: return ['.']
		return [self.m_name, os.sep]+self.m_parent.pathlist3(node)
	
	# same as pathlist3, but do not append './' at the beginning
	def pathlist4(self, node):
		if self.m_parent is node: return [self.m_name]
		return [self.m_name, os.sep]+self.m_parent.pathlist4(node)
	
	# path relative to a direct parent
	def relpath(self, parent):
		#print "relpath", self, parent
		try:
			return g_relpath_cache[self][parent]
		except:
			lst=self.pathlist3(parent)
			lst.reverse()
			val=''.join(lst)

			try:
				g_relpath_cache[self][parent]=val
			except:
				g_relpath_cache[self]={}
				g_relpath_cache[self][parent]=val
			return val

	# path relative to the src directory (useful for building targets : almost - ita)
	def srcpath(self):
		if not Params.g_srcnode: error("BUG in srcpath")
		return self.relpath(Params.g_srcnode)

	# path used when building targets
	def bldpath(self):
		if not Params.g_bldnode: error("BUG in bldpath")
		return self.relpath(Params.g_bldnode)

	# find a common ancestor for two nodes - for the shortest path in hierarchy
	def find_ancestor(self, node):
		dist=self.height()-node.height()
		if dist<0: return node.find_ancestor(self)
		# now the real code
		cand=self
		while dist>0:
			cand=cand.m_parent
			dist=dist-1
		if cand is node: return cand
		cursor=node
		while cand.m_parent:
			cand   = cand.m_parent
			cursor = cursor.m_parent
			if cand is cursor: return cand

	# prints the amount of "../" between two nodes
	def invrelpath(self, parent):
		lst=[]
		cand=self
		while cand is not parent:
			cand=cand.m_parent
			lst+=['..',os.sep]
		return lst

	# TODO: do this in a single function (this one uses invrelpath, find_ancestor and pathlist4)
	# string representing a relative path between two nodes, we are at relative_to
	def relpath_gen(self, going_to):
		if self is going_to: return '.'

		# up_path is '../../../' and down_path is 'dir/subdir/subdir/file'
		ancestor  = self.find_ancestor(going_to)
		up_path   = going_to.invrelpath(ancestor)
		down_path = self.pathlist4(ancestor)
		down_path.reverse()
		return "".join( up_path+down_path )

	# TODO look at relpath_gen - it is certainly possible to get rid of find_ancestor
	def relpath_gen2(self, going_to):
		if self is going_to: return '.'
		ancestor = Params.g_srcnode
		up_path   = going_to.invrelpath(ancestor)
		down_path = self.pathlist4(ancestor)
		down_path.reverse()
		return "".join( up_path+down_path )

	## ===== END relpath-related methods  ===== ##

	def debug(self):
		print "========= debug node ============="
		print "dirs are ", self.m_dirs
		print "files are", self.m_files
		print "======= end debug node ==========="

	def unlink(self):
		ret = os.unlink( self.abspath() )
		print ret

	def is_child_of(self, node):
		if self.m_parent:
			if self.m_parent is node: return 1
			else: return self.m_parent.is_child_of(node)
		return 0

	# returns the folder in the build dir for reaching this node
	def cd_to(self):
		reldir = Params.g_build.m_tree.m_bldnode.difflst(self)
		reldir = reldir[:len(reldir)-1]
		reldir = os.sep.join(reldir)
		return reldir

def reset():
	global g_abspath_cache, g_relpath_cache, g_height_cache
	g_abspath_cache = {}
	g_relpath_cache = {}
	g_height_cache = {}

