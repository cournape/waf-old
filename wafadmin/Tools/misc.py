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
	"Make a file copy. This might be used to make other kinds of file processing (even calling a compiler is possible)"
	env = task.m_env
	infile = task.m_inputs[0].abspath(env)
	outfile = task.m_outputs[0].abspath(env)
	try:
		shutil.copy2(infile, outfile)
		if task.chmod: os.chmod(outfile, chmod)
		return 0
	except:
		return 1

def action_process_file_func(task):
	"Ask the function attached to the task to process it"
	if not task.fun: fatal('task must have a function attached to it for copy_func to work!')
	return task.fun(task)

class cmdobj(Object.genobj):
	"This object will call a command everytime"
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
	"By default, make a file copy, if fun is provided, fun will make the copy (or call a compiler, etc)"
	def __init__(self, type='none'):
		Object.genobj.__init__(self, 'copy')

		self.source = ''
		self.target = ''
		self.chmod  = ''
		self.fun = copy_func

		self.env = Params.g_build.m_allenvs['default'].copy()

	def apply(self):

		lst = self.to_list(self.source)

		for filename in lst:
			node = self.m_current_path.find_node( filename.split('/') )
			if not node: fatal('cannot find input file %s for processing' % filename)

			target = self.target
			if not target or len(lst)>1: target = node.m_name

			# TODO the file path may be incorrect
			newnode = self.m_current_path.search_existing_node( target.split('/') )
			if not newnode:
                		newnode = Node.Node(target, self.m_current_path)
				self.m_current_path.m_build.append(newnode)

			task = self.create_task('copy', self.env, 8)
			task.set_inputs(node)
			task.set_outputs(newnode)
			task.m_env = self.env
			task.fun = self.fun
			task.chmod = self.chmod

			if not task.m_env:
				task.debug()
				fatal('task witout an environment')

def setup(env):
	Object.register('cmd', cmdobj)
	Object.register('copy', copyobj)
	Action.Action('copy', vars=[], func=action_process_file_func)

def detect(conf):
	return 1

