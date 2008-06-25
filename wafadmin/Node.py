#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"""
Node: filesystem structure, contains lists of nodes

Each file/folder is represented by exactly one node

we do not want to add another type attribute (memory)
rather, we will use the id to find out:
type = id & 3
setting: new type = type + x - type & 3

IMPORTANT:
Some would-be class properties are stored in Build: nodes to depend on, signature, flags, ..
In fact, unused class members increase the .wafpickle file size sensibly with lots of objects
eg: the m_tstamp is used for every node, while the signature is computed only for build files

the build is launched from the top of the build dir (for example, in _build_/)
"""

import os, sys
import Utils, Build
from Logs import *

UNDEFINED = 0
DIR = 1
FILE = 2
BUILD = 3

type_to_string = {UNDEFINED: "unk", DIR: "dir", FILE: "src", BUILD: "bld"}

class Node(object):
	__slots__ = ("m_name", "m_parent", "id", "childs")
	def __init__(self, name, parent, node_type = UNDEFINED):
		self.m_name = name
		self.m_parent = parent

		# assumption: one build object at a time
		Build.bld.id_nodes += 4
		self.id = Build.bld.id_nodes + node_type

		if node_type == DIR: self.childs = {}

		# The checks below could be disabled for speed, if necessary
		# TODO check for . .. / \ in name

		# Node name must contain only one level
		if Utils.split_path(name)[0] != name:
			fatal('name forbidden '+name)

		if parent and name in parent.childs:
			fatal('node %s exists in the parent files %s already' % (name, str(parent)))

		if parent: parent.childs[name] = self

	def __str__(self):
		if not self.m_parent: return ''
		return "%s://%s" % (type_to_string[self.id & 3], self.abspath())

	def __repr__(self):
		return self.__str__()

	def __hash__(self):
		"expensive, make certain it is not used"
		fatal('nodes, you are doing it wrong')

	def get_type(self):
		return self.id & 3

	def set_type(self, t):
		self.id = self.id + t - self.id & 3

	def dirs(self):
		return [x for x in self.childs.values() if x.id & 3 == DIR]

	def get_dir(self, name, default=None):
		node = self.childs.get(name, None)
		if not node or node.id & 3 != DIR: return default
		return  node

	def files(self):
		return [x for x in self.childs.values() if x.id & 3 == FILE]

	def get_file(self, name, default=None):
		node = self.childs.get(name, None)
		if not node or node.id & 3 != FILE: return default
		return node

	def get_build(self, name, default=None):
		node = self.childs.get(name, None)
		if not node or node.id & 3 != BUILD: return default
		return node

	# ===== BEGIN find methods ===== #

	def find_resource(self, path):
		lst = Utils.split_path(path)
		return self.find_resource_lst(lst)

	def find_resource_lst(self, lst):
		"Find an existing input file: either a build node declared previously or a source node"
		if not lst[:-1]:
			parent = self
		else:
			parent = self.find_dir_lst(lst[:-1])
			if not parent: return None
		Build.bld.rescan(parent)

		name = lst[-1]
		node = parent.childs.get(name, None)
		if node:
			tp = node.id & 3
			if tp == FILE or tp == BUILD:
				return node

		tree = Build.bld
		if not name in tree.cache_dir_contents[parent.id]:
			return None

		path = parent.abspath() + os.sep + name
		try:
			st = Utils.h_file(path)
		except IOError:
			return None

		child = Node(name, parent, FILE)
		tree.m_tstamp_variants[0][child.id] = st
		return child

	def find_or_declare(self, path):
		lst = Utils.split_path(path)
		return self.find_or_declare_lst(lst)

	def find_or_declare_lst(self, lst):
		"Used for declaring a build node representing a file being built"
		if not lst[:-1]:
			parent = self
		else:
			parent = self.find_dir_lst(lst[:-1])
			if not parent: return None
		Build.bld.rescan(parent)

		name = lst[-1]
		node = parent.childs.get(name, None)
		if node:
			tp = node.id & 3
			if tp != BUILD:
				fatal("find_or_declare returns a build node, not a source nor a directory"+str(lst))
			return node
		node = Node(name, parent, BUILD)
		return node

	def find_dir(self, path):
		lst = Utils.split_path(path)
		return self.find_dir_lst(lst)

	def find_dir_lst(self, lst):
		"search a folder in the filesystem"
		current = self
		for name in lst:
			Build.bld.rescan(current)
			prev = current

			if not current.m_parent and name == current.m_name:
				continue
			elif not name:
				continue
			elif name == '.':
				continue
			elif name == '..':
				current = current.m_parent or current
			else:
				current = prev.childs.get(name, None)
				if current is None:
					dir_cont = Build.bld.cache_dir_contents
					if prev.id in dir_cont and name in dir_cont[prev.id]:
						current = Node(name, prev, DIR)
					else:
						return None
		return current

	# compatibility
	find_build = find_or_declare
	find_build_lst = find_or_declare_lst
	find_source = find_resource
	find_source_lst = find_resource_lst

	def ensure_dir_node_from_path(self, path):
		return self.ensure_dir_node_from_path_lst(Utils.split_path(path))

	def ensure_dir_node_from_path_lst(self, plst):
		"used very rarely, force the construction of a branch of node instance for representing folders"
		current = self
		for name in plst:
			if not name:
				continue
			elif name == '.':
				continue
			elif name == '..':
				current = current.m_parent or current
			else:
				prev = current
				current = prev.childs.get(name, None)
				if current is None:
					current = Node(name, prev, DIR)
		return current

	def exclusive_build_node(self, path):
		"""
		create a hierarchy in the build dir (no source folders) for ill-behaving compilers
		the node is not hashed, so you must do it manually

		after declaring such a node, find_dir and find_resource should work as expected
		"""
		lst = Utils.split_path(path)
		name = lst[-1]
		if len(lst) > 1:
			parent = None
			try:
				parent = self.find_dir_lst(lst[:-1])
			except OSError:
				pass
			if not parent:
				# exclusive build directory -> mark the parent as rescanned
				# for find_dir and find_resource to work
				parent = self.ensure_dir_node_from_path_lst(lst[:-1])
				Build.bld.m_scanned_folders[parent.id] = 1
			else:
				try:
					Build.bld.rescan(parent)
				except OSError:
					pass
		else:
			parent = self

		node = parent.childs.get(name, None)
		if not node:
			node = Node(name, parent, BUILD)

		return node

	## ===== END find methods	===== ##


	## ===== BEGIN relpath-related methods	===== ##

	def relpath(self, parent):
		"path relative to a direct ancestor, as string"
		lst = []
		p = self
		h1 = parent.height()
		h2 = p.height()
		while h2 > h1:
			h2 -= 1
			lst.append(p.m_name)
			p = p.m_parent
		if lst:
			lst.reverse()
			ret = os.path.join(*lst)
		else:
			ret = ''
		return ret

	# find a common ancestor for two nodes - for the shortest path in hierarchy
	def find_ancestor(self, node):
		dist = self.height() - node.height()
		if dist < 0: return node.find_ancestor(self)
		# now the real code
		cand = self
		while dist > 0:
			cand = cand.m_parent
			dist -= 1
		if cand == node: return cand
		cursor = node
		while cand.m_parent:
			cand = cand.m_parent
			cursor = cursor.m_parent
			if cand == cursor: return cand

	def relpath_gen(self, going_to):
		"string representing a relative path between two nodes, we are at relative_to"

		if self == going_to: return '.'
		if going_to.m_parent == self: return '..'

		# up_path is '../../../' and down_path is 'dir/subdir/subdir/file'
		ancestor = self.find_ancestor(going_to)
		lst = []
		cand = self
		while not cand.id == ancestor.id:
			lst.append(cand.m_name)
			cand = cand.m_parent
		cand = going_to
		while not cand.id == ancestor.id:
			lst.append('..')
			cand = cand.m_parent
		lst.reverse()
		return os.sep.join(lst)

	def nice_path(self, env=None):
		"printed in the console, open files easily from the launch directory"
		tree = Build.bld
		ln = tree.launch_node()
		name = self.m_name
		x = self.m_parent.get_file(name)
		if x: return self.relative_path(ln)
		else: return os.path.join(tree.m_bldnode.relative_path(ln), env.variant(), self.relative_path(tree.m_srcnode))

	def relative_path(self, folder):
		"relative path between a node and a directory node"
		hh1 = h1 = self.height()
		hh2 = h2 = folder.height()
		p1 = self
		p2 = folder
		while h1 > h2:
			p1 = p1.m_parent
			h1 -= 1
		while h2 > h1:
			p2 = p2.m_parent
			h2 -= 1

		# now we have two nodes of the same height
		ancestor = None
		if p1.m_name == p2.m_name:
			ancestor = p1
		while p1.m_parent:
			p1 = p1.m_parent
			p2 = p2.m_parent
			if p1.m_name != p2.m_name:
				ancestor = None
			elif not ancestor:
				ancestor = p1

		anh = ancestor.height()
		n1 = hh1-anh
		n2 = hh2-anh

		lst = []
		tmp = self
		while n1:
			n1 -= 1
			lst.append(tmp.m_name)
			tmp = tmp.m_parent

		lst.reverse()
		up_path = os.sep.join(lst)
		down_path = (".."+os.sep) * n2

		return "".join(down_path + up_path)

	## ===== END relpath-related methods  ===== ##

	def debug(self):
		print "========= debug node ============="
		print "dirs are ", self.dirs()
		print "files are", self.files()
		print "======= end debug node ==========="

	def is_child_of(self, node):
		"does this node belong to the subtree node"
		p = self
		diff = self.height() - node.height()
		while diff > 0:
			diff -= 1
			p = p.m_parent
		return p.id == node.id

	def variant(self, env):
		"variant, or output directory for this node, a source has for variant 0"
		if not env: return 0
		elif self.id & 3 == FILE: return 0
		else: return env.variant()

	def height(self):
		"amount of parents"
		# README a cache can be added here if necessary
		d = self
		val = 0
		while d.m_parent:
			d = d.m_parent
			val += 1
		return val

	# helpers for building things

	def abspath(self, env=None):
	 	"""
		Returns the absolute file path for this node.  If this
		node is a build node, the absolute path will be a
		build path, else it will be a source path.

		@param env: Environment object.  This is used to
		determine the variant we are interested in.  'env' can
		be None if we are sure to be working with a source
		Node, but when in doubt a real Environment object
		should be provided.
		"""
		## absolute path - hot zone, so do not touch

		if not self.m_name:
			return '/'

		variant = self.variant(env)
		ret = Build.bld.m_abspath_cache[variant].get(self.id, None)
		if ret: return ret

		if not variant:
			cur = self
			lst = []
			while cur:
				lst.append(cur.m_name)
				cur = cur.m_parent
			lst.reverse()
			# the real hot zone is the os path join
			val = os.sep.join(lst)
		else:
			val = os.sep.join((Build.bld.m_bldnode.abspath(), env.variant(), self.relpath(Build.bld.m_srcnode)))
		Build.bld.m_abspath_cache[variant][self.id] = val
		return val

	def change_ext(self, ext):
		"node of the same path, but with a different extension"
		name = self.m_name
		k = name.rfind('.')
		if k >= 0:
			name = name[:k] + ext
		else:
			name = name + ext

		node = self.m_parent.childs.get(name, None)
		if not node:
			node = Node(name, self.m_parent, BUILD)
		return node

	def bld_dir(self, env):
		"build path without the file name"
		return self.m_parent.bldpath(env)

	def bldbase(self, env):
		"build path without the extension: src/dir/foo(.cpp)"
		s = self.m_name
		s = s[:s.rfind('.')]
		return os.path.join(self.bld_dir(env), s)

	def bldpath(self, env=None):
		"path seen from the build dir default/src/foo.cpp"
		x = self.m_parent.get_file(self.m_name)

		if x: return self.relpath_gen(Build.bld.m_bldnode)
		if self.relpath(Build.bld.m_srcnode) is not '':
			return os.path.join(env.variant(), self.relpath(Build.bld.m_srcnode))
		return env.variant()

	def srcpath(self, env):
		"path in the srcdir from the build dir ../src/foo.cpp"
		x = self.m_parent.get_build(self.m_name)
		if x: return self.bldpath(env)
		return self.relpath_gen(Build.bld.m_bldnode)

	def read(self, env):
		"get the contents of a file, it is not used anywhere for the moment"
		try:
			file = open(self.abspath(env), 'rb')
			return file.read()
		finally:
			if file: file.close()

# win32 fixes follow
if sys.platform == "win32":
	def find_dir_lst_win32(self, lst):
		current = self
		for name in lst:
			Build.bld.rescan(current)
			prev = current

			if not current.m_parent and name == current.m_name:
				continue
			if not name:
				continue
			elif name == '.':
				continue
			elif name == '..':
				current = current.m_parent or current
			else:
				current = prev.childs.get(name, None)
				if current is None:
					if (name in Build.bld.cache_dir_contents[prev.id]
						or (not prev.m_parent and name[1] == ":")):
						current = Node(name, prev, DIR)
					else:
						return None
		return current
	Node.find_dir_lst = find_dir_lst_win32

	def abspath_win32(self, env=None):
		variant = self.variant(env)
		ret = Build.bld.m_abspath_cache[variant].get(self.id, None)
		if ret: return ret

		if not variant:
			cur = self
			lst = []
			while cur:
				lst.append(cur.m_name)
				cur = cur.m_parent
			lst.reverse()
			val = os.sep.join(lst)
		else:
			val = os.sep.join((Build.bld.m_bldnode.abspath(), env.variant(), self.relpath(Build.bld.m_srcnode)))
		if val.startswith("\\"): val = val[1:]
		if val.startswith("\\"): val = val[1:]
		Build.bld.m_abspath_cache[variant][self.id] = val
		return val
	Node.abspath = abspath_win32

