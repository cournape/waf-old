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

MAX_BATCH = 50
USE_SHELL = False
GCCDEPS = True
MAXPARALLEL = False

EXT_C = ['.c', '.cc', '.cpp', '.cxx']

import os, threading
import TaskGen, Task, ccroot, Build, Logs
from TaskGen import extension, feature, before
from Constants import *

if GCCDEPS:
	lock = threading.Lock()

	@feature('cc')
	@before('apply_core')
	def add_mmd_cc(self):
		if self.env.get_flat('CCFLAGS').find('-MD') < 0:
			self.env.append_value('CCFLAGS', '-MD')

	@feature('cxx')
	@before('apply_core')
	def add_mmd_cxx(self):
		if self.env.get_flat('CXXFLAGS').find('-MD') < 0:
			self.env.append_value('CXXFLAGS', '-MD')

	def scan(self):
		"the scanner does not do anything initially"
		nodes = self.generator.bld.node_deps.get(self.unique_id(), [])
		names = [] # self.generator.bld.raw_deps.get(self.unique_id(), [])
		return (nodes, names)

	for name in 'cc cxx'.split():
		try:
			cls = Task.TaskBase.classes[name]
		except KeyError:
			pass
		else:
			cls.scan = scan

count = 12345
class batch_task(Task.Task):
	color = 'RED'
	before = 'cc_link cxx_link ar_link_static'

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

		lst = []
		lst2 = []
		for id in xrange(len(self.slaves)):
			name = 'batch_%d_%d.c' % (self.idx, id)
			lst.append(name)
			f = open(name, 'wb')
			f.write('#include "%s"\n' % self.slaves[id].inputs[0].relpath_gen(self.generator.bld.bldnode))
			f.close()

			if USE_SHELL:
				si = '/bin/mv -f %s %s' % (name.replace('.c', '.o'), self.slaves[id].outputs[0].abspath(self.slaves[id].env))
				lst2.append(si)

		if USE_SHELL:
			self.env['CC_TGT_F'] = self.env['CXX_TGT_F'] = '-c ' + " ".join(lst) + " && (%s)" % " && ".join(lst2)
		else:
			self.env['CC_TGT_F'] = self.env['CXX_TGT_F'] = '-c ' + " ".join(lst)


		ret = self.slaves[0].__class__.__dict__['oldrun'](self)
		if ret:
			return ret

		self.outputs = outputs

		env = self.slaves[0].env
		rootdir = self.generator.bld.srcnode.abspath(env)

		if not USE_SHELL:
			for id in xrange(len(self.slaves)):
				name = 'batch_%d_%d.o' % (self.idx, id)
				#print "moving", name, self.slaves[id].outputs[0].abspath(self.slaves[id].env)

				task = self.slaves[id]
				dest = task.outputs[0].abspath(task.env)
				try:
					os.unlink(dest)
				except OSError:
					pass
				os.rename(name, dest)
				#shutil.move(name, task.outputs[0].abspath(task.env))

		if GCCDEPS:
			for id in xrange(len(self.slaves)):
				task = self.slaves[id]
				name = 'batch_%d_%d.d' % (self.idx, id)

				f = open(name, 'r')
				txt = f.read()
				f.close()
				os.unlink(name)

				txt = txt.replace('\\\n', '')

				lst = txt.strip().split(':')
				val = ":".join(lst[1:])
				val = val.split()

				# remove the first two sources
				val = val[2:]

				lock.acquire()
				nodes = []
				for x in val:
					if os.path.isabs(x):
						node = self.generator.bld.root.find_resource(x)
					else:
						x = x.lstrip('../')
						node = self.generator.bld.srcnode.find_resource(x)

					if not node:
						raise ValueError, 'could not find' + x
					else:
						nodes.append(node)
				lock.release()

				Logs.debug('deps: real scanner for %s returned %s' % (str(self), str(nodes)))

				id = self.unique_id()
				self.generator.bld.node_deps[id] = nodes
				self.generator.bld.raw_deps[id] = []

				try: delattr(self, 'cache_sig')
				except: pass
				Task.Task.post_run(task)

		return None

	def post_run(self):
		for t in self.slaves:
			sig = t.signature()
			for node in t.outputs:
				variant = node.variant(t.env)
				t.generator.bld.node_sigs[variant][node.id] = sig

			t.generator.bld.task_sigs[t.unique_id()] = t.cache_sig

from TaskGen import extension, feature, after

import cc, cxx
def wrap(fun):
	def foo(self, node):
		task = fun(self, node)
		if not getattr(self, 'master', None):
			self.master = self.create_task('batch')
			try:
				self.all_masters.append(self.master)
			except AttributeError:
				self.all_masters = [self.master]
		else:
			if len(self.master.slaves) > MAX_BATCH:
				# another group
				self.master = self.create_task('batch')
				try:
					self.all_masters.append(self.master)
				except AttributeError:
					self.all_masters = [self.master]

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

if MAXPARALLEL:
	# relax the constraints between cxx and cxx_link (in the build section)
	Task.TaskBase.classes['cxx'].ext_out = []
	batch_task.before = ''

	@feature('cc', 'cxx')
	@after('apply_link')
	def masters(self):
		try:
			link_task = self.link_task
		except AttributeError:
			pass
		else:
			for k in self.all_masters:
				link_task.set_run_after(k)

