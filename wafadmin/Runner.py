#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"Execute the tasks"

import os, sys, random, threading
try:
	from queue import Queue
except:
	from Queue import Queue
import Utils, Logs, Options, Task, Base

GAP = 15
MAXJOBS = 999

run_old = threading.Thread.run
def run(*args, **kwargs):
	try:
		run_old(*args, **kwargs)
	except (KeyboardInterrupt, SystemExit):
		raise
	except:
		sys.excepthook(*sys.exc_info())
threading.Thread.run = run

def compare_exts(t1, t2):
	"extension production"
	x = "ext_in"
	y = "ext_out"
	in_ = t1.attr(x, ())
	out_ = t2.attr(y, ())
	for k in in_:
		if k in out_:
			return -1
	in_ = t2.attr(x, ())
	out_ = t1.attr(y, ())
	for k in in_:
		if k in out_:
			return 1
	return 0

def compare_partial(t1, t2):
	"partial relations after/before"
	m = "after"
	n = "before"
	name = t2.__class__.__name__
	if name in Utils.to_list(t1.attr(m, ())): return -1
	elif name in Utils.to_list(t1.attr(n, ())): return 1
	name = t1.__class__.__name__
	if name in Utils.to_list(t2.attr(m, ())): return 1
	elif name in Utils.to_list(t2.attr(n, ())): return -1
	return 0

def set_file_constraints(tasks):
	"will set the run_after constraints on all tasks (may cause a slowdown with lots of tasks)"
	ins = {}
	outs = {}
	for x in tasks:
		for a in getattr(x, 'inputs', []):
			try:
				ins[id(a)].append(x)
			except KeyError:
				ins[id(a)] = [x]
		for a in getattr(x, 'outputs', []):
			try:
				outs[id(a)].append(x)
			except KeyError:
				outs[id(a)] = [x]

	links = set(ins.keys()).intersection(outs.keys())
	for k in links:
		for a in ins[k]:
			for b in outs[k]:
				a.set_run_after(b)

class TaskConsumer(threading.Thread):
	ready = Queue(0)
	consumers = []

	def __init__(self):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.start()

	def run(self):
		try:
			self.loop()
		except:
			pass

	def loop(self):
		while 1:
			tsk = TaskConsumer.ready.get()
			process_task(tsk)

def process_task(tsk):
	m = tsk.master
	if m.stop:
		m.out.put(tsk)
		return

	try:
		tsk.generator.bld.printout(tsk.display())
		if tsk.__class__.stat: ret = tsk.__class__.stat(tsk)
		# actual call to task's run() function
		else: ret = tsk.call_run()
	except Exception as e:
		tsk.err_msg = Utils.ex_stack()
		tsk.hasrun = Task.EXCEPTION

		# TODO cleanup
		m.error_handler(tsk)
		m.out.put(tsk)
		return

	if ret:
		tsk.err_code = ret
		tsk.hasrun = Task.CRASHED
	else:
		try:
			tsk.post_run()
		except Base.WafError:
			pass
		except Exception:
			tsk.err_msg = Utils.ex_stack()
			tsk.hasrun = Task.EXCEPTION
		else:
			tsk.hasrun = Task.SUCCESS
	if tsk.hasrun != Task.SUCCESS:
		m.error_handler(tsk)

	m.out.put(tsk)

class Parallel(object):
	"""
	keep the consumer threads busy, and avoid consuming cpu cycles
	when no more tasks can be added (end of the build, etc)
	"""
	def __init__(self, bld):

		# number of consumers
		self.numjobs = Options.options.jobs

		self.bld = bld # build context

		self.total = self.bld.total()

		# tasks waiting to be processed - IMPORTANT
		self.outstanding = []
		self.maxjobs = MAXJOBS

		# tasks that are awaiting for another task to complete
		self.frozen = []

		# tasks waiting to be run by the consumers
		self.out = Queue(0)

		self.count = 0 # tasks not in the producer area

		self.processed = 1 # progress indicator

		self.stop = False # error condition to stop the build
		self.error = False # error flag

	def get_next_task(self):
		"override this method to schedule the tasks in a particular order"
		if not self.outstanding:
			return None
		return self.outstanding.pop(0)

	def postpone(self, tsk):
		"override this method to schedule the tasks in a particular order"
		# TODO consider using a deque instead
		if random.randint(0, 1):
			self.frozen.insert(0, tsk)
		else:
			self.frozen.append(tsk)

	def refill_task_list(self):
		"called to set the next group of tasks"

		while self.count > self.numjobs + GAP or self.count >= self.maxjobs:
			self.get_out()

		while not self.outstanding:
			if self.count:
				self.get_out()

			if self.frozen:
				self.outstanding += self.frozen
				self.frozen = []
			elif not self.count:
				self.outstanding += self.get_next_set()
				break

	def get_out(self):
		"the tasks that are put to execute are all collected using get_out"
		ret = self.out.get()
		self.bld.add_finished(ret)
		if not self.stop and getattr(ret, 'more_tasks', None):
			self.outstanding += ret.more_tasks
			self.total += len(ret.more_tasks)
		self.count -= 1

	def error_handler(self, tsk):
		"by default, errors make the build stop (not thread safe so be careful)"
		if not Options.options.keep:
			self.stop = True
		self.error = True

	def start(self):
		"execute the tasks"
		self.cur = 0
		self.iter_cache = {}

		while not self.stop:

			self.refill_task_list()

			# consider the next task
			tsk = self.get_next_task()
			if not tsk:
				if self.count:
					# tasks may add new ones after they are run
					continue
				else:
					# no tasks to run, no tasks running, time to exit
					break

			if tsk.hasrun:
				# if the task is marked as "run", just skip it
				self.processed += 1
				self.bld.add_finished(tsk)
				continue

			try:
				st = tsk.runnable_status()
			except Exception as e:
				tsk.err_msg = Utils.ex_stack()
				tsk.hasrun = Task.EXCEPTION
				self.processed += 1
				self.error_handler(tsk)
				self.bld.add_finished(tsk)
				continue

			if st == Task.ASK_LATER:
				self.postpone(tsk)
			elif st == Task.SKIP_ME:
				self.processed += 1
				tsk.hasrun = Task.SKIPPED
				self.bld.add_finished(tsk)
			else:
				# run me: put the task in ready queue
				tsk.position = (self.processed, self.total)
				self.count += 1
				tsk.master = self
				self.processed += 1

				if self.numjobs == 1:
					process_task(tsk)
				else:
					TaskConsumer.ready.put(tsk)
					# create the consumer threads only if there is something to consume
					if not TaskConsumer.consumers:
						TaskConsumer.consumers = [TaskConsumer() for i in xrange(self.numjobs)]


		# self.count represents the tasks that have been made available to the consumer threads
		# collect all the tasks after an error else the message may be incomplete
		while self.error and self.count:
			self.get_out()

		#print loop
		assert (self.count == 0 or self.stop)

	def get_next_set(self):
		"""return the next set of tasks to execute"""

		while self.cur < len(self.bld.groups):
			if not self.cur in self.iter_cache:
				self.iter_cache[self.cur] = self.sorted_tasks(self.cur)

			try:
				ret = self.iter_cache[self.cur].next()
			except StopIteration:
				self.cur += 1
		return []

	def sorted_tasks(self, idg):
		tasks = []
		for tg in self.bld.groups[idg]:
			# TODO a try-except might be more efficient
			if isinstance(tg, Task.TaskBase):
				tasks.append(tg)
			else:
				tasks.extend(tg.tasks)

		# if the constraints are set properly (ext_in/ext_out, before/after)
		# the method set_file_constraints is not necessary (can be 15% penalty on no-op rebuilds)
		#
		# the constraint extraction thing is splitting the tasks by groups of independent tasks that may be parallelized
		# this is slightly redundant with the task manager groups
		#
		# if the tasks have only files, set_file_constraints is required but extract_constraints is not necessary
		#
		set_file_constraints(tasks)

		# use the after/before + ext_out/ext_in to perform a topological sort
		cstr_groups = Utils.defaultdict(list)
		cstr_order = Utils.defaultdict(set)
		for x in tasks:
			h = x.hash_constraints()
			cstr_groups[h].append(x)

		keys = list(cstr_groups.keys())
		maxi = len(keys)

		# this list should be short
		for i in range(maxi):
			t1 = cstr_groups[keys[i]][0]
			for j in range(i + 1, maxi):
				t2 = cstr_groups[keys[j]][0]

				# add the constraints based on the comparisons
				val = (compare_exts(t1, t2) or compare_partial(t1, t2))
				if val > 0:
					cstr_order[keys[i]].add(keys[j])
				elif val < 0:
					cstr_order[keys[j]].add(keys[i])

		while 1:
			unconnected = []
			remainder = []

			for u in keys:
				for k in cstr_order.values():
					if u in k:
						remainder.append(u)
						break
				else:
					unconnected.append(u)

			toreturn = []
			for y in unconnected:
				toreturn.extend(cstr_groups[y])

			# remove stuff only after
			for y in unconnected:
				try: cstr_order.__delitem__(y)
				except KeyError: pass
				cstr_groups.__delitem__(y)

			if not toreturn:
				if remainder:
					raise Base.WafError("Circular order constraint detected %r" % remainder)
				raise StopIteration

			yield toreturn

