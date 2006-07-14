#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, re, md5
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
		#print "scanner:get_signature(self, task)"
		return self._get_signature(task)

	# scans a node
	# this method takes as input a node and a list of paths
	# it searches dependencies in the paths, and returns a list
	# of nodes that should trigger a rebuild.

	# it returns a tuple containing:
	# * a list of nodes corresponding to real files
	# * a list of names for files not found in path_lst
	def scan(self, node, env, path_lst):
		#print "scanner:scan(self, node, env, path_lst)"
		return self._scan_default(node, env, path_lst)


	# re-scan a node, update the tree
	def do_scan(self, node, env, hashparams):
		#print "scanner:do_scan(self, node, env, hashparams)"

		if node in node.m_parent.m_files: variant = 0
		else: variant = env.m_variant

		debug("rescanning "+str(node))
		if not node:
			print "BUG rescanning a null node"
			return
		(nodes, names) = self.scan(node, env, **hashparams)
		tree = Params.g_build

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
		#print "scanner:_get_signature(self, task)"
		if Params.g_strong_hash:
			return self._get_signature_default_strong(task)
		else:
			return self._get_signature_default_weak(task)

	# private method
	# default scanner function
	def _scan_default(self, node, env, path_lst):
		#print "scanner:_scan_default(self, node, env, path_lst)"
		if node in node.m_parent.m_files: variant = 0
		else: variant = env.m_variant

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

	def _get_signature_default_strong(self, task):
		m = md5.new()
		tree = Params.g_build
		seen = []
		def add_node_sig(node):
			if not node: print "warning: null node in get_node_sig"
			if node in seen: return

			# TODO - using the variant each time is stupid
			if node in node.m_parent.m_files: variant = 0
			else: variant = task.m_env.m_variant
			seen.append(node)

			m.update(tree.m_tstamp_variants[variant][node])
		# add the signatures of the input nodes
		for node in task.m_inputs: add_node_sig(node)
		# add the signatures of the task it depends on
		for task in task.m_run_after: m.update(task.signature())
		return m.digest()

	def _get_signature_default_weak(self, task):
		msum = 0
		tree = Params.g_build
		seen = []
		def add_node_sig(node):
			if not node: print "warning: null node in get_node_sig"
			if node in seen: return 0

			sum = 0
			# TODO - using the variant each time is stupid
			if node in node.m_parent.m_files: variant = 0
			else: variant = task.m_env.m_variant
			seen.append(node)

			sum += tree.m_tstamp_variants[variant][node]
			return sum
		# add the signatures of the input nodes
		for node in task.m_inputs: msum += add_node_sig(node)
		# add the signatures of the task it depends on
		for task in task.m_run_after: msum += task.signature()
		return int(msum % 2000000011) # this number was not chosen randomly


# ======================================= #
# scanner implementations

# a scanner for c/c++ files
class c_scanner(scanner):
	def __init__(self):
		scanner.__init__(self)

	# re-scan a node, update the tree
	def do_scan(self, node, env, hashparams):
		print "c:do_scan(self, node, env, hashparams)"

		if node in node.m_parent.m_files: variant = 0
		else: variant = env.m_variant

		debug("rescanning "+str(node))
		if not node:
			print "BUG rescanning a null node"
			return
		(nodes, names) = self.scan(node, env, **hashparams)
		tree = Params.g_build

		tree.m_depends_on[variant][node] = nodes
		tree.m_raw_deps[variant][node] = names

		debug("variant is "+str(variant))
		#print tree.m_tstamp_variants[variant]

		tree.m_deps_tstamp[variant][node] = tree.m_tstamp_variants[variant][node]
		if Params.g_preprocess:
			for n in nodes:
				tree.m_deps_tstamp[variant][n] = tree.m_tstamp_variants[variant][n]


	def get_signature(self, task):
		#print "c:get_signature(self, task)"
		if Params.g_preprocess:
			#print "c: will preprocess"
			if Params.g_strong_hash:
				return self._get_signature_preprocessor(task)
			else:
				return self._get_signature_preprocessor_weak(task)
		else:
			if Params.g_strong_hash:
				return self._get_signature_regexp_strong(task)
			else:
				return self._get_signature_regexp_weak(task)

	def scan(self, node, env, path_lst):
		#print "c:scan"
		if Params.g_preprocess:
			return self._scan_preprocessor(node, env, path_lst)
		else:
			return scanner.scan(self, node, env, path_lst)

	def _scan_preprocessor(self, node, env, path_lst):
		#print "c:_scan_preprocessor(self, node, env, path_lst)"
		import preproc
		gruik = preproc.cparse(nodepaths = path_lst)
	        gruik.start2(node, env)
		#print "nodes found for ", str(node), " ", str(gruik.m_nodes), " ", str(gruik.m_names)
		return (gruik.m_nodes, gruik.m_names)

	def _get_signature_regexp_strong(self, task):
		m = md5.new()
		tree = Params.g_build
		seen = []
		def add_node_sig(node):
			if not node: print "warning: null node in get_node_sig"
			if node in seen: return

			# TODO - using the variant each time is stupid
			if node in node.m_parent.m_files: variant = 0
			else: variant = task.m_env.m_variant
			seen.append(node)

			# rescan if necessary, and add the signatures of the nodes it depends on
			if tree.needs_rescan(node, task.m_env): self.do_scan(node, task.m_env, task.m_scanner_params)
                        lst = tree.m_depends_on[variant][node]
                        for dep in lst: add_node_sig(dep)
			m.update(tree.m_tstamp_variants[variant][node])
		# add the signatures of the input nodes
		for node in task.m_inputs: add_node_sig(node)
		# add the signatures of the task it depends on
		for task in task.m_run_after: m.update(task.signature())
		return m.digest()

	def _get_signature_regexp_weak(self, task):
		msum = 0
		tree = Params.g_build
		seen = []
		def add_node_sig(node):
			if not node: print "warning: null node in get_node_sig"
			if node in seen: return 0

			sum = 0

			# TODO - using the variant each time is stupid
			if node in node.m_parent.m_files: variant = 0
			else: variant = task.m_env.m_variant
			seen.append(node)

			sum += tree.m_tstamp_variants[variant][node]
			# rescan if necessary, and add the signatures of the nodes it depends on
			if tree.needs_rescan(node, task.m_env): self.do_scan(node, task.m_env, task.m_scanner_params)
			lst = tree.m_depends_on[variant][node]
			for dep in lst: sum += add_node_sig(dep)
			return sum
		# add the signatures of the input nodes
		for node in task.m_inputs: msum += add_node_sig(node)
		# add the signatures of the task it depends on
		for task in task.m_run_after: msum += task.signature()
		return int(msum % 2000000011) # this number was not chosen randomly

	def _get_signature_preprocessor_weak(self, task):
		msum = 0
		tree = Params.g_build
		rescan = 0

		seen=[]
		def add_node_sig(n):
			if not n: print "warning: null node in get_node_sig"
			if n in seen: return 0

			# TODO - using the variant each time is stupid
			if n in n.m_parent.m_files: variant = 0
			else: variant = task.m_env.m_variant
			seen.append(n)

			return tree.m_tstamp_variants[variant][n]

		# there is only one c/cpp file as input
		node = task.m_inputs[0]

		if node in node.m_parent.m_files: variant = 0
		else: variant = task.m_env.m_variant

		if not variant == 0: fatal('variant is not 0')

		if tree.needs_rescan(node, task.m_env): rescan = 1
		if not rescan:
			for anode in tree.m_depends_on[variant][node]:
				if tree.needs_rescan(anode, task.m_env): rescan = 1

		# rescan the cpp file if necessary
		if rescan:
			#print "rescanning ", node
			self.do_scan(node, task.m_env, task.m_scanner_params)

#		print "rescan for ", task.m_inputs[0], " is ", rescan,  " and deps ", \
#			tree.m_depends_on[variant][node], tree.m_raw_deps[variant][node]

		# we are certain that the files have been scanned - compute the signature
		msum += add_node_sig(node)
		for n in tree.m_depends_on[variant][node]: msum += add_node_sig(n)

		# and now xor the signature with the other tasks
		for task in task.m_run_after: msum += task.signature()
		#debug("signature of the task %d is %s" % (task.m_idx, Params.vsig(sig)) )

		return int(msum % 2000000011) # this number was not chosen randomly

	def _get_signature_preprocessor(self, task):
		# assumption: there is only one cpp file to compile in a task

		tree = Params.g_build
		rescan = 0

		m = md5.new()
		seen=[]
		def add_node_sig(n):
			if not n: print "warning: null node in get_node_sig"
			if n in seen:
				print "node already seen"
				return

			# TODO - using the variant each time is stupid
			if n in n.m_parent.m_files: variant = 0
			else: variant = task.m_env.m_variant
			seen.append(n)

			m.update(tree.m_tstamp_variants[variant][n])

		# there is only one c/cpp file as input
		node = task.m_inputs[0]

		if node in node.m_parent.m_files: variant = 0
		else: variant = task.m_env.m_variant
		if not variant == 0: fatal('variant is not 0')


		if tree.needs_rescan(node, task.m_env): rescan = 1

		if rescan: print "node has changed, a rescan is req ", node

		if not rescan:
			for anode in tree.m_depends_on[variant][node]:
				if tree.needs_rescan(anode, task.m_env):
					print "rescanning because of ", anode
					rescan = 1

		# rescan the cpp file if necessary
		if rescan:
			#print "rescanning ", node
			self.do_scan(node, task.m_env, task.m_scanner_params)

		#print "rescan for ", task.m_inputs[0], " is ", rescan,  " and deps ", \
		#	tree.m_depends_on[variant][node], tree.m_raw_deps[variant][node]

		# we are certain that the files have been scanned - compute the signature
		add_node_sig(node)
		for n in tree.m_depends_on[variant][node]: add_node_sig(n)

		# and now xor the signature with the other tasks
		#for task in task.m_run_after: m.update(task.signature())
		#debug("signature of the task %d is %s" % (task.m_idx, Params.vsig(sig)) )
		return m.digest()


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
	#print ( "scanner function added: %s" % (name) )

