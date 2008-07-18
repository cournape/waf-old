#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Execute the tasks"

import sys, random, time, threading, Queue, traceback
import Build, Utils, Logs, Options
import pproc as subprocess
from Logs import debug, error
from Constants import *

g_quiet = 0
"do not output anything"

def print_log(msg, nl='\n'):
	f = Build.bld.log
	if f:
		f.write(msg)
		f.write(nl)
		f.flush()

def printout(s):
	if not Build.bld.log:
		sys.stdout.write(s)
		sys.stdout.flush()
	print_log(s, nl='')

def exec_command(s, shell=1):
	debug('runner: system command -> %s' % s)
	log = Build.bld.log
	if log or Logs.verbose: printout(s+'\n')
	proc = subprocess.Popen(s, shell=shell, stdout=log, stderr=log)
	return proc.wait()

if sys.platform == "win32":
	old_log = exec_command
	def exec_command(s, shell=1):
		# TODO very long command-lines are unlikely to be used in the configuration
		if len(s) < 2000: return old_log(s, shell=shell)

		log = Build.bld.log
		if log or Logs.verbose: printout(s+'\n')
		startupinfo = subprocess.STARTUPINFO()
		startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
		proc = subprocess.Popen(s, shell=False, startupinfo=startupinfo)
		return proc.wait()

class TaskConsumer(threading.Thread):
	def __init__(self, i, m):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.id     = i
		self.master = m
		self.start()

	def run(self):
		m = self.master

		while 1:
			tsk = m.ready.get()
			if m.failed and not m.running:
				m.out.put(tsk)
				continue

			try:
				printout(tsk.display())
				if tsk.__class__.stat: ret = tsk.__class__.stat(tsk)
				else: ret = tsk.run()
			except Exception, e:
				tsk.err_msg = "TODO print the exception here"
				#exc_type, exc_value, tb = sys.exc_info()
				#traceback.print_exception(exc_type, exc_value, tb)
				ret = tsk.hasrun = EXCEPTION

			if ret:
				tsk.err_code = ret
				tsk.hasrun = CRASHED
			else:
				try:
					tsk.post_run()
				except OSError:
					tsk.hasrun = MISSING
				else:
					tsk.hasrun = SUCCESS
			if tsk.hasrun != SUCCESS: # TODO for now, do no keep running in parallel  and not Options.options.keep:
				m.failed = 1

			m.out.put(tsk)

class Parallel(object):
	"""
	The following is a small scheduler for making as many tasks available to the consumer threads
	It uses the serial shuffling system
	"""
	def __init__(self, bld, j=2):

		# number of consumers
		self.numjobs = j

		self.manager = bld.task_manager

		self.total = self.manager.total()

		# tasks waiting to be processed - IMPORTANT
		self.outstanding = []
		self.maxjobs = sys.maxint

		# tasks that are awaiting for another task to complete
		self.frozen = []

		# tasks waiting to be run by the consumers
		self.ready = Queue.Queue(0)
		self.out = Queue.Queue(0)

		self.count = 0 # tasks not in the producer area
		self.failed = 0 # some task has failed
		self.running = 0 # keep running ?
		self.processed = 0 # progress indicator

		self.consumers = None

	def get_next(self):
		"override this method to schedule the tasks in a particular order"
		return self.outstanding.pop(0)

	def postpone(self, tsk):
		"override this method to schedule the tasks in a particular order"
		# TODO consider using a deque instead
		if random.randint(0,1):
			self.frozen.insert(0, tsk)
		else:
			self.frozen.append(tsk)

	def refill_task_list(self):
		"called to set the next group of tasks"
		if self.count > 0: self.get_out()
		self.outstanding = self.frozen
		self.frozen = []
		if not self.outstanding:
			while self.count > 0: self.get_out()
			(self.maxjobs, self.outstanding) = self.manager.get_next_set()

	def get_out(self):
		"the tasks that are put to execute are all collected using get_out"
		self.manager.add_finished(self.out.get())
		self.count -= 1

	def start(self):
		#loop=0
		while 1:
			#loop += 1
			if self.failed and not self.running:
				while self.count > 0:
					self.get_out()
				if self.failed:
					return -1

			# optional limit on the amount of jobs to run at the same time
			# for example, link tasks are run one by one
			while self.count >= self.maxjobs:
				self.get_out()

			# empty the returned tasks as much as possible
			#while not self.out.empty(): self.get_out()

			if not self.outstanding:
				self.refill_task_list()
				if self.maxjobs is None:
					break

			# consider the next task
			tsk = self.get_next()

			try:
				st = tsk.runnable_status()
			except Exception, e:
				tsk.err_msg = "TODO print the exception here"
				tsk.hasrun = EXCEPTION
				self.failed = 1

			if st == ASK_LATER:
				self.postpone(tsk)
			elif st == SKIP_ME:
				self.processed += 1
				tsk.hasrun = SKIPPED
				self.manager.add_finished(tsk)
			else:
				tsk.position = (self.processed, self.total)
				self.count += 1
				self.ready.put(tsk)
				self.processed += 1

				# create the consumer threads only if there is something to consume
				if not self.consumers:
					self.consumers = [TaskConsumer(i, self) for i in range(self.numjobs)]

		#print loop
		while self.count:
			self.get_out()

