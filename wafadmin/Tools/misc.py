#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"""
An object that executes a function everytime
An object that copies a file somewhere else
"""

import shutil
import Object, Action, Node, Params
from Params import fatal

def copy_func(task):
	env = task.m_env
	infile = task.m_inputs[0].abspath(env)
	outfile = task.m_outputs[0].abspath(env)
	try:
		shutil.copy2(infile, outfile)
		return 0
	except:
		return 1

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

class copyobj(Object.genobj):
	def __init__(self, type='none'):
		Object.genobj.__init__(self, 'copy')

		self.source = ''
		self.target = ''
		self.chmod  = ''

		self.env = Params.g_build.m_allenvs['default'].copy()

	def apply(self):

		for filename in self.to_list(self.source):
			#base, ext = os.path.splitext(filename)
			#if not ext in self.s_default_ext: continue

			node = self.m_current_path.find_node( filename.split('/') )
			if not node: fatal('cannot find %s' % filename)

			target = self.target
			if not target:
				target = node.m_name

			#if not target:
			#	node2 = self.m_current_path.;

			newnode = self.m_current_path.find_node( target.split('/') )
			if not newnode:
                		newnode = Node.Node(target, self.m_current_path)
				self.m_current_path.m_build.append(newnode)

			task = self.create_task('copy', self.env, 8)
			task.set_inputs(node)
			task.set_outputs(newnode)
			task.m_env = self.env

			if not task.m_env:
				task.debug()
				fatal('task witout an environment')
def setup(env):
	Object.register('cmd', cmdobj)
	Object.register('copy', copyobj)
	Action.Action('copy', vars=[], func=copy_func)

def detect(conf):
	return 1

