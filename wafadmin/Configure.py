#! /usr/bin/env python
# encoding: utf-8

import os, types, imp, cPickle, md5
import Params, Environment, Runner, Build, Utils
from Params import error, fatal, warning

g_maxlen = 40
"""initial length of configuration messages"""

g_debug  = 0
"""enable/disable debug"""

g_stdincpath = ['/usr/include/', '/usr/local/include/']
"""standard include paths"""

g_stdlibpath = ['/usr/lib/', '/usr/local/lib/', '/lib']
"""standard library search paths"""

#####################
## Helper functions

def find_file(filename, path_list):
	"""find a file in a list of paths
filename - name of the file to search for
path_list - list of directories to search
returns the first occurrence filename or '' if filename could not be found
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
filename - name of the file to search for
path_list - list of directories to search
returns the first occurrence filename or '' if filename could not be found
"""
	import os, fnmatch;
	if type(path_list) is types.StringType:
		lst = path_list.split()
	else:
		lst = path_list
	for directory in lst:
		for path, subdirs, files in os.walk( directory ):
			for name in files:
				if fnmatch.fnmatch( name, filename ):
					return path
	return ''

def find_program_impl(lenv, filename, path_list=None, var=None):
	"""find a program in folders path_lst, and sets lenv[var]
lenv - directory to be set
filename - name of the program to search for
path_list - list of directories to search for filename
var - environment value to be checked for in lenv or os.environ
returns - eigther the value that is referenced with [var] in lenv or os.environ
or the first  occurrence filename or '' if filename could not be found
"""
	if not path_list:
		path_list = []
	elif type(path_list) is types.StringType:
		path_list = path_list.split()

	if var:
		if lenv[var]:
			return lenv[var]
		elif var in os.environ:
			return os.environ[var]

	if lenv['WINDOWS']: filename += '.exe'
	if not path_list:
		try:
			path_list = os.environ['PATH'].split(':')
		except KeyError:
			return None
	for directory in path_list:
		if os.path.exists( os.path.join(directory, filename) ):
			ret = os.path.join(directory, filename)
			if var: lenv[var] = ret
			return ret
	return ''

###############
## ENUMERATORS

class enumerator_base:
	def __init__(self, conf):
		self.conf        = conf
		self.env         = conf.env
		self.define = ''
		self.mandatory   = 0

	def error(self):
		fatal('A mandatory check failed. Make sure all dependencies are ok and can be found.')

	def update_hash(self, md5hash):
		classvars = vars(self)
		for (var, value) in classvars.iteritems():
			if callable(var):          continue
			if value == self:          continue
			if value == self.env:      continue
			if value == self.conf:     continue
			md5hash.update(str(value))

	def update_env(self, hashtable):
		for name in hashtable:
			self.env[name] = hashtable[name]

	def validate(self):
		try: self.names = self.names.split()
		except: pass

	def hash(self):
		m = md5.new()
		self.update_hash(m)
		return m.digest()

	def run_cache(self, retvalue):
		pass

	def run(self):
		self.validate()
		if not Params.g_options.nocache:
			newhash = self.hash()
			try:
				ret = self.conf.m_cache_table[newhash]
				self.run_cache(ret)
				return ret
			except KeyError:
				pass

		ret = self.run_test()

		if self.mandatory and not ret:
			self.error()

		if not Params.g_options.nocache:
			self.conf.m_cache_table[newhash] = ret
		return ret

	# Override this method, not run()!
	def run_test(self):
		return 0

class configurator_base(enumerator_base):
	def __init__(self, conf):
		enumerator_base.__init__(self, conf)
		self.uselib = ''

class program_enumerator(enumerator_base):
	def __init__(self,conf):
		enumerator_base.__init__(self, conf)

		self.name = ''
		self.path = []
		self.var  = None

	def error(self):
		fatal('program %s cannot be found' % self.name)

	def run_cache(self, retval):
		self.conf.checkMessage('program %s (cached)' % self.name, '', retval, option=retval)
		if self.var: self.env[self.var] = retval

	def run_test(self):
		ret = find_program_impl(self.env, self.name, self.path, self.var)
		self.conf.checkMessage('program', self.name, ret, ret)
		if self.var: self.env[self.var] = ret
		return ret

class function_enumerator(enumerator_base):
	def __init__(self,conf):
		enumerator_base.__init__(self, conf)

		self.function      = ''
		self.define        = ''

		self.headers       = []
		self.header_code   = ''
		self.custom_code   = ''

		self.include_paths = []
		self.libs          = []
		self.lib_paths     = []

	def error(self):
		fatal('function %s cannot be found' % self.function)

	def validate(self):
		if not self.define:
			self.define = self.function.upper()

	def run_cache(self, retval):
		self.conf.checkMessage('function %s (cached)' % self.function, '', 1, option='')
		self.conf.add_define(self.define, retval)

	def run_test(self):
		ret = 0 # not found

		oldlibpath = self.env['LIBPATH']
		oldlib = self.env['LIB']

		code = []
		code.append(self.header_code)
		code.append('\n')
		for header in self.headers:
			code.append('#include <%s>\n' % header)

		if self.custom_code:
			code.append('int main(){%s\nreturn 0;}\n' % self.custom_code)
		else:
			code.append('int main(){\nvoid *p;\np=(void*)(%s);\nreturn 0;\n}\n' % self.function)

		self.env['LIB'] = self.libs
		self.env['LIBPATH'] = self.lib_paths

		obj               = check_data()
		obj.code          = "\n".join(code)
		obj.includes      = self.include_paths
		obj.env           = self.env

		ret = int(not self.conf.run_check(obj))
		self.conf.checkMessage('function %s' % self.function, '', ret, option='')

		self.conf.add_define(self.define, ret)

		self.env['LIB'] = oldlib
		self.env['LIBPATH'] = oldlibpath

		return ret

class library_enumerator(enumerator_base):
	"find a library in a list of paths"
	def __init__(self, conf):
		enumerator_base.__init__(self, conf)

		self.name = ''
		self.path = []
		self.code = 'int main() {return 0;}'
		self.uselib = '' # to set the LIB_NAME and LIBPATH_NAME
		self.nosystem = 0 # do not use standard lib paths
		self.want_message = 1

	def error(self):
		fatal('library %s cannot be found' % self.name)

	def run_cache(self, retval):
		if self.want_message:
			self.conf.checkMessage('library %s (cached)' % self.name, '', 1, option=retval)
		self.env['LIB_'+self.uselib] = self.name
		self.env['LIBPATH_'+self.uselib] = retval

	def validate(self):
		if not self.path:
			self.path = g_stdlibpath
		else:
			if not self.nosystem:
				self.path += g_stdlibpath

	def run_test(self):
		ret=''

		name = self.env['shlib_PREFIX']+self.name+self.env['shlib_SUFFIX']
		ret  = find_file(name, self.path)

		if not ret:
			name = self.env['staticlib_PREFIX']+self.name+self.env['staticlib_SUFFIX']
			ret  = find_file(name, self.path)

		if self.want_message:
			self.conf.checkMessage('library '+self.name, '', ret, option=ret)
		if self.uselib:
			self.env['LIB_'+self.uselib] = self.name
			self.env['LIBPATH_'+self.uselib] = ret

		return ret

class header_enumerator(enumerator_base):
	"find a header in a list of paths"
	def __init__(self,conf):
		enumerator_base.__init__(self, conf)

		self.name   = []
		self.path   = []
		self.define = []
		self.nosystem = 0

	def validate(self):
		if not self.path:
			self.path = g_stdincpath
		else:
			if not self.nosystem:
				self.path += g_stdincpath

	def error(self):
		fatal('cannot find %s in %s' % (self.name, str(self.path)))

	def run_cache(self, retval):
		self.conf.checkMessage('header %s (cached)' % self.name, '', 1, option=retval)
		if self.define: self.env[self.define] = retval

	def run_test(self):
		ret = find_file(self.name, self.path)
		self.conf.checkMessage('header', self.name, ret, ret)
		if self.define: self.env[self.define] = ret
		return ret

## ENUMERATORS END
###################

###################
## CONFIGURATORS

class cfgtool_configurator(configurator_base):
	def __init__(self,conf):
		configurator_base.__init__(self, conf)

		self.uselib   = ''
		self.define   = ''
		self.binary   = ''

		self.tests    = {}

	def error(self):
		fatal('%s cannot be found' % self.binary)

	def validate(self):
		if not self.binary:
			raise "error"
		if not self.define:
			self.define = 'HAVE_'+self.uselib

		if not self.tests:
			self.tests['--cflags'] = 'CCFLAGS'
			self.tests['--cflags'] = 'CXXFLAGS'
			self.tests['--libs']   = 'LINKFLAGS'

	def run_cache(self, retval):
		if retval:
			self.update_env(retval)
			self.conf.add_define(self.define, 1)
		else:
			self.conf.add_define(self.define, 0)
		self.conf.checkMessage('config-tool %s (cached)' % self.binary, '', retval, option='')

	def run_test(self):
		retval = {}
		found = 1

		try:
			ret = os.popen('%s --help' % self.binary).close()
			if ret: raise "error"

			for flag in self.tests:
				var = self.tests[flag] + '_' + self.uselib
				cmd = '%s %s 2>/dev/null' % (self.binary, flag)
				retval[var] = [os.popen(cmd).read().strip()]

			self.update_env(retval)
		except:
			retval = {}
			found = 0

		self.conf.add_define(self.define, found)
		self.conf.checkMessage('config-tool ' + self.binary, '', found, option = '')
		return retval

class pkgconfig_configurator(configurator_base):
	""" pkgconfig_configurator is a frontend to pkg-config
variables:
 name - name of the .pc file  (has to be set at least)
 version - atleast-version to check for
 path - override the pkgconfig path (PKG_CONFIG_PATH)
 uselib - name that could be used in tasks with obj.uselib
              if not set uselib = upper(name)
 define - name that will be used in config.h  ...
              if not set define = HAVE_+uselib

variables - list of addional variables to be checked for
                for  example variables='prefix libdir'
"""
	def __init__(self, conf):
		configurator_base.__init__(self,conf)

		self.name        = '' # name of the .pc file
		self.version     = '' # version to check
		self.path        = '' # PKG_CONFIG_PATH
		self.uselib = '' # can be set automatically
		self.define = '' # can be set automatically
		self.binary      = '' # name and path for pkg-config

		# You could also check for extra values in a pkg-config file.
		# Use this value to define which values should be checked
		# and defined. Several formats for this value are supported:
		# - string with spaces to separate a list
		# - list of values to check (define name will be upper(uselib"_"value_name))
		# - a list of [value_name, override define_name]
		self.variables   = []

	def error(self):
		if self.version:
			fatal('pkg-config cannot find %s >= %s' % (self.name, self.version))
		fatal('pkg-config cannot find %s' % self.name)

	def validate(self):
		if not self.uselib:
			self.uselib = self.name.upper()
		if not self.define:
			self.define = 'HAVE_'+self.uselib

	def run_cache(self, retval):
		if self.version:
			self.conf.checkMessage('package %s >= %s (cached)' % (self.name, self.version), '', retval, option='')
		else:
			self.conf.checkMessage('package %s (cached)' % self.name, '', retval, option='')
		if retval:
			self.conf.add_define(self.define, 1)
		else:
			self.conf.add_define(self.define, 0)
		self.update_env(retval)

	def run_test(self):
		pkgpath = self.path
		pkgbin = self.binary
		uselib = self.uselib

		# check if self.variables is a string with spaces
		# to separate the variables to check for
		# if yes convert variables to a list
		if type(self.variables) is types.StringType:
			self.variables = str(self.variables).split()

		if not pkgbin:
			pkgbin = 'pkg-config'
		if pkgpath:
			pkgpath = 'PKG_CONFIG_PATH=' + pkgpath
		pkgcom = '%s %s' % (pkgpath, pkgbin)

		retval = {}

		try:
			if self.version:
				ret = os.popen("%s --atleast-version=%s %s" % (pkgcom, self.version, self.name)).close()
				self.conf.checkMessage('package %s >= %s' % (self.name, self.version), '', not ret)
				if ret: raise "error"
			else:
				ret = os.popen("%s %s" % (pkgcom, self.name)).close()
				self.conf.checkMessage('package %s' % (self.name), '', not ret)
				if ret: raise "error"

			retval['CCFLAGS_'+uselib]   = [os.popen('%s --cflags %s' % (pkgcom, self.name)).read().strip()]
			retval['CXXFLAGS_'+uselib]  = [os.popen('%s --cflags %s' % (pkgcom, self.name)).read().strip()]
			#env['LINKFLAGS_'+uselib] = os.popen('%s --libs %s' % (pkgcom, self.name)).read().strip()
			# Store the library names:
			modlibs = os.popen('%s --libs-only-l %s' % (pkgcom, self.name)).read().strip().split()
			retval['LIB_'+uselib] = []
			for item in modlibs:
				retval['LIB_'+uselib].append( item[2:] ) #Strip '-l'

			# Store the library paths:
			modpaths = os.popen('%s --libs-only-L %s' % (pkgcom, self.name)).read().strip().split()
			retval['LIBPATH_'+uselib] = []
			for item in modpaths:
				retval['LIBPATH_'+uselib].append( item[2:] ) #Strip '-l'

			for variable in self.variables:
				var_defname = ''
				# check if variable is a list
				if (type(variable) is types.ListType):
					# is it a list of [value_name, override define_name] ?
					if len(variable) == 2 and variable[1]:
						# if so use the overrided define_name as var_defname
						var_defname = variable[1]
					# convert variable to a string that name the variable to check for.
					variable = variable[0]

				# if var_defname was not overrided by the list containing the define_name
				if not var_defname:
					var_defname = uselib + '_' + variable.upper()

				retval[var_defname] = os.popen('%s --variable=%s %s' % (pkgcom, variable, self.name)).read().strip()

			self.conf.add_define(self.define, 1)
			self.update_env(retval)
		except:
			retval = {}
			self.conf.add_define(self.define, 0)

		return retval

class test_configurator(configurator_base):
	def __init__(self, conf):
		configurator_base.__init__(self, conf)
		self.name = ''
		self.code = ''
		self.flags = ''
		self.define = ''
		self.uselib = ''
		self.want_message = 0

	def error(self):
		fatal('test program would not run')

	def run_cache(self, retval):
		if self.want_message:
			self.conf.checkMessage('custom code (cached)', '', 1, option=retval['result'])

	def validate(self):
		if not self.code:
			fatal('test configurator needs code to compile and run!')

	def run_test(self):
		obj = check_data()
		obj.code = self.code
		obj.env  = self.env
		obj.uselib = self.uselib
		obj.flags = self.flags
		obj.execute = 1
		ret = self.conf.run_check(obj)

		if self.want_message:
			if ret: data = ret['result']
			else: data = ''

			self.conf.checkMessage('custom code', '', ret, option=data)

		return ret

class library_configurator(configurator_base):
	def __init__(self,conf):
		configurator_base.__init__(self,conf)

		self.name = ''
		self.path = []
		self.define = ''
		self.uselib = ''

		self.code = 'int main(){ return 0; }'

	def error(self):
		fatal('library %s cannot be linked' % self.name)

	def run_cache(self, retval):
		self.conf.checkMessage('library %s (cached)' % self.name, '', 1)
		self.env['LIB_'+self.uselib] = self.name
		self.env['LIBPATH_'+self.uselib] = retval

	def validate(self):
		if not self.path:
			self.path = ['/usr/lib/', '/usr/local/lib', '/lib']

		if not self.uselib: self.uselib = self.name.upper()
		if not self.define: self.define = 'HAVE_'+self.uselib

		if not self.uselib: fatal('uselib is not defined')
		if not self.code: fatal('library enumerator must have code to compile')

	def run_test(self):
		oldlibpath = self.env['LIBPATH']
		oldlib = self.env['LIB']

		# try the enumerator to find the correct libpath
		test = self.conf.create_library_enumerator()
		test.name = self.name
		test.want_message = 0
		test.path = self.path
		test.env = self.env
		ret = test.run()

		if ret:
			self.env['LIBPATH_'+self.uselib] = ret

		self.env['LIB_'+self.uselib] = self.name

		val = {}

		#self.env['LIB'] = self.name
		#self.env['LIBPATH'] = self.lib_paths

		obj               = check_data()
		obj.code          = self.code
		obj.env           = self.env
		obj.uselib        = self.uselib

		ret = int(not self.conf.run_check(obj))
		self.conf.checkMessage('library %s' % self.name, '', ret)

		self.conf.add_define(self.define, ret)

		if ret:
			val['LIBPATH_'+self.uselib] = self.env['LIBPATH_'+self.uselib]
			val['LIB_'+self.uselib] = self.env['LIB_'+self.uselib]
			val[self.define] = ret

		self.env['LIB'] = oldlib
		self.env['LIBPATH'] = oldlibpath

		if not ret: return {}
		return val

class header_configurator(configurator_base):
	def __init__(self,conf):
		configurator_base.__init__(self,conf)

		self.name = ''
		self.include_paths = []
		self.header_code = ''
		self.custom_code = ''
		self.code = 'int main() {return 0;}'

		self.define = '' # HAVE_something

		self.libs = []
		self.lib_paths = []
		self.uselib = ''

	def error(self):
		fatal('header %s cannot be found via compiler' % self.name)

	def validate(self):
		#try: self.names = self.names.split()
		#except: pass
		#if not self.define: self.define = 'HAVE_'+self.uselib

		if not self.code: self.code = "#include <%s>\nint main(){return 0;}\n"

		if not self.code: fatal('no code to run')
		if not self.define: fatal('no define given')

	def run_cache(self, retvalue):
		self.update_env(retvalue)
		self.conf.checkMessage('header %s (cached)' % self.name, '', 1)
		self.conf.add_define(self.define, 1)

	def run_test(self):
		ret = {} # not found

		oldlibpath = self.env['LIBPATH']
		oldlib = self.env['LIB']

		code = []
		code.append(self.header_code)
		code.append('\n')
		code.append('#include <%s>\n' % self.name)

		code.append('int main(){%s\nreturn 0;}\n' % self.custom_code)

		self.env['LIB'] = self.libs
		self.env['LIBPATH'] = self.lib_paths

		obj               = check_data()
		obj.code          = "\n".join(code)
		obj.includes      = self.include_paths
		obj.env           = self.env
		obj.uselib        = self.uselib

		ret = int(not self.conf.run_check(obj))
		self.conf.checkMessage('header %s' % self.name, '', ret, option='')

		self.conf.add_define(self.define, ret)

		self.env['LIB'] = oldlib
		self.env['LIBPATH'] = oldlibpath

		if not ret: return {}
		ret = {self.define: 1}
		return ret

# CONFIGURATORS END
####################

class check_data:
	def __init__(self):

		self.env           = '' # environment to use

		self.code          = '' # the code to execute

		self.flags         = '' # the flags to give to the compiler

		self.uselib        = '' # uselib
		self.includes      = '' # include paths

		self.function_name = '' # function to check for

		self.lib           = []
		self.libpath       = [] # libpath for linking

		self.define   = '' # define to add if run is successful

		self.header_name   = '' # header name to check for

		self.execute       = 0  # execute the program produced and return its output
		self.options       = '' # command-line options

class Configure:
	def __init__(self, env=None, blddir='', srcdir=''):

		self.env       = None
		self.m_envname = ''

		self.m_blddir = blddir
		self.m_srcdir = srcdir

		self.m_allenvs = {}
		self.defines = {}
		self.configheader = 'config.h'
		self.cwd = os.getcwd()

		self.setenv('default')

		self.m_cache_table = {}

		self.lastprog = ''

		try:
			file = open(os.sep.join([os.environ['HOME'], '.wafcache', 'runs.txt']), 'rb')
			self.m_cache_table = cPickle.load(file)
			file.close()
		except:
			pass

		self._a=0
		self._b=0
		self._c=0
		self._quiet=0

	def set_env_name(self, name, env):
		"add a new environment called name"
		self.m_allenvs[name] = env
		return env

	def retrieve(self, name, fromenv=None):
		"retrieve an environment called name"
		try:
			env = self.m_allenvs[name]
			if fromenv: warning("The environment %s may have been configured already" % name)
			return env
		except:
			env = Environment.Environment()
			self.m_allenvs[name] = env
			return env

	def check_tool(self, input, tooldir=None):
		"load a waf tool"
		if type(input) is types.ListType: lst = input
		else: lst = input.split()

		ret = True
		for i in lst: ret = ret and self._check_tool_impl(i, tooldir)
		return ret

	def _check_tool_impl(self, tool, tooldir=None):
		"private method, do not use directly"
		define = 'HAVE_'+tool.upper().replace('.','_').replace('+','P')

		if self.isDefined(define):
			return self.getDefine(define)

		try:
			file,name,desc = imp.find_module(tool, tooldir)
		except:
			print "no tool named '" + tool + "' found"
			return
		module = imp.load_module(tool,file,name,desc)
		ret = int(module.detect(self))
		self.add_define(define, ret)
		self.env.appendValue('tools', {'tool':tool, 'tooldir':tooldir})
		return ret

	def setenv(self, name):
		"enable the environment called name"
		self.env     = self.retrieve(name)
		self.envname = name

	def find_program(self, program_name, path_list=[], var=None):
		"wrapper provided for convenience"
		ret = find_program_impl(self.env, program_name, path_list, var)
		self.checkMessage('program', program_name, ret, ret)
		return ret

	def store(self, file=''):
		"save the config results into the cache file"
		try: os.makedirs(Params.g_cachedir)
		except OSError: pass

		if not self.m_allenvs:
			fatal("nothing to store in Configure !")
		for key in self.m_allenvs:
			tmpenv = self.m_allenvs[key]
			tmpenv.store(os.path.join(Params.g_cachedir, key+'.cache.py'))

	def check_pkg(self, modname, destvar='', vnum='', pkgpath='', pkgbin=''):
		"wrapper provided for convenience"
		pkgconf = self.create_pkgconfig_configurator()

		if not destvar: destvar = modname.upper()

		pkgconf.uselib = destvar
		pkgconf.name = modname
		pkgconf.version = vnum
		pkgconf.path = pkgpath
		pkgconf.binary = pkgbin
		return pkgconf.run()

	def sub_config(self, dir):
		"executes the configure function of a wscript module"
		current = self.cwd

		self.cwd = os.path.join(self.cwd, dir)
		cur = os.path.join(self.cwd, 'wscript')

		try:
			mod = Utils.load_module(cur)
		except:
			msg = "no module or function configure was found in wscript\n[%s]:\n * make sure such a function is defined \n * run configure from the root of the project"
			fatal(msg % self.cwd)

		# TODO check
		#if not 'configure' in mod:
		#	fatal('the module has no configure function')
		mod.configure(self)
		self.cwd = current

	def cleanup(self):
		"called on shutdown"
		try:
			dir = os.sep.join([os.environ['HOME'], '.wafcache'])
			try:
				os.makedirs(dir)
			except:
				pass

			file = open(os.sep.join([os.environ['HOME'], '.wafcache', 'runs.txt']), 'wb')
			cPickle.dump(self.m_cache_table, file)
			file.close()
		except:
			raise
			pass


	def add_define(self, define, value, quote=-1):
		"""store a single define and its state into an internal list
		   for later writing to a config header file"""
		# the user forgot to tell if the value is quoted or not
		if quote < 0:
			if type(value) is types.StringType:
				self.defines[define] = '"%s"' % str(value)
			else:
				self.defines[define] = value
		elif not quote:
			self.defines[define] = value
		else:
			self.defines[define] = '"%s"' % str(value)

		if not define: raise "define must be .. defined"

		# add later to make reconfiguring faster
		self.env[define] = value

	def isDefined(self, define):
		return self.defines.has_key(define)

	def getDefine(self, define):
		"get the value of a previously stored define"
		try: return self.defines[define]
		except: return 0

	def writeConfigHeader(self, configfile='config.h', env=''):
		"save the defines into a file"
		if configfile=='': configfile = self.configheader

		try:
			# just in case the path is 'something/blah.h' (under the builddir)
			lst=configfile.split('/')
			lst = lst[:-1]
			os.mkdir( os.sep.join(lst) )
		except:
			pass

		dir = os.path.join(self.m_blddir, self.env.variant())
		try: os.makedirs(dir)
		except: pass

		dir = os.path.join(dir, configfile)

		dest=open(dir, 'w')
		dest.write('/* configuration created by waf */\n')
		dest.write('#ifndef _CONFIG_H_WAF\n#define _CONFIG_H_WAF\n\n')

		for key in self.defines:
			if self.defines[key]:
				dest.write('#define %s %s\n' % (key, self.defines[key]))
				#if addcontent:
				#	dest.write(addcontent);
			else:
				dest.write('/* #undef '+key+' */\n')
		dest.write('\n#endif /* _CONFIG_H_WAF */\n')
		dest.close()

	def setConfigHeader(self, header):
		"set a config header file"
		self.configheader = header

	def checkMessage(self,type,msg,state,option=''):
		"print an checking message. This function is used by other checking functions"
		sr = 'Checking for ' + type + ' ' + msg

		lst = []
		lst.append(sr)

		global g_maxlen
		dist = len(sr)
		if dist > g_maxlen:
			g_maxlen = dist+1

		if dist < g_maxlen:
			diff = g_maxlen - dist
			while diff>0:
				lst.append(' ')
				diff -= 1

		lst.append(':')
		print ''.join(lst),

		p=Params.pprint
		if state: p('GREEN', 'ok ' + option)
		else: p('YELLOW', 'not found')

	def checkMessageCustom(self,type,msg,custom,option=''):
		"""print an checking message. This function is used by other checking functions"""
		sr = 'Checking for ' + type + ' ' + msg

		lst = []
		lst.append(sr)

		global g_maxlen
		dist = len(sr)
		if dist > g_maxlen:
			g_maxlen = dist+1

		if dist < g_maxlen:
			diff = g_maxlen - dist
			while diff>0:
				lst.append(' ')
				diff -= 1

		lst.append(':')
		print ''.join(lst),

		p=Params.pprint
		p('CYAN', custom)

	def hook(self, func):
		"attach the function given as input as new method"
		setattr(self.__class__, func.__name__, func)

	def mute_logging(self):
		"mutes the output temporarily"
		if Params.g_options.verbose: return
		# store the settings
		(self._a,self._b,self._c) = Params.get_trace()
		self._quiet = Runner.g_quiet
		# then mute
		if not g_debug:
			Params.set_trace(0,0,0)
			Runner.g_quiet = 1

	def restore_logging(self):
		"see mute_logging"
		if Params.g_options.verbose: return
		# restore the settings
		if not g_debug:
			Params.set_trace(self._a,self._b,self._c)
			Runner.g_quiet = self._quiet


	def create_program_enumerator(self):
		return program_enumerator(self)

	def create_library_enumerator(self):
		return library_enumerator(self)

	def create_header_enumerator(self):
		return header_enumerator(self)

	def create_function_enumerator(self):
		return function_enumerator(self)

	def create_pkgconfig_configurator(self):
		return pkgconfig_configurator(self)

	def create_cfgtool_configurator(self):
		return cfgtool_configurator(self)

	def create_test_configurator(self):
		return test_configurator(self)

	def create_library_configurator(self):
		return library_configurator(self)

	def create_header_configurator(self):
		return header_configurator(self)

	def pkgconfig_fetch_variable(self,pkgname,variable,pkgpath='',pkgbin='',pkgversion=0,env=None):
		if not env: env=self.env

		if not pkgbin: pkgbin='pkg-config'
		if pkgpath: pkgpath='PKG_CONFIG_PATH='+pkgpath
		pkgcom = '%s %s' % (pkgpath, pkgbin)
		try:
			if pkgversion:
				ret = os.popen("%s --atleast-version=%s %s" % (pkgcom, pkgversion, pkgname)).close()
				self.conf.checkMessage('package %s >= %s' % (pkgname, pkgversion), '', not ret)
				if ret: raise "error"
			else:
				ret = os.popen("%s %s" % (pkgcom, pkgname)).close()
				self.conf.checkMessage('package %s ' % (pkgname), '', not ret)
				if ret: raise "error"

			return os.popen('%s --variable=%s %s' % (pkgcom, variable, pkgname)).read().strip()
		except:
			return ''


	def run_check(self, obj):
		"compile, link and run if necessary"

		# first make sure the code to execute is defined
		if not obj.code:
			error('run_check: no code to process in check')
			raise

		# create a small folder for testing
		dir = os.path.join(self.m_blddir, '.wscript-trybuild')

		# if the folder already exists, remove it
		for (root, dirs, filenames) in os.walk(dir):
			for f in list(filenames):
				os.remove(os.path.join(root, f))

		bdir = os.path.join( dir, '_testbuild_')
		try: os.makedirs(dir)
		except: pass
		try: os.makedirs(bdir)
		except: pass

		dest=open(os.path.join(dir, 'test.c'), 'w')
		dest.write(obj.code)
		dest.close()

		if obj.env: env = obj.env
		else: env = self.env.copy()

		# very important
		Utils.reset()

		back=os.path.abspath('.')

		bld = Build.Build()
		bld.load_dirs(dir, bdir, isconfigure=1)
		bld.m_allenvs['default'] = env

		os.chdir(dir)

		for t in env['tools']: env.setup(**t)

		# not sure yet when to call this:
		#bld.rescan(bld.m_srcnode)

		if env['CXX']:
			import cpp
			o=cpp.cppobj('program')
		else:
			import cc
			o=cc.ccobj('program')

		o.source   = 'test.c'
		o.target   = 'testprog'
		o.uselib   = obj.uselib
		o.cppflags = obj.flags
		o.includes = obj.includes

		# compile the program
		self.mute_logging()
		try:
			ret = bld.compile()
			self.restore_logging()
		except:
			ret = 1
			self.restore_logging()

		# keep the name of the program to execute
		if obj.execute:
			lastprog = o.m_linktask.m_outputs[0].abspath(o.env)

		#if runopts is not None:
		#	ret = os.popen(obj.m_linktask.m_outputs[0].abspath(obj.env)).read().strip()

		os.chdir(back)
		Utils.reset()

		# if we need to run the program, try to get its result
		if obj.execute:
			if ret: return None
			try:
				data = os.popen(lastprog).read().strip()
				ret = {'result': data}
			except:
				raise
				pass
		return ret


	# TODO deprecated
	def checkTool(self, input, tooldir=None):
		warning('use conf.check_tool instead of checkTool')
		return self.check_tool(input, tooldir)

