#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
Configuration system

A configuration instance is created when "waf configure" is called, it is used to:
* create data dictionaries (ConfigSet instances)
* store the list of modules to import

The old model (copied from Scons) was to store logic (mapping file extensions to functions)
along with the data. In Waf a way was found to separate that logic by adding an indirection
layer (storing the names in the ConfigSet instances)

In the new model, the logic is more object-oriented, and the user scripts provide the
logic. The data files (ConfigSets) must contain configuration data only (flags, ..).

Note: the c/c++ related code is in the module config_c
"""

import os, shlex, sys, time
import ConfigSet, Utils, Options, Logs, Base

BREAK    = 'break'
"""in case of error, break"""

CONTINUE = 'continue'
"""in case of error, continue"""

CACHE_DIR = 'c4che'
"""location of the cache files"""

CACHE_SUFFIX = '.cache.py'
"""suffix for the cache files"""

WAF_CONFIG_LOG = 'config.log'
"""name of the configuration log file"""

try:
	from urllib import request
except:
	from urllib import urlopen
else:
	urlopen = request.urlopen

conf_template = '''# project %(app)s configured on %(now)s by
# waf %(wafver)s (abi %(abi)s, python %(pyver)x on %(systype)s)
# using %(args)s
#
'''

def download_tool(tool, force=False):
	"""downloads a tool from the waf repository"""
	for x in Utils.to_list(Options.remote_repo):
		for sub in ['branches/waf-%s/wafadmin/3rdparty' % Base.WAFVERSION, 'trunk/wafadmin/3rdparty']:
			url = '/'.join((x, sub, tool + '.py'))
			try:
				web = urlopen(url)
				if web.getcode() != 200:
					continue
			except Exception as e:
				continue
			else:
				try:
					loc = open(_3rdparty + os.sep + tool + '.py', 'wb')
					loc.write(web.read())
					web.close()
				finally:
					loc.close()
				Logs.warn('downloaded %s from %s' % (tool, url))
				return Base.load_tool(tool)
		else:
				break
		raise Errors.WafError('Could not load the tool')

class ConfigurationContext(Base.Context):
	"""configures the project"""

	cmd = 'configure'

	tests = {}
	error_handlers = []
	def __init__(self, start_dir=None, blddir='', srcdir=''):

		super(self.__class__, self).__init__(start_dir)
		self.env = None
		self.envname = ''

		self.environ = dict(os.environ)

		self.line_just = 40

		self.blddir = blddir
		self.srcdir = srcdir
		self.all_envs = {}

		self.tools = [] # tools loaded in the configuration, and that will be loaded when building

		self.setenv('default')

		self.lastprog = ''

		self.hash = 0
		self.files = []

		self.tool_cache = []

		if self.blddir:
			self.post_init()

	def post_init(self):

		self.cachedir = os.path.join(self.blddir, CACHE_DIR)

		path = os.path.join(self.blddir, WAF_CONFIG_LOG)
		try: os.unlink(path)
		except (OSError, IOError): pass

		try:
			self.log = open(path, 'w')
		except (OSError, IOError):
			self.fatal('could not open %r for writing' % path)

		app = getattr(Base.g_module, 'APPNAME', '')
		if app:
			ver = getattr(Base.g_module, 'VERSION', '')
			if ver:
				app = "%s (%s)" % (app, ver)

		now = time.ctime()
		pyver = sys.hexversion
		systype = sys.platform
		args = " ".join(sys.argv)
		wafver = Base.WAFVERSION
		abi = Base.ABI
		self.log.write(conf_template % vars())

	def __del__(self):
		"""cleanup function: close config.log"""

		# may be ran by the gc, not always after initialization
		if hasattr(self, 'log') and self.log:
			self.log.close()

	def fatal(self, msg):
		"""raise a configuration error"""
		raise ConfigurationError(msg)

	def check_tool(self, input, tooldir=None, funs=None, download=True):
		"loads a waf tool"

		tools = Utils.to_list(input)
		if tooldir: tooldir = Utils.to_list(tooldir)
		for tool in tools:
			# avoid loading the same tool more than once with the same functions
			# used by composite projects

			mag = (tool, id(self.env), funs)
			if mag in self.tool_cache:
				continue
			self.tool_cache.append(mag)

			#try:
			module = Base.load_tool(tool, tooldir)
			#except Exception as e:
			#	if 1:
			#		raise ConfigurationError(e)
			#	module = download_tool(tool)

			if funs is not None:
				self.eval_rules(funs)
			else:
				func = getattr(module, 'configure', None)
				if func:
					if type(func) is type(Utils.readf): func(self)
					else: self.eval_rules(func)

			self.tools.append({'tool':tool, 'tooldir':tooldir, 'funs':funs})

	def find_file(self, filename, path_list):
		"""finds a file in a list of paths
		@param filename: name of the file to search for
		@param path_list: list of directories to search
		@return: the first occurrence filename or '' if filename could not be found
		"""
		for directory in Utils.to_list(path_list):
			if os.path.exists(os.path.join(directory, filename)):
				return directory
		return ''

	def post_recurse(self, name_or_mod, path, nexdir):
		"""records the path and a hash of the scripts visited, see Context.post_recurse"""
		super(ConfigurationContext, self).post_recurse(self, name_or_mod, path, nexdir)
		self.hash = hash((self.hash, getattr(name_or_mod, 'waf_hash_val', name_or_mod)))
		self.files.append(path)

	def set_env_name(self, name, env):
		"adds a new environment called name"
		self.all_envs[name] = env
		return env

	def retrieve(self, name, fromenv=None):
		"retrieve an environment called name"
		try:
			env = self.all_envs[name]
		except KeyError:
			env = ConfigSet.ConfigSet()
			env['PREFIX'] = os.path.abspath(os.path.expanduser(Options.options.prefix))
			self.all_envs[name] = env
		else:
			if fromenv: Logs.warn("The environment %s may have been configured already" % name)
		return env

	def setenv(self, name):
		"""Sets the environment called name"""
		self.env = self.retrieve(name)
		self.envname = name

	def add_os_flags(self, var, dest=None):
		"""Imports operating system environment values into an env dict"""
		# do not use 'get' to make certain the variable is not defined
		try: self.env.append_value(dest or var, Utils.to_list(self.environ[var]))
		except KeyError: pass

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

		self.line_just = max(self.line_just, len(msg))
		for x in ('\n', self.line_just * '-', '\n', msg, '\n'):
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
		self.log.write(msg)
		self.log.write('\n')
		Logs.pprint(color, msg)

	def find_program(self, filename, path_list=[], var=None, mandatory=True, environ=None, exts=''):
		"""Search for a program on the operating system"""

		if not environ:
			environ = os.environ

		ret = ''
		if var:
			if self.env[var]:
				ret = self.env[var]
			elif var in environ:
				ret = environ[var]

		if not ret:
			if path_list:
				path_list = Utils.to_list(path_list)
			else:
				path_list = environ.get('PATH', '').split(os.pathsep)

			if not isinstance(filename, list):
				filename = [filename]

			if not exts:
				if Options.platform == 'win32':
					exts = '.exe,.com,.bat,.cmd'

			for a in exts.split(','):
				if ret:
					break
				for b in filename:
					if ret:
						break
					for c in path_list:
						if ret:
							break
						x = os.path.join(c, b + a)
						if os.path.isfile(x):
							ret = x

		filename = Utils.to_list(filename)
		self.start_msg('Checking for program ' + ','.join(filename))
		self.end_msg(ret)
		self.log.write('find program=%r paths=%r var=%r -> %r\n\n' % (filename, path_list, var, ret))

		if not ret and mandatory:
			self.fatal('The program %r could not be found' % filename)

		if var:
			self.env[var] = ret
		return ret

	def cmd_to_list(self, cmd):
		"""Detects if a command is written in pseudo shell like 'ccache g++'"""
		if isinstance(cmd, str) and cmd.find(' '):
			try:
				os.stat(cmd)
			except OSError:
				return shlex.split(cmd)
			else:
				return [cmd]
		return cmd

	def eval_rules(self, rules):
		"""Executes the configuration tests"""
		self.rules = Utils.to_list(rules)
		for x in self.rules:
			f = getattr(self, x)
			if not f: self.fatal("No such method '%s'." % x)
			try:
				f()
			except Exception as e:
				ret = self.err_handler(x, e)
				if ret == BREAK:
					break
				elif ret == CONTINUE:
					continue
				else:
					self.fatal(e)

	def err_handler(self, fun, error):
		"""error handler for the configuration tests, the default is to let the exceptions rise"""
		pass

	def store(self):
		"""Saves the config results into the cache file"""
		try:
			os.makedirs(self.cachedir)
		except:
			pass

		f = open(os.path.join(self.cachedir, 'build.config.py'), 'w')
		f.write('version = 0x%x\n' % Base.HEXVERSION)
		f.write('tools = %r\n' % self.tools)
		f.close()

		if not self.all_envs:
			self.fatal('nothing to store in the configuration context!')
		for key in self.all_envs:
			tmpenv = self.all_envs[key]
			tmpenv.store(os.path.join(self.cachedir, key + CACHE_SUFFIX))

	def execute(self):
		"""See Context.prepare"""
		src = getattr(Options.options, Base.SRCDIR, None)
		if not src: src = getattr(Base.g_module, Base.SRCDIR, None)
		if not src:
			src = '.'
			incomplete_src = 1
		src = os.path.abspath(src)

		bld = getattr(Options.options, Base.BLDDIR, None)
		if not bld:
			bld = getattr(Base.g_module, Base.BLDDIR, None)
		if not bld:
			bld = 'build'
			incomplete_bld = 1
		bld = os.path.abspath(bld)

		try: os.makedirs(bld)
		except OSError: pass

		self.srcdir = src
		self.blddir = bld
		self.post_init()

		if 'incomplete_src' in vars():
			self.start_msg('Setting srcdir to')
			self.end_msg(src)
		if 'incomplete_bld' in vars():
			self.start_msg('Setting blddir to')
			self.end_msg(bld)

		super(ConfigurationContext, self).execute()

		self.store()

		Options.top_dir = self.srcdir
		Options.out_dir = self.blddir

		# this will write a configure lock so that subsequent builds will
		# consider the current path as the root directory (see prepare_impl).
		# to remove: use 'waf distclean'
		env = ConfigSet.ConfigSet()
		env['argv'] = sys.argv
		env['options'] = Options.options.__dict__

		env.run_dir = Options.run_dir
		env.top_dir = Options.top_dir
		env.out_dir = Options.out_dir

		# conf.hash & conf.files hold wscript files paths and hash
		# (used only by Configure.autoconfig)
		env['hash'] = self.hash
		env['files'] = self.files
		env['environ'] = dict(self.environ)

		env.store(Options.run_dir + os.sep + Options.lockfile)
		env.store(Options.top_dir + os.sep + Options.lockfile)
		env.store(Options.out_dir + os.sep + Options.lockfile)

def conf(f):
	"decorator: attach new configuration functions"
	ConfigurationContext.tests[f.__name__] = f
	setattr(ConfigurationContext, f.__name__, f)
	return f

@conf
def check_waf_version(self, mini='1.6.0', maxi='1.7.0'):
	"""
	check for the waf version

	Versions should be supplied as hex. 0x01000000 means 1.0.0,
	0x010408 means 1.4.8, etc.

	@type  mini: number, tuple or string
	@param mini: Minimum required version
	@type  maxi: number, tuple or string
	@param maxi: Maximum allowed version
	"""
	ver = Base.HEXVERSION
	if num2ver(min_val) > ver:
		conf.fatal('waf version should be at least %r (%r found)' % (mini, ver))

	if num2ver(max_val) < ver:
		conf.fatal('waf version should be at most %r (%r found)' % (maxi, ver))

