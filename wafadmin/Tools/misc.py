#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"""
Custom objects:
 - execute a function everytime
 - copy a file somewhere else
"""

import shutil, re, os, types

import TaskGen, Node, Params, Task, Common
import pproc as subprocess
from Params import fatal, debug

def copy_func(tsk):
	"Make a file copy. This might be used to make other kinds of file processing (even calling a compiler is possible)"
	env = tsk.env()
	infile = tsk.m_inputs[0].abspath(env)
	outfile = tsk.m_outputs[0].abspath(env)
	try:
		shutil.copy2(infile, outfile)
	except OSError, IOError:
		return 1
	else:
		if tsk.chmod: os.chmod(outfile, tsk.chmod)
		return 0

def action_process_file_func(tsk):
	"Ask the function attached to the task to process it"
	if not tsk.fun: fatal('task must have a function attached to it for copy_func to work!')
	return tsk.fun(tsk)

class cmd_taskgen(TaskGen.task_gen):
	"This object will call a command everytime"
	def __init__(self, type='none'):
		TaskGen.task_gen.__init__(self)
		self.m_type = type
		self.prio   = 1
		self.fun    = None
		self.inst_var = ''
		self.inst_dir = ''

	def apply(self):
		# create a task
		if not self.fun: fatal('cmdobj needs a function!')
		tsk = Task.TaskCmd(self.fun, self.env)
		tsk.prio = self.prio
		self.m_tasks.append(tsk)
		tsk.install = {'var': self.inst_var, 'dir': self.inst_dir}

class copy_taskgen(TaskGen.task_gen):
	"By default, make a file copy, if fun is provided, fun will make the copy (or call a compiler, etc)"
	def __init__(self, type='none'):
		TaskGen.task_gen.__init__(self)

		self.source = ''
		self.target = ''
		self.chmod  = ''
		self.fun = copy_func

		self.env = Params.g_build.env().copy()

	def apply(self):

		lst = self.to_list(self.source)

		for filename in lst:
			node = self.path.find_resource(filename)
			if not node: fatal('cannot find input file %s for processing' % filename)

			target = self.target
			if not target or len(lst)>1: target = node.m_name

			# TODO the file path may be incorrect
			newnode = self.path.find_or_declare(target)

			tsk = self.create_task('copy', self.env, 10)
			tsk.set_inputs(node)
			tsk.set_outputs(newnode)
			tsk.m_env = self.env
			tsk.fun = self.fun
			tsk.chmod = self.chmod

			if not tsk.env():
				tsk.debug()
				fatal('task witout an environment')

def subst_func(tsk):
	"Substitutes variables in a .in file"

	m4_re = re.compile('@(\w+)@', re.M)

	env = tsk.env()
	infile = tsk.m_inputs[0].abspath(env)
	outfile = tsk.m_outputs[0].abspath(env)

	file = open(infile, 'r')
	code = file.read()
	file.close()

	s = m4_re.sub(r'%(\1)s', code)

	dict = tsk.dict
	if not dict:
		names = m4_re.findall(code)
		for i in names:
			if env[i] and type(env[i]) is types.ListType :
				dict[i] = " ".join(env[i])
			else: dict[i] = env[i]

	file = open(outfile, 'w')
	file.write(s % dict)
	file.close()

	return 0

class subst_taskgen(TaskGen.task_gen):
	def __init__(self, type='none'):
		TaskGen.task_gen.__init__(self)
		self.fun = subst_func
		self.dict = {}
		self.prio = 8

		self.inst_var = ''
		self.inst_dir = ''

	def apply(self):

		lst = self.to_list(self.source)

		for filename in lst:
			node = self.path.find_resource(filename)
			if not node: fatal('cannot find input file %s for processing' % filename)

			newnode = node.change_ext('')

			if self.dict and not self.env['DICT_HASH']:
				self.env = self.env.copy()
				self.env['DICT_HASH'] = hash(str(self.dict)) # <- pretty sure it wont work (ita)

			tsk = self.create_task('copy', self.env, self.prio)
			tsk.set_inputs(node)
			tsk.set_outputs(newnode)
			tsk.m_env = self.env
			tsk.fun = self.fun
			tsk.dict = self.dict
			tsk.dep_vars = ['DICT_HASH']
			tsk.install = {'var': self.inst_var, 'dir': self.inst_dir}

			if not tsk.env():
				tsk.debug()
				fatal('task witout an environment')



####################
## command-output ####
####################

class CmdArg(object):
	"""Represents a command-output argument that is based on input or output files or directories"""
	pass

class CmdFileArg(CmdArg):
	def __init__(self, file_name, template=None):
		CmdArg.__init__(self)
		self.file_name = file_name
		if template is None:
			self.template = '%s'
		else:
			self.template = template
		self.node = None

class CmdInputFileArg(CmdFileArg):
	def find_node(self, base_path):
		assert isinstance(base_path, Node.Node)
		self.node = base_path.find_resource(self.file_name)
		if self.node is None:
			Params.fatal("Input file %s not found in " % (self.file_name, base_path))

	def get_path(self, env, absolute):
		if absolute:
			return self.template % self.node.abspath(env)
		else:
			return self.template % self.node.srcpath(env)

class CmdOutputFileArg(CmdFileArg):
	def find_node(self, base_path):
		assert isinstance(base_path, Node.Node)
		self.node = base_path.find_or_declare(self.file_name)
		if self.node is None:
			Params.fatal("Output file %s not found in " % (self.file_name, base_path))
	def get_path(self, env, absolute):
		if absolute:
			return self.template % self.node.abspath(env)
		else:
			return self.template % self.node.bldpath(env)

class CmdDirArg(CmdArg):
	def __init__(self, dir_name):
		CmdArg.__init__(self)
		self.dir_name = dir_name
		self.node = None
	def find_node(self, base_path):
		assert isinstance(base_path, Node.Node)
		self.node = base_path.find_dir(self.dir_name)
		if self.node is None:
			Params.fatal("Directory %s not found in " % (self.dir_name, base_path))

class CmdInputDirArg(CmdDirArg):
	def get_path(self, dummy_env, dummy_absolute):
		return self.node.abspath()

class CmdOutputDirArg(CmdFileArg):
	def get_path(self, env, dummy_absolute):
		return self.node.abspath(env)


class command_output(Task.Task):
	m_color = "BLUE"
	def __init__(self, env, priority, command, command_node, command_args, stdin, stdout, cwd, os_env):
		Task.Task.__init__(self, 'command-output', env, prio=priority, normal=1)
		assert isinstance(command, (str, Node.Node))
		self.command = command
		self.command_args = command_args
		self.stdin = stdin
		self.stdout = stdout
		self.cwd = cwd
		self.os_env = os_env

		if command_node is not None: self.dep_nodes = [command_node]
		self.dep_vars = [] # additional environment variables to look

	def run(self):
		task = self
		assert len(task.m_inputs) > 0

		def input_path(node, template):
			if task.cwd is None:
				return template % node.bldpath(task.env())
			else:
				return template % node.abspath()
		def output_path(node, template):
			fun = node.abspath
			if task.cwd is None: fun = node.bldpath
			return template % fun(task.env())

		if isinstance(task.command, Node.Node):
			argv = [input_path(task.command, '%s')]
		else:
			argv = [task.command]

		for arg in task.command_args:
			if isinstance(arg, str):
				argv.append(arg)
			else:
				assert isinstance(arg, CmdArg)
				argv.append(arg.get_path(task.env(), (task.cwd is not None)))

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

		if task.os_env is None:
			os_env = os.environ
		else:
			os_env = task.os_env
		command = subprocess.Popen(argv, stdin=stdin, stdout=stdout, cwd=task.cwd, env=os_env)
		return command.wait()

class cmd_output_taskgen(TaskGen.task_gen):

	def __init__(self, *k):
		TaskGen.task_gen.__init__(self, *k)

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
		# values must be 'task_gen' instances (not names!)
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

		# OS environment variables to pass to the subprocess
		# if None, use the default environment variables unchanged
		self.os_env = None


	def apply(self):
		if self.command is None:
			Params.fatal("command-output missing command")
		if self.command_is_external:
			cmd = self.command
			cmd_node = None
		else:
			cmd_node = self.path.find_resource(self.command)
			assert cmd_node is not None, ('''Could not find command '%s' in source tree.
Hint: if this is an external command,
use command_is_external=True''') % (self.command,)
			cmd = cmd_node

		if self.cwd is None:
			cwd = None
		else:
			assert isinstance(cwd, CmdDirArg)
			self.cwd.find_node(self.path)

		args = []
		inputs = []
		outputs = []

		for arg in self.argv:
			if isinstance(arg, CmdArg):
				arg.find_node(self.path)
				if isinstance(arg, CmdInputFileArg):
					inputs.append(arg.node)
				if isinstance(arg, CmdOutputFileArg):
					outputs.append(arg.node)

		if self.stdout is None:
			stdout = None
		else:
                        assert isinstance(self.stdout, basestring)
			stdout = self.path.find_or_declare(self.stdout)
			if stdout is None:
				Params.fatal("File %s not found" % (self.stdout,))
			outputs.append(stdout)

		if self.stdin is None:
			stdin = None
		else:
                        assert isinstance(self.stdin, basestring)
			stdin = self.path.find_resource(self.stdin)
			if stdin is None:
				Params.fatal("File %s not found" % (self.stdin,))
			inputs.append(stdin)

		for hidden_input in self.to_list(self.hidden_inputs):
			node = self.path.find_resource(hidden_input)
			if node is None:
				Params.fatal("File %s not found in dir %s" % (hidden_input, self.path))
			inputs.append(node)

		for hidden_output in self.to_list(self.hidden_outputs):
			node = self.path.find_or_declare(hidden_output)
			if node is None:
				Params.fatal("File %s not found in dir %s" % (hidden_output, self.path))
			outputs.append(node)

		if not inputs:
			Params.fatal("command-output objects must have at least one input file")
		if not outputs:
			Params.fatal("command-output objects must have at least one output file")

		task = command_output(self.env, self.prio,
					 cmd, cmd_node, self.argv,
					 stdin, stdout, cwd, self.os_env)
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
		return CmdInputFileArg(file_name, template)

	def output_file(self, file_name, template='%s'):
		"""Returns an object to be used as argv element that instructs
		the task to use a file from the output vector at the given
		position as argv element."""
		return CmdOutputFileArg(file_name, template)

	def input_dir(self, dir_name):
		"""Returns an object to be used as argv element that instructs
		the task to use a directory path from the input vector at the given
		position as argv element."""
		return CmdInputDirArg(dir_name)

	def output_dir(self, dir_name):
		"""Returns an object to be used as argv element that instructs
		the task to use a directory path from the output vector at the given
		position as argv element."""
		return CmdOutputDirArg(dir_name)

Task.task_type_from_func('copy', vars=[], func=action_process_file_func)
TaskGen.task_gen.classes['command-output'] = cmd_output_taskgen

