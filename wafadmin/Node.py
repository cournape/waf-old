#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os
import Params
from Params import debug, error, trace

class Node:
	def __init__(self, name, parent):

		self.m_name     = name
		self.m_parent   = parent

		if name == '.' or name == '..' or '/' in name:
			error('name forbidden '+name)
			raise "boo"

		if parent:
			for node in parent.m_files:
				if name == node.m_name:
					error('node %s exists in the parent files %s already' % (name, str(parent)))
					raise "inconsistency"

			for node in parent.m_build:
				if name == node.m_name:
					error('node %s exists in the parent build %s already' % (name, str(parent)))
					raise "inconsistency"

		# contents of this node (filesystem structure)
		# these lists contain nodes too
		self.m_dirs     = [] # sub-folders
		self.m_files    = [] # files existing in the src dir
		self.m_build    = [] # nodes produced in the build dirs

		# debugging only - a node is supposed to represent exactly one folder
		if os.sep in name: print "error in name ? "+name

		# timestamp or hash of the file (string hash or md5) - we will use the timestamp by default
		#self.m_tstamp   = None

		# IMPORTANT:
		# Some would-be class properties are stored in Build: nodes to depend on, signature, flags, ..
		# In fact, unused class members increase the .dblite file size sensibly with lots of objects 
		#   eg: the m_tstamp is used for every node, while the signature is computed only for build files

	def __str__(self):
		if self in self.m_parent.m_files: isbld = ""
		else: isbld = "b:"
		return "<%s%s>" % (isbld, self.abspath())

	def __repr__(self):
		if self in self.m_parent.m_files: isbld = ""
		else: isbld = "b:"
		return "<%s%s>" % (isbld, self.abspath())

	# ====================================================== #

	# for the build variants, the same nodes are used to spare memory
	# the timestamps/signatures are accessed using the following methods

	def get_tstamp_variant(self, variant):
		vars = Params.g_build.m_tstamp_variants[variant]
		try: return vars[variant]
		except: return None

	def set_tstamp_variant(self, variant, value):
		Params.g_build.m_tstamp_variants[variant][self] = value

	def get_tstamp_node(self):
		try: return Params.g_build.m_tstamp_variants[0][self]
		except: return None

	def set_tstamp_node(self, value):
		Params.g_build.m_tstamp_variants[0][self] = value

	# ====================================================== #

	# size of the subtree
	def size(self):
		l_size=1
		for i in self.m_dirs: l_size += i.size()
		l_size += len(self.m_files)
		return l_size

	# uses a cache, so calling height should have no overhead
	def height(self):
		try:
			return Params.g_build.m_height_cache[self]
		except:
			if not self.m_parent: val=0
			else:                 val=1+self.m_parent.height()
			Params.g_build.m_height_cache[self]=val
			return val

	def child_of_name(self, name):
		for d in self.m_dirs:
			trace('child of name '+d.m_name)
			if d.m_name == name:
				return d
		# throw an exception ?
		return None

	## ===== BEGIN relpath-related methods  ===== ##

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

	# TODO : make it procedural, not recursive
	# find a node given an existing node and a list like ['usr', 'local', 'bin']
	def find_node(self, lst):
		#print self, lst
		if not lst: return self
		name=lst[0]


		Params.g_build.rescan(self)

		#print self.m_dirs
		#print self.m_files

		if name == '.':  return self.find_node( lst[1:] )
		if name == '..': return self.m_parent.find_node( lst[1:] )


		for d in self.m_dirs+self.m_files+self.m_build:
			if d.m_name == name:
				return d.find_node( lst[1:] )

		if len(lst)>0:
			node = Node(name, self)
			self.m_dirs.append(node)
			return node.find_node(lst[1:])

		trace('find_node returns nothing '+str(self)+' '+str(lst))
		return None

	def search_existing_node(self, lst):
		"returns a node from the tree, do not create if missing"
		#print self, lst
		if not lst: return self
		name=lst[0]

		Params.g_build.rescan(self)

		if name == '.':  return self.find_node( lst[1:] )
		if name == '..': return self.m_parent.find_node( lst[1:] )

		for d in self.m_dirs+self.m_files+self.m_build:
			if d.m_name == name:
				return d.find_node( lst[1:] )

		trace('search_node returns nothing '+str(self)+' '+str(lst))
		return None

	# absolute path
	def abspath(self, env=None):

		if not env:
			variant = 0
		else:
			if self in self.m_parent.m_files: variant = 0
			else: variant = env.variant()

		#print "variant is", self.m_name, variant, "and env is ", env

		## 1. stupid method
		# if self.m_parent is None: return ''
		# return self.m_parent.abspath()+os.sep+self.m_name
		#
		## 2. without a cache
		# return ''.join( self.pathlist2() )
		#
		## 3. with the cache
		try:
			return Params.g_build.m_abspath_cache[variant][self]
		except:
			if not variant:
				lst=self.pathlist2()
				lst.reverse()
				val=''.join(lst)
				Params.g_build.m_abspath_cache[variant][self]=val
				return val
			else:
				p = Params.g_build.m_bldnode.abspath() + os.sep + env.variant() + os.sep
				q = self.relpath(Params.g_build.m_srcnode)
				debug("var is p+q is "+p+q)
				return p+q


	# the build is launched from the top of the build dir (for example, in _build_/)
	def bldpath(self, env=None):
		if self in self.m_parent.m_files:
			var = self.relpath_gen(Params.g_build.m_bldnode)
		elif not env:
			raise "bldpath for node: an environment is required"
		else:
			var = env.variant() + os.sep + self.relpath(Params.g_build.m_srcnode)
		debug("bldpath: "+var)
		return var

	# the build is launched from the top of the build dir (for example, in _build_/)
	def srcpath(self, env):
		if not self in self.m_parent.m_build:
			var = self.relpath_gen(Params.g_build.m_bldnode)
		else:
			var = self.bldpath(env)
		debug("srcpath: "+var)
		return var

	def bld_dir(self, env):
		return self.m_parent.bldpath(env)

	def bldbase(self, env):
		i = 0
		n = self.m_name
		while 1:
			try:
				if n[i]=='.': break
			except:
				break
			i += 1
		s = n[:i]
		return self.bld_dir(env)+os.sep+s

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
		#try:
		#	return Params.g_build.m_relpath_cache[self][parent]
		#except:
		#	lst=self.pathlist3(parent)
		#	lst.reverse()
		#	val=''.join(lst)

		#	try:
		#		Params.g_build.m_relpath_cache[self][parent]=val
		#	except:
		#		Params.g_build.m_relpath_cache[self]={}
		#		Params.g_build.m_relpath_cache[self][parent]=val
		#	return val
		if self is parent: return ''

		lst=self.pathlist4(parent)
		lst.reverse()
		val=''.join(lst)
		return val


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
		if going_to.m_parent is self: return '..'

		# up_path is '../../../' and down_path is 'dir/subdir/subdir/file'
		ancestor  = self.find_ancestor(going_to)
		up_path   = going_to.invrelpath(ancestor)
		down_path = self.pathlist4(ancestor)
		down_path.reverse()
		return "".join( up_path+down_path )

	# TODO look at relpath_gen - it is certainly possible to get rid of find_ancestor
	def relpath_gen2(self, going_to):
		if self is going_to: return '.'
		ancestor = Params.srcnode()
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

	def is_child_of(self, node):
		if self.m_parent:
			if self.m_parent is node: return 1
			else: return self.m_parent.is_child_of(node)
		return 0

	#def ensure_scan(self):
	#	if not self in Params.g_build.m_scanned_folders:
	#		Params.g_build.rescan(self)
	#		Params.g_build.m_scanned_folders.append(self)

	def cd_to(self, env=None):
		return self.m_parent.bldpath(env)


	def variant(self, env):
		if self in self.m_parent.m_files: return 0
		else: return env.variant()

	# =============================================== #
	# helpers for building things
	def change_ext(self, ext):
		name = self.m_name
		l = len(name)
		while l>0:
			l -= 1
			if name[l] == '.':
				break
		newname = name[:l] + ext

		for n in self.m_parent.m_files:
			if n.m_name == newname:
				return n
		for n in self.m_parent.m_build:
			if n.m_name == newname:
				return n

		newnode = Node(newname, self.m_parent)
		self.m_parent.m_build.append(newnode)

		return newnode

	# =============================================== #
	# obsolete code

	def unlink(self, env=None):
		ret = os.unlink(self.abspath(env))
		print ret

	# TODO FIXME
	def get_sig(self):
		try: return Params.g_build.m_tstamp_variants[0][self]
		except: return Params.sig_nil

