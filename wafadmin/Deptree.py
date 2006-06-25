#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os
import os.path
from stat import *
import shutil
import cPickle

import Node
import Params
from Params import debug, error, trace, fatal

# this module will disappear in the future (merge into Build.py)

# List of current assumptions:
# * there is a build dir
# * there are nodes to represent the folder and file system
# * files are not copied/linked into the build dir
# * the list of folders that have been scanned is kept
# * computing the signatures is delegated to the scanner classes
class Deptree:
	def __init__(self):

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
		self.m_flags       = {}

	# IMPORTANT
	# Fast node access - feed an internal dictionary (to keep between runs -> TODO not sure)
	def store_node(self, node):
		nn=node.m_name
		try:
			# prevent silly errors
			if node in self.m_name2nodes[nn]: print "BUG: name2nodes already contains node!", nn
			else: self.m_name2nodes[nn].append(node)
		except:
			self.m_name2nodes[nn] = [node]

	# list of dependencies, for example give the .h a .cpp relies on
	def get_depends_on(self, node):
		try: return self.m_depends_on[node]
		except: return []

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

	# returns the files names that do not have an associated node (scanner results)
	def get_raw_deps(self, node):
		try: return self.m_raw_deps[node]
		except: return []

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





	# OBSOLETE
	# return the mirror of a node in a particular builddir, both nodes must exist
	def get_mirror_node(self, dirnode):
		# get the difference between srcnode and dirnode
		lst = self.m_srcnode.difflst( dirnode )
		if not lst: debug("lst is empty, this should not happen")

		# TODO: use name2nodes ? a cache ? to investigate

		# get find the node from the build directory using the difference above
		mirrornode = self.m_bldnode.find_node(lst)
		return mirrornode

	# return the node in the source directory, given a node in the build directory
	def get_src_from_mirror(self, bldnode):
		return self.m_srcnode.find_node( self.m_bldnode.difflst(bldnode) )
	# TODO FIXME : why the ..
	def get_bld_from_src(self, srcnode):
		return self.m_src_to_bld[srcnode]

	# the following is used for launching the commands to create the nodes
	# the node must exist (and so it has a mirror), but the filename may not exist up to that point
	def mirror_file(self, dirnode, filename):
		if os.sep in filename:
			lst = filename.split(os.sep)
			dirnode = dirnode.find_node(lst[:len(lst)-1])
			filename = lst[len(lst)-1]

		# get the the dirnode mirror
		mirrornode = self.get_mirror_node(dirnode)
		# now that we have the mirror of dirnode, try to find the filename
		ret=None
		for file in mirrornode.m_files:
			if file.m_name==filename:
				ret=file
				break
		# if that node does not exist, just create it
		if not ret:
			ret = Node.Node(filename, mirrornode)
			mirrornode.m_files.append(ret)

		if ret: trace("mirror node is found "+str(ret))
		else:   trace("mirror node is NOT FOUND"+str(ret))

		return ret




	# the first important algorithm of the app:
	#   -> replicate files into the builddir
	#   -> find the nodes to scan for dependencies
	def scanner_mirror(self, dir):
		trace("scanner mirror for dir "+dir)

		lst = dir.split(os.sep)

		src_node = self.ensure_node_from_lst( self.m_srcnode, lst )
		(exists, mir_node) = self.ensure_directory_lst( self.m_bldnode, lst )

		# the source node must be stat'd - this is a folder so we use the stat
		src_sig = os.stat(src_node.abspath()).st_mtime
		if Params.g_strong_hash: src_sig = str(src_sig)

		# two essential conditions 1. the mirror node exists and 2. the src folder has not changed
		C1 = exists
		C2 = (src_sig == src_node.m_tstamp)

		#print "C1 and C2 ", C1, " ",C2

		# first one, condition to skip everything (folders untouched)
		if C1 and C2:
			if len(src_node.m_files) == len(mir_node.m_files):

				# we only need to update the hash sig of each source file
				for node in src_node.m_files:
					#node.m_tstamp = os.stat(node.abspath()).st_mtime
					node.m_tstamp = Params.h_file(node.abspath())

				return
		if C1:
			#print "untested part"

			# difficult part, find what nodes to update, etc
			# C1&!C2 | C1&C2&!C3
			# FIXME TODO this is inefficient and written very late
			names_read = os.listdir( src_node.abspath() )
			removed = []
			added   = []

			e_files = []
			e_dirs  = []
			e_unknown = []
			for file in src_node.m_files:
				try:
					# try to stat the file ..
					st = os.stat(file.abspath())
					ts = file.m_tstamp

					#file.m_tstamp = st.st_mtime
					file.m_tstamp = Params.h_file(file.abspath())

					e_files.append(file.m_name)
					# if the timestamp has changed, we need to re-scan the file - not here though
					if ts!=file.m_tstamp:
						trace("A file changed! %s %s now %s" % (str(file),str(ts),str(file.m_tstamp)) )
				except:
					# remove the node here and in the builddir
					name = file.m_name
					src_node.m_files.remove(file)

					for mn in mir_node.m_files:
						if mn.m_name == name:
							mir_node.m_files.remove(mn)
							#print "remove trailing file %s from builddir "%mn.m_name²
							try: os.remove(os.path.join(mir_node.abspath(), mn.m_name))
							except: pass
							break

			for file in src_node.m_dirs:
				# same as above comment, if fails then the dir does not exist anymore
				st = os.stat(file.abspath())
				file.m_tstamp = st.st_mtime
				e_dirs.append(file.m_name)

			excl = e_files+e_dirs+Params.g_excludes
			#print excl
			for name in names_read:
				if name in excl: continue
				e_unknown.append(name)

			#print "unkn ", e_unknown
			for name in e_unknown:
				# new files or dirs - create the corresponding nodes
				child_node = Node.Node(name, src_node)
				#print 'adding child node '+str(child_node)

				st = os.stat( child_node.abspath() )

				relp = src_node.relpath_gen(mir_node)
				# in case of a regular file, create a mirror node in the builddir
				if S_ISREG( st[ST_MODE] ):
					#print "regular file"

					src_node.m_files.append(child_node)

					#child_node.m_tstamp = st.st_mtime
					child_node.m_tstamp = Params.h_file(child_node.abspath())

					# mirror the new node
					mir_child_node = Node.Node(name, mir_node)
					mir_node.m_files.append(mir_child_node)
					#mir_child_node.m_tstamp = st.st_mtime
					mir_child_node.m_tstamp = src_node.m_tstamp

					dupe = mir_child_node.abspath()

					self.m_bld_to_src[mir_child_node]=child_node
					self.m_src_to_bld[child_node]=mir_child_node
				else:
					src_node.m_dirs.append(child_node)
			src_node.m_tstamp = src_sig
		else:
			relp = src_node.relpath_gen(mir_node)
			if C2:
				# replicate the files in the newly created destdir blindly
				for child_node in src_node.m_files:
					name = child_node.m_name
					mir_child_node = Node.Node(child_node.m_name, mir_node)
					mir_node.m_files.append( mir_child_node )

					# same signature of course
					mir_child_node.m_tstamp = child_node.m_tstamp

					dupe = mir_child_node.abspath()
					self.m_bld_to_src[mir_child_node]=child_node
					self.m_src_to_bld[child_node]=mir_child_node
			else:

				# we need to update the info in the srcdir first - remove the m_files nodes
				src_node.m_files = []
				names_read = os.listdir( src_node.abspath() )
				abspath = src_node.abspath()
				for file_or_dir in names_read:
					subpath = os.path.join(abspath, file_or_dir)
					st = os.stat( subpath )
					if not S_ISREG(st[ST_MODE]):
						# this could be left aside, unfortunately that's a bad idea
						src_node.m_dirs.append( Node.Node(file_or_dir, src_node) )
						continue

					# create the corresponding nodes in src and mir folders
					child_node = Node.Node(file_or_dir, src_node)
					src_node.m_files.append( child_node )

					mir_child_node = Node.Node(file_or_dir, mir_node)
					mir_node.m_files.append( mir_child_node )

					# timestamp is the same (sig)
					#tstamp = st.st_mtime
					tstamp = Params.h_file(subpath)
					child_node.m_tstamp = tstamp
					mir_child_node.m_tstamp = tstamp

					dupe = mir_child_node.abspath()
					self.m_bld_to_src[mir_child_node]=child_node
					self.m_src_to_bld[child_node]=mir_child_node
			src_node.m_tstamp = src_sig

	# ensure a directory node from a list, given a node to start from
	def ensure_node_from_lst(self, node, plst):
		curnode=node
		for dirname in plst:
			if 0:
				if not dirname: continue

				nc = Params.g_build.m_cache_node_content
				try:
					htbl = nc[curnode]
				except:
					nc[curnode] = {}
					htbl = nc[curnode]

					for file in curnode.m_dirs+curnode.m_files:
						htbl[file.m_name]=file

				try:
					#print "found !"
					found = htbl[dirname]
				except:
					found = Node.Node(dirname, curnode)
					curnode.m_dirs.append(found)
					htbl[dirname]=found
				curnode = found
			if 1:
				if not dirname: continue
				found=None
				for cand in curnode.m_dirs:
					if cand.m_name == dirname:
						found = cand
						break
				if not found:
					found = Node.Node(dirname, curnode)
					curnode.m_dirs.append(found)
				curnode = found
		return curnode

	def ensure_directory_lst(self, node, plst):
		curnode = node
		exists  = 1
		for dirname in plst:
			#print "finding ", dirname
			if not dirname: continue

			# try to find the node in existing deptree
			found=None
			for cand in curnode.m_dirs:
				if cand.m_name == dirname:
					found = cand
					break
			# the node is found and is already scanned, keep walking
			try:
				if found and self.m_flags[found]>0:
					curnode=found
					continue
			except: pass

			# the node is not found, add it
			if not found:
				found = Node.Node(dirname, curnode)
				curnode.m_dirs.append(found)
			# we have a node, but it is not scanned
			curnode = found
			try: os.stat(curnode.abspath())
			except OSError:
				exists = 0
				trace("make dir %s"%curnode.abspath())
				try: os.mkdir(curnode.abspath())
				except: trace('mkdir failed '+curnode.abspath())
				#st=os.stat(curnode.abspath())
				# TRICK_1: the subtree is obsolete -> forget sub-nodes recursively
				curnode.m_dirs=[]
				curnode.m_files=[]
			self.m_flags[curnode] = 1
		return (exists, curnode)


	# FIXME: duplicates some code
	# return a node corresponding to an absolute path, creates nodes if necessary
	def ensure_node_from_path(self, abspath):
		trace('Deptree:ensure_node_from_path %s' % (abspath))
		plst = abspath.split(os.sep)
		curnode = self.m_root # root of the tree
		for dirname in plst:
			if not dirname: continue
			found=None
			for cand in curnode.m_dirs:
				if cand.m_name == dirname:
					found = cand
					break
			if not found:
				found = Node.Node(dirname, curnode)
				curnode.m_dirs.append(found)
			curnode = found
		return curnode

	# FIXME: duplicates some code
	# Creates the folders if they do not exist
	# Flag the intermediate nodes as 'already existing' with m_flag=1
	def ensure_directory(self, path):
		trace('ensure_directory %s' % (path))
		dir_lst = path.split(os.sep)

		curnode = self.m_root # root of the tree
		for dirname in dir_lst:
			if not dirname: continue

			# try to find the node in existing deptree
			found=None
			for cand in curnode.m_dirs:
				if cand.m_name == dirname:
					found = cand
					break
			# the node is found and is already scanned, keep walking
			try:
				if found and self.m_flags[found]>0:
					curnode=found
					continue
			except: pass

			# the node is not found, add it
			if not found:
				found = Node.Node(dirname, curnode)
				curnode.m_dirs.append(found)
			# we have a node, but it is not scanned
			curnode = found
			try: st = os.stat(curnode.abspath())
			except OSError:
				trace("make dir %s"%curnode.abspath())
				os.mkdir(curnode.abspath())
				st=os.stat(curnode.abspath())
				# TRICK_1: the subtree is obsolete -> forget sub-nodes recursively
				curnode.m_dirs=[]
				curnode.m_files=[]
			self.m_flags[curnode] = 1
		return curnode

	# TODO deprecated ?
	def is_a_built_node(self, node):
		return node.is_child_of(self.m_bldnode)


