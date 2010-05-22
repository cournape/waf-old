#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
Base classes (mostly abstract)
"""

import traceback, os, imp, sys
import Utils

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

class WafError(Exception):
	"""Base for all waf errors"""
	def __init__(self, *args):
		self.args = args
		try:
			self.stack = traceback.extract_stack()
		except:
			pass
		Exception.__init__(self, *args)
	def __str__(self):
		return str(len(self.args) == 1 and self.args[0] or self.args)

class WscriptError(WafError):
	"""Waf errors that come from python code"""
	def __init__(self, message, pyfile=None):
		if pyfile:
			self.pyfile = pyfile
			self.pyline = None
		else:
			try:
				(self.pyfile, self.pyline) = self.locate_error()
			except:
				(self.pyfile, self.pyline) = (None, None)

		msg_file_line = ''
		if self.pyfile:
			msg_file_line = "%s:" % self.pyfile
			if self.pyline:
				msg_file_line += "%s:" % self.pyline
		err_message = "%s error: %s" % (msg_file_line, message)
		WafError.__init__(self, err_message)

	def locate_error(self):
		stack = traceback.extract_stack()
		stack.reverse()
		for frame in stack:
			file_name = os.path.basename(frame[0])
			if file_name.find(WSCRIPT_FILE) > -1:
				return (frame[0], frame[1])
		return (None, None)

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
			raise WafError('Missing command for the context class %r (cmd)' % name)

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
	def __init__(self, start=None):
		if not start:
			import Options
			start = Options.run_dir
		self.curdir = start

	def pre_recurse(self, name_or_mod, path, nexdir):
		pass

	def post_recurse(self, name_or_mod, path, nextdir):
		pass

	def recurse(self, dirs, name=None):
		"""
		Run user code from the supplied list of directories.
		The directories can be either absolute, or relative to the directory
		of the wscript file.
		@param dirs: List of directories to visit
		@type  name: string
		@param name: Name of function to invoke from the wscript
		"""
		function_name = self.fun

		# convert to absolute paths
		dirs = Utils.to_list(dirs)
		dirs = [x if os.path.isabs(x) else os.path.join(self.curdir, x) for x in dirs]

		for d in dirs:
			wscript_file = os.path.join(d, WSCRIPT_FILE)
			partial_wscript_file = wscript_file + '_' + function_name

			# if there is a partial wscript with the body of the user function,
			# use it in preference
			if os.path.exists(partial_wscript_file):
				exec_dict = {'ctx':self, 'conf':self, 'bld':self, 'opt':self}
				function_code = Utils.readf(partial_wscript_file, m='rU')

				self.pre_recurse(function_code, partial_wscript_file, d)
				old_dir = self.curdir
				self.curdir = d
				try:
					exec(function_code, exec_dict)
				except Exception:
					raise WscriptError(traceback.format_exc(), d)
				finally:
					self.curdir = old_dir
				self.post_recurse(function_code, partial_wscript_file, d)

			# if there is only a full wscript file, use a suitably named
			# function from it
			elif os.path.exists(wscript_file):
				# do not catch any exceptions here
				wscript_module = load_module(wscript_file)
				user_function = getattr(wscript_module, function_name, None)
				if not user_function:
					raise WscriptError('No function %s defined in %s'
						% (function_name, wscript_file))
				self.pre_recurse(user_function, wscript_file, d)
				old_dir = self.curdir
				self.curdir = d

				try:
					user_function(self)
				finally:
					self.curdir = old_dir
				self.post_recurse(user_function, wscript_file, d)

			# no wscript file - raise an exception
			else:
				raise WscriptError('No wscript file in directory %s' % d)

	def prepare(self):
		"""Executed before the context is passed to the user function."""
		pass

	def run_user_code(self):
		"""Call the user function to which this context is bound."""
		f = getattr(g_module, self.fun, None)
		if f is None:
			raise WscriptError('Undefined command: %s' % self.fun)

		f(self)

	def finalize(self):
		"""Executed after the user function finishes."""
		pass

	def execute(self):
		"""Run the command represented by this context."""
		self.prepare()
		self.run_user_code()
		self.finalize()

g_loaded_modules = {}
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
		return g_loaded_modules[file_path]
	except KeyError:
		pass

	module = imp.new_module(WSCRIPT_FILE)
	try:
		code = Utils.readf(file_path, m='rU')
	except (IOError, OSError):
		raise WscriptError('Could not read the file %r' % file_path)

	module.waf_hash_val = code

	module_dir = os.path.dirname(file_path)
	sys.path.insert(0, module_dir)
	try:
		exec(code, module.__dict__)
	except Exception as e:
		try:
			ex = WscriptError(traceback.format_exc(), file_path)
		except:
			raise e
		else:
			raise ex
	sys.path.remove(module_dir)

	g_loaded_modules[file_path] = module

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
		try:
			return __import__(tool)
		except ImportError as e:
			raise WscriptError('Could not load the tool %r in %r' % (tool, sys.path))
	finally:
		if tooldir:
			for d in tooldir:
				sys.path.remove(d)

