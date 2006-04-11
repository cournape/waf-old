#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, popen2, sys, time, random
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

### TODO the following part neeeds to be rewritten seriously ###

class TaskConsumer(threading.Thread):
	def __init__(self, id, master):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.m_master = master
		self.m_id     = id
		self.start()

	def run(self):
		master = self.m_master
		while 1:
			master.m_countlock.acquire()
			if master.m_stop:
				time.sleep(1)
				continue
			master.m_countlock.release()

			# take the next task
			proc = master.m_ready.get(block=1)
			
			# display the label for the command executed
			print proc.m_str

			# run the command, it might be a function attached to an action
			# usually we will only popen a string
			if proc.m_action.m_function_to_run:
				ret = proc.m_action.m_function_to_run(proc)
			else:
				ret = exec_command(proc.m_cmd)

			if ret:
				self.m_master.m_countlock.acquire()
				error("task failed! (return code %s and task id %s)"%(str(ret), str(proc.m_idx)))
				proc.debug(1)
				master.m_count -= 1
				master.m_stop = 1
				master.m_countlock.release()
				continue

			try:
				proc.update_stat()
			except:
				self.m_master.m_countlock.acquire()
				error('the nodes have not been produced !')
				master.m_count -= 1
				master.m_stop = 1
				master.m_countlock.release()

			proc.m_hasrun=1

			master.m_countlock.acquire()
			master.m_count -= 1
			master.m_countlock.release()

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
		self.m_total        = 0
		self.m_processed    = 1

		# tasks waiting to be processed
		self.m_outstanding  = []
		# tasks waiting to be run by the consumers
		self.m_ready        = Queue.Queue(150)
		# tasks that are awaiting for another task to complete
		self.m_frozen       = []

		# lock for self.m_count - count the amount of tasks active
		self.m_count        = 0
		self.m_countlock    = threading.Lock()
		# counter that is not updated by the threads
		self.m_prevcount    = 0

		# a priority is finished means :
		# m_outstanding, m_frozen are empty, and m_count is 0
		self.m_stop         = 0

		# update the variables for the progress bar
		self.compute_total()

	def compute_total(self):
		self.m_total=0
		for htbl in self.m_tasks:
			for tasks in htbl.values():
				self.m_total += len(tasks)
	
	def wait_all_finished(self):
		while self.m_count>0:
			# check the global stop flag
			self.m_countlock.acquire()
			if self.m_stop:
				break
			self.m_countlock.release()

			time.sleep(0.02)

	def start(self):

		# unleash the consumers
		for i in range(self.m_numjobs): TaskConsumer(i, self)

		# the current group
		group = None

		# current priority
		currentprio = 0

		# add the tasks to the queue
		while 1:
			if self.m_stop:
				self.wait_all_finished()
				break

			# if there are no tasks to run, wait for the consumers to eat all of them
			# and then skip to the next priority group
			if (not self.m_frozen) and (not self.m_outstanding):
				self.wait_all_finished()
				if not group:
					try:
						lst = self.m_tasks.pop(0)
						group = []
						keys = lst.keys()
						keys.sort()
						for key in keys:
							group.append( (key, lst[key]) )
					except:
						self.wait_all_finished()
						break

				(currentprio, self.m_outstanding) = group.pop(0)

			# for tasks that must run sequentially
			# (linking object files uses a lot of memory for example)
			if (currentprio%2)==1:
				# make sure there is no more than one task in the queue
				cond = 0
				self.m_countlock.acquire()
				if self.m_count: cond=1
				self.m_countlock.release()
	
				if cond:
					time.sleep(0.02)
					continue

			# if there is no outstanding task to process, look at the frozen ones
			if not self.m_outstanding:
				cond=0
				self.m_countlock.acquire()
				if self.m_count != self.m_prevcount:
					cond=1
					self.m_prevcount = self.m_count
				else:
					if self.m_count == 0:
						print "this should not happen"
				self.m_countlock.release()
				if cond:
					self.m_outstanding = self.m_frozen
					self.m_frozen = []
				else:
					time.sleep(0.02)
					continue

			# now we are certain that there are outstanding or frozen threads
			if self.m_outstanding:
				proc = self.m_outstanding.pop(0)
				if not proc.may_start():
					# shuffle
					#print "shuf0"
					#self.m_frozen.append(proc)
					#self.m_frozen = [proc]+self.m_frozen
					if random.randint(0,1):
						#print "shuf1"
						self.m_frozen.append(proc)
					else:
						#print "shuf2"
						self.m_frozen = [proc]+self.m_frozen
					continue
				else:
					proc.prepare()
					if not proc.must_run():
						proc.m_has_run=2
						continue

					# display the command that we are about to run
					col1=''
					col2=''
					try:
						col1=Params.g_colors[proc.m_action.m_name]
						col2=Params.g_colors['NORMAL']
					except: pass
					proc.m_str = '[%d/%d] %s%s%s' % (self.m_processed, self.m_total, col1, proc.m_str, col2)

					self.m_countlock.acquire()
					self.m_count += 1
					self.m_prevcount = self.m_count
					self.m_processed += 1

					self.m_countlock.release()

					self.m_ready.put(proc, block=1)


