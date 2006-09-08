#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, types, shutil
import Params, Scan, Action
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
g_default_param    = { 'path_lst' : [] }

def add_group():
	global g_tasks
	# we already have an empty group to fill with tasks
	if not g_tasks[0]: return
	g_tasks = [{}]+g_tasks

class Task:
	def __init__(self, action_name, env, priority=5):
		# name of the action associated to this task
		self.m_action = Action.g_actions[action_name]
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
		self.m_dep_sig=0

		global g_idx
		self.m_idx=g_idx+1
		g_idx = g_idx+1

		trace("priority given is "+str(priority))

		global g_default_param

		# scanner function
		self.m_scanner        = Scan.g_default_scanner
		self.m_scanner_params = g_default_param

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
		sig = self.signature()

		cnt = 0
		for node in self.m_outputs:
			if node in node.m_parent.m_files: variant = 0
			else: variant = self.m_env.variant()
			#if node in tree.m_tstamp_variants[variant]:
			#	print "variant is ", variant
			#	print "self sig is ", Params.vsig(tree.m_tstamp_variants[variant][node])

			# check if the node exists ..
			try:
				os.stat(node.abspath(env))
			except:
				error('a node was not produced for task %s %s' % (str(self.m_idx), node.abspath(env)))
				raise

			tree.m_tstamp_variants[variant][node] = sig

			if Params.g_options.usecache:
				ssig = sig.encode('hex')
				dest = os.path.join(Params.g_options.usecache, ssig+'-'+str(cnt))
				shutil.copy2(node.abspath(env), dest)
				cnt += 1

		self.m_executed=1

	# wait for other tasks to complete
	def may_start(self):
		if len(self.m_inputs) < 1 or len(self.m_outputs) < 1:
			error("grave error, task is invalid : no inputs or outputs")
			self.debug()

		if not self.m_scanner.may_start(self): return 1

		for t in self.m_run_after:
			if not t.m_hasrun: return 0
		return 1

	# see if this task must or must not be run
	def must_run(self):
		ret = 0

		self.m_dep_sig = self.m_scanner.get_signature(self)


		i1 = Params.vsig(self.m_sig)
		i2 = Params.vsig(self.m_dep_sig)


		sg = self.signature()

		node = self.m_outputs[0]

		# TODO should make a for loop as the first node is not enough
		if node in node.m_parent.m_files: variant = 0
		else: variant = self.m_env.variant()

		if not node in Params.g_build.m_tstamp_variants[variant]:
			debug("task should run as the first node does not exist"+str(node))
			ret = self.can_retrieve_cache(sg)
			return not ret

		outs = Params.g_build.m_tstamp_variants[variant][node]

		a1 = Params.vsig(sg)
		a2 = Params.vsig(outs)
		
		debug("task %s must run ? signature is %s while node signature is %s (sig:%s depsig:%s)" \
			% (str(self.m_idx), a1, a2, i1, i2))

		if sg != outs:
			ret = self.can_retrieve_cache(sg)
			return not ret
		return 0

	def prepare(self):
		self.m_action.prepare(self)

	def can_retrieve_cache(self, sig):
		if not Params.g_options.usecache: return None
		if Params.g_options.nocache: return None

		tree = Params.g_build
		env  = self.m_env
		sig = self.signature()

		try:
			cnt = 0
			for node in self.m_outputs:
				if node in node.m_parent.m_files: variant = 0
				else: variant = self.m_env.variant()

				ssig = sig.encode('hex')
				orig = os.path.join(Params.g_options.usecache, ssig+'-'+str(cnt))
				#print "trying to restore ", orig, node.abspath(env)
				shutil.copy2(orig, node.abspath(env))
				# GOTCHA 
				# touch the file that we copied, so it should be possible to clean
				# the temporary directory by time (unlike scons)
				os.utime(orig, None)
				cnt += 1

				Params.g_build.m_tstamp_variants[variant][node] = sig
				Params.pprint('GREEN', "restored from cache %s" % node.bldpath(env))
		except:
			# just return 1 if the retrieval failed
			debug("failed retrieving file")
			return None

		return 1

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

	# IMPORTANT: users want this to set dependencies on other tasks
	def set_run_after(self, task):
		self.m_run_after.append(task)

def reset():
	global g_tasks
	g_tasks=[{}]


