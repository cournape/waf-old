#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Execute the tasks"

import sys, random, time, threading, Queue
import Params, Task, Utils, pproc
from Params import debug, error

g_quiet = 0
"do not output anything"

missing = 1
crashed = 2
skipped = 8
success = 9

class CompilationError(Exception):
	pass

def printout(s):
	sys.stdout.write(s); sys.stdout.flush()

def progress_line(state, total, col1, task, col2):
	"do not print anything if there is nothing to display"
	if Params.g_options.progress_bar == 1:
		return Utils.progress_line(state, total, col1, col2)

	if Params.g_options.progress_bar == 2:
		global g_initial
		eta = time.strftime('%H:%M:%S', time.gmtime(time.time() - g_initial))
		ins  = ','.join([n.m_name for n in task.m_inputs])
		outs = ','.join([n.m_name for n in task.m_outputs])
		return '|Total %s|Current %s|Inputs %s|Outputs %s|Time %s|\n' % (total, state, ins, outs, eta)

	n = len(str(total))
	fs = "[%%%dd/%%%dd] %%s%%s%%s\n" % (n, n)
	return fs % (state, total, col1, task.get_display(), col2)

def process_cmd_output(cmd_stdout, cmd_stderr):
	stdout_eof = stderr_eof = 0
	while not (stdout_eof and stderr_eof):
		if not stdout_eof:
			s = cmd_stdout.read()
			if not s: stdout_eof = 1
			elif not g_quiet: printout(s)
		if not stderr_eof:
			s = cmd_stderr.read()
			if not s: stderr_eof = 1
			elif not g_quiet:
				sys.stderr.write('\n')
				sys.stderr.write(s)
		#time.sleep(0.1)

def exec_command_normal(s):
	"run commands in a portable way the subprocess module backported from python 2.4 and should work on python >= 2.2"
	debug("system command -> "+ s, 'runner')
	if Params.g_verbose: print s
	# encase the command in double-quotes in windows
	if sys.platform == 'win32' and not s.startswith('""'):
		s = '"%s"' % s
	proc = pproc.Popen(s, shell=1, stdout=pproc.PIPE, stderr=pproc.PIPE)
	process_cmd_output(proc.stdout, proc.stderr)
	stat = proc.wait()
	if stat & 0xff: return stat | 0x80
	return stat >> 8

def exec_command_interact(s):
	"this one is for the latex output, where we cannot capture the output while the process waits for stdin"
	debug("system command (interact) -> "+ s, 'runner')
	if Params.g_verbose: print s
	# encase the command in double-quotes in windows
	if sys.platform == 'win32' and not s.startswith('""'):
		s = '"%s"' % s
	proc = pproc.Popen(s, shell=1)
	stat = proc.wait()
	if stat & 0xff: return stat | 0x80
	return stat >> 8

exec_command = exec_command_interact # python bug on stdout overload
def set_exec(mode):
	global exec_command
	if mode == 'normal': exec_command = exec_command_normal
	elif mode == 'noredir': exec_command = exec_command_interact
	else: error('set_runner_mode')

class JobGenerator(object):
	"kind of iterator - the data structure is a bit complicated (price to pay for flexibility)"
	def __init__(self):

		self.curgroup = 0
		self.curprio = -1
		self.outstanding = [] # list of tasks in the current priority

		self.priolst = []

		# progress bar
		self.total = Task.g_tasks.total()
		self.processed = 0

		self.switchflag = 1 # postpone
		#Task.g_tasks.debug()

	# warning, this one is recursive ..
	def get_next(self):
		if self.outstanding:
			t = self.outstanding.pop(0)
			self.processed += 1
			return t

		# handle case where only one wscript exist
		# that only install files
		if not Task.g_tasks.groups:
			return None

		# stop condition
		if self.curgroup >= len(Task.g_tasks.groups):
			return None

		# increase the priority value
		self.curprio += 1

		# there is no current list
		group = Task.g_tasks.groups[self.curgroup]
		if self.curprio >= len(group.prio.keys()):
			self.curprio = -1
			self.curgroup += 1
			return self.get_next()

		# sort keys if necessary
		if self.curprio == 0:
			self.priolst = group.prio.keys()
			self.priolst.sort()

		# now fill outstanding
		id = self.priolst[self.curprio]
		self.outstanding = group.prio[id]

		return self.get_next()

	def progress(self):
		return (self.processed, self.total)

	def postpone(self, task):
		self.processed -= 1
		# shuffle the list
		self.switchflag *= -1
		if self.switchflag>0: self.outstanding = [task]+self.outstanding
		else:                 self.outstanding.append(task)

	# TODO FIXME
	def debug(self):
		debug("debugging a task: something went wrong:", 'runner')
		s = " ".join([str(t.m_idx) for t in Task.g_tasks])
		debug(s, 'runner')

	# skip a group and report the failure
	def skip_group(self):
		self.curgroup += 1
		self.curprio = -1
		self.outstanding = []
		try: Task.g_tasks.groups[self.curgroup].prio.sort()
		except: pass

class Serial(object):
	def __init__(self, gen):
		self.generator = gen
	def start(self):
		global g_quiet
		debug("Serial start called", 'runner')
		#self.generator.debug()
		while 1:
			# get next Task
			tsk = self.generator.get_next()
			if tsk is None: break

			debug("retrieving #"+str(tsk.m_idx), 'runner')

			# # =======================
			#if tsk.m_hasrun:
			#	error("task has already run! "+str(tsk.m_idx))

			if not tsk.may_start():
				debug("delaying   #"+str(tsk.m_idx), 'runner')
				self.generator.postpone(tsk)
				#self.generator.debug()
				#tsk = None
				continue
			# # =======================

			tsk.prepare()
			#tsk.debug()

			#debug("m_sig is "+str(tsk.m_sig), 'runner')
			#debug("obj output m_sig is "+str(tsk.m_outputs[0].get_sig()), 'runner')

			#continue
			if not tsk.must_run():
				tsk.m_hasrun = skipped
				#debug("task is up-to_date "+str(tsk.m_idx), 'runner')
				continue

			debug("executing  #"+str(tsk.m_idx), 'runner')

			# display the command that we are about to run
			if not g_quiet:
				(s, t) = self.generator.progress()
				col1=Params.g_colors[tsk.color()]
				col2=Params.g_colors['NORMAL']
				printout(progress_line(s, t, col1, tsk, col2))

			# run the command
			ret = tsk.run()
			Task.g_tasks_done.append(tsk)

			# non-zero means something went wrong
			if ret:
				tsk.m_hasrun = crashed
				tsk.err_code = ret
				if Params.g_options.keep: continue
				else: raise CompilationError()

			try:
				tsk.update_stat()
				tsk.m_hasrun = success
			except:
				tsk.m_hasrun = missing
				if Params.g_options.keep: continue
				else: raise CompilationError()

class TaskConsumer(threading.Thread):
	def __init__(self, i, m):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.id     = i
		self.master = m
		self.start()

	def run(self):
		do_stat = getattr(self, 'do_stat', None)
		m = self.master

		while 1:
			tsk = m.ready.get()
			if m.failed and not m.running:
				m.out.put(tsk)
				continue

			if do_stat: do_stat(1)

			printout(tsk.get_display())
			try: ret = tsk.run()
			except: ret = -1

			if do_stat: do_stat(-1)

			if ret:
				tsk.err_code = ret
				tsk.m_hasrun = crashed
			else:
				try:
					tsk.update_stat()
					tsk.m_hasrun = success
				except:
					tsk.m_hasrun = missing
			if tsk.m_hasrun != success and not Params.g_options.keep:
				m.failed = 1

			m.out.put(tsk)

class Parallel(object):
	"""
	The following is a small scheduler for making as many tasks available to the consumer threads
	It uses the serial shuffling system
	"""
	def __init__(self, j=2):

		# number of consumers
		self.numjobs = j

		# progress bar
		self.total = Task.g_tasks.total()
		self.processed = 0

		# tasks waiting to be processed - IMPORTANT
		self.outstanding = []
		# tasks that are awaiting for another task to complete
		self.frozen = []

		# tasks waiting to be run by the consumers
		self.ready = Queue.Queue(0)
		self.out = Queue.Queue(0)

		self.count = 0 # tasks not in the producer area
		self.failed = 0 # some task has failed
		self.running = 0 # keep running ?
		self.progress = 0 # progress indicator

		self.curgroup = 0
		self.curprio = -1
		self.priolst = []

		# for consistency
		self.generator = self

	def get_next_prio(self):
		# stop condition
		if self.curgroup >= len(Task.g_tasks.groups):
			return (None, None)

		# increase the priority value
		self.curprio += 1

		# there is no current list
		group = Task.g_tasks.groups[self.curgroup]
		if self.curprio >= len(group.prio.keys()):
			self.curprio = -1
			self.curgroup += 1
			return self.get_next_prio()

		# sort keys if necessary
		if self.curprio == 0:
			self.priolst = group.prio.keys()
			self.priolst.sort()

		id = self.priolst[self.curprio]
		return (id, group.prio[id])

	def start(self):
		for i in range(self.numjobs): TaskConsumer(i, self)

		# the current group
		#group = None

		def get_out():
			Task.g_tasks_done.append(self.out.get())
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
				if self.failed:
					raise CompilationError()

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
				(currentprio, self.outstanding) = self.get_next_prio()
				#if self.outstanding: random.shuffle(self.outstanding)
				if currentprio is None: break

			# consider the next task
			tsk = self.outstanding.pop(0)
			if tsk.may_start():
				tsk.prepare()
				self.progress += 1
				if not tsk.must_run():
					tsk.m_hasrun = skipped
					continue
				cl = Params.g_colors
				tsk.set_display(progress_line(self.progress, self.total, cl[tsk.color()], tsk, cl['NORMAL']))
				self.count += 1
				self.ready.put(tsk)
			else:
				if random.randint(0,1): self.frozen.insert(0, tsk)
				else: self.frozen.append(tsk)
		#print loop

