#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, sys, types
import Utils, Params, Action, Object, Runner, Common
from Params import debug, error, trace, fatal

class NAction(Action.Action):
	def __init__(self, name, vars=[], func=None, color='GREEN'):
		Action.Action.__init__(self, name, vars, func, color)
	def get_str(self, task):
		return "* %s" % self.m_name

class cmdobj(Object.genobj):
	def __init__(self, type='none'):
		Object.genobj.__init__(self, 'none')
		self.m_type       = type
		self.prio = 1
		self.fun = None

	def apply(self):
		# create the task

		if not self.fun:
			fatal('cmdobj needs a function!')

		name = self.fun.__name__

		if not name in Action.g_actions:
			act = NAction(name, vars=[], func=self.fun)

		task = self.create_task(name, self.env, self.prio)
		task.m_inputs  = []
		task.m_outputs = []

def setup(env):
	Object.register('cmd', cmdobj)

def detect(conf):
	conf.find_program('mcs', var='MCS')
	return 1

