#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"C# support"

import Params, TaskGen, Utils, Task
from Params import error

g_types_lst = ['program', 'library']
class cs_taskgen(TaskGen.task_gen):
	def __init__(self, *k):
		TaskGen.task_gen.__init__(self, *k)

		self.m_type     = k[1]

		self.source     = ''
		self.target     = ''

		self.flags      = ''
		self.assemblies = ''
		self.resources  = ''

		self.uselib     = ''

		self._flag_vars = ['FLAGS', 'ASSEMBLIES']

		if not self.m_type in g_types_lst:
			error('type for csobj is undefined '+type)
			type='program'

	def apply(self):
		self.apply_uselib()

		# process the flags for the assemblies
		assemblies_flags = []
		for i in self.to_list(self.assemblies) + self.env['ASSEMBLIES']:
			assemblies_flags += '/r:'+i
		self.env['_ASSEMBLIES'] += assemblies_flags

		# process the flags for the resources
		for i in self.to_list(self.resources):
			self.env['_RESOURCES'].append('/resource:'+i)

		# additional flags
		self.env['_FLAGS'] += self.to_list(self.flags) + self.env['FLAGS']

		curnode = self.path

		# process the sources
		nodes = []
		for i in self.to_list(self.source):
			nodes.append(curnode.find_resource(i))

		# create the task
		task = self.create_task('mcs', self.env)
		task.m_inputs  = nodes
		task.set_outputs(self.path.find_build(self.target))

	def apply_uselib(self):
		if not self.uselib:
			return
		for var in self.to_list(self.uselib):
			for v in self._flag_vars:
				val = self.env[v+'_'+var]
				if val: self.env.append_value(v, val)

Task.simple_task_type('mcs', '${MCS} ${SRC} /out:${TGT} ${_FLAGS} ${_ASSEMBLIES} ${_RESOURCES}', color='YELLOW', prio=101)

def detect(conf):
	mcs = conf.find_program('mcs', var='MCS')
	if not mcs: mcs = conf.find_program('gmcs', var='MCS')

