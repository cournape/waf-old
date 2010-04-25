#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
Node: filesystem structure, contains lists of nodes

1. Each file/folder is represented by exactly one node.

2. Some potential class properties are stored in Build: nodes to depend on..
unused class members increase the .wafpickle file size sensibly with lots of objects.

3. The build is lunched from the top of the build dir (for example, in build/).

4. Node objects should not be created directly - use make_node or find_node

Each instance of Build.BuildContext has a unique Node subclass.
(aka: 'Nod3', see BuildContext initializer)
The BuildContext is referenced here as self.__class__.bld
Its Node class is referenced here as self.__class__
"""

import os, sys, shutil, re
import Utils

UNDEFINED = 0
DIR = 1
FILE = 2
BUILD = 3

# These fnmatch expressions are used by default to prune the directory tree
# while doing the recursive traversal in the find_iter method of the Node class.
prune_pats = '.git .bzr .hg .svn _MTN _darcs CVS SCCS'.split()

# These fnmatch expressions are used by default to exclude files and dirs
# while doing the recursive traversal in the find_iter method of the Node class.
exclude_pats = prune_pats + '*~ #*# .#* %*% ._* .gitignore .cvsignore vssver.scc .DS_Store'.split()

# These Utils.jar_regexp expressions are used by default to exclude files and dirs and also prune the directory tree
# while doing the recursive traversal in the ant_glob method of the Node class.
exclude_regs = '''
**/*~
**/#*#
**/.#*
**/%*%
**/._*
**/CVS
**/CVS/**
**/.cvsignore
**/SCCS
**/SCCS/**
**/vssver.scc
**/.svn
**/.svn/**
**/.git
**/.git/**
**/.gitignore
**/.bzr
**/.bzr/**
**/.hg
**/.hg/**
**/_MTN
**/_MTN/**
**/_darcs
**/_darcs/**
**/.DS_Store'''

class Node(object):
	def __init__(self, name, parent):
		self.name = name
		self.parent = parent

		if parent:
			if name in parent.children:
				raise WafError('node %s exists in the parent files %r already' % (name, parent))
			parent.children[name] = self

	def __str__(self):
		return self.abspath()

	def __repr__(self):
		return self.abspath()

	def __hash__(self):
		"expensive, make certain it is not used"
		raise WafError('nodes, you are doing it wrong')

	def __eq__(self, node):
		return id(self) == id(node)

	def __copy__(self):
		"nodes are not supposed to be copied"
		raise WafError('nodes are not supposed to be copied')

	def read(self, flags='r'):
		"get the contents, assuming the node is a file"
		return Utils.readf(self.abspath(), flags)

	def write(self, data, flags='w'):
		"write some text to the physical file, assuming the node is a file"
		f = None
		try:
			f = open(self.abspath(), flags)
			f.write(data)
		finally:
			if f:
				f.close()

	def chmod(self, val):
		"change file/dir permissions"
		os.chmod(self.abspath(), val)

	def delete(self):
		"delete the file physically, do not destroy the nodes"
		try:
			shutil.rmtree(self.abspath())
		except:
			pass

		try:
			# TODO: if tons of folders are removed and added again, id(self) might be found in cache
			self.__class__.bld.existing_dirs.remove(id(self))
		except:
			pass

		try:
			delattr(self, 'children')
		except:
			pass

	def suffix(self):
		"scons-like - hot zone so do not touch"
		k = max(0, self.name.rfind('.'))
		return self.name[k:]

	def height(self):
		"amount of parents"
		d = self
		val = -1
		while d:
			d = d.parent
			val += 1
		return val

	def compute_sig(self):
		"compute the signature if it is a file"
		self.sig = Utils.h_file(self.abspath())

	def listdir(self):
		"list the directory contents"
		return Utils.listdir(self.abspath())

	# TODO is this useful?
	#def isdir(self):
	#	return os.path.isdir(self.abspath())

	def mkdir(self):
		"write a directory for the node"
		try:
			if id(self) in self.__class__.bld.existing_dirs:
				return
		except:
			self.__class__.bld.existing_dirs = set([])

		try:
			self.parent.mkdir()
		except:
			pass

		if self.name:
			try:
				os.mkdir(self.abspath())
			except OSError as e:
				pass

			if not os.path.isdir(self.abspath()):
				raise WafError('%s is not a directory' % self)

			try:
				self.children
			except:
				self.children = {}

		self.__class__.bld.existing_dirs.add(id(self))

	def find_node(self, lst):
		"read the file system, make the nodes as needed"
		cur = self
		for x in lst:
			try:
				if x in cur.children:
					cur = cur.children[x]
					continue
			except:
				cur.children = {}
			cur = self.__class__(x, cur)

		# optimistic, first create the nodes if necessary, then fix if we were wrong
		# one stat and no listdir
		try:
			os.stat(cur.abspath())
		except:
			del self.children[x[0]]
			return None
		ret = cur

		while not id(cur.parent) in self.__class__.bld.existing_dirs:
			self.__class__.bld.existing_dirs.add(id(cur.parent))
			cur = cur.parent

		return ret

	def make_node(self, lst):
		"make a branch of nodes"
		cur = self
		for x in lst:
			if getattr(cur, 'children', {}):
				if x in cur.children:
					cur = cur.children[x]
					break
			else:
				cur.children = {}
			cur = self.__class__(x, cur)
		return cur

	# TODO search the tree / search the file system / create the object tree

	def path_from(self, node):
		"""path of this node seen from the other
			self = foo/bar/xyz.txt
			node = foo/stuff/
			-> ../bar/xyz.txt
		"""
		# common root in rev 7673

		c1 = self
		c2 = node

		c1h = c1.height()
		c2h = c2.height()

		lst = []
		up = 0

		while c1h > c2h:
			lst.append(c1.name)
			c1 = c1.parent
			c1h -= 1

		while c2h > c1h:
			up += 1
			c2 = c2.parent
			c2h -= 1

		while id(c1) != id(c2):
			lst.append(c1.name)
			up += 1

			c1 = c1.parent
			c2 = c2.parent

		for i in range(up):
			lst.append('..')
		lst.reverse()
		return os.sep.join(lst) or '.'

	def abspath(self):
		"""
		absolute path
		cache into the build context, cache_node_abspath
		"""
		try:
			ret = self.__class__.bld.cache_node_abspath.get(id(self), None)
		except AttributeError:
			self.__class__.bld.cache_node_abspath = {}
			ret = None

		if ret:
			return ret

		# think twice before touching this (performance + complexity + correctness)
		if not self.parent:
			val = os.sep == '/' and os.sep or ''
		elif not self.parent.name:
			# drive letter for win32
			val = (os.sep == '/' and os.sep or '') + self.name
		else:
			val = self.parent.abspath() + os.sep + self.name

		self.__class__.bld.cache_node_abspath[id(self)] = val
		return val

	# the following methods require the source/build folders (bld.srcnode/bld.bldnode)

	def is_src(self):
		cur = self
		x = id(self.__class__.bld.srcnode)
		y = id(self.__class__.bld.bldnode)
		while cur.parent:
			if id(cur) == y:
				return False
			if id(cur) == x:
				return True
			cur = cur.parent
		return False

	def src(self):
		cur = self
		x = id(self.__class__.bld.srcnode)
		y = id(self.__class__.bld.bldnode)
		lst = []
		while cur.parent:
			if id(cur) == y:
				lst.reverse()
				return self.__class__.bld.srcnode.make_node(lst)
			if id(cur) == x:
				return self
			lst.append(cur.name)
			cur = cur.parent
		return self

	def bld(self):
		cur = self
		x = id(self.__class__.bld.srcnode)
		y = id(self.__class__.bld.bldnode)
		lst = []
		while cur.parent:
			if id(cur) == y:
				return self
			if id(cur) == x:
				lst.reverse()
				return self.__class__.bld.bldnode.make_node(lst)
			lst.append(cur.name)
			cur = cur.parent
		return self

	def is_bld(self):
		cur = self
		y = id(self.__class__.bld.bldnode)
		while cur.parent:
			if id(cur) == y:
				return True
			cur = cur.parent
		return False

	def search(self, lst):
		cur = self
		try:
			for x in lst:
				cur = cur.children[x]
			return cur
		except:
			pass

	def find_resource(self, lst):
		"""
		if 'self' is in the source directory, try to find the matching source file
		if no file is found, look in the build directory if possible
		return a node if the node exists

		if 'self' is in the build directory, try to find the a matching node
		"""
		if self.is_src():
			node = self.find_node(lst)
			if node:
				return node
			return self.bld().search(lst)
		elif node.is_bld():
			return self.search(lst)

	def find_dir(self, lst):
		"""
		search a folder in the filesystem
		create the corresponding mappings source <-> build directories
		"""
		node = self.find_node(lst)
		try:
			os.path.is_dir(node.abspath())
		except:
			return None
		return node

	def find_or_declare(self, lst):
		"""
		if 'self' is in build directory, try to return an existing node
		if no node is found, go to the source directory
		try to find an existing node in the source directory
		if no node is found, create it in the build directory
		"""
		if self.is_bld():
			node = self.search(lst)
			if node:
				return node
			self = self.src()

		node = self.find_node(lst)
		if node:
			return node
		if self.is_src():
			self = self.bld()
			node = self.make_node(lst)
			return node
		return None

	# helpers for building things
	def change_ext(self, ext):
		"node of the same path, but with a different extension - hot zone so do not touch"
		name = self.name
		k = name.rfind('.')
		if k >= 0:
			name = name[:k] + ext
		else:
			name = name + ext

		return self.parent.find_or_declare([name])

	def nice_path(self, env=None):
		"printed in the console, open files easily from the launch directory"
		return self.path_from(self.__class__.bld.launch_node())

	def bldpath(self):
		"path seen from the build directory default/src/foo.cpp"
		return self.path_from(self.__class__.bld.bldnode)

	def srcpath(self):
		"path seen from the source directory ../src/foo.cpp"
		return self.path_from(self.__class__.bld.srcnode)

	def relpath(self):
		"if a build node, bldpath, else srcpath"
		cur = self
		x = id(self.__class__.bld.bldnode)
		while cur.parent:
			if id(cur) == x:
				return self.bldpath()
			cur = cur.parent
		return self.srcpath()

	def bld_dir(self):
		"build path without the file name"
		return self.parent.bldpath()

	def bld_base(self):
		"build path without the extension: src/dir/foo(.cpp)"
		s = os.path.splitext(self.name)[0]
		return self.bld_dir() + os.sep + s


	# complicated stuff below

	def ant_glob(self, *k, **kw):

		src=kw.get('src', 1)
		bld=kw.get('bld', 1)
		dir=kw.get('dir', 0)
		excl = kw.get('excl', exclude_regs)
		incl = k and k[0] or kw.get('incl', '**')

		def to_pat(s):
			lst = Utils.to_list(s)
			ret = []
			for x in lst:
				x = x.replace('//', '/')
				if x.endswith('/'):
					x += '**'
				lst2 = x.split('/')
				accu = []
				for k in lst2:
					if k == '**':
						accu.append(k)
					else:
						k = k.replace('.', '[.]').replace('*', '.*').replace('?', '.')
						k = '^%s$' % k
						#print "pattern", k
						accu.append(re.compile(k))
				ret.append(accu)
			return ret

		def filtre(name, nn):
			ret = []
			for lst in nn:
				if not lst:
					pass
				elif lst[0] == '**':
					ret.append(lst)
					if len(lst) > 1:
						if lst[1].match(name):
							ret.append(lst[2:])
					else:
						ret.append([])
				elif lst[0].match(name):
					ret.append(lst[1:])
			return ret

		def accept(name, pats):
			nacc = filtre(name, pats[0])
			nrej = filtre(name, pats[1])
			if [] in nrej:
				nacc = []
			return [nacc, nrej]

		def ant_iter(nodi, maxdepth=25, pats=[]):
			nodi.rescan()
			for name in nodi.__class__.bld.cache_dir_contents[nodi.id]:
				npats = accept(name, pats)
				if npats and npats[0]:
					accepted = [] in npats[0]
					#print accepted, nodi, name

					node = nodi.find_resource(name)
					if node and accepted:
						if src and node.id & 3 == FILE:
							yield node
					else:
						node = nodi.find_dir(name)
						if node:
							if accepted and dir:
								yield node
							if maxdepth:
								for k in ant_iter(node, maxdepth=maxdepth - 1, pats=npats):
									yield k
			if bld:
				for node in nodi.children.values():
					if node.id & 3 == BUILD:
						npats = accept(node.name, pats)
						if npats and npats[0] and [] in npats[0]:
							yield node
			raise StopIteration

		ret = [x for x in ant_iter(self, pats=[to_pat(incl), to_pat(excl)])]

		if kw.get('flat', True):
			return " ".join([x.path_from(self) for x in ret])

		return ret

class Nod3(Node):
	pass

