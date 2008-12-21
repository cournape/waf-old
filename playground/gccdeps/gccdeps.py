#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008 (ita)

import Task, Utils
import preproc
from Constants import *

"""
We create a pseudo task that runs in the main thread
to compute the dependencies the slaves then
obtain their dependencies from it
"""

ccvars = "CC CCFLAGS CPPFLAGS _CCINCFLAGS _CCDEFFLAGS".split()
cxxvars = "CXX CXXFLAGS CPPFLAGS _CXXINCFLAGS _CXXDEFFLAGS".split()

class ccdeps_task(Task.TaskBase):
	def __init__(self, *k, **kw):
		Task.TaskBase.__init__(self, *k, **kw)
		self.slaves = []
		self.deps = {} # map slave id to tuple (nodes, [])

	def runnable_status(self):
		"""This must be executed from the main thread"""

		if not self.slaves:
			return SKIP_ME

		for x in self.slaves:
			try:
				x.run_after.remove(self)
			except ValueError:
				pass

		to_run = SKIP_ME
		for x in self.slaves:
			st = x.runnable_status()
			if st == RUN_ME:
				to_run = RUN_ME
			elif st == ASK_LATER:
				to_run = ASK_LATER

		if to_run == SKIP_ME:
			return SKIP_ME

		# ARGH!
		if to_run == ASK_LATER:
			for x in self.slaves:
				x.set_run_after(self)

			return ASK_LATER

		if self.slaves[0].__class__.__name__ == 'cxx':
			vars = cxxvars
		else:
			vars = ccvars

		env = self.slaves[0].env

		# obtain the list of c files to process
		inputs = []
		for x in self.slaves:
			inputs.extend(x.inputs)
		inp = [x.abspath(env) for x in inputs]
		inp = " ".join(inp)

		# now obtain the command-line
		vars = [env.get_flat(k) for k in vars]
		vars.append('-M')
		vars.append(inp)
		cmd = " ".join(vars)

		try:
			deps = Utils.cmd_output(cmd)
		except ValueError:
			# the code does not compile, let it fail for real to display the errors
			return ([], [])

		deps = deps.replace('\\\n', '')
		deps = deps.strip()
		for line in deps.split('\n'):
			lst = line.split(':')
			name = lst[0]

			val = ":".join(lst[1:])
			val = val.split()

			nodes = [self.generator.bld.root.find_resource(x) for x in val]
			# TODO: display which nodes cannot be found?
			nodes = [x for x in nodes if x]

			# FIXME will not work for nested folders
			name = name.replace('.o', '')
			name += '_%d.o' % self.generator.idx

			self.deps[name] = nodes

		# now remove the cached signatures from the slaves
		for x in self.slaves:
			try:
				delattr(x, "cache_sig")
			except AttributeError:
				pass

		return SKIP_ME

	def run(self):
		return None

def scan(self):
	"new scan function for c/c++ classes"
	#print self.master.deps, self.run_after
	nodes = self.master.deps.get(self.outputs[0].name, [])
	return (nodes, [])

from TaskGen import extension
import cc, cxx
@extension(cc.EXT_CC)
def c_hook(self, node):
	task = cc.c_hook(self, node)
	if not getattr(self, 'master', None):
		self.master = self.create_task('ccdeps')
	self.master.slaves.append(task)
	task.set_run_after(self.master)
	task.master = self.master
	return task

t = Task.TaskBase.classes
if 'cc' in t:
	t['cc'].scan = scan

if 'cxx' in t:
	t['cxx'].scan = scan

