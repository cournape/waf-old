#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Execute the tasks"

import sys, random, time, threading, Queue, traceback
import Build, Utils, Logs, Options
import pproc
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
	proc = pproc.Popen(s, shell=shell, stdout=log, stderr=log)
	return proc.wait()

if sys.platform == "win32":
	old_log = exec_command
	def exec_command(s, shell=1):
		# TODO very long command-lines are unlikely to be used in the configuration
		if len(s) < 2000: return old_log(s, shell=shell)

		log = Build.bld.log
		if log or Logs.verbose: printout(s+'\n')
		startupinfo = pproc.STARTUPINFO()
		startupinfo.dwFlags |= pproc.STARTF_USESHOWWINDOW
		proc = pproc.Popen(s, shell=False, startupinfo=startupinfo)
		return proc.wait()

class TaskConsumer(threading.Thread):
	def __init__(self, m):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.master = m
		self.start()

	def run(self):
		m = self.master

		while 1:
			tsk = m.ready.get()
			if m.stop:
				m.out.put(tsk)
				continue

			try:
				printout(tsk.display())
				if tsk.__class__.stat: ret = tsk.__class__.stat(tsk)
				else: ret = tsk.run()
			except Exception, e:
				# TODO add the stack error message
				tsk.err_msg = e.message
				tsk.hasrun = EXCEPTION

				# TODO cleanup
				m.error_handler(tsk)
				m.out.put(tsk)
				continue

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
			if tsk.hasrun != SUCCESS:
				m.error_handler(tsk)

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
		self.processed = 0 # progress indicator

		self.consumers = None # the consumer threads, created lazily

		self.stop = False # error condition to stop the build
		self.error = False # error flag

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
		# TODO review for busy loop problems
		if self.count > 0: self.get_out()
		self.outstanding = self.frozen
		self.frozen = []
		if not self.outstanding:
			# avoid the busy loop
			while self.count > 0: self.get_out()
			(self.maxjobs, self.outstanding) = self.manager.get_next_set()

	def get_out(self):
		"the tasks that are put to execute are all collected using get_out"
		self.manager.add_finished(self.out.get())
		self.count -= 1

	def error_handler(self, tsk):
		"by default, errors make the build stop (not thread safe so be careful)"
		if not Options.options.keep:
			self.stop = True
		self.error = True

	def start(self):
		"execute the tasks"

		while not self.stop:

			# optional limit on the amount of jobs to run at the same time
			# for example, link tasks are run one by one
			while self.count >= self.maxjobs:
				self.get_out()

			if not self.outstanding:
				self.refill_task_list()
				if self.maxjobs is None:
					break

			# consider the next task
			tsk = self.get_next()
			if tsk.hasrun:
				# if the task is marked as "run" already, we just skip it
				self.processed += 1
				self.manager.add_finished(tsk)

			try:
				st = tsk.runnable_status()
			except Exception, e:
				tsk.err_msg = "TODO print the exception here"
				tsk.hasrun = EXCEPTION
				self.error_handler(tsk)

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
					self.consumers = [TaskConsumer(self) for i in xrange(self.numjobs)]

		#print loop
		while self.count:
			self.get_out()

