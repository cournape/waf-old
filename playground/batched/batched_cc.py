#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"""
Batched builds - compile faster
instead of compiling object files one by one, c/c++ compilers are often able to compile at once:
cc -c ../file1.c ../file2.c ../file3.c

Files are output on the directory where the compiler is called, and dependencies are more difficult
to track (do not run the command on all source files if only one file changes)

As such, we do as if the files were compiled one by one, but no command is actually run:
replace each cc/cpp Task by a TaskSlave
A new task called TaskMaster collects the signatures from each slave and finds out the command-line
to run.

To set this up, the method ccroot::create_task is replaced by a new version, to enable batched builds
it is only necessary to import this module in the configuration (no other change required)
"""

EXT_C = ['.c', '.cc', '.cpp', '.cxx']

import shutil, os
import TaskGen, Task, ccroot, Build
from TaskGen import extension
from Constants import *

count = 12345
class batch_task(Task.Task):
	#before = 'cc_link cxx_link ar_link_static'
	before = 'cc_link'
	after = 'cc cxx'
	color = 'RED'

	def __str__(self):
		return '(batch compilation)\n'

	def __init__(self, *k, **kw):
		Task.Task.__init__(self, *k, **kw)
		self.slaves=[]
		self.inputs=[]
		#self.outputs=[]
		self.hasrun = 0

		global count
		count += 1
		self.idx = count

	def add_slave(self, slave):
		self.slaves.append(slave)
		self.set_run_after(slave)

	def runnable_status(self):
		for t in self.run_after:
			if not t.hasrun:
				return ASK_LATER

		for t in self.slaves:
			#if t.executed:
			if t.hasrun != SKIPPED:
				return RUN_ME

		return SKIP_ME

	def run(self):
		outputs = []
		self.outputs = []

		self.slaves = [t for t in self.slaves if t.hasrun != SKIPPED]

		for t in self.slaves:
			#self.inputs.extend(t.inputs)
			outputs.extend(t.outputs)

		# unfortunately building the files in batch mode outputs
		# them into the current folder (the build dir)
		# move them to the correct location
		shell_move = True

		lst = []
		lst2 = []
		for id in xrange(len(self.slaves)):
			name = 'batch_%d_%d.c' % (self.idx, id)
			lst.append(name)
			f = open(name, 'wb')
			f.write('#include "%s"' % self.slaves[id].inputs[0].relpath_gen(self.generator.bld.bldnode))
			f.close()

			if shell_move:
				si = 'mv %s %s' % (name.replace('.c', '.o'), self.slaves[id].outputs[0].abspath(self.slaves[id].env))
				lst2.append(si)

		if shell_move:
			self.env['CC_TGT_F'] = '-c ' + " ".join(lst) + " && " + " && ".join(lst2)
			self.env['CXX_TGT_F'] = '-c ' + " ".join(lst) + " && " + " && ".join(lst2)
		else:
			self.env['CC_TGT_F'] = '-c ' + " ".join(lst)
			self.env['CXX_TGT_F'] = '-c ' + " ".join(lst)


		ret = self.slaves[0].__class__.__dict__['oldrun'](self)
		if ret:
			return ret

		self.outputs = outputs

		env = self.slaves[0].env
		rootdir = self.generator.bld.srcnode.abspath(env)

		if not shell_move:
			for id in xrange(len(self.slaves)):
				name = 'batch_%d_%d.o' % (self.idx, id)
				#print "moving", name, self.slaves[id].outputs[0].abspath(self.slaves[id].env)
				shutil.move(name, self.slaves[id].outputs[0].abspath(self.slaves[id].env))

		return None

	def post_run(self):
		for t in self.slaves:
			sig = t.signature()
			for node in t.outputs:
				variant = node.variant(t.env)
				t.generator.bld.node_sigs[variant][node.id] = sig

			t.generator.bld.task_sigs[t.unique_id()] = t.cache_sig

from TaskGen import extension

import cc, cxx
def wrap(fun):
	def foo(self, node):
		task = fun(self, node)
		if not getattr(self, 'master', None):
			self.master = self.create_task('batch')
		self.master.add_slave(task)
		return task
	return foo

c_hook = wrap(cc.c_hook)
extension(cc.EXT_CC)(c_hook)

cxx_hook = wrap(cxx.cxx_hook)
extension(cxx.EXT_CXX)(cxx_hook)

for c in ['cc', 'cxx']:
	t = Task.TaskBase.classes[c]
	def run(self):
		pass

	def post_run(self):
		#self.executed=1
		pass

	def can_retrieve_cache(self):
		pass

	setattr(t, 'oldrun', t.__dict__['run'])
	setattr(t, 'run', run)
	setattr(t, 'post_run', post_run)
	setattr(t, 'can_retrieve_cache', can_retrieve_cache)


