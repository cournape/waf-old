#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"""
Custom objects:
 - execute a function everytime
 - copy a file somewhere else
"""

import shutil, re, os, types

import Object, Action, Node, Params, Task, Common
import pproc as subprocess
from Params import fatal, debug

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
		self.install_var = ''
		self.install_subdir = ''

	def apply(self):
		# create a task
		if not self.fun: fatal('cmdobj needs a function!')
		self.m_tasks.append(Task.TaskCmd(self.fun, self.env))

	def install(self):
		if not self.install_var:
			return
		current = Params.g_build.m_curdirnode
		for task in self.m_tasks:
			out = task.m_outputs[0]
			Common.install_files(self.install_var, self.install_subdir, out.abspath(self.env), self.env)


class copyobj(Object.genobj):
	"By default, make a file copy, if fun is provided, fun will make the copy (or call a compiler, etc)"
	def __init__(self, type='none'):
		Object.genobj.__init__(self, 'other')

		self.source = ''
		self.target = ''
		self.chmod  = ''
		self.fun = copy_func

		self.env = Params.g_build.env().copy()

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

		self.install_var = ''
		self.install_subdir = ''

	def install(self):
		if not self.install_var:
			return
		current = Params.g_build.m_curdirnode
		for task in self.m_tasks:
			out = task.m_outputs[0]
			Common.install_files(self.install_var, self.install_subdir, out.abspath(self.env), self.env)

	def apply(self):

		lst = self.to_list(self.source)

		for filename in lst:
			node = self.path.find_source(filename)
			if not node: fatal('cannot find input file %s for processing' % filename)

			newnode = node.change_ext('')

			if self.dict and not self.env['DICT_HASH']:
				self.env = self.env.copy()
				self.env['DICT_HASH'] = hash(str(self.dict)) # <- pretty sure it wont work (ita)

			task = self.create_task('copy', self.env, self.prio)
			task.set_inputs(node)
			task.set_outputs(newnode)
			task.m_env = self.env
			task.fun = self.fun
			task.dict = self.dict
			task.dep_vars = ['DICT_HASH']

			if not task.m_env:
				task.debug()
				fatal('task witout an environment')

class CommandOutputTask(Task.Task):

	def __init__(self, env, priority, command, command_node, command_args, stdin, stdout, cwd):
		Task.Task.__init__(self, 'command-output', env, prio=priority, normal=1)
		assert isinstance(command, (str, Node.Node))
		self.command = command
		self.command_args = command_args
		self.stdin = stdin
		self.stdout = stdout
		self.cwd = cwd

		if command_node is not None: self.dep_nodes = [command_node]
		self.dep_vars = [] # additional environment variables to look

class CommandOutput(Object.genobj):

	CMD_ARGV_INPUT, CMD_ARGV_OUTPUT, CMD_ARGV_INPUT_DIR, CMD_ARGV_OUTPUT_DIR = range(4)

	def __init__(self, env=None):
		Object.genobj.__init__(self, 'other')
		self.env = env
		if not self.env:
			self.env = Params.g_build.env().copy()

		self.stdin = None
		self.stdout = None

		# the command to execute
		self.command = None

		# whether it is an external command; otherwise it is assumed
		# to be an executable binary or script that lives in the
		# source or build tree.
		self.command_is_external = False

		# extra parameters (argv) to pass to the command (excluding
		# the command itself)
		self.argv = []

		# task priority
		self.prio = 100

		# dependencies to other objects -> this is probably not what you want (ita)
		# values must be 'genobj' instances (not names!)
		self.dependencies = []

		# dependencies on env variable contents
		self.dep_vars = []

		# input files that are implicit, i.e. they are not
		# stdin, nor are they mentioned explicitly in argv
		self.hidden_inputs = []

		# output files that are implicit, i.e. they are not
		# stdout, nor are they mentioned explicitly in argv
		self.hidden_outputs = []

		# change the subprocess to this cwd (must use obj.input_dir() or output_dir() here)
		self.cwd = None

	def _command_output_func(task):
		assert len(task.m_inputs) > 0

		def input_path(node, template):
			if task.cwd is None:
				return template % node.bldpath(task.m_env)
			else:
				return template % node.abspath()
		def output_path(node, template):
			fun = node.abspath
			if task.cwd is None: fun = node.bldpath
			return template % fun(task.m_env)

		if isinstance(task.command, Node.Node):
			argv = [input_path(task.command, '%s')]
		else:
			argv = [task.command]

		for arg in task.command_args:
			if isinstance(arg, str):
				argv.append(arg)
			else:
				role, node, template = arg
				if role in (CommandOutput.CMD_ARGV_INPUT, CommandOutput.CMD_ARGV_INPUT_DIR):
					argv.append(input_path(node, template))
				elif role in (CommandOutput.CMD_ARGV_OUTPUT, CommandOutput.CMD_ARGV_OUTPUT_DIR):
					argv.append(output_path(node, template))
				else:
					raise AssertionError

		if task.stdin:
			stdin = file(input_path(task.stdin, '%s'))
		else:
			stdin = None

		if task.stdout:
			stdout = file(output_path(task.stdout, '%s'), "w")
		else:
			stdout = None

		if task.cwd is None:
			cwd = ('None (actually %r)' % os.getcwd())
		else:
			cwd = repr(task.cwd)
		Params.debug("command-output: cwd=%s, stdin=%r, stdout=%r, argv=%r" %
			     (cwd, stdin, stdout, argv))
		command = subprocess.Popen(argv, stdin=stdin, stdout=stdout, cwd=task.cwd)
		return command.wait()

	_command_output_func = staticmethod(_command_output_func)

	def apply(self):
		if self.command is None:
			Params.fatal("command-output missing command")
		if self.command_is_external:
			cmd = self.command
			cmd_node = None
		else:
			cmd_node = self.path.find_build(self.command, create=True)
			assert cmd_node is not None, ('''Could not find command '%s' in source tree.
Hint: if this is an external command,
use command_is_external=True''') % (self.command,)
			cmd = cmd_node

		if self.cwd is None:
			cwd = None
		else:
			role, file_name, template = self.cwd
			if role == CommandOutput.CMD_ARGV_INPUT_DIR:
				if isinstance(file_name, Node.Node):
					input_node = file_name
				else:
					input_node = self.path.find_dir(file_name)
					if input_node is None:
						Params.fatal("File %s not found" % (file_name,))
				cwd = input_node.abspath()
			elif role == CommandOutput.CMD_ARGV_OUTPUT_DIR:
				if isinstance(file_name, Node.Node):
					output_node = file_name
				else:
					output_node = self.path.find_dir(file_name)
					if output_node is None:
						Params.fatal("File %s not found" % (file_name,))
				cwd = output_node.abspath(self.env)
			else:
				raise AssertionError

		args = []
		inputs = []
		outputs = []

		for arg in self.argv:
			if isinstance(arg, str):
				args.append(arg)
			else:
				role, file_name, template = arg
				if role == CommandOutput.CMD_ARGV_INPUT:
					if isinstance(file_name, Node.Node):
						input_node = file_name
					else:
						input_node = self.path.find_build(file_name, create=True)
						if input_node is None:
							Params.fatal("File %s not found" % (file_name,))
					inputs.append(input_node)
					args.append((role, input_node, template))
				elif role == CommandOutput.CMD_ARGV_OUTPUT:
					if isinstance(file_name, Node.Node):
						output_node = file_name
					else:
						output_node = self.path.find_build(file_name, create=True)
						if output_node is None:
							Params.fatal("File %s not found" % (file_name,))
					outputs.append(output_node)
					args.append((role, output_node, template))
				elif role == CommandOutput.CMD_ARGV_INPUT_DIR:
					if isinstance(file_name, Node.Node):
						input_node = file_name
					else:
						input_node = self.path.find_dir(file_name)
						if input_node is None:
							Params.fatal("File %s not found" % (file_name,))
					args.append((role, input_node, template))
				elif role == CommandOutput.CMD_ARGV_OUTPUT_DIR:
					if isinstance(file_name, Node.Node):
						output_node = file_name
					else:
						output_node = self.path.find_dir(file_name)
						if output_node is None:
							Params.fatal("File %s not found" % (file_name,))
					args.append((role, output_node, template))
				else:
					raise AssertionError

		if self.stdout is None:
			stdout = None
		else:
			stdout = self.path.find_build(self.stdout, create=True)
			if stdout is None:
				Params.fatal("File %s not found" % (self.stdout,))
			outputs.append(stdout)

		if self.stdin is None:
			stdin = None
		else:
			stdin = self.path.find_build(self.stdin, create=True)
			if stdin is None:
				Params.fatal("File %s not found" % (self.stdin,))
			inputs.append(stdin)

		for hidden_input in self.to_list(self.hidden_inputs):
			node = self.path.find_build(hidden_input, create=True)
			if node is None:
				Params.fatal("File %s not found in dir %s" % (hidden_input, self.path))
			inputs.append(node)

		for hidden_output in self.to_list(self.hidden_outputs):
			node = self.path.find_build(hidden_output, create=True)
			if node is None:
				Params.fatal("File %s not found in dir %s" % (hidden_output, self.path))
			outputs.append(node)

		if not inputs:
			Params.fatal("command-output objects must have at least one input file")
		if not outputs:
			Params.fatal("command-output objects must have at least one output file")

		task = CommandOutputTask(self.env, self.prio,
					 cmd, cmd_node, args,
					 stdin, stdout, cwd)
		self.m_tasks.append(task)

		task.set_inputs(inputs)
		task.set_outputs(outputs)
		task.dep_vars = self.to_list(self.dep_vars)


		for dep in self.dependencies:
			assert dep is not self
			if not dep.m_posted:
				dep.post()
			for dep_task in dep.m_tasks:
				task.set_run_after(dep_task)

	def input_file(self, file_name, template='%s'):
		"""Returns an object to be used as argv element that instructs
		the task to use a file from the input vector at the given
		position as argv element."""
		return (CommandOutput.CMD_ARGV_INPUT, file_name, template)

	def output_file(self, file_name, template='%s'):
		"""Returns an object to be used as argv element that instructs
		the task to use a file from the output vector at the given
		position as argv element."""
		return (CommandOutput.CMD_ARGV_OUTPUT, file_name, template)

	def input_dir(self, file_name, template='%s'):
		"""Returns an object to be used as argv element that instructs
		the task to use a directory path from the input vector at the given
		position as argv element."""
		return (CommandOutput.CMD_ARGV_INPUT_DIR, file_name, template)

	def output_dir(self, file_name, template='%s'):
		"""Returns an object to be used as argv element that instructs
		the task to use a directory path from the output vector at the given
		position as argv element."""
		return (CommandOutput.CMD_ARGV_OUTPUT_DIR, file_name, template)

	def install(self):
		pass

def setup(bld):
	Object.register('cmd', cmdobj)
	Object.register('copy', copyobj)
	Object.register('subst', substobj)
	Action.Action('copy', vars=[], func=action_process_file_func)
	Action.Action('command-output', func=CommandOutput._command_output_func, color='BLUE')
	Object.register('command-output', CommandOutput)

