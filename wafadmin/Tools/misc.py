#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"""
Custom objects:
 - execute a function everytime
 - copy a file somewhere else
"""

import shutil, re, os, types, subprocess
import Object, Action, Node, Params, Utils, Task
from Params import fatal

def copy_func(task):
	"Make a file copy. This might be used to make other kinds of file processing (even calling a compiler is possible)"
	env = task.m_env
	infile = task.m_inputs[0].abspath(env)
	outfile = task.m_outputs[0].abspath(env)
	try:
		shutil.copy2(infile, outfile)
		if task.chmod: os.chmod(outfile, task.chmod)
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
		Object.genobj.__init__(self, 'other')
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
		Object.genobj.__init__(self, 'other')

		self.source = ''
		self.target = ''
		self.chmod  = ''
		self.fun = copy_func

		self.env = Params.g_build.m_allenvs['default'].copy()

	def apply(self):

		lst = self.to_list(self.source)

		for filename in lst:
			node = self.path.find_source(filename)
			if not node: fatal('cannot find input file %s for processing' % filename)

			target = self.target
			if not target or len(lst)>1: target = node.m_name

			# TODO the file path may be incorrect
			newnode = self.path.find_build(target)

			task = self.create_task('copy', self.env, 10)
			task.set_inputs(node)
			task.set_outputs(newnode)
			task.m_env = self.env
			task.fun = self.fun
			task.chmod = self.chmod

			if not task.m_env:
				task.debug()
				fatal('task witout an environment')

def subst_func(task):
	"Substitutes variables in a .in file"

	m4_re = re.compile('@(\w+)@', re.M)

	env = task.m_env
	infile = task.m_inputs[0].abspath(env)
	outfile = task.m_outputs[0].abspath(env)

	file = open(infile, 'r')
	code = file.read()
	file.close()

	s = m4_re.sub(r'%(\1)s', code)

	dict = task.dict
	if not dict:
		names = m4_re.findall(code)
		for i in names:
			if task.m_env[i] and type(task.m_env[i]) is types.ListType :
				dict[i] = " ".join( task.m_env[i] )
			else: dict[i] = task.m_env[i]

	file = open(outfile, 'w')
	file.write(s % dict)
	file.close()

	return 0

class substobj(Object.genobj):
	def __init__(self, type='none'):
		Object.genobj.__init__(self, 'other')
		self.fun = subst_func
		self.dict = {}
		self.prio = 8
	def apply(self):

		lst = self.to_list(self.source)

		for filename in lst:
			node = self.path.find_source(filename)
			if not node: fatal('cannot find input file %s for processing' % filename)

			newnode = node.change_ext('')

			task = self.create_task('copy', self.env, self.prio)
			task.set_inputs(node)
			task.set_outputs(newnode)
			task.m_env = self.env
			task.fun = self.fun
			task.dict = self.dict

			if not task.m_env:
				task.debug()
				fatal('task witout an environment')

class CommandOutput(Object.genobj):

	CMD_ARGV_INPUT, CMD_ARGV_OUTPUT = range(2)

	def __init__(self, env=None):
		Object.genobj.__init__(self, 'other')
		self.env = env
		if not self.env:
			self.env = Params.g_build.m_allenvs['default']

		## input file(s)
		## note: if multiple inputs are specified, only the first is
		## used (as stdin of the command); other input files are just
		## informative to let waf work out the dependencies correctly.
		self.input = ''

		## output file(s)
		## note: if multiple outputs are specified, only the first is
		## used (as stdout of the command); other output files are just
		## informative to let waf work out the dependencies correctly.
		self.output = ''
		
		## the command to execute
		self.command = None

		## whether it is an external command; otherwise it is assumed
		## to be an excutable binary or script that lives in the
		## source or build tree.
		self.command_is_external = False

		## extra parameters (argv) to pass to the command
		self.command_args = []

		## task priority
		self.priority = 100

		## dependencies to other objects
		## values must be 'genobj' instances (not names!)
		self.dependencies = []

	def _command_output_func(task):
		assert len(task.m_inputs) > 0
		inputs = [inp.bldpath(task.m_env) for inp in task.m_inputs]
		outputs = [out.bldpath(task.m_env) for out in task.m_outputs]

		args = []
		for idx, arg in enumerate(task.command_args):
			if isinstance(arg, str):
				args.append(arg)
			else:
				role, position = arg
				if role == CommandOutput.CMD_ARGV_INPUT:
					args.append(inputs[position])
					inputs[position] = None
				elif role == CommandOutput.CMD_ARGV_OUTPUT:
					args.append(outputs[position])
					outputs[position] = None
				else:
					raise AssertionError

		## remove all the None's in inputs
		while 1:
			for idx, elem in enumerate(inputs):
				if elem is None:
					del inputs[idx]
					break
			else:
				break
		## remove all the None's in outputs
		while 1:
			for idx, elem in enumerate(outputs):
				if elem is None:
					del outputs[idx]
					break
			else:
				break
		
		argv = [task.command] + args

		## if there are any inputs left, use the first one as stdin
		if inputs:
			stdin = file(inputs[0])
		else:
			stdin = None

		## if there are any outputs left, use the first one as stdout
		if outputs:
			stdout = file(outputs[0], "w")
		else:
			stdout = None

		Params.debug("command-output: stdin=%r, stdout=%r, argv=%r" %
					 (stdin, stdout, argv))
		command = subprocess.Popen(argv, stdin=stdin, stdout=stdout)
		return command.wait()

	_command_output_func = staticmethod(_command_output_func)

	def apply(self):
		if self.command_is_external:
			cmd = self.command
		else:
			cmd_node = self.path.find_source(self.command)
			assert cmd_node is not None,\
				   ("Could not find command '%s' in source tree.\n"
					"Hint: if this is an external command, "
					"use command_is_external=True") % (self.command,)
 			cmd = cmd_node.bldpath(self.env)
 		outputs = [self.path.find_build(target) for target in self.to_list(self.output)]
 		inputs = [self.path.find_source(input_) for input_ in self.to_list(self.input)]
		assert inputs
		task = self.create_task('command-output', self.env, self.priority)
		task.command_args = self.command_args
		task.command = cmd
		task.set_inputs(inputs)
		task.set_outputs(outputs)

		for dep in self.dependencies:
			assert dep is not self
			if not dep.m_posted:
				dep.post()
			for dep_task in dep.m_tasks:
				task.m_run_after.append(dep_task)

	def argv_input(self, position):
		"""Returns an object to be used as argv element that instructs
		the task to use a file from the input vector at the given
		position as argv element."""
		return (CommandOutput.CMD_ARGV_INPUT, position)

	def argv_output(self, position):
		"""Returns an object to be used as argv element that instructs
		the task to use a file from the output vector at the given
		position as argv element."""
		return (CommandOutput.CMD_ARGV_OUTPUT, position)

	def install(self):
		pass

def setup(env):
	Object.register('cmd', cmdobj)
	Object.register('copy', copyobj)
	Object.register('subst', substobj)
	Action.Action('copy', vars=[], func=action_process_file_func)
	Action.Action('command-output', func=CommandOutput._command_output_func, color='BLUE')
	Object.register('command-output', CommandOutput)

def detect(conf):
	return 1

