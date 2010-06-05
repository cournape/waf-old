#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
Base classes (mostly abstract)
"""

import traceback, os, imp, sys
from wafadmin import Utils, Errors, Logs
import wafadmin.Node

g_module = None
"""
wscript file representing the entry point of the project
"""

WSCRIPT_FILE = 'wscript'

# do not touch these 5 lines, they are updated automatically
HEXVERSION = 0x106000
WAFVERSION="1.6.0"
WAFREVISION = "XXXXX"
ABI = 98
DBFILE = '.wafpickle-%d' % ABI

APPNAME = 'APPNAME'
VERSION = 'VERSION'

SRCDIR  = 'top'
BLDDIR  = 'out'

classes = []
def create_context(cmd_name, *k, **kw):
	"""TODO warn if more than one context is provided for a given command?"""
	global classes
	for x in classes:
		if x.cmd == cmd_name:
			return x(*k, **kw)
	ctx = Context(*k, **kw)
	ctx.fun = cmd_name
	return ctx

class store_context(type):
	"""metaclass: store the command classes into a global list"""
	def __init__(cls, name, bases, dict):
		super(store_context, cls).__init__(name, bases, dict)
		name = cls.__name__

		if name == 'ctx' or name == 'Context':
			return

		try:
			cls.cmd
		except AttributeError:
			raise Errors.WafError('Missing command for the context class %r (cmd)' % name)

		if not getattr(cls, 'fun', None):
			cls.fun = cls.cmd

		global classes
		classes.append(cls)

# metaclass
ctx = store_context('ctx', (object,), {})

class Context(ctx):
	"""
	Base class for command contexts. Those objects are passed as the arguments
	of user functions (commands) defined in Waf scripts.
	"""

	errors = Errors

	def __init__(self, start=None):
		if not start:
			from wafadmin import Options
			start = Options.run_dir

		# bind the build context to the nodes in use
		# this means better encapsulation and no context singleton
		class node_class(wafadmin.Node.Node):
			pass
		self.node_class = wafadmin.Node.Nod3 = node_class
		self.node_class.__module__ = "wafadmin.Node"
		self.node_class.__name__ = "Nod3"
		self.node_class.bld = self

		self.root = wafadmin.Node.Nod3('', None)
		self.cur_script = None
		self.path = self.root.find_dir(start)

		self.stack_path = []
		self.exec_dict = {'ctx':self, 'conf':self, 'bld':self, 'opt':self}

	def execute(self):
		"""executes the command represented by this context"""
		global g_module
		self.recurse(os.path.dirname(g_module.root_path))

	def pre_recurse(self, node):
		"""from the context class"""
		self.stack_path.append(self.cur_script)

		self.cur_script = node
		self.path = node.parent

	def post_recurse(self, node):
		"""from the context class"""
		self.cur_script = self.stack_path.pop()
		if self.cur_script:
			self.path = self.cur_script.parent

	def recurse(self, dirs, name=None):
		"""
		Run user code from the supplied list of directories.
		The directories can be either absolute, or relative to the directory
		of the wscript file.
		@param dirs: List of directories to visit
		@type  name: string
		@param name: Name of function to invoke from the wscript
		"""
		for d in Utils.to_list(dirs):

			if not os.path.isabs(d):
				# absolute paths only
				d = os.path.join(self.path.abspath(), d)

			WSCRIPT     = os.path.join(d, WSCRIPT_FILE)
			WSCRIPT_FUN = WSCRIPT + '_' + self.fun

			node = self.root.find_node(WSCRIPT_FUN)
			if node:
				self.pre_recurse(node)
				function_code = node.read('rU')

				try:
					exec(function_code, self.exec_dict)
				except Exception:
					raise Errors.WscriptError(traceback.format_exc(), d)
				self.post_recurse(node)

			else:
				node = self.root.find_node(WSCRIPT)
				if not node:
					raise Errors.WscriptError('No wscript file in directory %s' % d)
				self.pre_recurse(node)
				wscript_module = load_module(node.abspath())
				user_function = getattr(wscript_module, self.fun, None)
				if not user_function:
					raise Errors.WscriptError('No function %s defined in %s' % (self.fun, node.abspath()))
				user_function(self)
				self.post_recurse(node)

	def msg(self, msg, result, color=None):
		"""Prints a configuration message 'Checking for xxx: ok'"""
		self.start_msg('Checking for ' + msg)

		if not isinstance(color, str):
			color = color and 'GREEN' or 'YELLOW'

		self.end_msg(result, color)

	def start_msg(self, msg):
		"""Prints the beginning of a 'Checking for xxx' message"""
		try:
			if self.in_msg:
				self.in_msg += 1
				return
		except:
			self.in_msg = 0
		self.in_msg += 1

		try:
			self.line_just = max(self.line_just, len(msg))
		except AttributeError:
			self.line_just = max(40, len(msg))
		for x in ('\n', self.line_just * '-', '\n', msg, '\n'):
			if self.log:
				self.log.write(x)
		Logs.pprint('NORMAL', "%s :" % msg.ljust(self.line_just), sep='')

	def end_msg(self, result, color=None):
		"""Prints the end of a 'Checking for' message"""
		self.in_msg -= 1
		if self.in_msg:
			return

		defcolor = 'GREEN'
		if result == True:
			msg = 'ok'
		elif result == False:
			msg = 'not found'
			defcolor = 'YELLOW'
		else:
			msg = str(result)

		color = color or defcolor
		if self.log:
			self.log.write(msg)
			self.log.write('\n')
		Logs.pprint(color, msg)


cache_modules = {}
"""
Dictionary holding already loaded modules, keyed by their absolute path.
private cache
"""

def load_module(file_path):
	"""
	Load a Python source file containing user code.
	@type  file_path: string
	@param file_path: Directory of the python file
	@type  name: string
	@param name: Basename of file with user code (default: "wscript")
	@rtype: module
	@return: Loaded Python module
	"""
	try:
		return cache_modules[file_path]
	except KeyError:
		pass

	module = imp.new_module(WSCRIPT_FILE)
	try:
		code = Utils.readf(file_path, m='rU')
	except (IOError, OSError):
		raise Errors.WscriptError('Could not read the file %r' % file_path)

	module_dir = os.path.dirname(file_path)
	sys.path.insert(0, module_dir)
	try:
		exec(code, module.__dict__)
	except Exception as e:
		try:
			ex = Errors.WscriptError(traceback.format_exc(), file_path)
		except:
			raise e
		else:
			raise ex
	sys.path.remove(module_dir)

	cache_modules[file_path] = module

	return module

def load_tool(tool, tooldir=None):
	"""
	Import the Python module that contains the specified tool from
	the tools directory.
	@type  tool: string
	@param tool: Name of the tool
	@type  tooldir: list
	@param tooldir: List of directories to search for the tool module
	"""
	tool = tool.replace('++', 'xx')
	tool = tool.replace('java', 'javaw')

	if tooldir:
		assert isinstance(tooldir, list)
		sys.path = tooldir + sys.path
		try:
			__import__(tool)
			return sys.modules[tool]
		except ImportError:
			raise Errors.WscriptError('Could not load the tool %r in %r' % (tool, sys.path))
		for d in tooldir:
			sys.path.remove(d)
	else:
		for x in ['Tools', 'extras']:
			imp = 'wafadmin.%s.%s' % (x, tool)
			try:
				__import__(imp)
			except ImportError:
				pass
			else:
				return sys.modules[imp]
		else:
			raise Errors.WscriptError('Could not load the waf tool %r' % tool)

