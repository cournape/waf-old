#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, sys, types
import Utils, Params, Action, Object, Runner, Common
from Params import debug, error, trace, fatal

g_types_lst = ['program', 'library']
class csobj(Object.genobj):
	def __init__(self, type='program'):
		Object.genobj.__init__(self, 'cs')

		self.m_type       = type

		self.source       = ''
		self.target       = ''

		self.flags        = ''
		self.assemblies   = ''
		self.resources    = ''

		self.uselib       = ''

		self._flag_vars = ['FLAGS', 'ASSEMBLIES']

		if not self.env: self.env = Params.g_build.m_allenvs['default']

		if not type in g_types_lst:
			error('type for csobj is undefined '+type)
			type='program'

	def apply(self):
		self.apply_uselib()

		# process the flags for the assemblies
		assemblies_flags = []
		for i in self.to_list(self.assemblies) + self.env['ASSEMBLIES']:
			nodes += '/r:'+i
		self.env['_ASSEMBLIES'] += assemblies_flags

		# process the flags for the resources
		for i in self.to_list(self.resources):
			self.env['_RESOURCES'].append('/resource:'+i)

		# additional flags
		self.env['_FLAGS'] += self.to_list(self.flags) + self.env['FLAGS']

		# process the sources
		nodes = []
		for i in self.to_list(self.source):
			nodes += self.file_in(i)

		# create the task
		task = self.create_task('mcs', self.env, 101)
		task.m_inputs  = nodes
		task.m_outputs = self.file_in(self.target)

	def apply_uselib(self):
		if not self.uselib:
			return
		for var in self.to_list(self.uselib):
			for v in self._flag_vars:
				val=''
				try:    val = self.env[v+'_'+l]
				except: pass
				if val:
					self.env.appendValue(v, val)

	#def to_list(self, value):
	#	if type(value) is types.ListType: lst = self.value
	#	else: lst = value.split()
	#	return lst

def setup(env):
	Object.register('cs', csobj)
	Action.simple_action('mcs', '${MCS} ${SRC} /out:${TGT} ${_FLAGS} ${_ASSEMBLIES} ${_RESOURCES}', color='YELLOW')

def detect(conf):
	mcs = conf.find_program('mcs', var='MCS')
	conf.env['MCS'] = mcs

	return 1

