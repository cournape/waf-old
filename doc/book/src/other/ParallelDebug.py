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

import time, threading, random, Queue
import Runner
from Constants import *

INTERVAL = 0.009
BAND = 22

mp = {
'cxx': 'green',
'ar_link_static': '#8106ff'
}

info = {
'green': 'Compilation task',
'#8106ff': 'Link task'
}

def map_to_color(name):
	if name in mp:
		return mp[name]
	return "red"


mylock = threading.Lock()
taskinfo = Queue.Queue()
state = 0
def set_running(by, i, tsk):
	mylock.acquire()
	global state
	state += by
	mylock.release()
	taskinfo.put(  (i, id(tsk), time.time(), tsk.__class__.__name__)  )


def newrun(self):
	m = self.master

	while 1:
		tsk = m.ready.get()
		if m.stop:
			m.out.put(tsk)
			continue

		set_running(1, id(self), tsk)
		try:
			Runner.printout(tsk.display())
			if tsk.__class__.stat: ret = tsk.__class__.stat(tsk)
			else: ret = tsk.call_run()
		except Exception, e:
			# TODO add the stack error message
			tsk.err_msg = e.message
			tsk.hasrun = EXCEPTION

			# TODO cleanup
			m.error_handler(tsk)
			m.out.put(tsk)
			set_running(-1, id(self), tsk)
			continue

		time.sleep(1 + 2* random.random())

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
		set_running(-1, id(self), tsk)
		m.out.put(tsk)

Runner.TaskConsumer.run = newrun

class TaskPrinter(threading.Thread):
	def __init__(self, master):
		threading.Thread.__init__(self)
		self.setDaemon(1)
		self.m_master = master
		self.stat = []
		self.start()

	def run(self):
		global state, mylock
		while self.m_master:
			try:
				mylock.acquire()
				self.stat.append( (time.time(), self.m_master.processed, state) )
				#self.stat.append( (time.time(), self.m_master.processed, self.m_master.ready.qsize()) )
				mylock.release()
			except:
				raise
				pass

			try: time.sleep(INTERVAL)
			except: pass

		while 1:
			try:
				time.sleep(250)
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

		global taskinfo
		process_colors(taskinfo)
		#file = open('/tmp/colors.dat', 'w')
		#try:
		#	while True:
		#		(s, t, tm) = taskinfo.get(False)
		#		file.write('%d %d %f\n' % (s, t, tm))
		#except:
		#	pass
		file.close()
Runner.Parallel.start = do_start


def process_colors(q):

	tmp = []
	try:
		while True:
			(s, t, tm, clsname) = q.get(False)
			tmp.append([s, t, tm, clsname])
	except:
		pass

#file = open('colors.dat', 'rb')
#code = file.read()
#file.close()

#lst = code.strip().split('\n')
#tmp = [x.split() for x in lst]

	ini = float(tmp[0][2])
	tmp = [lst[:2] + [float(lst[2]) - ini] + lst[3:] for lst in tmp]

	st = {}
	for l in tmp:
		if not l[0] in st:
			st[l[0]] = len(st.keys())
	tmp = [  [st[lst[0]]] + lst[1:] for lst in tmp ]
	THREAD_AMOUNT = len(st.keys())

	st = {}
	for l in tmp:
		if not l[1] in st:
			st[l[1]] = len(st.keys())
	tmp = [  [lst[0]] + [st[lst[1]]] + lst[2:] for lst in tmp ]


	seen = {}
	acc = []
	for x in xrange(len(tmp)):
		line = tmp[x]
		id = line[1]

		if id in seen:
			continue
		seen[id] = True

		begin = line[2]
		thread_id = line[0]
		for y in xrange(x + 1, len(tmp)):
			line = tmp[y]
			if line[1] == id:
				end = line[2]
				#print id, thread_id, begin, end
				#acc.append(  ( 10*thread_id, 10*(thread_id+1), 10*begin, 10*end ) )
				acc.append( (BAND * begin, BAND*thread_id, BAND*end - BAND*begin, BAND, line[3]) )
				break

	gwidth = 0
	for x in tmp:
			m = BAND * x[2]
			if m > gwidth: gwidth = m
	gheight = BAND * (THREAD_AMOUNT + len(info.keys()) + 1)

	out = []

	out.append("""<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>
<!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.0//EN\"
\"http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd\">
<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" version=\"1.0\"
   x=\"%d\" y=\"%d\" width=\"%d\" height=\"%d\"
   id=\"svg602\" xml:space=\"preserve\">
<defs id=\"defs604\" />\n""" % (-1, -1, gwidth + 3, gheight + 2))

	# main title
	out.append("""<text x="%d" y="%d" style=" font-family:Arial Black; font-size:15; text-anchor:middle">Task execution using waf -j%d</text>
""" % (gwidth/2, gheight - 5, THREAD_AMOUNT))

	# the rectangles
	for (x, y, w, h, clsname) in acc:
		out.append("""<rect
   x='%r' y='%r'
   width='%r' height='%r'
   style=\"font-size:10;fill:%s;fill-opacity:0.7;fill-rule:evenodd;stroke:#000000;\"
   />\n""" % (x, y, w, h, map_to_color(clsname)))

	# output the caption
	cnt = THREAD_AMOUNT
	for (color, text) in info.iteritems():
		# caption box
		b = BAND/2
		out.append("""<rect
		x='%d' y='%r'
		width='%d' height='%d'
		style=\"font-size:10;fill:%s;fill-opacity:0.7;fill-rule:evenodd;stroke:#000000;\"
  />\n""" % (BAND, (cnt + 0.5) * BAND, b, b, color))

		# caption text
		out.append("""<text
   style="font-size:12px;font-style:normal;font-weight:normal;fill:#000000;fill-opacity:1;stroke:none;stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1;font-family:Arial"
   x="%r" y="%d">%s</text>\n""" % (2 * BAND, (cnt+1) * BAND, text))
		cnt += 1

	out.append("\n</svg>")

	file = open("foo.svg", "wb")
	file.write("".join(out))
	file.close()

	import os
	os.popen("convert foo.svg foo.png").read()


