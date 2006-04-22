#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os
import Params
from Params import debug, error, trace, fatal

# task index
g_idx=0

# the set of tasks is a list of groups : [group 2, group 1, group 0]
# groups are hashtables mapping priorities to lists of tasks ..
# parallelizing tasks is thus much easier with this scheme
g_tasks=[{}]

# tasks that have been run
# this is used in tests to check which tasks were actually launched
g_tasks_done       = []


def add_group():
	global g_tasks
	# we already have an empty group to fill with tasks
	if not g_tasks[0]: return
	g_tasks = [{}]+g_tasks

def add_task(task, priority=6):
	try: g_tasks[0][priority].append(task)
	except: g_tasks[0][priority] = [task]

class Task:
	def __init__(self, action_name, env, priority=5):
		# name of the action associated to this task
		self.m_action = Params.g_actions[action_name]
		# environment in use
		self.m_env = env
		# nodes used as input
		self.m_inputs=[]
		# nodes to produce
		self.m_outputs=[]

		# this task was run
		self.m_hasrun=0

		self.m_cmd=0
		self.m_sig=0
		self.m_str=0

		self.m_dep_sig=0

		global g_idx
		self.m_idx=g_idx+1
		g_idx = g_idx+1

		# scanner function
		self.m_scanner=0
		self.m_scanner_params={}
		self.m_recurse=1

		# add ourself to the list of tasks
		add_task(self, priority)

		self.m_run_after = []

	# TRICK_2 TODO LATER
	# Simplification if this task does not produce targets across folders
	# in self.must_run we look at the signature of the first object only
	# looking at others is only necessary if targets span across several folders
	def isMulti(self):
		return self.m_action.m_isMulti

	def signature(self):
		#s = str(self.m_sig)+str(self.m_dep_sig)
		#return s.__hash__()
		return Params.xor_sig(self.m_sig, self.m_dep_sig)

	def update_stat(self):
		tree=Params.g_build.m_tree
		for node in self.m_outputs:
			#trace("updating_stat of node "+node.abspath())
			#node.m_tstamp = os.stat(node.abspath()).st_mtime
			node.m_tstamp = Params.h_file(node.abspath())
			if node.get_sig() == self.signature():
				error("NODE ALREADY TAGGED - GRAVE ERROR")
			tree.m_sigs[node] = self.signature()
		self.m_executed=1

	# wait for other tasks to complete
	def may_start(self):
		if len(self.m_inputs) < 1 or len(self.m_outputs) < 1:
			error("grave error, task is invalid : no inputs or outputs")

		for t in self.m_run_after:
			if not t.m_hasrun: return 0
		return 1

	# see if this task must or must not be run
	def must_run(self):
		self.m_dep_sig = self.get_deps_signature()
		sg = self.signature()

		# DEBUG
		#error("signature is "+str(sg)+" while node signature is "+str(self.m_outputs[0].get_sig()))

		# check if the file actually exists - expect a moderate slowdown
		for f in self.m_outputs:
			if not os.path.exists(f.abspath()):
				return 1

		if sg != self.m_outputs[0].get_sig():
			trace("task %s must run %s %s" % (str(self.m_idx), str(sg), str(self.m_outputs[0].get_sig()) ))
			return 1
		return 0

	# return the signature of the dependencies
	def get_deps_signature(self):
		tree=Params.g_build.m_tree
		seen=[]
		def get_node_sig(node):
			if node in seen: return Params.sig_nil()
			seen.append(node)
			_sig = Params.xor_sig(node.get_sig(), Params.sig_nil())
			if self.m_recurse and self.m_scanner:
				if tree.needs_rescan(node):
					tree.rescan(node, self.m_scanner, self.m_scanner_params)
				# TODO looks suspicious
				lst = tree.m_depends_on[node]

				for dep in lst: _sig = Params.xor_sig(_sig, get_node_sig(dep))
			return Params.xor_sig(_sig, Params.sig_nil())
		sig=Params.sig_nil()
		for node in self.m_inputs:
			# WATCH OUT we are using the source node, not the build one for that kind of signature..

			try:
				n = tree.get_src_from_mirror(node)
				if n: sig = Params.xor_sig(sig, get_node_sig(n))
				else: sig = Params.xor_sig(sig, get_node_sig(node))
			except:
				print "ERROR in get_deps_signature"
				print n
				print node
				print sig
				print "details for the task are: ", self.m_outputs, self.m_inputs
				raise

		for task in self.m_run_after:
			sig = Params.xor_sig(task.signature(), sig)
			#debug("signature of this node is %s %s %s " % (str(s), str(n), str(node.m_tstamp)) )
		debug("signature of the task %d is %s" % (self.m_idx, str(sig)) )
		return sig

	def prepare(self):
		self.m_action.prepare(self)

	# TODO documentation
	def set_run_after(self, task):
		self.m_run_after.append(task)

	def debug(self, level=0):
		fun=debug
		if level>0: fun=error

		fun("-- begin task debugging --")
		fun("action: "+str(self.m_action)+" idx: "+str(self.m_idx))
		fun(str(self.m_inputs))
		fun(str(self.m_outputs))
		for node in self.m_outputs:
			fun(str(node.m_tstamp))
		fun("-- end task debugging --")

def reset():
	global g_tasks
	g_tasks=[{}]


