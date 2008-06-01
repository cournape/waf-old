#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Execute the tasks"

import sys, random, time, threading, Queue, traceback
import Params, Utils
import pproc as subprocess
from Params import debug, error
from Constants import *

g_quiet = 0
"do not output anything"

log_file = None
"output to a config.log file, see Configure.py {mute,restore}_logging"

def print_log(msg, nl='\n'):
	if log_file:
		log_file.write(msg)
		log_file.write(nl)
		log_file.flush()

def printout(s):
	if not g_quiet:
		sys.stdout.write(s)
		sys.stdout.flush()
	print_log(s, nl='')

def progress_line(state, total, col1, task, col2):
	"do not print anything if there is nothing to display"
	if Params.g_options.progress_bar == 1:
		return Utils.progress_line(state, total, col1, col2)

	if Params.g_options.progress_bar == 2:
		try: ini = Params.g_build.ini
		except AttributeError: ini = Params.g_build.ini = time.time()
		ela = time.strftime('%H:%M:%S', time.gmtime(time.time() - ini))
		ins  = ','.join([n.m_name for n in task.m_inputs])
		outs = ','.join([n.m_name for n in task.m_outputs])
		return '|Total %s|Current %s|Inputs %s|Outputs %s|Time %s|\n' % (total, state, ins, outs, ela)

	n = len(str(total))
	fs = '[%%%dd/%%%dd] %%s%%s%%s' % (n, n)
	return fs % (state, total, col1, task.get_display(), col2)

def process_cmd_output(proc):
	"""calling communicate to avoid race-condition between stdout and stderr"""
	(cmd_stdout, cmd_stderr) = proc.communicate()
	if cmd_stdout:
		printout(cmd_stdout)
	if cmd_stderr:
		if g_quiet:
			printout(cmd_stderr)
		else:
			sys.stderr.write(cmd_stderr)
			sys.stderr.flush()

def _exec_command_normal(s):
	"run commands in a portable way the subprocess module backported from python 2.4 and should work on python >= 2.2"
	debug("system command -> "+ s, 'runner')
	if Params.g_verbose or g_quiet: printout(s+'\n')
	# encase the command in double-quotes in windows
	if sys.platform == 'win32' and not s.startswith('""'):
		s = '"%s"' % s
	proc = subprocess.Popen(s, shell=1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	process_cmd_output(proc)
	stat = proc.wait()
	if stat & 0xff: return stat | 0x80
	return stat >> 8

def _exec_command_interact(s):
	"this one is for the latex output, where we cannot capture the output while the process waits for stdin"
	debug("system command (interact) -> "+ s, 'runner')
	if Params.g_verbose or g_quiet: printout(s+'\n')
	# encase the command in double-quotes in windows
	if sys.platform == 'win32' and not s.startswith('""'):
		s = '"%s"' % s
	proc = subprocess.Popen(s, shell=1)
	stat = proc.wait()
	if stat & 0xff: return stat | 0x80
	return stat >> 8

exec_command = _exec_command_interact # python bug on stdout overload
def set_exec(mode):
	global exec_command
	if mode == 'normal': exec_command = _exec_command_normal
	elif mode == 'noredir': exec_command = _exec_command_interact
	else: error('set_runner_mode')

class Serial(object):
	def __init__(self, bld):
		self.error = 0

		self.manager = bld.task_manager

		self.outstanding = []

		self.priolst = []

		# progress bar
		self.total = self.manager.total()
		self.processed = 0

		self.switchflag = 1 # postpone
		# self.manager.debug()

	# warning, this one is recursive ..
	def get_next(self):
		if self.outstanding:
			t = self.outstanding.pop(0)
			self.processed += 1
			return t

		# handle case where only one wscript exist
		# that only install files
		if not self.manager.groups:
			return None

		(_, self.outstanding) = self.manager.get_next_set()
		if not self.outstanding: return None

		if Params.g_verbose:
			debug("Preparing to run prio %i tasks: [\n%s\n\t]" %
			      (1, ',\n'.join(["\t#%i: %s" % (tsk.m_idx, repr(tsk).strip())
					       for tsk in self.outstanding])),
			      'runner')
		return self.get_next()

	def progress(self):
		return (self.processed, self.total)

	def postpone(self, tsk):
		self.processed -= 1
		# shuffle the list - why it does work is left as an exercise for the reader
		self.switchflag *= -1
		if self.switchflag>0: self.outstanding.insert(0, tsk)
		else:                 self.outstanding.append(tsk)

	# TODO FIXME
	def debug(self):
		debug("debugging a task: something went wrong:", 'runner')
		s = " ".join([str(t.m_idx) for t in self.manager])
		debug(s, 'runner')

	# skip a group and report the failure
	def skip_group(self):
		self.outstanding = []

	def start(self):
		global g_quiet
		debug("Serial start called", 'runner')
		#self.debug()
		while 1:
			# get next Task
			tsk = self.get_next()
			if tsk is None: break

			debug("retrieving #%i (%r)" % (tsk.m_idx, tsk), 'runner')

			# # =======================
			#if tsk.m_hasrun:
			#	error("task has already run! "+str(tsk.m_idx))

			if not tsk.may_start():
				debug("delaying   #"+str(tsk.m_idx), 'runner')
				self.postpone(tsk)
				#self.debug()
				#tsk = None
				continue
			# # =======================

			tsk.prepare()
			#tsk.debug()

			#debug("m_sig is "+str(tsk.m_sig), 'runner')
			#debug("obj output m_sig is "+str(tsk.m_outputs[0].get_sig()), 'runner')

			#continue
			if not tsk.must_run():
				tsk.m_hasrun = SKIPPED
				self.manager.add_finished(tsk)
				#debug("task is up-to_date "+str(tsk.m_idx), 'runner')
				continue

			debug("executing  #"+str(tsk.m_idx), 'runner')

			# display the command that we are about to run
			if not g_quiet:
				(s, t) = self.progress()
				cl = Params.g_colors
				printout(progress_line(s, t, cl[tsk.color()], tsk, cl['NORMAL']))

			# run the command
			ret = tsk.run()
			self.manager.add_finished(tsk)

			# non-zero means something went wrong
			if ret:
				self.error = 1
				tsk.m_hasrun = CRASHED
				tsk.err_code = ret
				if Params.g_options.keep: continue
				else: return -1

			try:
				tsk.update_stat()
			except OSError:
				traceback.print_stack()
				self.error = 1
				tsk.m_hasrun = MISSING
				if Params.g_options.keep: continue
				else: return -1
			else:
				tsk.m_hasrun = SUCCESS

		if self.error:
			return -1

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

			printout(tsk.get_display())
			ret = tsk.run()

			if ret:
				tsk.err_code = ret
				tsk.m_hasrun = CRASHED
			else:
				try:
					tsk.update_stat()
				except OSError:
					tsk.m_hasrun = MISSING
				else:
					tsk.m_hasrun = SUCCESS
			if tsk.m_hasrun != SUCCESS: # TODO for now, do no keep running in parallel  and not Params.g_options.keep:
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

		# progress bar
		self.total = self.manager.total()
		self.processed = 0

		# tasks waiting to be processed - IMPORTANT
		self.outstanding = []
		self.maxjobs = 100

		# tasks that are awaiting for another task to complete
		self.frozen = []

		# tasks waiting to be run by the consumers
		self.ready = Queue.Queue(0)
		self.out = Queue.Queue(0)

		self.count = 0 # tasks not in the producer area
		self.failed = 0 # some task has failed
		self.running = 0 # keep running ?
		self.progress = 0 # progress indicator

	def start(self):
		for i in range(self.numjobs): TaskConsumer(i, self)

		# the current group
		#group = None

		def get_out():
			self.manager.add_finished(self.out.get())
			self.count -= 1

		lastfailput = 0

		# iterate over all tasks at most one time for each task run
		penalty = 0
		currentprio = 0
		#loop=0
		while 1:
			#loop += 1
			if self.failed and not self.running:
				while self.count > 0: get_out()
				if self.failed: return -1

			if 1 == currentprio % 2:
				# allow only one process at a time in priority 'even'
				while self.count > 0: get_out()
			else:
				# not too many jobs in the queue
				while self.count > self.numjobs + 10: get_out()

			# empty the returned tasks as much as possible
			while not self.out.empty(): get_out()

			if not self.outstanding:
				if self.count > 0: get_out()
				self.outstanding = self.frozen
				self.frozen = []
			if not self.outstanding:
				while self.count > 0: get_out()
				(currentprio, self.outstanding) = self.manager.get_next_set()
				#if self.outstanding: random.shuffle(self.outstanding)
				if currentprio is None: break

			# consider the next task
			tsk = self.outstanding.pop(0)
			if tsk.may_start():
				tsk.prepare()
				self.progress += 1
				if not tsk.must_run():
					tsk.m_hasrun = SKIPPED
					self.manager.add_finished(tsk)
					continue
				cl = Params.g_colors
				tsk.set_display(progress_line(self.progress, self.total, cl[tsk.color()], tsk, cl['NORMAL']))
				self.count += 1
				self.ready.put(tsk)
			else:
				if random.randint(0,1): self.frozen.insert(0, tsk)
				else: self.frozen.append(tsk)
		#print loop

def get_instance(bld, njobs):
	if njobs <= 1: executor = Serial(bld)
	else: executor = Parallel(bld, njobs)
	return executor

