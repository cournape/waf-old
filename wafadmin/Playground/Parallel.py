#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2007 (ita)

# debugging helpers for parallel compilation
dostat=0
"""
output a stat file (data for gnuplot) when running tasks in parallel

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

	def do_stat(self, num):
		global running
		lock.acquire()
		running += num
		lock.release()

	def start(self):
		if dostat: TaskPrinter(-1, self)

		# Runner.py code here

		# in parallel mode, what matters is the amount of misses: trying to launch tasks that cannot be run yet
		# there are two schemes to reduce that latency
		# * separate the tasks in independant groups that can be parallelized (often the case)
		# * use a heuristic to take the next task from the list of awaiting tasks
		debug("amount of loops "+str(loop), 'runner')
		global stat
		if dostat and stat:
			file = open('test.dat', 'w')
			(t1, queue, run) = stat[0]
			for (time, queue, run) in stat:
				file.write("%f %f %f\n" % (time-t1, queue, run))
			file.close()

