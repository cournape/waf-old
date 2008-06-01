#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2007 (ita)

"""
debugging helpers for parallel compilation

To output a stat file (data for gnuplot) when running tasks in parallel:

#! /usr/bin/gnuplot -persist
set terminal png
set output "output.png"
set yrange [-1:6]
plot 'test.dat' using 1:3 with linespoints
"""

import time, threading
import Runner
from Constants import *

INTERVAL = 0.01


mylock = threading.Lock()
state = 0
def set_running(by):
	mylock.acquire()
	global state
	state += by
	mylock.release()

def newrun(self):
	m = self.master

	while 1:
		tsk = m.ready.get()
		if m.failed and not m.running:
			m.out.put(tsk)
			continue

		set_running(1)
		Runner.printout(tsk.get_display())
		ret = tsk.run()
		set_running(-1)

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
		#set_running(-1)

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
				#self.stat.append( (time.time(), self.m_master.progress, state) )
				self.stat.append( (time.time(), self.m_master.progress, self.m_master.ready.qsize()) )
			except:
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
		(t1, queue, run) = collector.stat[0]
		for (time, queue, run) in collector.stat:
			#print time, t1, queue, run
			file.write("%f %f %f\n" % (time-t1, queue, run))
		file.close()
Runner.Parallel.start = do_start


