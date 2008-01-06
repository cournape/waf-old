#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Execute the tasks"

import sys, random, time, threading, Queue
import Params, Task, Utils, pproc
from Params import debug, error

g_quiet = 0
"do not output anything"

class CompilationError(Exception):
	pass

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
			elif not g_quiet:
				sys.stdout.write(s)
				sys.stdout.flush()
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
	if Params.g_verbose>=1: print s
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
	if Params.g_verbose>=1: print s
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
	def skip_group(self, reason):
		Task.g_tasks.groups[self.curgroup].info = reason
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
				tsk.m_hasrun=2
				#debug("task is up-to_date "+str(tsk.m_idx), 'runner')
				continue

			debug("executing  #"+str(tsk.m_idx), 'runner')

			# display the command that we are about to run
			if not g_quiet:
				(s, t) = self.generator.progress()
				col1=Params.g_colors[tsk.color()]
				col2=Params.g_colors['NORMAL']
				sys.stdout.write(progress_line(s, t, col1, tsk, col2))
				sys.stdout.flush()

			# run the command
			ret = tsk.run()

			# non-zero means something went wrong
			if ret:
				if Params.g_options.keep:
					self.generator.skip_group('non-zero return code\n' + tsk.debug_info())
					continue
				else:
					if Params.g_verbose:
						error("task failed! (return code %s for #%s)"%(str(ret), str(tsk.m_idx)))
						tsk.debug(1)
					return ret

			try:
				tsk.update_stat()
			except:
				if Params.g_options.keep:
					self.generator.skip_group('missing nodes\n' + tsk.debug_info())
					continue
				else:
					if Params.g_verbose: error('the nodes have not been produced !')
					raise CompilationError()
			tsk.m_hasrun=1

			# register the task to the ones that have run - useful for debugging purposes
			Task.g_tasks_done.append(tsk)

		debug("Serial end", 'runner')
		return 0

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
		lock = m.lock

		def end():
			m.count -= 1
			try: m.prod_turn.get(block=0)
			except: pass
			m.prod_turn.put(1)

		while 1:
			if m.stop:
				while 1:
					# force the scheduler to check for failure
					if m.failed > 0: m.count = 0
					time.sleep(1)

			# block here
			tsk = m.ready.get()

			if do_stat: do_stat(1)

			sys.stdout.write(tsk.get_display())
			sys.stdout.flush()
			try:
				ret = tsk.run()
			except:
				ret = -1

			if do_stat: do_stat(-1)

			if ret:
				lock.acquire()
				if Params.g_verbose:
					error("task failed! (return code %s and task id %s)"%(str(ret), str(tsk.m_idx)))
					tsk.debug(1)
				m.stop   = 1
				m.failed = 1
				end()
				lock.release()
				continue

			try:
				tsk.update_stat()
			except:
				lock.acquire()
				if Params.g_verbose: error('the nodes have not been produced !')
				m.stop   = 1
				m.failed = 1
				end()
				lock.release()
				continue

			tsk.m_hasrun = 1
			lock.acquire()
			end()
			lock.release()

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
		self.processed = 1

		# tasks waiting to be processed - IMPORTANT
		self.outstanding = []
		# tasks waiting to be run by the consumers
		self.ready = Queue.Queue(0)
		# tasks that are awaiting for another task to complete
		self.frozen = []
		# time to unblock the producer
		self.prod_turn = Queue.Queue(0)

		self.count = 0 # amount of active tasks
		self.stop = 0
		self.failed = 0
		self.running = 0

		self.curgroup = 0
		self.curprio = -1
		self.priolst = []

		self.lock = threading.Lock()

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

	def wait_all_finished(self):
		while self.count > 0: self.prod_turn.get()
		if self.failed:
			while 1:
				if self.running == 0: raise CompilationError()
				time.sleep(0.5)

	def start(self):

		for i in range(self.numjobs): TaskConsumer(i, self)

		# the current group
		#group = None

		currentprio = 0
		loop=0

		# add the tasks to the queue
		while 1:
			if self.stop:
				self.wait_all_finished()
				break

			# if there are no tasks to run, wait for the consumers to eat all of them
			# and then skip to the next priority group
			if not (self.frozen or self.outstanding):
				self.wait_all_finished()
				(currentprio, self.outstanding) = self.get_next_prio()
				if currentprio is None: break

			# for tasks that must run sequentially
			# (linking object files uses a lot of memory for example)
			if 1 == currentprio % 2:
				# make sure there is no more than one task in the queue
				if self.count > 0: self.prod_turn.get()
			else:
				# wait a little bit if there are enough jobs for the consumer threads
				while self.count > self.numjobs + 10: # FIXME why 10 once again ?
					self.prod_turn.get()

			loop += 1

			# no task to give, unfreeze the previous ones
			if not self.outstanding:
				self.outstanding = self.frozen
				self.frozen = []

			# now we are certain that there are outstanding or frozen threads
			if self.outstanding:
				tsk = self.outstanding.pop(0)
				if not tsk.may_start():
					if random.randint(0,1): self.frozen.append(tsk) #;print "shuf1"
					else: self.frozen = [tsk]+self.frozen #;print "shuf2"
					if not self.outstanding:
						# if all frozen, wait one to finish
						self.prod_turn.get()
				else:
					tsk.prepare()
					if not tsk.must_run():
						tsk.m_hasrun=2
						self.processed += 1
						continue

					# display the command that we are about to run
					cl = Params.g_colors
					tsk.set_display(progress_line(self.processed, self.total, cl[tsk.color()], tsk, cl['NORMAL']))

					self.lock.acquire()
					self.count += 1
					self.processed += 1
					self.lock.release()

					self.ready.put(tsk)

