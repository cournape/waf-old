#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008 (ita)

import Task, Utils
import preproc
from Constants import *

"""
We create a ccdeps task that computes the dependencies for others

The compilation tasks are set to run after the ccdeps task

1. the ccdeps task ask its slaves if they have changed
2. if one of the task has changed, ccdeps computes the dependencies
   by calling gcc
3. ccdeps clears the task signatures and marks itself as "skipped"
4. when each of the compilation task evaluates if it has to run,
   it asks the ccdeps task for the dependency nodes
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

		# because we are in the main thread, we may remove
		# the dependencies for just a moment
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

		# we re-add the dependencies
		for x in self.slaves:
			x.set_run_after(self)

		if to_run == ASK_LATER:
			return ASK_LATER

		return RUN_ME

	def run(self):
		"""All this is for executing gcc and computing the dependencies"""

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
			# errors: let it fail in the chilren tasks to display the errors
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

def scan(self):
	"new scan function for c/c++ classes"
	#print self.master.deps, self.run_after
	nodes = self.master.deps.get(self.outputs[0].name, [])
	return (nodes, [])

from TaskGen import extension
import cc, cxx
def wrap(fun):
	def foo(self, node):
		task = fun(self, node)
		if not getattr(self, 'master', None):
			self.master = self.create_task('ccdeps')
		self.master.slaves.append(task)
		task.set_run_after(self.master)
		task.master = self.master
		return task
	return foo

c_hook = wrap(cc.c_hook)
extension(cc.EXT_CC)(c_hook)

cxx_hook = wrap(cxx.cxx_hook)
extension(cxx.EXT_CXX)(cxx_hook)


t = Task.TaskBase.classes
if 'cc' in t:
	t['cc'].scan = scan

if 'cxx' in t:
	t['cxx'].scan = scan

