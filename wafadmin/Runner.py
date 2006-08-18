#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, popen2, sys, time, random, string, time
import Params, Task, pproc
from Params import debug, error, trace, fatal

# output a stat file (data for gnuplot) when running tasks in parallel
dostat=0
g_initial = time.time()

g_quiet = 0

def write_progress(s):
	if Params.g_options.progress_bar == 1:
		sys.stderr.write(s + '\r')
	elif Params.g_options.progress_bar == 2:
		print s
		sys.stdout.flush()
	else:
		print s

def progress_line(s, t, col1, task, col2):
	global g_initial
	if Params.g_options.progress_bar == 1:
		pc = (100.*s)/t
		bar = ('='*int((70.*s)/t-1)+'>').ljust(70)

		eta = time.strftime('%H:%M:%S', time.gmtime(time.time() - g_initial))
		return '[%d/%d] %s%d%%%s |%s| %s%s%s' % (s, t, col1, pc, col2, bar, col1, eta, col2)
	elif Params.g_options.progress_bar == 2:
		eta = time.strftime('%H:%M:%S', time.gmtime(time.time() - g_initial))

		ins  = ','.join(map(lambda n: n.m_name, task.m_inputs))
		outs = ','.join(map(lambda n: n.m_name, task.m_outputs))

		return '|Total %s|Current %s|Inputs %s|Outputs %s|Time %s|' % (t, s, ins, outs, eta)

	return '[%d/%d] %s%s%s' % (s, t, col1, task.m_str, col2)

def process_cmd_output(cmd_stdout, cmd_stderr):
	stdout_eof = stderr_eof = 0
	while not (stdout_eof and stderr_eof):
		if not stdout_eof:
			str = cmd_stdout.read()
			if not str: stdout_eof = 1
			elif not g_quiet: sys.stdout.write(str)
		if not stderr_eof:
			str = cmd_stderr.read()
			if not str: stderr_eof = 1
			elif not g_quiet:
				sys.stderr.write('\n')
				sys.stderr.write(str)
		#time.sleep(0.1)

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
					debug("no more task to give")
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
		debug("debugging a task: something went wrong:")
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
				write_progress(progress_line(s, t, col1, proc, col2))

			# run the command
			ret = proc.m_action.run(proc)

			# non-zero means something went wrong
			if ret:
				error("task failed! (return code %s and task id %s)"%(str(ret), str(proc.m_idx)))
				proc.debug(1)
				return ret

			try:
				proc.update_stat()
			except:
				error('the nodes have not been produced !')
				raise
			proc.m_hasrun=1

			# register the task to the ones that have run - useful for debugging purposes
			Task.g_tasks_done.append(proc)	

			"""try:
				proc.apply()
			except KeyboardInterrupt:
				raise
			except:
				print "hum hum .. task failed!"
			"""

		debug("Serial end")
		return 0

import threading
import Queue


lock = None
condition = None
count = 0
stop = 0
running = 0


"""
#! /usr/bin/gnuplot -persist
set terminal png
set output "output.png"
set yrange [-1:6]
plot 'test.dat' using 1:3 with linespoints
"""
stat = []
class TaskPrinter(threading.Thread):
	def __init__(self, id, master):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.m_master = master
		self.start()

	def run(self):
		global count, lock, running, stat
		while 1:
			lock.acquire()
			stat.append( (time.time(), count, running) )
			lock.release()
			time.sleep(0.1)

class TaskConsumer(threading.Thread):
	def __init__(self, id, master):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.m_master = master
		self.m_id     = id
		self.start()

		self.m_count = 0
		self.m_stop  = 0

	def notify(self):
		global condition
		condition.acquire()
		condition.notify()
		condition.release()

	def do_stat(self, num):
		global running
		lock.acquire()
		running += num
		lock.release()

	def run(self):
		global lock, count, stop, running
		while 1:
			lock.acquire()
			self.m_stop  = stop
			lock.release()

			if self.m_stop:
				time.sleep(1)
				continue

			# take the next task
			proc = self.m_master.m_ready.get(block=1)

			self.do_stat(1)

			# display the label for the command executed
			write_progress(proc.m_str)

			# run the command
			ret = proc.m_action.run(proc)

			self.do_stat(-1)

			if ret:
				lock.acquire()
				error("task failed! (return code %s and task id %s)"%(str(ret), str(proc.m_idx)))
				proc.debug(1)
				count -= 1
				stop   = 1
				self.notify()
				lock.release()
				continue

			try:
				proc.update_stat()
			except:
				lock.acquire()
				error('the nodes have not been produced !')
				count -= 1
				stop = 1
				self.notify()
				lock.release()

			proc.m_hasrun = 1

			lock.acquire()
			count -= 1
			lock.release()
			self.notify()

# The following is a small scheduler, using an agressive scheme
# for making as many tasks available to the consumer threads
#
# Someone may come with a much better scheme, as i do not have too much
# time to spend on this (ita)
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
		self.m_stop         = 0

		# update the variables for the progress bar
		self.compute_total()

		global condition
		condition = threading.Condition()

		global lock
		lock = threading.Lock()

	def compute_total(self):
		self.m_total=0
		for htbl in self.m_tasks:
			for tasks in htbl.values():
				self.m_total += len(tasks)
	
	def read_values(self):
		#print "read values acquire lock"
		global lock, stop, count
		lock.acquire()
		self.m_stop  = stop
		self.m_count = count
		lock.release()
		#print "read values release lock"

	def wait_all_finished(self):
		global condition
		condition.acquire()
		while self.m_count>0:
			condition.wait()
			self.read_values()
		condition.release()

	def start(self):
		global count, lock, stop, condition, dostat

		# unleash the consumers
		for i in range(self.m_numjobs): TaskConsumer(i, self)

		if dostat: TaskPrinter(-1, self)

		# the current group
		group = None

		# current priority
		currentprio = 0

		loop=0

		# add the tasks to the queue
		while 1:
			self.read_values()
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
				condition.acquire()
				while self.m_count>0:
					condition.wait()
					self.read_values()
				condition.release()
			else:
				# wait a little bit if there are enough jobs for the consumer threads
				condition.acquire()
				while self.m_count>self.m_numjobs+10:
					condition.wait()
					self.read_values()
				condition.release()

			loop += 1

			if not self.m_outstanding:
				self.m_outstanding = self.m_frozen
				self.m_frozen = []

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
					
					if not self.m_outstanding:
						condition.acquire()
						condition.wait()
						condition.release()

				else:
					proc.prepare()
					if not proc.must_run():
						proc.m_hasrun=2
						continue

					# display the command that we are about to run
					col1=''
					col2=''
					try:
						col1=Params.g_colors[proc.m_action.m_name]
						col2=Params.g_colors['NORMAL']
					except: pass
					proc.m_str = progress_line(self.m_processed, self.m_total, col1, proc, col2)
					#proc.m_str = '[%d/%d] %s%s%s' % (self.m_processed, self.m_total, col1, proc.m_str, col2)

					lock.acquire()
					count += 1
					self.m_processed += 1
					lock.release()

					self.m_ready.put(proc, block=1)

		trace("amount of loops "+str(loop))
		global stat
		if dostat and stat:
			file = open('test.dat', 'w')
			(t1, queue, run) = stat[0]
			for (time, queue, run) in stat:
				file.write("%f %f %f\n" % (time-t1, queue, run))
			file.close()

