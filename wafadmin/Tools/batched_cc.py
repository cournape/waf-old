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

class TaskMaster(Task.Task):
	def __init__(self, action_name, env, normal=1, master=None):
		Task.Task.__init__(self, env, normal=normal)
		self.slaves=[]
		self.inputs2=[]
		self.outputs2=[]

	def add_slave(self, slave):
		self.slaves.append(slave)
		self.set_run_after(slave)

	def runnable_status(self):
		for t in self.run_after:
			if not t.hasrun: return ASK_LATER

		for t in self.slaves:
			self.inputs.append(t.inputs[0])
			self.outputs.append(t.outputs[0])
			if t.must_run:
				self.inputs2.append(t.inputs[0])
				self.outputs2.append(t.outputs[0])
		return Task.Task.runnable_status(self)

	def run(self):
		tmpinputs = self.inputs
		self.inputs = self.inputs2
		tmpoutputs = self.outputs
		self.outputs = self.outputs2

		ret = self.action.run(self)
		env = self.env

		rootdir = Build.bld.srcnode.abspath(env)

		# unfortunately building the files in batch mode outputs them in the current folder (the build dir)
		# now move the files from the top of the builddir to the correct location
		for i in self.outputs:
			name = i.name
			if name[-1] == "s": name = name[:-1] # extension for shlib is .os, remove the s
			shutil.move(name, i.bldpath(env))

		self.inputs = tmpinputs
		self.outputs = tmpoutputs

		return ret

class TaskSlave(Task.Task):
	def __init__(self, action_name, env, normal=1, master=None):
		Task.Task.__init__(self, env, normal)
		self.master = master

	def prepare(self):
		self.display = "* skipping "+ self.inputs[0].name

	def update_stat(self):
		self.executed=1

	def runnable_status(self):
		self.must_run = Task.Task.must_run(self)
		return self.must_run

	def run(self):
		return 0

	def can_retrieve_cache(self, sig):
		return None

@extension(EXT_C)
def create_task_cxx_new(self, node):
	try:
		mm = self.mastertask
	except AttributeError:
		mm = TaskMaster("all_"+self.type_initials, self.env)
		self.mastertask = mm

	task = TaskSlave(self.type_initials, self.env, 40, master=mm)
	self.tasks.append(task)
	mm.add_slave(task)

	task.set_inputs(node)
	task.set_outputs(node.change_ext('.o'))

	self.compiled_tasks.append(task)

cc_str = '${CC} ${CCFLAGS} ${CPPFLAGS} ${_CCINCFLAGS} ${_CCDEFFLAGS} -c ${SRC}'
Task.simple_task_type('all_cc', cc_str, 'GREEN')

cpp_str = '${CXX} ${CXXFLAGS} ${CPPFLAGS} ${_CXXINCFLAGS} ${_CXXDEFFLAGS} -c ${SRC}'
Task.simple_task_type('all_cpp', cpp_str, color='GREEN')

