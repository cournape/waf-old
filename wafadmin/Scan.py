#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Scan for dependencies, compute task signatures"

try: from hashlib import md5
except ImportError: from md5 import md5
import Params
from Params import debug, error

g_all_scanners={}
"all instances of scanners"

# TODO double check for threading issues
class scanner:
	"TODO: call this a dependency manager (not a scanner), as it does scan and compute the signatures"

	def __init__(self):
		global g_all_scanners
		g_all_scanners[self.__class__.__name__] = self

	# ======================================= #
	# interface definition

	"TODO: add the manually added dependencies"
	"TODO: add the environment variables dependencies"

	# it returns a tuple containing:
	# * a list of nodes corresponding to real files
	# * a list of names for files not found in path_lst
	# the input parameters may have more parameters that the ones used below
	def scan(self, task, node):
		"usually reimplemented"
		return ([], [])

	# scans a node
	# this method takes as input a node and a list of paths
	# it searches dependencies in the paths, and returns a list
	# of nodes that should trigger a rebuild.
	def do_scan(self, task, node):
		"rarely reimplemented"
		debug("do_scan(self, node, env, hashparams)", 'ccroot')

		variant = node.variant(task.m_env)

		if not node:
			error("BUG rescanning a null node")
			return

		(nodes, names) = self.scan(task, node)
		if Params.g_verbose:
			if Params.g_zones:
				debug('scanner for %s returned %s %s' % (node.m_name, str(nodes), str(names)), 'deps')

		tree = Params.g_build
		tree.m_depends_on[variant][node] = nodes
		tree.m_raw_deps[variant][node] = names

	# compute the signature
	# recompute the signature if it does not match the cache
	def get_signature(self, task):
		"the signature obtained may not be the one if the files have changed, we do it in two steps"
		tree = Params.g_build
		env = task.m_env

		# assumption: we assume that we can still get the old signature from the signature cache
		try:
			node = task.m_outputs[0]
			variant = node.variant(task.m_env)
			time = tree.m_tstamp_variants[variant][node]
			key = hash( (variant, node, time, self.__class__.__name__) )
			prev_sig = tree.get_sig_cache(key)[1]
		except KeyError:
			prev_sig = Params.sig_nil
		except:
			raise

		# we can compute and return the signature if
		#   * the source files have not changed (rescan is 0)
		#   * the computed signature has not changed
		sig = self.get_signature_queue(task)

		# if the previous signature is the same
		if sig == prev_sig: return sig

		#print "scanning the file", task.m_inputs[0].abspath()

		# therefore some source or some header is dirty, rescan the source files
		for node in task.m_inputs:
			self.do_scan(task, node)

		# recompute the signature and return it
		sig = self.get_signature_queue(task)

		# DEBUG
		#print "rescan for ", task.m_inputs[0], " is ", rescan,  " and deps ", \
		#	tree.m_depends_on[variant][node], tree.m_raw_deps[variant][node]

		return sig

	# ======================================= #
	# protected methods - override if you know what you are doing

	# FIXME used by the c and d tools
	def get_signature_queue(self, task):
		"the basic scheme for computing signatures from .cpp and inferred .h files"
		tree = Params.g_build

		rescan = 0
		seen = []
		queue = []+task.m_inputs
		m = md5()

		# add the defines - TODO make this specific for c/c++/d
		m.update(str(task.m_env['CXXDEFINES']))
		m.update(str(task.m_env['CCDEFINES']))

		# add the hashes of all files entering into the dependency system
		while len(queue) > 0:
			node = queue[0]
			queue = queue[1:]

			if node in seen: continue
			seen.append(node)

			# TODO: look at the case of stale nodes and dependencies types
			variant = node.variant(task.m_env)
			try: queue += tree.m_depends_on[variant][node]
			except: pass

			m.update(tree.m_tstamp_variants[variant][node])

		return m.digest()

