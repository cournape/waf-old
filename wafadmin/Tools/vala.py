#! /usr/bin/env python
# encoding: utf-8
# Jaap Haitsma, 2008

"Vala support"

import Params, Action, Object, Utils

g_types_lst = ['program']
class valaobj(Object.genobj):
	s_default_ext = ['.vala']
	def __init__(self, type='program'):
		Object.genobj.__init__(self, 'other')
		self.m_type       = type
		self.source       = ''
		self.target       = ''
		self.packages     = ''
		self.ccoptions    = ''

		if not self.env: self.env = Params.g_build.env().copy()

		if not type in g_types_lst:
			error('type for valaobj is undefined '+type)
			type='program'

	def apply(self):
		# process the flags for the packages
		self.env['_PACKAGES'] = []
		for i in self.to_list(self.packages):
			self.env['_PACKAGES'].append('--pkg '+i)

		if self.ccoptions:
			self.env['_CCOPTIONS'] = []
			self.env['_CCOPTIONS'].append('-X "' + self.ccoptions + '"')

		curnode = self.path
		# process the sources
		nodes = []
		for i in self.to_list(self.source):
			nodes.append(curnode.find_source(i))

		# create the task
		task = self.create_task('valac', self.env, 101)
		task.m_inputs  = nodes
		task.set_outputs(self.path.find_build(self.target))

def setup(bld):
	Object.register('vala', valaobj)
	Action.simple_action('valac', '${VALAC} ${SRC} -o ${TGT} ${_PACKAGES} ${_CCOPTIONS}', color='YELLOW')

def detect(conf):
	valac = conf.find_program('valac', var='VALAC')

