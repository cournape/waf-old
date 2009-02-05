#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008 (ita)

"""
Execute the tasks with gcc -MD, read the dependencies from the .d file
and prepare the dependency calculation for the next run
"""

import os
import threading
import Task, Logs
from TaskGen import feature, before

lock = threading.Lock()

# change to '-MMD' if you don't want to check system header files too.
preprocessor_flag = '-MD'

@feature('cc')
@before('apply_core')
def add_mmd_cc(self):
	if self.env.get_flat('CCFLAGS').find(preprocessor_flag) < 0:
		self.env.append_value('CCFLAGS', preprocessor_flag)

@feature('cxx')
@before('apply_core')
def add_mmd_cxx(self):
	if self.env.get_flat('CXXFLAGS').find(preprocessor_flag) < 0:
		self.env.append_value('CXXFLAGS', preprocessor_flag)

def scan(self):
	"the scanner does not do anything initially"
	nodes = self.generator.bld.node_deps.get(self.unique_id(), [])
	names = []
	return (nodes, names)

def post_run(self):
	"""The following code is executed by threads, it is not safe"""

	lock.acquire()

	try:
		name = self.outputs[0].abspath(self.env)
		name = name.rstrip('.o') + '.d'

		f = open(name, 'r')
		txt = f.read()
		f.close()
		os.unlink(name)

		txt = txt.replace('\\\n', '')

		lst = txt.strip().split(':')
		val = ":".join(lst[1:])
		val = val.split()

		nodes = []
		bld = self.generator.bld
		for x in val:
			if os.path.isabs(x):
				node = bld.root.find_resource(x)
			else:
				node = bld.bldnode.find_resource(x)

			if not node:
				raise ValueError, 'could not find' + x
			else:
				nodes.append(node)

		Logs.debug('deps: real scanner for %s returned %s' % (str(self), str(nodes)))

		bld.node_deps[self.unique_id()] = nodes
		bld.raw_deps[self.unique_id()] = []

		if getattr(self, 'cache_sig', ''): del self.cache_sig
		Task.Task.post_run(self)
	finally:
		lock.release()

for name in 'cc cxx'.split():
	try:
		cls = Task.TaskBase.classes[name]
	except KeyError:
		pass
	else:
		cls.post_run = post_run
		cls.scan = scan

