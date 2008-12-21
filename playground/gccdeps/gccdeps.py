#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008 (ita)

import os
import Task, Utils
import preproc
from Constants import *

"""
Execute the tasks with gcc -MD, read the dependencies from the .d file
and prepare the dependency calculation for the nexte run
"""

import Task, Logs
from TaskGen import feature, before, after

@feature('cc', 'cxx')
@before('apply_core')
def add_mmd(self):
	if self.env.get_flat('CCFLAGS').find('-MD') < 0:
		self.env.append_value('CCFLAGS', '-MD')

def scan(self):
	"the scanner does not do anything initially"
	nodes = self.generator.bld.node_deps.get(self.unique_id(), [])
	names = [] # self.generator.bld.raw_deps.get(self.unique_id(), [])
	return (nodes, names)

def post_run(self):
	#print "post_run!!!", self.outputs[0].abspath(self.env)

	name = self.outputs[0].abspath(self.env)
	name = name.rstrip('.o') + '.d'

	f = open(name, 'r')
	txt = f.read()
	f.close()
	os.unlink(name)

	lst = txt.strip().split(':')
	val = ":".join(lst[1:])
	val = val.split()

	nodes = []
	for x in val:
		if os.path.isabs(x):
			node = self.generator.bld.root.find_resource(x)
		if x.startswith('..'):
			node = self.generator.bld.bldnode.find_resource(x)
		else:
			node = self.generator.bld.srcnode.find_resource(x)

		if not node:
			raise ValueError, 'could not find' + x
		else:
			nodes.append(node)

	Logs.debug('deps: scanner for %s returned %s' % (str(self), str(nodes)))

	self.generator.bld.node_deps[self.unique_id()] = nodes
	self.generator.bld.raw_deps[self.unique_id()] = []

	delattr(self, 'cache_sig')
	Task.Task.post_run(self)

for name in 'cc cxx'.split():
	try:
		cls = Task.TaskBase.classes[name]
	except KeyError:
		pass
	else:
		cls.post_run = post_run
		cls.scan = scan

