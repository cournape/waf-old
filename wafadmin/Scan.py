#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, re
import Params, Node
from Params import debug, error, trace, fatal

# look in this global var when looking for a scanner object
g_all_scanners={}


# ======================================= #
# The single scanner instances to use are at the end
# TODO double check for threading issues
# ======================================= #



#cregexp='^[ \t]*#[ \t]*(?:include)[ \t]*(<|")([^>"]+)(>|")'
#cregexp1 = re.compile('^[ \t]*#[ \t]*(?:include)[ \t]*(<|")([^>"]+)(>|")', re.M)
cregexp1 = re.compile(r'^[ \t]*#[ \t]*(?:include)[ \t]*(?:/\*.*?\*/)?[ \t]*(<|")([^>"]+)(>|")', re.M)
cregexp2 = re.compile('^[ \t]*#[ \t]*(?:include)[ \t]*"([^>"]+)"', re.M)
cregexp3 = re.compile('^[ \t]*#[ \t]*(?:include|import)[ \t]*(<|")([^>"]+)(>|")', re.M)
kcfg_regexp = re.compile('[fF]ile\s*=\s*(.+)\s*', re.M)


# scanners are now classes
# behaviours can be very different
class scanner:
	def __init__(self):
		global g_all_scanners
		g_all_scanners[self.__class__.__name__] = self

	# ======================================= #
	# interface definition

	# computes the signature for a task
	# returns a string
	def get_signature(self, task):
		return self._get_signature(task)

	# scans a node
	# this method takes as input a node and a list of paths
	# it searches dependencies in the paths, and returns a list
	# of nodes that should trigger a rebuild.

	# it returns a tuple containing:
	# * a list of nodes corresponding to real files
	# * a list of names for files not found in path_lst
	def scan(self, node, env, path_lst):
		return self._scan_default(node, env, path_lst)


	# re-scan a node, update the tree
	def do_scan(self, node, env, hashparams):

		if node in node.m_parent.m_files: variant = 0
		else: variant = env.m_variant

		debug("rescanning "+str(node))
		if not node:
			print "BUG rescanning a null node"
			return
		(nodes, names) = self.scan(node, env, **hashparams)
		tree = Params.g_build

		# TODO remove this check in the future:
		for l in [tree.m_depends_on, tree.m_raw_deps, tree.m_deps_tstamp]:
			if not variant in l:
				l[variant] = {}

		tree.m_depends_on[variant][node] = nodes
		tree.m_raw_deps[variant][node] = names

		debug("variant is "+str(variant))
		#print tree.m_tstamp_variants[variant]

		tree.m_deps_tstamp[variant][node] = tree.m_tstamp_variants[variant][node]

	# ======================================= #
	# private method

	# default scanner scheme
	# climb up until all nodes have been visited and xor signatures
	# the climbing scheme must be deterministic
	def _get_signature(self, task):	

		tree = Params.g_build
		seen=[]
		def get_node_sig(node):
			if not node:
				print "warning: null node in get_node_sig"
			if not node or node in seen: return Params.sig_nil()
			seen.append(node)
			_sig = Params.xor_sig(node.get_sig(), Params.sig_nil())
			#if task.m_recurse:
			#	if tree.needs_rescan(node, task.m_env):
			#		self.do_scan(tree, node, task.m_scanner_params)
			#	# TODO looks suspicious
			#	lst = tree.m_depends_on[node]
			#
			#	for dep in lst: _sig = Params.xor_sig(_sig, get_node_sig(dep))
			return Params.xor_sig(_sig, Params.sig_nil())
		sig=Params.sig_nil()
		for node in task.m_inputs:
			# WATCH OUT we are using the source node, not the build one for that kind of signature..

			try:
				sig = Params.xor_sig(sig, get_node_sig(node))
			except:
				raise
				print "ERROR in get_deps_signature"
				print node
				print sig
				print "details for the task are: ", task.m_outputs, task.m_inputs, task.m_name
				raise

		for task in task.m_run_after:
			sig = Params.xor_sig(task.signature(), sig)
			#debug("signature of this node is %s %s %s " % (str(s), str(n), str(node.m_tstamp)) )
		debug("signature of the task %d is %s" % (task.m_idx, Params.vsig(sig)) )
		return sig

	# private method
	# default scanner function
	def _scan_default(self, node, env, path_lst):

		if node in node.m_parent.m_files: variant = 0
		else: variant = task.m_env.m_variant

		file = open(node.abspath(env), 'rb')
		found = cregexp1.findall( file.read() )
		file.close()

		nodes = []
		names = []
		if not node: return (nodes, names)

		for (_, name, _) in found:
			#print 'boo', name

			# quite a few nested 'for' loops, looking suspicious
			found = None
			for dir in path_lst:
				for node in dir.m_files:
					if node.m_name == name:
						found = node
						break
				if found:
					break
			if found: nodes.append(found)
			else:     names.append(name)
		#print "-S ", nodes, names
		return (nodes, names)


# ======================================= #
# scanner implementations

# a scanner for c/c++ files
class c_scanner(scanner):
	def __init__(self):
		scanner.__init__(self)

	def get_signature(self, task):
		if Params.g_preprocess:
			return self._get_signature_preprocessor(task)
		else:
			return self._get_signature_dumb(task)

	def _get_signature_preprocessor(self, task):
		# assumption: there is only one cpp file to compile in a task

		tree = Params.g_build
		rescan = 0

		node = task.m_inputs[0]

		if node in node.m_parent.m_files: variant = 0
		else: variant = task.m_env.m_variant

		if tree.needs_rescan(node, task.m_env): rescan = 1
		if not rescan:
			for node in tree.m_depends_on[variant][node]:
				if tree.needs_rescan(node, task.m_env): rescan = 1

		# rescan the cpp file if necessary
		if rescan:
			self.do_scan(node, task.m_env, task.m_scanner_params)

		# we are certain that the files have been scanned - compute the signature
		sig = Params.sig_nil()
		sig = Params.xor_sig(sig, node.get_sig())
		for n in tree.m_depends_on[variant][node]:
			sig = Params.xor_sig(sig, n.get_sig())

		# and now xor the signature with the other tasks
		for task in task.m_run_after:
			sig = Params.xor_sig(task.signature(), sig)
		debug("signature of the task %d is %s" % (task.m_idx, Params.vsig(sig)) )
		return sig

	def _get_signature_dumb(self, task):
		tree = Params.g_build
		seen=[]
		def get_node_sig(node):
			if not node:
				print "warning: null node in get_node_sig"
			if not node or node in seen: return Params.sig_nil()

			if node in node.m_parent.m_files: variant = 0
			else: variant = task.m_env.m_variant

			seen.append(node)
			_sig = Params.xor_sig(node.get_sig(), Params.sig_nil())
			if tree.needs_rescan(node, task.m_env):
				self.do_scan(node, variant, task.m_scanner_params)
			# TODO looks suspicious
			lst = tree.m_depends_on[variant][node]
			
			for dep in lst: _sig = Params.xor_sig(_sig, get_node_sig(dep))
			return Params.xor_sig(_sig, Params.sig_nil())
		sig=Params.sig_nil()
		for node in task.m_inputs:
			# WATCH OUT we are using the source node, not the build one for that kind of signature..

			try:
				sig = Params.xor_sig(sig, get_node_sig(node))
			except:
				print "ERROR in get_deps_signature"
				#print n
				#print node
				#print sig
				print "details for the task are: ", task.m_outputs, task.m_inputs, task.m_name
				raise

		for task in task.m_run_after:
			sig = Params.xor_sig(task.signature(), sig)
			#debug("signature of this node is %s %s %s " % (str(s), str(n), str(node.m_tstamp)) )
		debug("signature of the task %d is %s" % (task.m_idx, Params.vsig(sig)) )
		return sig


	def scan(self, node, env, path_lst):
		if Params.g_preprocess:
			return self._scan_preprocessor(node, env, path_lst)
		else:
			return scanner.scan(self, node, env, path_lst)

	def _scan_preprocessor(self, node, env, path_lst):
		import preproc
		gruik = preproc.cparse(nodepaths = path_lst)
	        gruik.start2(node, env)
		#print "nodes found for ", str(node), " ", str(gruik.m_nodes), " ", str(gruik.m_names)
		return (gruik.m_nodes, gruik.m_names)

# a scanner for .kcfgc files (kde xml configuration files)
class kcfg_scanner(scanner):
	def __init__(self):
		scanner.__init__(self)

	def scan(self, node, env, path_lst):

		if node in node.m_parent.m_files: variant = 0
		else: variant = task.m_env.m_variant

		trace("kcfg scanner called for "+str(node))
		file = open(node.abspath(env), 'rb')
		found = kcfg_regexp.findall(file.read())
		file.close()

		if not found:
			fatal("no kcfg file found when scanning the .kcfgc- that's very bad")

		name = found[0]
		for dir in path_lst:
			for node in dir.m_files:
				if node.m_name == name:
					return ([node], found)
		fatal("the kcfg file was not found - that's very bad")



# ======================================= #
# TODO look in g_all_scanners[classname] first
# these globals can be considered singletons
g_default_scanner = scanner()
g_c_scanner    = c_scanner()
g_kcfg_scanner = kcfg_scanner()


### obsolete code
def add_scanner(name, fun, recurse=0):
	Params.g_scanners[name] = fun
	if recurse: Params.g_recursive_scanners_names.append(name)
	print ( "scanner function added: %s" % (name) )

