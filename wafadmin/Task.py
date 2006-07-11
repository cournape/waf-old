#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, types
import Params, Scan
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

class Task:
	def __init__(self, action_name, env, priority=5):
		# name of the action associated to this task
		self.m_action = Params.g_actions[action_name]
		# environment in use
		self.m_env = env

		# use setters to set the input and output nodes - when possible
		# nodes used as input
		self.m_inputs  = []
		# nodes to produce
		self.m_outputs = []


		# this task was run
		self.m_hasrun=0

		self.m_sig=0
		self.m_str=0

		self.m_dep_sig=0

		global g_idx
		self.m_idx=g_idx+1
		g_idx = g_idx+1

		trace("priority given is "+str(priority))

		# scanner function
		self.m_scanner        = Scan.g_default_scanner
		self.m_scanner_params = {}

		# add ourself to the list of tasks
		self._add_task(priority)

		self.m_run_after = []

	def _add_task(self, priority=6):
		global g_tasks
		if len(g_tasks) == 0:
			g_tasks=[{}]
		try: g_tasks[0][priority].append(self)
		except: g_tasks[0][priority] = [self]

	def set_inputs(self, inp):
		if type(inp) is types.ListType:
			self.m_inputs = inp
		else:
			self.m_inputs = [inp]

	def set_outputs(self, out):
		if type(out) is types.ListType:
			self.m_outputs = out
		else:
			self.m_outputs = [out]

	def signature(self):
		#s = str(self.m_sig)+str(self.m_dep_sig)
		#return s.__hash__()
		return Params.xor_sig(self.m_sig, self.m_dep_sig)

	def update_stat(self):
		tree = Params.g_build
		env  = self.m_env
		for node in self.m_outputs:
			#trace("updating_stat of node "+node.abspath())
			#node.m_tstamp = os.stat(node.abspath()).st_mtime
			#node.m_tstamp = Params.h_file(node.abspath())

			if node in node.m_parent.m_files: variant = 0
			else: variant = self.m_env.m_variant

			Params.g_build.m_tstamp_variants[variant][node] = Params.h_file(node.abspath(env))

			if node.get_sig() == self.signature():
				error("NODE ALREADY TAGGED - GRAVE ERROR")
			tree.m_tstamp_variants[variant][node] = self.signature()
		self.m_executed=1

	# wait for other tasks to complete
	def may_start(self):
		if len(self.m_inputs) < 1 or len(self.m_outputs) < 1:
			error("grave error, task is invalid : no inputs or outputs")
			self.debug()

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
			if not os.path.exists(f.bldpath(self.m_env)):
				return 1

		if sg != self.m_outputs[0].get_sig():
			trace("task %s must run %s %s" % (str(self.m_idx), str(sg), str(self.m_outputs[0].get_sig()) ))
			return 1
		return 0

	# return the signature of the dependencies
	def get_deps_signature(self):
		return self.m_scanner.get_signature(self)

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
		#for node in self.m_outputs:
		#	fun(str(node.m_tstamp))
		fun("-- end task debugging --")

def reset():
	global g_tasks
	g_tasks=[{}]


