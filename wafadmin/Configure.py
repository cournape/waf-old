#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"""
Configuration system

A configuration instance is created when "waf configure" is called, it is used to:
* create data dictionaries (Environment instances)
* store the list of modules to import

The old model (copied from Scons) was to store logic (mapping file extensions to functions)
along with the data. In Waf a way was found to separate that logic by adding an indirection
layer (storing the names in the Environment instances)

In the new model, the logic is more object-oriented, and the user scripts provide the
logic. The data files (Environments) must contain configuration data only (flags, ..).

Note: the c/c++ related code is in the module config_c
"""

import os, types, imp, cPickle, sys
import Params, Environment, Runner, Build, Utils, Options
from Logs import *
from Constants import *

TEST_OK = True

class ConfigurationError(Exception):
	pass

autoconfig = False
"reconfigure the project automatically"

g_maxlen = 40
"""initial length of configuration messages"""

g_stdincpath = ['/usr/include/', '/usr/local/include/']
"""standard include paths"""

g_stdlibpath = ['/usr/lib/', '/usr/local/lib/', '/lib']
"""standard library search paths"""

#####################
## Helper functions

def find_file(filename, path_list):
	"""find a file in a list of paths
	@param filename: name of the file to search for
	@param path_list: list of directories to search
	@return: the first occurrence filename or '' if filename could not be found
"""
	if type(path_list) is types.StringType:
		lst = path_list.split()
	else:
		lst = path_list
	for directory in lst:
		if os.path.exists( os.path.join(directory, filename) ):
			return directory
	return ''

def find_file_ext(filename, path_list):
	"""find a file in a list of paths using fnmatch
	@param filename: name of the file to search for
	@param path_list: list of directories to search
	@return: the first occurrence filename or '' if filename could not be found
"""
	import fnmatch
	if type(path_list) is types.StringType:
		lst = path_list.split()
	else:
		lst = path_list
	for directory in lst:
		for path, subdirs, files in os.walk(directory):
			for name in files:
				if fnmatch.fnmatch(name, filename):
					return path
	return ''

def find_program_impl(env, filename, path_list=[], var=None):
	"""find a program in folders path_lst, and sets env[var]
	@param env: environment
	@param filename: name of the program to search for
	@param path_list: list of directories to search for filename
	@param var: environment value to be checked for in env or os.environ
	@return: either the value that is referenced with [var] in env or os.environ
         or the first occurrence filename or '' if filename could not be found
"""
	try: path_list = path_list.split()
	except AttributeError: pass

	if var:
		if var in os.environ: env[var] = os.environ[var]
		if env[var]: return env[var]

	if not path_list: path_list = os.environ['PATH'].split(os.pathsep)

	if Params.g_platform=='win32':
		# TODO isnt fnmatch for this?
		for y in [filename+x for x in '.exe,.com,.bat,.cmd'.split(',')]:
			for directory in path_list:
				x = os.path.join(directory, y)
				if os.path.isfile(x):
					if var: env[var] = x
					return x
	else:
		for directory in path_list:
			x = os.path.join(directory, filename)
			if os.access(x, os.X_OK) and os.path.isfile(x):
				if var: env[var] = x
				return x
	return ''

class Configure(object):
	tests = {}
	error_handlers = []
	def __init__(self, env=None, blddir='', srcdir=''):
		self.env       = None
		self.m_envname = ''

		self.m_blddir  = blddir
		self.m_srcdir  = srcdir

		self.m_allenvs = {}
		self.defines = {}
		self.cwd = os.getcwd()

		self.tools = [] # tools loaded in the configuration, and that will be loaded when building

		self.setenv('default')

		self.m_cache_table = {}

		self.lastprog = ''

		# load the cache
		if Options.cache_global and not Options.options.nocache:
			fic = os.path.join(Options.cache_global, Params.g_conf_name)
			try:
				file = open(fic, 'rb')
			except (OSError, IOError):
				pass
			else:
				try:
					self.m_cache_table = cPickle.load(file)
				finally:
					file.close()

		self.hash = 0
		self.files = []

		path = os.path.join(self.m_blddir, WAF_CONFIG_LOG)
		try: os.unlink(path)
		except (OSError, IOError): pass
		self.log = open(path, 'wb')

	def errormsg(self, msg):
		Params.niceprint(msg, 'ERROR', 'Configuration')

	def fatal(self, msg):
		raise ConfigurationError(msg)

	def check_tool(self, input, tooldir=None, funs=None):
		"load a waf tool"
		tools = Utils.to_list(input)
		if tooldir: tooldir = Utils.to_list(tooldir)
		for tool in tools:
			try:
				file,name,desc = imp.find_module(tool, tooldir)
			except ImportError, ex:
				raise ConfigurationError("no tool named '%s' found (%s)" % (tool, str(ex)))
			module = imp.load_module(tool, file, name, desc)

			func = getattr(module, 'detect', None)
			if func:
				if type(func) is types.FunctionType: func(self)
				else: self.eval_rules(funs or func)

			self.tools.append({'tool':tool, 'tooldir':tooldir, 'funs':funs})

	def sub_config(self, dir):
		"executes the configure function of a wscript module"

		current = self.cwd

		self.cwd = os.path.join(self.cwd, dir)
		cur = os.path.join(self.cwd, WSCRIPT_FILE)

		try:
			mod = Utils.load_module(cur)
		except IOError:
			fatal("the wscript file %s was not found." % cur)

		if not hasattr(mod, 'configure'):
			fatal('the module %s has no configure function; make sure such a function is defined' % cur)

		ret = mod.configure(self)
		global autoconfig
		if autoconfig:
			self.hash = Utils.hash_function_with_globals(self.hash, mod.configure)
			self.files.append(os.path.abspath(cur))
		self.cwd = current
		return ret

	def store(self, file=''):
		"save the config results into the cache file"
		if not os.path.isdir(Params.g_cachedir):
			os.makedirs(Params.g_cachedir)

		file = open(os.path.join(Params.g_cachedir, 'build.config.py'), 'w')
		file.write('version = 0x%x\n' % HEXVERSION)
		file.write('tools = %r\n' % self.tools)
		file.close()

		if not self.m_allenvs:
			fatal("nothing to store in Configure !")
		for key in self.m_allenvs:
			tmpenv = self.m_allenvs[key]
			tmpenv.store(os.path.join(Params.g_cachedir, key+CACHE_SUFFIX))

	def __del__(self):
		"""cleanup function:
		close config.log, store config results when there is a cache directory"""
		if Options.cache_global:
			# not during the build
			if not os.path.isdir(Options.cache_global):
				os.makedirs(Options.cache_global)

			fic = os.path.join(Options.cache_global, Params.g_conf_name)
			file = open(fic, 'wb')
			try:
				cPickle.dump(self.m_cache_table, file)
			finally:
				if file: file.close()

		if self.log:
			self.log.close()

	def set_env_name(self, name, env):
		"add a new environment called name"
		self.m_allenvs[name] = env
		return env

	def retrieve(self, name, fromenv=None):
		"retrieve an environment called name"
		try:
			env = self.m_allenvs[name]
		except KeyError:
			env = Environment.Environment()
			self.m_allenvs[name] = env
		else:
			if fromenv: warn("The environment %s may have been configured already" % name)
		return env

	def setenv(self, name):
		"enable the environment called name"
		self.env = self.retrieve(name)
		self.envname = name

	def add_os_flags(self, var, dest=None):
		if not dest: dest = var
		# do not use 'get' to make certain the variable is not defined
		try: self.env[dest] = os.environ[var]
		except KeyError: pass

	def check_message(self, type, msg, state, option=''):
		"print an checking message. This function is used by other checking functions"
		sr = 'Checking for %s %s' % (type, msg)
		global g_maxlen
		g_maxlen = max(g_maxlen, len(sr))
		print "%s :" % sr.ljust(g_maxlen),

		p = Utils.pprint
		if state: p('GREEN', 'ok ' + option)
		else: p('YELLOW', 'not found')
		self.log.write(sr + '\n\n')

	def check_message_custom(self, type, msg, custom, option='', color='PINK'):
		"""print an checking message. This function is used by other checking functions"""
		sr = 'Checking for ' + type + ' ' + msg
		global g_maxlen
		g_maxlen = max(g_maxlen, len(sr))
		print "%s :" % sr.ljust(g_maxlen),
		Utils.pprint(color, custom)
		self.log.write(sr + '\n\n')

	def find_program(self, program_name, path_list=[], var=None):
		"wrapper provided for convenience"
		ret = find_program_impl(self.env, program_name, path_list, var)
		self.check_message('program', program_name, ret, ret)
		return ret

	def check_pkg(self, modname, destvar='', vnum='', pkgpath='', pkgbin='',
	              pkgvars=[], pkgdefs={}, mandatory=False):
		"wrapper provided for convenience"
		pkgconf = self.create_pkgconfig_configurator()

		if not destvar: destvar = modname.upper()

		pkgconf.uselib_store = destvar
		pkgconf.name = modname
		pkgconf.version = vnum
		if pkgpath: pkgconf.pkgpath = pkgpath
		pkgconf.binary = pkgbin
		pkgconf.variables = pkgvars
		pkgconf.defines = pkgdefs
		pkgconf.mandatory = mandatory
		return pkgconf.run()

	def pkgconfig_fetch_variable(self,pkgname,variable,pkgpath='',pkgbin='',pkgversion=0,env=None):
		if not env: env=self.env

		if not pkgbin: pkgbin='pkg-config'
		if pkgpath: pkgpath='PKG_CONFIG_PATH=$PKG_CONFIG_PATH:'+pkgpath
		pkgcom = '%s %s' % (pkgpath, pkgbin)
		if pkgversion:
			ret = os.popen("%s --atleast-version=%s %s" % (pkgcom, pkgversion, pkgname)).close()
			self.conf.check_message('package %s >= %s' % (pkgname, pkgversion), '', not ret)
			if ret:
				return '' # error
		else:
			ret = os.popen("%s %s" % (pkgcom, pkgname)).close()
			self.check_message('package %s ' % (pkgname), '', not ret)
			if ret:
				return '' # error

		return os.popen('%s --variable=%s %s' % (pkgcom, variable, pkgname)).read().strip()

	def eval_rules(self, rules):
		self.rules = Utils.to_list(rules)
		for x in self.rules:
			f = getattr(self, x)
			try:
				f()
			except Exception, e:
				if err_handler(x, e) == STOP:
					break
				else:
					raise
	def err_handler(self, error):
		pass

def conf(f):
	"decorator: attach new configuration functions"
	setattr(Configure, f.__name__, f)
	return f

def conftest(f):
	"decorator: attach new configuration tests (registered as strings)"
	setattr(Configure, f.__name__, f)
	Configure.tests[f.__name__] = f
	return f

