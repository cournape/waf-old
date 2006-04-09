#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)
"""
try:
	import threading
	import Queue
except ImportError:
	import dummy_threading as threading
"""

import os, popen2, sys
import Params, Task, pproc
from Params import debug, error, trace, fatal

def process_cmd_output(cmd_stdout, cmd_stderr):
	stdout_eof = stderr_eof = 0
	while not (stdout_eof and stderr_eof):
		if not stdout_eof:
			str = cmd_stdout.read()
			if not str: stdout_eof = 1
			else: sys.stdout.write(str)
		if not stderr_eof:
			str = cmd_stderr.read()
			if not str: stderr_eof = 1
			else: sys.stderr.write(str)

# run commands in a portable way
# the subprocess module backported from python 2.4 and should work on python >= 2.2
def exec_command(str):
	# for now
	trace("system command -> "+ str)
	if Params.g_verbose==1: print str
	proc = pproc.Popen(str, shell=1, stdout=pproc.PIPE, stderr=pproc.PIPE)
	process_cmd_output(proc.stdout, proc.stderr)
	stat = proc.wait()
	if stat & 0xff: return stat | 0x80
	return stat >> 8

# kind of iterator - the data structure is a bit complicated (price to pay for flexibility)
class JobGenerator:
	def __init__(self, tree):
		self.m_tree = tree

		# we will use self.m_current_group = self.m_tasks.pop()
		self.m_tasks = Task.g_tasks

		# current group
		self.m_current_group    = {}

		# this is also a list that we pop to get the next task list
		self.m_task_prio_lst    = []

		# this is the list of the tasks
		self.m_current_task_lst = {}

		# progress bar
		self.m_total     = 0
		self.m_processed = 0

		self.compute_total()

		self.m_switchflag=1 # postpone

	def compute_total(self):
		self.m_total=0
		for htbl in self.m_tasks:
			for tasks in htbl.values():
				self.m_total += len(tasks)

	# warning, this one is recursive ..
	def get_next(self):
		try:
			t = self.m_current_task_lst.pop(0)
			self.m_processed += 1
			return t
		except:
			try:
				self.m_current_task_lst = self.m_current_group[ self.m_task_prio_lst.pop(0) ]
			except:
				try:
					self.m_current_group = self.m_tasks.pop(0)
					self.m_task_prio_lst = self.m_current_group.keys()
					self.m_task_prio_lst.sort()
				except:
					error("no more task to give")
					return None
			return self.get_next()

	def progress(self):
		return (self.m_processed, self.m_total)

	def postpone(self, task):
		self.m_processed -= 1
		# shuffle the list - some fanciness of mine (ita)
		self.m_switchflag=-self.m_switchflag
		if self.m_switchflag>0: self.m_current_task_lst = [task]+self.m_current_task_lst
		else:                   self.m_current_task_lst.append(task)
		#self.m_current_task_lst = [task]+self.m_current_task_lst

	def debug(self):
		error("debugging a task: something went wrong:")
		#trace("tasks to run in order")
		#Task.g_tasks.reverse()
		s=""
		for t in Task.g_tasks:
			s += str(t.m_idx)+" "
		trace(s)
		#Task.g_tasks.reverse()

class Serial:
	def __init__(self, generator):
		self.m_generator = generator
	def start(self):
		debug("Serial start called")
		#self.m_generator.debug()
		while 1:
			# get next Task
			proc = self.m_generator.get_next()
			if proc is None:
				break

			trace("retrieving task "+str(proc.m_idx))

			# # =======================
			if proc.m_hasrun:
				error("task has already run! "+str(proc.m_idx))

			if not proc.may_start():
				trace("delaying task no "+str(proc.m_idx))
				self.m_generator.postpone(proc)
				self.m_generator.debug()
				proc = None
				continue
			# # =======================

			proc.prepare()
			#proc.debug()

			#trace("m_sig is "+str(proc.m_sig))
			#trace("obj output m_sig is "+str(proc.m_outputs[0].get_sig()))

			#continue
			if not proc.must_run():
				proc.m_hasrun=2
				debug("task is up-to_date "+str(proc.m_idx))
				continue

			trace("executing task "+str(proc.m_idx))

			# display the command that we are about to run
			if not Params.g_commands['configure']:
				(s, t) = self.m_generator.progress()
				col1=''
				col2=''
				try:
					col1=Params.g_colors[proc.m_action.m_name]
					col2=Params.g_colors['NORMAL']
				except: pass
				print '[%d/%d] %s%s%s' % (s, t, col1, proc.m_str, col2)

			# run the command, it might be a function attached to an action
			# usually we will only popen a string
			if proc.m_action.m_function_to_run:
				ret = proc.m_action.m_function_to_run(proc)
			else:
				ret = exec_command(proc.m_cmd)

			# non-zero means something went wrong
			if ret:
				error("task failed! (return code %s and task id %s)"%(str(ret), str(proc.m_idx)))
				proc.debug(1)
				return ret

			try: proc.update_stat()
			except: error('the nodes have not been produced !')
			proc.m_hasrun=1

			# register the task to the ones that have run - useful for debugging purposes
			Params.g_tasks_done.append(proc)	

			"""try:
				proc.apply()
			except KeyboardInterrupt:
				raise
			except:
				print "hum hum .. task failed!"
			"""

		debug("Serial end")
		if not Params.g_commands['configure']:
			print "Build finished successfully"
		return 0

import threading
import Queue

class TaskConsumer(threading.Thread):
	def __init__(self, id, q_in, master):
		threading.Thread.__init__(self)
		self.setDaemon(1)

		self.m_master = master

		self.m_id    = id
		self.m_q_in  = q_in

		self.start()

	def run(self):
		while 1:
			proc = self.m_q_in.get(block=1)
			
			# display the label for the command executed
			print proc.m_str

			# run the command, it might be a function attached to an action
			# usually we will only popen a string
			if proc.m_action.m_function_to_run:
				ret = proc.m_action.m_function_to_run(proc)
			else:
				ret = exec_command(proc.m_cmd)

			if ret:
				self.m_master.m_lock.acquire(block=1)
				error("task failed! (return code %s and task id %s)"%(str(ret), str(proc.m_idx)))
				proc.debug(1)
				self.m_count -= 1
				self.m_finished.put(ret)
				self.m_master.m_lock.release()
				continue

			try: proc.update_stat()
			except: error('the nodes have not been produced !')
			proc.m_hasrun=1

			self.m_master.m_lock.acquire(block=1)
			self.m_master.m_count -= 1
			self.m_master.m_finished.put(ret)
			self.m_master.m_lock.release()

# This is a bit more complicated than for serial builds
class Parallel:
	def __init__(self, tree, numjobs):
		# the tree we are working on
		self.m_tree = tree

		# maximum amount of consumers
		self.m_numjobs   = numjobs

		# the container of all tasks: a list of hashtables containing lists of tasks
		self.m_tasks = Task.g_tasks

		# progress bar
		self.m_total     = 0
		self.m_processed = 0

		# tasks waiting to be processed
		self.m_outstanding = []
		# tasks waiting to be run by the consumers
		self.m_ready       = Queue.Queue(150)
		# results from the consumers
		self.m_results     = Queue.Queue(150)
		# tasks that are awaiting for another task to complete
		self.m_frozen      = []

		# lock for self.m_count - count the amount of tasks active
		self.m_lock      = threading.Lock()
		self.m_count     = 0
		# counter that is not updated by the threads
		self.m_prevcount = 0

		# a priority is finished means :
		# m_outstanding, m_ready, m_results and m_frozen are empty, and m_count is 0

		# update the variables for the progress bar
		self.compute_total()

		#############################################################

		## current group
		#self.m_current_group    = {}
		## this is also a list that we pop to get the next task list
		#self.m_task_prio_lst    = []
		## this is the list of the tasks
		#self.m_current_task_lst = {}
		#self.m_switchflag=1 # postpone
		#self.m_finished  = 0

	def compute_total(self):
		self.m_total=0
		for htbl in self.m_tasks:
			for tasks in htbl.values():
				self.m_total += len(tasks)
	
	# warning, this one is recursive ..
	#def get_next(self):
	#	try:
	#		t = self.m_current_task_lst.pop(0)
	#		self.m_processed += 1
	#		return t
	#	except:
	#		try:
	#			self.m_current_task_lst = self.m_current_group[ self.m_task_prio_lst.pop(0) ]
	#		except:
	#			try:
	#				self.m_current_group = self.m_tasks.pop(0)
	#				self.m_task_prio_lst = self.m_current_group.keys()
	#				self.m_task_prio_lst.sort()
	#			except:
	#				error("no more task to give")
	#				return None
	#		return self.get_next()

	#def postpone(self, task):
	#	self.m_processed -= 1
	#	# shuffle the list - some fanciness of mine (ita)
	#	self.m_switchflag=-self.m_switchflag
	#	if self.m_switchflag>0: self.m_current_task_lst = [task]+self.m_current_task_lst
	#	else:                   self.m_current_task_lst.append(task)
	#	#self.m_current_task_lst = [task]+self.m_current_task_lst

	def debug(self):
		error("debugging a task: something went wrong:")
		#trace("tasks to run in order")
		#Task.g_tasks.reverse()
		s=""
		for t in Task.g_tasks:
			s += str(t.m_idx)+" "
		trace(s)
		#Task.g_tasks.reverse()

	def start(self):

		# unleash the consumers
		for i in range(self.m_numjobs): TaskConsumer(i, self.m_ready, self.m_frozen)

		# to be continued
		print "parallel builds are not ready"
		sys.exit(0)




		self.add_task()

		while 1:
			while self.m_count>0:
				self.process_finished_targets()

			if self.m_finished: return 0

			while self.m_count<2*self.m_numjobs and not self.m_finished:
				self.add_task()

		if self.m_count != 0:
			error("thread count is wrong "+str(self.m_count))
		if not Params.g_commands['configure']:
			print "Build finished successfully"
		return 0

	# no need to parallelize this, there is no i/o, so it will not get any faster
	def add_task(self):
		proc=None
		while proc is None:
			proc = self.get_next()
			if proc is None:
				self.m_finished=1
				return 0
		
			if not proc.may_start():
				trace("delaying task no "+str(proc.m_idx))
				self.postpone(proc)
				self.debug()
				proc=None
				continue
			#proc.debug()
			proc.prepare()
			if not proc.must_run():
				proc.m_hasrun=2
				debug("task is up-to_date "+str(proc.m_idx))
				proc=None
				continue
			break

		trace("executing task "+str(proc.m_idx))
		# display the command that we are about to run
		col1=''
		col2=''
		try:
			col1=Params.g_colors[proc.m_action.m_name]
			col2=Params.g_colors['NORMAL']
		except: pass
		proc.m_str = '[%d/%d] %s%s%s' % (self.m_processed, self.m_total, col1, proc.m_str, col2)

		self.m_lock.acquire(block=1)
		self.m_count += 1		
		self.m_lock.release()

		self.m_q_in.put(proc, block=1)
		return 1

	def process_finished_targets(self):
		ret = self.m_q_out.get(block=1)
		self.m_count -= 1
		if ret:
			print "task failed - uh-oh"
			raise "task failed"

