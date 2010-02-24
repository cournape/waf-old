#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2007-2010 (ita)

"""
debugging helpers for parallel compilation

To output a stat file (data for gnuplot) when running tasks in parallel:

set terminal X11
set ylabel "Amount of jobs running in parallel"
set xlabel "Time in seconds"
set title "Amount of jobs running in parallel (waf -j5)"
unset label
set yrange [-0.1:5.2]
set ytic 1
plot 'test.dat' using 1:3 with lines title "" lt 3
"""

import time, threading
import Runner
from Runner import TaskConsumer
from Constants import *

INTERVAL = 0.05

mylock = threading.Lock()
state = 0
def set_running(by):
	mylock.acquire()
	global state
	state += by
	mylock.release()

def newrun(self):
	if 1 == 1:
		while 1:
			tsk = TaskConsumer.ready.get()
			set_running(1)
			m = tsk.master
			if m.stop:
				m.out.put(tsk)
				continue

			try:
				tsk.generator.bld.printout(tsk.display())
				if tsk.__class__.stat: ret = tsk.__class__.stat(tsk)
				# actual call to task's run() function
				else: ret = tsk.call_run()
			except Exception, e:
				tsk.err_msg = Utils.ex_stack()
				tsk.hasrun = EXCEPTION

				m.error_handler(tsk)
				m.out.put(tsk)
				continue

			if ret:
				tsk.err_code = ret
				tsk.hasrun = CRASHED
			else:
				try:
					tsk.post_run()
				except Utils.WafError:
					pass
				except Exception:
					tsk.err_msg = Utils.ex_stack()
					tsk.hasrun = EXCEPTION
				else:
					tsk.hasrun = SUCCESS
			if tsk.hasrun != SUCCESS:
				m.error_handler(tsk)

			m.out.put(tsk)
			set_running(-1)

Runner.TaskConsumer.run = newrun

class TaskPrinter(threading.Thread):
	def __init__(self, master):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.m_master = master
		self.stat = []
		self.start()

	def run(self):
		global state
		while self.m_master:
			try:
				self.stat.append( (time.time(), self.m_master.processed, state, self.m_master.count) )
				#self.stat.append( (time.time(), self.m_master.processed, self.m_master.ready.qsize()) )
			except:
				raise
				pass

			try: time.sleep(INTERVAL)
			except: pass

		while 1:
			try:
				time.sleep(60)
			except:
				pass

old_start = Runner.Parallel.start
def do_start(self):
	collector = TaskPrinter(self)
	old_start(self)
	collector.m_master = None

	if len(collector.stat) <= 0:
		print "nothing to display! start from an empty build"
	else:
		file = open('/tmp/test.dat', 'w')
		(t1, queue, run, count) = collector.stat[0]
		for (time, queue, run, count) in collector.stat:
			#print time, t1, queue, run
			file.write("%f %f %f %f\n" % (time-t1, queue, run, count))
		file.close()
Runner.Parallel.start = do_start


