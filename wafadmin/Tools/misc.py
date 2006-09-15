#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, sys, types
import Utils, Params, Action, Object, Runner, Common
from Params import debug, error, trace, fatal

class cmdobj(Object.genobj):
	def __init__(self, type='none'):
		Object.genobj.__init__(self, 'none')
		self.m_type = type
		self.prio   = 1
		self.fun    = None

	def apply(self):
		# create a task
		if not self.fun: fatal('cmdobj needs a function!')
		import Task
		Task.TaskCmd(self.fun, self.env, self.prio)

def setup(env):
	Object.register('cmd', cmdobj)

def detect(conf):
	return 1

