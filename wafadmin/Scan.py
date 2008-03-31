#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"Scan for dependencies, compute task signatures"

from hashlib import md5
import Params
from Params import debug, error
from Constants import *

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
		tree.node_deps[variant][node.id] = nodes
		tree.raw_deps[variant][node.id] = names

	# compute the signature, recompute it if there is no match in the cache
	def get_signature(self, tsk):
		"the signature obtained may not be the one if the files have changed, we do it in two steps"
		tree = Params.g_build
		env = tsk.env()

		# assumption: we assume that we can still get the old signature from the signature cache
		try:
			node = tsk.m_outputs[0]
			variant = node.variant(tsk.env())
			time = tree.m_tstamp_variants[variant][node.id]
			key = hash( (variant, node.m_name, time, self.__class__.__name__) )
			prev_sig = tree.get_sig_cache(key)[1]
		except KeyError:
			prev_sig = SIG_NIL

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
		#	tree.node_deps[variant][node.id], tree.raw_deps[variant][node.id]

		return sig

	# ======================================= #
	# protected methods - override if you know what you are doing

	def get_signature_queue(self, tsk):
		"""the basic scheme for computing signatures from .cpp and inferred .h files
		hot spot so do not touch"""
		tree = Params.g_build

		seen = set()
		lst = []+tsk.m_inputs
		m = md5()
		upd = m.update

		# additional variables to hash (command-line defines for example)
		env = tsk.env()
		for x in self.vars:
			k = env[x]
			if k: upd(str(k))

		# cross-variant builds are disabled for performance reasons (and for little usage)
		# if you want to do that, put the variant var in the loop
		if lst:
			variant = lst[0].variant(env)
			node_deps = tree.node_deps[variant]
			tstamp_variants = tree.m_tstamp_variants[variant]

		# add the build hashes of all files entering into the dependency system
		for node in lst:
			id = node.id
			if id in seen: continue
			else: seen.add(id)

			# TODO: look at the case of stale nodes and dependencies types
			k = node_deps.get(id, ())
			if k: lst.extend(k)

			# the exception should not happen
			try: upd(tstamp_variants[id])
			except KeyError: return SIG_NIL

		return m.digest()

