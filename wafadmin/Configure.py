#! /usr/bin/env python
# encoding: utf-8

import os, types, sys, string, imp, cPickle, md5
import Params, Environment, Runner, Build, Utils
from Params import debug, error, trace, fatal, warning


import traceback

g_maxlen = 40
g_debug  = 0


#######################################################################
## Helper functions

def find_path(file, path_list):
	if type(path_list) is types.StringType: lst = [path_list]
	else: lst = path_list
	for dir in lst:
		if os.path.exists( os.path.join(dir, file) ):
			return dir
	return ''

def find_file(file, path_list):
	if type(path_list) is types.StringType: lst = [path_list]
	else: lst = path_list
	for dir in lst:
		if os.path.exists( os.path.join(dir, file) ):
			return dir
	return ''

def find_file_ext(file, path_list):
	import os, fnmatch;
	if type(path_list) is types.StringType: lst = [path_list]
	else: lst = path_list
	for p in lst:
		for path, subdirs, files in os.walk( p ):
			for name in files:
				if fnmatch.fnmatch( name, file ):
					return path
	return ''

# find the program "file" in folders path_lst, and sets lenv[var]
def find_program_impl(lenv, file, path_list=None, var=None):
	if not path_list: path_list = []
	elif type(path_list) is types.StringType: path_list = path_list.split()

	if var:
		if lenv[var]: return lenv[var]
		elif var in os.environ: return os.environ[var]

	if lenv['WINDOWS']: file += '.exe'
	if not path_list: 
		try:
			path_list = os.environ['PATH'].split(':')
		except KeyError:
			return None
	for dir in path_list:
		if os.path.exists( os.path.join(dir, file) ):
			ret = os.path.join(dir, file)
			if var: lenv[var] = ret
			return ret
	return ''

def find_program_using_which(lenv, prog):
	if lenv['WINDOWS']: # we're not depending on Cygwin
		return ''
	return os.popen("which %s 2>/dev/null" % prog).read().strip()



#######################################################################
## ENUMERATORS

class enumerator_base:
	def __init__(self, conf):
		self.conf               = conf
		self.env                = conf.env
		self.define_name        = ''
		self.mandatory          = 0
		self.mandatory_errormsg	= 'A mandatory check failed. Make sure all dependencies are ok and can be found.'

	def update_hash(self, md5hash):
		classvars = vars(self)
		for (var, value) in classvars.iteritems():
			if callable(var):                    continue
			if value == self:                    continue
			if value == self.env:                continue
			if value == self.conf:               continue
			if value == self.mandatory_errormsg: continue
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
			fatal(self.mandatory_errormsg)

		if not Params.g_options.nocache:
			# Store the result no matter if it failed or not; if it is mandatory, Python never comes here anyway	
			self.conf.m_cache_table[newhash] = ret
		return ret
		
	
	# Override this method, not run()!
	def run_test(self):
		return 0


class configurator_base(enumerator_base):
	def __init__(self,conf):
		enumerator_base.__init__(self,conf)
		self.uselib_name	= ''

class program_enumerator(enumerator_base):
	def __init__(self,conf):
		enumerator_base.__init__(self, conf)
	
		self.name               = ''
		self.path               = []
		self.var                = None
		self.mandatory_errormsg	= 'The program cannot be found. Building cannot be performed without this program. Make sure it is installed and can be found.'

	def run_cache(self,retvalue):
		self.conf.checkMessage('program %s (cached)' % self.name, '', retvalue, option=retvalue)

	def run_test(self):
		ret = find_program_impl(self.env, self.name, self.paths, self.var)
		self.conf.checkMessage('program', self.name, ret, ret)
		return ret

class function_enumerator(enumerator_base):
	def __init__(self,conf):
		enumerator_base.__init__(self, conf)

		self.function_calls	= []
		self.headers		= []
		self.include_paths	= []
		self.header_code	= ''
		self.libs		= []
		self.lib_paths		= []
		self.mandatory_errormsg	= 'This function could not be found in the specified headers and libraries. Make sure you have the right headers & libraries installed.'

	def run_cache(self,retvalue):
		if retvalue:
			self.conf.checkMessage('function '+retvalue+' (cached)', '', 1, option='')
		else:
			for funccall in self.function_calls:
				self.conf.checkMessage('function %s (cached)' % str(funccall[0]), '', 0, option='')

	def run_test(self):
		foundname = ''
	
		ret = ''

		oldlibpath = self.env['LIBPATH']
		oldlib = self.env['LIB']

		for funccall in self.function_calls:
		
			code = self.header_code
			for header in self.headers:
				code=code+"#include <%s>\n" % header
			
			# If a third column is present and not empty, use the given code
			# (the third column contains optional custom code for probing functions; useful for overloaded functions)
			customcheck = 0
			if len(funccall)>=3:
				if funccall[2]: customcheck = 1			
			
			if customcheck:
				code+="""
int main()
{
	%s
	return 0;
}
""" % funccall[2];
				
			else:
				code+="""
int main()
{
	void *p;
	p=(void*)(%s);
	return 0;
}
""" % funccall[0];

			self.env['LIB'] = self.libs
			self.env['LIBPATH'] = self.lib_paths

			obj               = check_data()
			obj.define_name   = self.define_name
			obj.code          = code
			obj.includes      = self.include_paths
			obj.env           = self.env

			ret = self.conf.run_check(obj)
			
			self.conf.checkMessage('function %s' % funccall[0], '', not ret, option='')

			# If a second column is present and not empty, set the given defines
			# (the second column contains optional defines to be set)
			if len(funccall)>=2:
				if funccall[1]:
				
					# Necessary because direct assignment of "not ret" results in "True" or "False", but not 0 or 1
					if ret:
						retnum = 0
					else:
						retnum = 1
				
					self.env[funccall[1]]=retnum
					self.conf.addDefine(funccall[1],retnum)

			if not ret:
				# Store the found name
				foundname = funccall[0]
				break

		self.env['LIB'] = oldlib
		self.env['LIBPATH'] = oldlibpath
				
		return foundname

class library_enumerator(enumerator_base):
	def __init__(self, conf):
		enumerator_base.__init__(self,conf)

		self.names		= []
		self.paths		= []
		self.code		= 'int main() {return 0;}'
		self.mandatory_errormsg	= 'No matching library could be found. Make sure the library is installed and can be found.'

	def run_cache(self,retvalue):
		if retvalue:
			self.conf.checkMessage('library %s (cached)' % retvalue['name'], '', 1, option=retvalue['path'])
		else:
			for name in self.names:
				self.conf.checkMessage('library %s (cached)' % name, '', 0, option='')

	def update_hash(self,md5hash):
		enumerator_base.update_hash(self,md5hash)
		md5hash.update(str(self.env['LIBPATH']))

	def run_test(self):
		env = self.env
		oldlibpath = env['LIBPATH']
		oldlib = env['LIB']

		foundname = ''
		foundpath = ''
		found = {}

		code = self.code
		if not code: code = "\n\nint main() {return 0;}\n"

		ret=''
		
		if self.paths:

			for libname in self.names:
				for libpath in self.paths:

					#First look for a shared library
					full_libname=env['shlib_PREFIX']+libname+env['shlib_SUFFIX']
					ret = find_file(full_libname, [libpath])
					
					#If no shared lib was found, look for a static one
					if not ret:
						full_libname=env['staticlib_PREFIX']+libname+env['staticlib_SUFFIX']
						ret = find_file(full_libname, [libpath])				
	
					if ret:
						foundname = libname
						foundpath = libpath
						found['name'] = foundname
						found['path'] = foundpath
						break

				self.conf.checkMessage('library '+libname, '', ret, option=libpath)

				if ret: break
		
		if not ret:
			# Either lib was not found in the libpaths
			#or no paths were given. Test if the compiler can find the lib anyway

			for libname in self.names:
				env['LIB'] = [libname]

				env['LIBPATH'] = ['']

				obj               = check_data()
				obj.code          = code
				obj.env           = env
				ret = self.conf.run_check(obj)

				self.conf.checkMessage('library %s via linker' % libname, '', not ret, option='')
				#self.conf.checkMessage('library '+libname, '', not ret, option='')
	
				if not ret:
					foundname = libname
					foundpath = libpath
					found['name'] = foundname
					found['path'] = foundpath
					break

		env['LIB'] = oldlib
		env['LIBPATH'] = oldlibpath

		if found: ret = 1
		else:     ret = 0
		
		if self.define_name:
			env[self.define_name] = ret
			
		return found

class header_enumerator(enumerator_base):
	def __init__(self,conf):
		enumerator_base.__init__(self,conf)

		self.names			= []
		self.paths			= []
		self.code			= 'int main() {return 0;}'
		self.mandatory_errormsg	= 'No matching header could be found. Make sure the header is installed and can be found.'

	def run_cache(self,retvalue):
		if retvalue:
			self.conf.checkMessage('header %s (cached)' % retvalue['name'], '', 1, option=retvalue['path'])
		else:
			for name in self.names:
				self.conf.checkMessage('header %s (cached)' % name, '', 0, option='')

	def run_test(self):
		env = self.env

		foundname = ''
		foundpath = ''
		found = {}

		ret=''
		
		if self.paths:
		
			for headername in self.names:
				for incpath in self.paths:

					ret = find_file(headername, [incpath])
	
					if ret:
						foundname = headername
						foundpath = incpath
						found['name'] = foundname
						found['path'] = foundpath
						break
						
				self.conf.checkMessage('header '+headername, '', ret, option=incpath)
						
				if ret: break
					
		if not ret: # Either the header was not found in the incpaths, or no paths were given. Test if the compiler can find the header anyway
		
			for headername in self.names:

				obj               = check_data()
				#obj.define_name   = self.define_name #TODO: should this be '' ? The define is set below anyway
				obj.header_name   = headername
				obj.code          = self.code
				obj.env           = env
				ret = self.conf.run_check(obj)
					
				if not ret:
					foundname = headername
					foundpath = ''
					found['name'] = foundname
					found['path'] = foundpath
					break
					
				self.conf.checkMessage('header %s via compiler' % headername, '', ret, option='')

		if found: ret = 1
		else:     ret = 0

		if self.define_name:
			env[self.define_name] = ret

		return found

## ENUMERATORS END
#######################################################################

#######################################################################
## CONFIGURATORS

class cfgtool_configurator(configurator_base):
	def __init__(self,conf):
		configurator_base.__init__(self,conf)

		self.define_name        = ''
		self.binary		= ''
		self.cflagsparam 	= '--cflags'
		self.cppflagsparam	= '--cflags'
		self.libsparam		= '--libs'
		self.mandatory_errormsg	= 'The config tool cannot be found. Most likely the software to which the tool belongs is not installed.'

	def validate(self):
		try: self.names = self.names.split()
		except: pass
		if not self.define_name: self.define_name = 'HAVE_'+self.uselib_name

	def run_cache(self, retval):
		if retval:
			self.update_env(retval)
			self.conf.addDefine(self.define_name, 1)
		else:
			self.conf.addDefine(self.define_name, 0)
		self.conf.checkMessage('config-tool %s (cached)' % self.binary, '', retval, option='')

	def run_test(self):
		retval = {}

		#TODO: replace the "2>/dev/null" with some other mechanism for suppressing the stderr output
		bincflagscom = '%s %s 2>/dev/null' % (self.binary, self.cflagsparam)
		bincppflagscom = '%s %s 2>/dev/null' % (self.binary, self.cppflagsparam)
		binlibscom = '%s %s 2>/dev/null' % (self.binary, self.libsparam)
				
		try:
			ret = os.popen(bincflagscom).close()
			if ret: raise "error"

			retval['CCFLAGS_'+self.uselib_name]   = [os.popen(bincflagscom).read().strip()]
			retval['CXXFLAGS_'+self.uselib_name]  = [os.popen(bincppflagscom).read().strip()]
			retval['LINKFLAGS_'+self.uselib_name] = [os.popen(binlibscom).read().strip()]

			self.update_env(retval)
			self.conf.addDefine(self.define_name, 1)
		except:
			retval = {}
			self.conf.addDefine(self.define_name, 0)

		self.conf.checkMessage('config-tool '+self.binary, '', ret, option='')
		return retval

class pkgconfig_configurator(configurator_base):
	def __init__(self, conf):
		configurator_base.__init__(self,conf)

		self.name		= ''
		self.version		= ''
		self.path		= ''
		self.uselib_name        = ''
		self.binary		= ''
		self.variables		= []
		self.mandatory_errormsg	= 'No matching pkg-config package could be found. It is likely that the software to which the package belongs is not installed.'

	def validate(self):
		try: self.names = self.names.split()
		except: pass

		if not self.uselib_name: self.uselib_name = self.name.upper()
		if not self.define_name: self.define_name = 'HAVE_'+self.uselib_name

	def run_cache(self,retvalue):
		if retvalue:
			self.update_env(retvalue)
			self.conf.addDefine(self.define_name, 1)
		else:
			self.conf.addDefine(self.define_name, 0)

		self.conf.checkMessage('package %s (cached)' % self.name, '', retvalue, option='')

	def run_test(self):
		pkgpath = self.path
		pkgbin = self.binary
		uselib = self.uselib_name
		
		if not pkgbin: pkgbin='pkg-config'
		if pkgpath: pkgpath='PKG_CONFIG_PATH='+pkgpath
		pkgcom = '%s %s' % (pkgpath, pkgbin)
		
		retval = {}
		
		try:
			if self.version:
				ret = os.popen("%s --atleast-version=%s %s" % (pkgcom, self.version, self.name)).close()
				self.conf.checkMessage('package %s >= %s' % (self.name, self.version), '', not ret)
				if ret: raise "error"
			else:
				ret = os.popen("%s %s" % (pkgcom, self.name)).close()
				self.conf.checkMessage('package %s ' % (self.name), '', not ret)
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
				if len(variable) >= 2:
					if variable[1]:
						var_defname = variable[1]

				if not var_defname:				
					var_defname = uselib + '_' + variable.upper()

				retval[var_defname] = os.popen('%s --variable=%s %s' % (pkgcom, variable, self.name)).read().strip()

			self.conf.addDefine(self.define_name, 1)
			self.update_env(retval)	
		except:
			retval = {}
			self.conf.addDefine(self.define_name, 0)

		return retval


class library_configurator(configurator_base):
	def __init__(self,conf):
		configurator_base.__init__(self,conf)

		self.names			= []
		self.paths			= []
		self.code			= ''
		self.mandatory_errormsg	= 'No matching library could be found. Make sure the library is installed and can be found.'


	def run_cache(self, retval):
		#if not define_name: define_name = 'HAVE_'+self.uselib_name
		if retval:
			self.conf.checkMessage('library '+retval['name']+' (cached)', '', 1, option=retval['path'])
			self.update_env(retval)
			self.conf.addDefine(self.define_name, 1)
		else:
			self.conf.addDefine(self.define_name, 0)

			for name in self.names:
				self.conf.checkMessage('library '+name+' (cached)', '', 0, option='')

	def validate(self):
		try: self.names = self.names.split()
		except: pass
		if not self.define_name: self.define_name = 'HAVE_'+self.uselib_name

	def run_test(self):
		library_enumerator = self.conf.create_library_enumerator()
		library_enumerator.names = self.names
		library_enumerator.paths = self.paths
		library_enumerator.code = self.code
		library_enumerator.define_name = self.define_name
		library_enumerator.env = self.env
		ret = library_enumerator.run()

		if ret:
			self.env['LIB_'+self.uselib_name]     = ret['name']
			self.env['LIBPATH_'+self.uselib_name] = ret['path']
		return ret

class header_configurator(configurator_base):
	def __init__(self,conf):
		configurator_base.__init__(self,conf)

		self.names			= []
		self.paths			= []
		self.code			= 'int main() {return 0;}'
		self.mandatory_errormsg	= 'No matching header could be found. Make sure the header is installed and can be found.'


	def validate(self):
		try: self.names = self.names.split()
		except: pass
		if not self.define_name: self.define_name = 'HAVE_'+self.uselib_name

	def run_cache(self, retvalue):
		if retvalue:
			self.update_env(retvalue)
			self.conf.checkMessage('library %s (cached)' % retvalue['name'], '', 1, option=retvalue['path'])
			self.conf.addDefine(self.define_name, 1)
		else:
			self.conf.addDefine(self.define_name, 0)
			for name in self.names:
				self.conf.checkMessage('header '+name+' (cached)', '', 0, option='')

	def run_test(self):	
		header_enumerator = self.conf.create_header_enumerator()
		header_enumerator.names = self.names
		header_enumerator.paths = self.paths
		header_enumerator.code = self.code
		header_enumerator.define_name = self.define_name
		ret = header_enumerator.run()
		
		if ret:
			self.env['CPPPATH_'+self.uselib_name] = ret['path']
		return ret

# CONFIGURATORS END
#######################################################################

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

		self.define_name   = '' # define to add if run is successful

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

	def checkTool(self, input, tooldir=None):
		"load a waf tool"
		if type(input) is types.ListType: lst = input
		else: lst = input.split()

		ret = True
		for i in lst:
			ret = ret and self._checkToolImpl(i, tooldir)
		return ret

	def _checkToolImpl(self, tool, tooldir=None):
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
		self.addDefine(define, ret)
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

		pkgconf.uselib_name = destvar
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


	def addDefine(self, define, value, quote=-1):
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
			lst = lst[:len(lst)-1]
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

		bdir = os.path.join( dir, '_build_')
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
				ret = os.popen(lastprog).read().strip()
			except:
				pass
		return ret

