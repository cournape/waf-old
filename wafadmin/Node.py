#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
Node: filesystem structure, contains lists of nodes

IMPORTANT:
1. Each file/folder is represented by exactly one node.

2. Most would-be class properties are stored in Build: nodes to depend on, signature, flags, ..
unused class members increase the .wafpickle file size sensibly with lots of objects.

3. The build is launched from the top of the build dir (for example, in _build_/).

4. Node should not be instantiated directly.
Each instance of Build.BuildContext has a Node subclass.
(aka: 'Nod3', see BuildContext initializer)
The BuildContext is referenced here as self.__class__.bld
Its Node class is referenced here as self.__class__

The public and advertised apis are the following:
${TGT}                 -> dir/to/file.ext
${TGT[0].suffix()}     -> .ext
${TGT[0].abspath()} -> /path/to/dir/to/file.ext



1 file/dir == one node (the only thing guaranteed by the file system)
"""

import os, sys, fnmatch, re
import Utils

UNDEFINED = 0
DIR = 1
FILE = 2
BUILD = 3

type_to_string = {UNDEFINED: 'unk', DIR: 'dir', FILE: 'src', BUILD: 'bld'}

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
	def __init__(self, name, parent, node_type = UNDEFINED):
		self.name = name
		self.parent = parent

		self.__class__.bld.id_nodes += 4
		self.id = self.__class__.bld.id_nodes + node_type

		if node_type == DIR:
			self.children = {}

		if parent:
			if name in parent.children:
				raise WafError('node %s exists in the parent files %r already' % (name, parent))
			parent.children[name] = self

	def __str__(self):
		if not self.parent: return ''
		return "%s://%s" % (type_to_string[self.id & 3], self.abspath())

	def __repr__(self):
		return self.__str__()

	def __hash__(self):
		"expensive, make certain it is not used"
		raise WafError('nodes, you are doing it wrong')

	def __eq__(self, node):
		return id(self) == id(node)

	def __copy__(self):
		"nodes are not supposed to be copied"
		raise WafError('nodes are not supposed to be copied')

	def read(self):
		"get the contents of a file, it is not used anywhere for the moment"
		return Utils.readf(self.abspath())

	def write(self, data):
		"write some text to the file"
		f = None
		try:
			f = open(self.abspath(), 'w')
			f.write(data)
		finally:
			f.close()

	def chmod(self, val):
		"change the file permissions"
		os.chmod(self.abspath(), val)

	def delete(self):
		"delete the file physically, do not destroy the nodes"
		shutil.rmtree(self.abspath())
		try:
			if self.children:
				self.children = {}
		except:
			pass

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

		for i in xrange(up):
			lst.append('..')
		lst.reverse()
		return os.sep.join(lst)

	def abspath(self):
		"""
		absolute path
		cache into the build context, cache_node_abspath
		"""
		# absolute path: this is usually a bottleneck

		ret = self.__class__.bld.cache_node_abspath.get(self.id, None)
		if ret:
			return ret

		if not self.parent:
			val = os.sep == '/' and os.sep or ''
		elif not self.parent.name:
			# drive letter for win32
			val = (os.sep == '/' and os.sep or '') + self.name
		else:
			val = self.parent.abspath() + os.sep + self.name

		self.__class__.bld.cache_node_abspath[id] = val
		return val

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

#find_dirs
#make_dirs
#read_dir

	# below the complex stuff

	def nice_path(self, env=None):
		"printed in the console, open files easily from the launch directory"
		bld = self.__class__.bld
		ln = bld.launch_node()

		if self.id & 3 == FILE: return self.path_from(ln)
		else: return bld.out_dir + os.sep + self.path_from(bld.srcnode)

	def rescan(self):
		"""
		look the contents of a (folder)node and update its list of children

		The intent is to perform the following steps
		* remove the nodes for the files that have disappeared
		* remove the signatures for the build files that have disappeared
		* cache the results of os.listdir
		* create the build folder equivalent (mkdir)
		src/bar -> build/default/src/bar, build/release/src/bar

		when a folder in the source directory is removed, we do not check recursively
		to remove the unused nodes. To do that, call 'waf clean' and build again.
		"""

		bld = self.__class__.bld

		# do not rescan over and over again
		if self.id in bld.cache_dir_contents:
			return

		# first, take the case of the source directory
		try:
			lst = set(Utils.listdir(self.abspath()))
		except OSError:
			lst = set([])

		# hash the existing source files, remove the others
		for x in self.children.values():
			if x.id & 3 != FILE:
				continue

			if x.name in lst:
				try:
					x.sig = Utils.h_file(x.abspath())
				except IOError:
					raise WafError('The file %s is not readable or has become a dir' % x.abspath())
			else:
				del self.children[x.name]

		if not bld.srcnode:
			# do not look at the build directory yet
			return
		bld.cache_dir_contents[self.id] = lst

		# first obtain the differences between srcnode and self
		h1 = bld.srcnode.height()
		h2 = self.height()

		lst = []
		child = self
		while h2 > h1:
			lst.append(child.name)
			child = child.parent
			h2 -= 1

		if child.id != bld.srcnode.id:
			# not a folder that we can duplicate in the build dir
			return

		lst.append(bld.out_dir)
		lst.reverse()
		path = os.sep.join(lst)

		try:
			lst = set(Utils.listdir(path))
		except OSError:
			for node in self.children.values():
				# do not remove the nodes representing directories
				if node.id & 3 != BUILD:
					continue

				del self.children[node.name]
			try:
				# recreate the folder in the build directory
				os.makedirs(path)
			except OSError:
				pass
		else:
			# the folder exist, look at the nodes
			vals = list(self.children.values())
			for node in vals:
				if node.id & 3 != BUILD:
					continue
				if not (node.name in lst):
					del self.children[node.name]

	def find_dir(self, lst):
		"search a folder in the filesystem"

		if isinstance(lst, str):
			lst = Utils.split_path(lst)

		current = self
		for name in lst:
			current.rescan()
			prev = current

			if not current.parent and name == current.name:
				continue
			elif not name:
				continue
			elif name == '.':
				continue
			elif name == '..':
				current = current.parent or current
			else:
				current = prev.children.get(name, None)
				if current is None:
					dir_cont = self.__class__.bld.cache_dir_contents
					if name in dir_cont.get(prev.id, []):
						if not prev.name:
							if os.sep == '/':
								# cygwin //machine/share
								dirname = os.sep + name
							else:
								# windows c:
								dirname = name
						else:
							# regular path
							dirname = prev.abspath() + os.sep + name
						if not os.path.isdir(dirname):
							return None
						current = self.__class__(name, prev, DIR)
					elif (not prev.name and len(name) == 2 and name[1] == ':') or name.startswith('\\\\'):
						# drive letter or \\ path for windows
						current = self.__class__(name, prev, DIR)
					else:
						try:
							os.stat(prev.abspath() + os.sep + name)
						except:
							return None
						else:
							current = self.__class__(name, prev, DIR)
				else:
					if current.id & 3 != DIR:
						return None
		return current

	def find_resource(self, lst):
		"Find an existing input file: either a build node declared previously or a source node"
		if isinstance(lst, str):
			lst = Utils.split_path(lst)

		if len(lst) == 1:
			parent = self
		else:
			parent = self.find_dir(lst[:-1])
			if not parent: return None
		parent.rescan()

		name = lst[-1]
		node = parent.children.get(name, None)
		if node:
			tp = node.id & 3
			if tp == FILE or tp == BUILD:
				return node
			else:
				return None

		tree = self.__class__.bld
		if not name in tree.cache_dir_contents[parent.id]:
			return None

		path = parent.abspath() + os.sep + name
		try:
			st = Utils.h_file(path)
		except IOError:
			return None

		child = self.__class__(name, parent, FILE)
		child.sig = st
		return child

	def find_or_declare(self, lst):
		"Used for declaring a build node representing a file being built"
		if isinstance(lst, str):
			lst = Utils.split_path(lst)

		if len(lst) == 1:
			parent = self
		else:
			parent = self.find_dir(lst[:-1])
			if not parent: return None
		parent.rescan()

		name = lst[-1]
		node = parent.children.get(name, None)
		if node:
			tp = node.id & 3
			if tp != BUILD:
				raise WafError("find_or_declare returns a build node, not a source nor a directory %r" % lst)
			return node
		node = self.__class__(name, parent, BUILD)
		return node

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

	def bldpath(self):
		"path seen from the build dir default/src/foo.cpp"

		if self.id &  3 != FILE:
			return self.path_from(self.__class__.bld.srcnode)
		return self.__class__.bld.up_path + os.sep + self.path_from(self.__class__.bld.srcnode)

	def srcpath(self):
		"path in the srcdir from the build dir ../src/foo.cpp"
		if self.id & 3 == BUILD:
			return self.bldpath()
		return self.__class__.bld.up_path + os.sep + self.path_from(self.__class__.bld.srcnode)

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

	def bld_dir(self):
		"build path without the file name"
		return self.parent.bldpath()

	def bld_base(self):
		"build path without the extension: src/dir/foo(.cpp)"
		s = os.path.splitext(self.name)[0]
		return self.bld_dir() + os.sep + s

class Nod3(Node):
	pass

