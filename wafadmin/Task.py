#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, types, shutil
import Params, Scan, Action
from Params import debug, error, trace, fatal, warning

# tasks that have been run
# this is used in tests to check which tasks were actually launched
g_tasks_done       = []
g_default_param    = { 'path_lst' : [] }

class TaskManager:
	def __init__(self):
		self.groups = None
		self.idx    = 0
	def add_group(self, name=''):
		# groups are added in a "first in last out fashion"
		if not name:
			try: size = len(self.groups)
			except: size = 0
			name = 'group-%d' % size
		if not self.groups:
			self.groups = [TaskGroup(name)]
			return
		if not self.groups[0].prio:
			warning('add_group: an empty group is already present')
			return
		self.groups = self.groups + [TaskGroup(name)]
	def add_task(self, task, prio):
		if not self.groups: self.add_group('group-0')
		task.m_idx = self.idx
		self.idx += 1
		self.groups[-1].add_task(task, prio)
	def total(self):
		total = 0
		if not self.groups: return 0
		for group in self.groups:
			for p in group.prio:
				total += len(group.prio[p])
		return total
	def debug(self):
		for i in self.groups:
			print "--------------group-----------------", i.name
			for j in i.prio:
				print "prio: ", j, str(i.prio[j])

g_tasks = TaskManager()

class TaskGroup:
	def __init__(self, name):
		self.name = name
		self.info = ''
		self.prio = {} # map priority numbers to tasks
	def add_task(self, task, prio):
		try: self.prio[prio].append(task)
		except: self.prio[prio] = [task]

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

		global g_default_param

		# scanner function
		self.m_scanner        = Scan.g_default_scanner
		self.m_scanner_params = g_default_param

		# add ourself to the list of tasks
		#self._add_task(priority)
		global g_tasks
		g_tasks.add_task(self, priority)

		self.m_run_after = []

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
		if (not self.m_inputs) or (not self.m_outputs):
			if not (not self.m_inputs) and (not self.m_outputs):
				error("potentially grave error, task is invalid : no inputs or outputs")
				self.debug()

		if not self.m_scanner.may_start(self): return 1

		for t in self.m_run_after:
			if not t.m_hasrun: return 0
		return 1

	# see if this task must or must not be run
	def must_run(self):
		ret = 0
		if not self.m_inputs and not self.m_outputs:
			self.m_dep_sig = Params.sig_nil()
			return 1

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

	def debug_info(self):
		ret = []
		ret.append('-- task details begin --')
		ret.append('action: %s' % str(self.m_action))
		ret.append('idx:    %s' % str(self.m_idx))
		ret.append('source: %s' % str(self.m_inputs))
		ret.append('target: %s' % str(self.m_outputs))
		ret.append('-- task details end --')
		return '\n'.join(ret)

	def debug(self, level=0):
		fun=Params.debug
		if level>0: fun=Params.error
		fun(self.debug_info())

	# IMPORTANT: users want this to set dependencies on other tasks
	def set_run_after(self, task):
		self.m_run_after.append(task)

#def reset():
#	global g_tasks
#	g_tasks=[{}]


