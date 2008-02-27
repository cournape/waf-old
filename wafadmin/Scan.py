#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"Scan for dependencies, compute task signatures"

# see: http://docs.python.org/lib/module-md5.html
try: from hashlib import md5
except ImportError: from md5 import md5

import Params
from Params import debug, error

g_all_scanners={}
"all instances of scanners"

class scanner(object):
	"TODO: call this a dependency manager (not a scanner), as it does scan and compute the signatures"

	def __init__(self):
		global g_all_scanners
		g_all_scanners[self.__class__.__name__] = self
		self.vars = [] # additional vars to add in the scanning process

	# ======================================= #
	# interface definition

	# this method returns a tuple containing:
	# * a list of nodes corresponding to real files
	# * a list of names for files not found in path_lst
	# the input parameters may have more parameters that the ones used below
	def scan(self, tsk, node):
		"usually reimplemented"
		return ([], [])

	# scans a node, the task may have additional parameters such as include paths, etc
	def do_scan(self, tsk, node):
		"more rarely reimplemented"
		debug("do_scan(self, node, env, hashparams)", 'ccroot')

		variant = node.variant(tsk.env())

		if not node:
			error("BUG rescanning a null node")
			return

		# we delegate the work to "def scan(self, tsk, node)" to avoid duplicate code
		(nodes, names) = self.scan(tsk, node)
		if Params.g_verbose:
			if Params.g_zones:
				debug('scanner for %s returned %s %s' % (node.m_name, str(nodes), str(names)), 'deps')

		tree = Params.g_build
		tree.m_depends_on[variant][node] = nodes
		tree.m_raw_deps[variant][node] = names

	# compute the signature, recompute it if there is no match in the cache
	def get_signature(self, tsk):
		"the signature obtained may not be the one if the files have changed, we do it in two steps"
		tree = Params.g_build
		env = tsk.env()

		# assumption: we assume that we can still get the old signature from the signature cache
		try:
			node = tsk.m_outputs[0]
			variant = node.variant(tsk.env())
			time = tree.m_tstamp_variants[variant][node]
			key = hash( (variant, node, time, self.__class__.__name__) )
			prev_sig = tree.get_sig_cache(key)[1]
		except KeyError:
			prev_sig = Params.sig_nil

		# we can compute and return the signature if
		#   * the source files have not changed (rescan is 0)
		#   * the computed signature has not changed
		sig = self.get_signature_queue(tsk)

		# if the previous signature is the same
		if sig == prev_sig: return sig

		#print "scanning the file", tsk.m_inputs[0].abspath()

		# therefore some source or some header is dirty, rescan the source files
		for node in tsk.m_inputs:
			self.do_scan(tsk, node)

		# recompute the signature and return it
		sig = self.get_signature_queue(tsk)

		# DEBUG
		#print "rescan for ", tsk.m_inputs[0], " is ", rescan,  " and deps ", \
		#	tree.m_depends_on[variant][node], tree.m_raw_deps[variant][node]

		return sig

	# ======================================= #
	# protected methods - override if you know what you are doing

	def get_signature_queue(self, tsk):
		"the basic scheme for computing signatures from .cpp and inferred .h files"
		tree = Params.g_build

		rescan = 0
		seen = []
		queue = []+tsk.m_inputs
		m = md5()

		# additional variables to hash (command-line defines for example)
		env = tsk.env()
		for x in self.vars:
			m.update(str(env[x]))

		# add the hashes of all files entering into the dependency system
		while queue:
			node = queue.pop(0)

			if node in seen: continue
			seen.append(node)

			# TODO: look at the case of stale nodes and dependencies types
			variant = node.variant(env)
			try: queue += tree.m_depends_on[variant][node]
			except KeyError: pass

			try: m.update(tree.m_tstamp_variants[variant][node])
			except KeyError: return Params.sig_nil

		return m.digest()

