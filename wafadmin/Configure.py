#! /usr/bin/env python
# encoding: utf-8

import os, types, sys, string, imp, cPickle, md5
import Params, Environment, Runner, Build, Utils
from Params import debug, error, trace, fatal


import traceback


g_maxlen = 35
g_debug  = 0



class enumerator_base:
	def __init__(self,conf):
		self.env				= None
		self.conf				= conf
		self.define_name		= ''
		self.mandatory			= 0
		self.mandatory_errormsg	= 'A mandatory check failed. Make sure all dependencies are ok and can be found.'

	def update_hash(self,md5hash):
		classvars = vars(self)
		for (var,value) in classvars.iteritems():
			if not callable(var) and value != self and value != self.env and value != self.conf and value != self.mandatory_errormsg:
				md5hash.update(str(value))
		
	def hash(self):
		m = md5.new()
		self.update_hash(m)

		return m.digest()

	def print_message_cached(self,retvalue):
		pass
	
	def run(self):
		if not Params.g_options.nocache:
			newhash = self.hash()
			try:
				ret = self.conf.m_cache_table[newhash]
				self.print_message_cached(ret)
				return ret
			except KeyError:
				pass
		
		ret = self.run_impl()
		
		if self.mandatory and not ret:
			fatal(self.mandatory_errormsg)

		if not Params.g_options.nocache:
			# Store the result no matter if it failed or not; if it is mandatory, Python never comes here anyway	
			self.conf.m_cache_table[newhash] = ret
		return ret
		
	
	# Override this method, not run()!
	def run_impl(self):
		return 0


class configurator_base(enumerator_base):
	def __init__(self,conf):
		enumerator_base.__init__(self,conf)
	
		self.uselib_name	= ''





# ENUMERATORS

class program_enumerator(enumerator_base):
	def __init__(self,conf):
		enumerator_base.__init__(self, conf)
	
		self.name			= ''
		self.paths 			= []
		self.mandatory_errormsg	= 'The program cannot be found. Building cannot be performed without this program. Make sure it is installed and can be found.'


	def print_message_cached(self,retvalue):
		self.conf.checkMessage('program '+self.name+' (cached)', '', retvalue, option=retvalue)


	def run_impl(self):
		ret = find_program_impl(self.conf.env, self.name, self.paths)
		self.conf.checkMessage('program', self.name, ret, ret)

		if self.define_name:
			env[self.define_name] = ret

		return ret


class function_enumerator(enumerator_base):
	def __init__(self,conf):
		enumerator_base.__init__(self, conf)

		self.function_calls	= []
		self.headers		= []
		self.include_paths	= []
		self.header_code	= ''
		self.libs			= []
		self.lib_paths		= []
		self.mandatory_errormsg	= 'This function could not be found in the specified headers and libraries. Make sure you have the right headers & libraries installed.'


	def print_message_cached(self,retvalue):
		if retvalue:
			self.conf.checkMessage('function '+retvalue+' (cached)', '', 1, option='')
		else:
			for funccall in self.function_calls:
				self.conf.checkMessage('function '+funccall[0]+' (cached)', '', 0, option='')


	def run_impl(self):
		env = self.env	
		if not env: env = self.conf.env

		foundname = ''
	
		ret = ''

		oldlibpath = env['LIBPATH']
		oldlib = env['LIB']

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

			env['LIB'] = self.libs
			env['LIBPATH'] = self.lib_paths

			obj               = check()
			obj.fun           = ''
			obj.define_name   = self.define_name
			obj.code          = code
			obj.includes      = self.include_paths
			obj.env           = env

			ret = self.conf.check(obj)
			
			self.conf.checkMessage('function '+funccall[0], '', not ret, option='')

			# If a second column is present and not empty, set the given defines
			# (the second column contains optional defines to be set)
			if len(funccall)>=2:
				if funccall[1]:
				
					# Necessary because direct assignment of "not ret" results in "True" or "False", but not 0 or 1
					if ret:
						retnum = 0
					else:
						retnum = 1
				
					env[funccall[1]]=retnum
					self.conf.addDefine(funccall[1],retnum)

			if not ret:
				# Store the found name
				foundname = funccall[0]
				break
				
				
				
		
		env['LIB'] = oldlib
		env['LIBPATH'] = oldlibpath
				
		return foundname


class library_enumerator(enumerator_base):
	def __init__(self,conf):
		enumerator_base.__init__(self,conf)

		self.names			= []
		self.paths			= []
		self.code			= ''
		self.mandatory_errormsg	= 'No matching library could be found. Make sure the library is installed and can be found.'


	def print_message_cached(self,retvalue):
		if retvalue:
			self.conf.checkMessage('library '+retvalue[0]+' (cached)', '', 1, option=retvalue[1])
		else:
			for name in self.names:
				self.conf.checkMessage('library '+name+' (cached)', '', 0, option='')
		


	def update_hash(self,md5hash):
		enumerator_base.update_hash(self,md5hash)

		env = self.env
		if not env: env=self.conf.env

		md5hash.update(str(env['LIBPATH']))


	def run_impl(self):
		env = self.env
		if not env: env=self.conf.env

		oldlibpath = env['LIBPATH']
		oldlib = env['LIB']

		foundname = ''
		foundpath = ''
		found = []

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
						found = [foundname, foundpath]
						break

				self.conf.checkMessage('library '+libname, '', ret, option=libpath)
						
				if ret: break
		
		if not ret: # Either lib was not found in the libpaths, or no paths were given. Test if the compiler can find the lib anyway

			for libname in self.names:
				env['LIB'] = [libname]

				env['LIBPATH'] = ['']
				obj               = check()
				obj.code          = code
				obj.fun           = 'find_library'
				obj.env           = env
				ret = self.conf.check(obj)

				self.conf.checkMessage('library '+libname+' via linker', '', not ret, option='')
				#self.conf.checkMessage('library '+libname, '', not ret, option='')
	
				if not ret:
					foundname = libname
					foundpath = libpath
					found = [foundname, foundpath]
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
		self.code			= ''
		self.mandatory_errormsg	= 'No matching header could be found. Make sure the header is installed and can be found.'


	def print_message_cached(self,retvalue):
		if retvalue:
			self.conf.checkMessage('header '+retvalue[0]+' (cached)', '', 1, option=retvalue[1])
		else:
			for name in self.names:
				self.conf.checkMessage('header '+name+' (cached)', '', 0, option='')


	def run_impl(self):
		env = self.env	
		if not env: env = self.conf.env

		foundname = ''
		foundpath = ''
		found = []

		ret=''
		
		if self.paths:
		
			for headername in self.names:
				for incpath in self.paths:

					ret = find_file(headername, [incpath])
	
					if ret:
						foundname = headername
						foundpath = incpath
						found = [foundname, foundpath]
						break
						
				self.conf.checkMessage('header '+headername, '', ret, option=incpath)
						
				if ret: break
					
		if not ret: # Either the header was not found in the incpaths, or no paths were given. Test if the compiler can find the header anyway
		
			for headername in self.names:
				
				obj               = check()
				obj.fun           = 'check_header'
				obj.define_name   = self.define_name #TODO: should this be '' ? The define is set below anyway
				obj.header_name   = headername
				obj.headers_code  = self.code
				obj.env           = env
				ret = self.conf.check(obj)
					
				if not ret:
					foundname = headername
					foundpath = ''
					found = [foundname, foundpath]
					break
					
				self.conf.checkMessage('header '+headername+' via compiler', '', ret, option='')

		if found: ret = 1
		else:     ret = 0

		if self.define_name:
			env[self.define_name] = ret

		return found

# ENUMERATORS END



# CONFIGURATORS

class cfgtool_configurator(configurator_base):
	def __init__(self,conf):
		configurator_base.__init__(self,conf)
	
		self.binary			= ''
		self.cflagsparam 	= '--cflags'
		self.cppflagsparam	= '--cflags'
		self.libsparam		= '--libs'
		self.mandatory_errormsg	= 'The config tool cannot be found. Most likely the software to which the tool belongs is not installed.'


	def print_message_cached(self,retvalue):
		if retvalue:
			self.conf.checkMessage('config-tool '+self.binary+' (cached)', '', 1, option='')
		else:
			self.conf.checkMessage('config-tool '+self.binary+' (cached)', '', 0, option='')


	def run_impl(self):
		env = self.env	
		if not env: env = self.conf.env
		
		define_name = self.define_name
		if not define_name: define_name = 'HAVE_'+self.uselib_name
	
		#TODO: replace the "2>/dev/null" with some other mechanism for suppressing the stderr output
		bincflagscom = '%s %s 2>/dev/null' % (self.binary, self.cflagsparam)
		bincppflagscom = '%s %s 2>/dev/null' % (self.binary, self.cppflagsparam)
		binlibscom = '%s %s 2>/dev/null' % (self.binary, self.libsparam)
				
		try:
			ret = os.popen(bincflagscom).close()
			if ret: raise "error"

			env['CCFLAGS_'+self.uselib_name]   = os.popen(bincflagscom).read().strip()
			env['CXXFLAGS_'+self.uselib_name]  = os.popen(bincppflagscom).read().strip()
			env['LINKFLAGS_'+self.uselib_name] = os.popen(binlibscom).read().strip()
			self.conf.addDefine(define_name, 1)
			ret = 1

		except:
			ret = 0
			self.conf.addDefine(define_name, 0)

		self.conf.checkMessage('config-tool '+self.binary, '', ret,option='')
			
		return ret


class pkgconfig_configurator(configurator_base):
	def __init__(self,conf):
		configurator_base.__init__(self,conf)

		self.name			= ''
		self.version		= ''
		self.path			= ''
		self.binary			= ''
		self.variables		= []
		self.mandatory_errormsg	= 'No matching pkg-config package could be found. It is likely that the software to which the package belongs is not installed.'


	def print_message_cached(self,retvalue):
		if retvalue:
			self.conf.checkMessage('package '+self.name+' (cached)', '', 1, option='')
		else:
			self.conf.checkMessage('package '+self.name+' (cached)', '', 0, option='')


	def run_impl(self):
		pkgpath = self.path
		pkgbin = self.binary
		
		env = self.env
		if not env: env=self.conf.env

		uselib = self.uselib_name
		if not uselib: uselib = self.name.upper()

		define_name = self.define_name	
		if not define_name: define_name = 'HAVE_'+uselib

		if not pkgbin: pkgbin='pkg-config'
		if pkgpath: pkgpath='PKG_CONFIG_PATH='+pkgpath
		pkgcom = '%s %s' % (pkgpath, pkgbin)
		try:
			if self.version:
				ret = os.popen("%s --atleast-version=%s %s" % (pkgcom, self.version, self.name)).close()
				self.conf.checkMessage('package %s >= %s' % (self.name, self.version), '', not ret)
				if ret: raise "error"
			else:
				ret = os.popen("%s %s" % (pkgcom, self.name)).close()
				self.conf.checkMessage('package %s ' % (self.name), '', not ret)
				if ret: raise "error"
				
			env['CCFLAGS_'+uselib]   = os.popen('%s --cflags %s' % (pkgcom, self.name)).read().strip()
			env['CXXFLAGS_'+uselib]  = os.popen('%s --cflags %s' % (pkgcom, self.name)).read().strip()
			#env['LINKFLAGS_'+uselib] = os.popen('%s --libs %s' % (pkgcom, self.name)).read().strip()
			self.conf.addDefine('HAVE_'+uselib, 1)

			# Store the library names:
			modlibs = os.popen('%s --libs-only-l %s' % (pkgcom, self.name)).read().strip().split()
			env['LIB_'+uselib] = []
			for item in modlibs:
				env['LIB_'+uselib].append( item[2:] ) #Strip '-l'

			# Store the library paths:
			modpaths = os.popen('%s --libs-only-L %s' % (pkgcom, self.name)).read().strip().split()
			env['LIBPATH_'+uselib] = []
			for item in modpaths:
				env['LIBPATH_'+uselib].append( item[2:] ) #Strip '-l'

			for variable in self.variables:
				var_defname = ''
				if len(variable) >= 2:
					if variable[1]:
						var_defname = variable[1]

				if not var_defname:				
					var_defname = uselib + '_' + variable.upper()

				env[var_defname] = os.popen('%s --variable=%s %s' % (pkgcom, variable, self.name)).read().strip()

		except:
			self.conf.addDefine(define_name, 0)
			return 0
		return 1


class library_configurator(configurator_base):
	def __init__(self,conf):
		configurator_base.__init__(self,conf)

		self.names			= []
		self.paths			= []
		self.code			= ''
		self.mandatory_errormsg	= 'No matching library could be found. Make sure the library is installed and can be found.'


	def print_message_cached(self,retvalue):
		if retvalue:
			self.conf.checkMessage('library '+retvalue[0]+' (cached)', '', 1, option=retvalue[1])
		else:
			for name in self.names:
				self.conf.checkMessage('library '+name+' (cached)', '', 0, option='')


	def run_impl(self):
		env = self.env
		if not env: env = self.conf.env

		define_name = self.define_name	
		if not define_name: define_name = 'HAVE_'+self.uselib_name

		library_enumerator = self.conf.create_library_enumerator()
		library_enumerator.names = self.names
		library_enumerator.paths = self.paths
		library_enumerator.code = self.code
		library_enumerator.define_name = define_name
		library_enumerator.env = env
		ret = library_enumerator.run()

		if ret:
			env['LIB_'+self.uselib_name]=ret[0]
			env['LIBPATH_'+self.uselib_name]=ret[1]
		return ret


class header_configurator(configurator_base):
	def __init__(self,conf):
		configurator_base.__init__(self,conf)

		self.names			= []
		self.paths			= []
		self.code			= ''
		self.mandatory_errormsg	= 'No matching header could be found. Make sure the header is installed and can be found.'


	def print_message_cached(self,retvalue):
		if retvalue:
			self.conf.checkMessage('library '+retvalue[0]+' (cached)', '', 1, option=retvalue[1])
		else:
			for name in self.names:
				self.conf.checkMessage('header '+name+' (cached)', '', 0, option='')


	def run_impl(self):	
		env = self.env
		if not env: env = self.conf.env

		define_name = self.define_name
		if not define_name: define_name = 'HAVE_'+self.uselib_name
		
		header_enumerator = self.conf.create_header_enumerator()
		header_enumerator.names = self.names
		header_enumerator.paths = self.paths
		header_enumerator.code = self.code
		header_enumerator.define_name = define_name
		ret = header_enumerator.run()
		
		if ret:
			env['CPPPATH_'+self.uselib_name]=ret[1]
		return ret

# CONFIGURATORS END










class check:
	def __init__(self):
		self.fun           = '' # function calling

		self.env           = '' # environment to use

		self.code          = '' # the code to execute

		self.flags         = '' # the flags to give to the compiler

		self.uselib        = '' # uselib
		self.includes      = '' # include paths

		self.function_name = '' # function to check for
		self.headers_code  = '' # additional headers for the main function

		self.lib           = []
		self.libpath       = [] # libpath for linking

		self.define_name   = '' # define to add if run is successful

		self.header_name   = '' # header name to check for

		self.options       = '' # command-line options

	def hash(self):
		attrs = 'fun code uselib includes function_name headers_code lib libpath define_name header_name options flags'
		m = md5.new()
		for a in attrs.split():
			val = getattr(self, a)
			m.update(str(val))
		if self.fun == 'find_library':
			m.update(str(self.env['LIBPATH']))

		return m.digest()

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

def find_program_impl(lenv, file, path_list=None):
	if not path_list: path_list = []
	elif type(path_list) is types.StringType: path_list = [path_list]

	if lenv['WINDOWS']: file += '.exe'
	if not path_list: 
		try:
			path_list = os.environ['PATH'].split(':')
		except KeyError:
			return None
		# ???
		#if type(path_list) is types.StringType: 
		#	path_list = string.split(path_list, os.pathsep)
	for dir in path_list:
		if os.path.exists( os.path.join(dir, file) ):
			return os.path.join(dir, file)
	return ''

def find_program_using_which(lenv, prog):
	if lenv['WINDOWS']: # we're not depending on Cygwin
		return ''
	return os.popen("which %s 2>/dev/null" % prog).read().strip()
	
def sub_config(file):
	return ''
	
	
	
	



class Configure:
	def __init__(self, env=None, blddir='', srcdir=''):
		#for key in self.env.m_table:
		#	if key == 'modules':
		#		self.modules = self.env[key].split()

		self.env       = None
		self.m_envname = ''

		self.m_blddir = blddir
		self.m_srcdir = srcdir

		self.m_allenvs = {}
		self.defines = {}
		self.configheader = 'config.h'
		self.cwd  = os.getcwd()

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

	def __del__(self):
		if not self.env['tools']:
			self.error('you should add at least a checkTool() call in your wscript, otherwise you cannot build anything')

	def set_env_name(self, name, env):
		self.m_allenvs[name] = env
		return env

	def retrieve(self, name, fromenv=None):
		try:
			env = self.m_allenvs[name]
			if fromenv: print "warning, the environment %s may have been configured already" % name
			return env
		except:
			env = Environment.Environment()
			self.m_allenvs[name] = env
			return env

	def setenv(self, name):
		self.env     = self.retrieve(name)
		self.envname = name

	def execute(self):
		"""for what is this function"""
		env = Environment.Environment()
		sys.path.append('bksys')
		for module in self.modules:
			module = __import__(module)
			if module.exists(env):
				env = module.generate(env)
		filename = env['OS'] + '.env'
		env.store(filename)

	def TryBuild(self, code, options='', pathlst=[], uselib=''):
		""" Uses the cache """

		hash = "".join(['TryBuild', code, str(options), str(pathlst), str(uselib)])
		if not Params.g_options.nocache:
			if hash in self.m_cache_table:
				#print "cache for tryBuild found !!!  skipping ", hash
				return self.m_cache_table[hash]

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
		dest.write(code)
		dest.close()

		env = self.env.copy()
		Utils.reset()
	
		back=os.path.abspath('.')

		bld = Build.Build()
		bld.load_dirs(dir, bdir, isconfigure=1)
		bld.m_allenvs['default'] = env

		os.chdir(dir)

		for t in env['tools']: env.setup(**t)

		# not sure yet when to call this:
		#bld.rescan(bld.m_srcnode)

		# TODO for the moment it is c++, in the future it will be c
		# and then we may need other languages here too
		if env['CXX']:
			import cpp
			obj=cpp.cppobj('program')
		else:
			import cc
			obj=cc.ccobj('program')

		obj.source = 'test.c'
		obj.target = 'test'
		obj.uselib = uselib

		envcopy = bld.m_allenvs['default'].copy()
		for p in pathlst:
			envcopy['CPPFLAGS'].append(' -I%s ' % p)

		(a,b,c) = Params.get_trace()
		quiet = Runner.g_quiet
		try:
			Params.set_trace(0,0,0)
			Runner.g_quiet = 1
			ret = bld.compile()
		except:
			ret = 1
			#raise
		Params.set_trace(a,b,c)
		Runner.g_quiet = quiet

		#if runopts is not None:
		#	ret = os.popen(obj.m_linktask.m_outputs[0].abspath(obj.env)).read().strip()

		os.chdir(back)
		Utils.reset()

		if not ret: self.m_cache_table[hash] = ret
		return ret

	def TryRun(self, code, options='', pathlst=[], uselib=''):
		""" Uses the cache """

		hash = "".join(['TryRun', code, str(options), str(pathlst), str(uselib)])
		if not Params.g_options.nocache:
			if hash in self.m_cache_table:
				#print "cache for tryBuild found !!!  skipping ", hash
				return self.m_cache_table[hash]

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
		dest.write(code)
		dest.close()

		env = self.env.copy()
		Utils.reset()
	
		back=os.path.abspath('.')

		bld = Build.Build()
		bld.load_dirs(dir, bdir, isconfigure=1)
		bld.m_allenvs['default'] = env

		os.chdir(dir)

		for t in env['tools']: env.setup(**t)

		# not sure yet when to call this:
		#bld.rescan(bld.m_srcnode)

		# TODO for the moment it is c++, in the future it will be c
		# and then we may need other languages here too
		if env['CXX']:
			import cpp
			obj=cpp.cppobj('program')
		else:
			import cc
			obj=cc.ccobj('program')

		obj.source = 'test.c'
		obj.target = 'test'
		obj.uselib = uselib

		envcopy = bld.m_allenvs['default'].copy()
		for p in pathlst:
			envcopy['CPPFLAGS'].append(' -I%s ' % p)

		try:
			ret = bld.compile()
		except:
			ret = 1
			raise

		ret = os.popen(obj.m_linktask.m_outputs[0].abspath(obj.env)).read().strip()

		os.chdir(back)
		Utils.reset()

		self.m_cache_table[hash] = ret
		return ret

	def TryCPP(self,code,options=''):
		"""run cpp for a given file, returns 0 if no errors (standard)
		This method is currently platform specific and has to be made platform 
		independent, probably by refactoring the c++ or cc build engine
		"""
		dest=open(os.path.join(self.env['_BUILDDIR_'], 'test.c'), 'w')
		dest.write(code)
		dest.close()
		# TODO: currently only for g++ 
		# implement platform independent compile function probably by refactoring 
		# Task/Action class
		return Runner.exec_command('%s test.c -o test %s 2>test.log '% (self.env['CPP'], str(options)) )

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
		if self.defines.has_key(define):
			return 1
		else:
			return 0

	def getDefine(self, define):
		"""get the value of a previously stored define"""
		if self.defines.has_key(define):
			return self.defines[define]
		else:
			return 0

	def writeConfigHeader(self, configfile='config.h', env=''):
		"""save the defines into a file"""
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
		"""set a config header file"""
		self.configheader = header
		pass

	# OBSOLETE
	def checkHeader(self, header, define='', pathlst=[]):
		"""find a C/C++ header"""
		if type(header) is types.ListType:
			for i in header: 
				self.checkHeader(i, pathlst=pathlst)
			return
			
		if define == '':
			define = 'HAVE_'+header.upper().replace('.','_').replace('/','_')

		if self.isDefined(define):
			return self.getDefine(define)
	
		code = """
#include <%s>
int main() {
	return 0;
}
""" % header
		is_found = int(not self.TryBuild(code, pathlst=pathlst))
		self.checkMessage('header',header,is_found)
		self.addDefine(define,is_found)
		return is_found
	
	# OBSOLETE
	def checkFunction(self, function, headers = None, define='', language = None):
		"""find a function"""
		if define == '':
			define = 'HAVE_'+function.upper().replace('.','_')

		if self.isDefined(define):
			return self.getDefine(define)

		if not headers:
			headers = """
#ifdef __cplusplus
extern "C"
#endif
char %s();
""" % function

		code = """
int main() {
	%s();
	return 0;
}
""" % function

		is_found = int(not self.TryBuild(headers + code))
		self.checkMessage('function',function,is_found)
		self.addDefine(define,is_found)
		return is_found

	# OBSOLETE
	def checkProgram(self, file, path_list=None, var=None):
		""" Find an application in the list of paths given as input """
		#print path_list
		# let the user override CXX from 1. the env variable 2. the os.environment
		if var:
			try:
				if self.env[var]:
					file=self.env[var]
				else:
					pvar=os.environ[var]
					if pvar: file=pvar
			except:
				pass
		ret = find_program_impl(self.env, file, path_list)
		self.checkMessage('program',file,ret,ret)
		return ret

	def checkLibrary(self, libname, funcname=None, headers=None, define='', uselib=''):
		"""find a library"""
		upname = libname.upper().replace('.','_')
		if define == '':
			define = 'HAVE_'+upname

		# wait ???? TODO
		#if self.isDefined(define):
		#	return self.getDefine(define)

		if not headers and funcname:
			headers = """
#ifdef __cplusplus
extern "C"
#endif
char %s();
""" % funcname

			code = """
int main() {
	%s();
	return 0;
}
""" % funcname
		elif not headers and not funcname: 
			headers = ""
			code = """
int main() { return 0; }
"""
		else:
			code = """
int main() {
	%s();
	return 0;
}
""" % funcname
		
		self.env['LINKFLAGS_'+upname] = self.env['LIB_ST'] % libname

		

		# TODO setup libpath
		libpath = "."

		ret = self.TryBuild(headers + code, pathlst = [libpath], uselib=uselib)

		is_found = int(not ret)
		self.checkMessage('library', libname, is_found)
		self.addDefine(define, is_found)
		return is_found

	def checkTool(self, input, tooldir=None):
		"""check if a waf tool is available"""
		if type(input) is types.ListType:
			lst = input
		else:
			lst = input.split()

		ret = True
		for i in lst:
			ret = ret and self._checkToolImpl(i, tooldir)
		return ret

	def _checkToolImpl(self, tool, tooldir=None):
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
			
	def checkModule(self,tool):
		"""check if a a user provided module is given"""
		pass

	def error(self,module,str=''):
		print "configuration error: " + module + " " + str

	def store(self, file=''):
		"""save config results into a cache file"""
		try: os.makedirs(Params.g_cachedir)
		except OSError: pass

		if not self.m_allenvs:
			fatal("nothing to store in Configure !")
		for key in self.m_allenvs:
			tmpenv = self.m_allenvs[key]
			tmpenv.store(os.path.join(Params.g_cachedir, key+'.cache.py'))

	def checkMessage(self,type,msg,state,option=''):
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

	def detect(self,tool):
		"""deprecated, replaced by checkTool"""
		return self.checkTool(tool)
	
	def sub_config(self, dir):
		current = self.cwd

		self.cwd = os.path.join(self.cwd, dir)
		cur = os.path.join(self.cwd, 'wscript')

		try:
			mod = Utils.load_module(cur)
		except:
			msg = "no module or function configure was found in wscript\n[%s]:\n * make sure such a function is defined \n * run configure from the root of the project"
			fatal(msg % self.cwd)
		#try:
		mod.configure(self)
		#except AttributeError:
		#	msg = "no configure function was found in wscript\n[%s]:\n * make sure such a function is defined \n * run configure from the root of the project"
		#	fatal(msg % self.cwd)

		self.cwd = current

	# this method is called usually only once
	def cleanup(self):
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

	def hook(self, func):
		# attach the function given as input as new method
		setattr(self.__class__, func.__name__, func) 

	def mute_logging(self):
		if Params.g_options.verbose: return

		# store the settings
		(self._a,self._b,self._c) = Params.get_trace()
		self._quiet = Runner.g_quiet
		# then mute
		if not g_debug:
			Params.set_trace(0,0,0)
			Runner.g_quiet = 1

	def restore_logging(self):
		if Params.g_options.verbose: return

		# restore the settings
		if not g_debug:
			Params.set_trace(self._a,self._b,self._c)
			Runner.g_quiet = self._quiet






	def check(self, obj):
		"compile, etc"
		def checkS(ret, cached):
			res = int(not ret)
			if obj.fun == 'check_function':
				if not obj.define_name:
       		                 	obj.define_name = 'HAVE_'+obj.function_name.upper().replace('.','_').replace('/','_')
				self.addDefine(obj.define_name, res)
				self.checkMessage('function', obj.function_name+cached, res)
			elif obj.fun == 'check_header':
				if not obj.define_name:
					obj.define_name = 'HAVE_'+obj.header_name.upper().replace('.','_').replace('/','_')
				self.addDefine(obj.define_name, res)
				#self.checkMessage('header', obj.header_name+cached, res)
			elif obj.fun == 'check_flags':
				self.checkMessage('flags', obj.flags, res)


		# first make sure the code to execute is defined
		if not obj.code:
			if obj.fun == 'check_header':
				obj.code = """
%s
#include <%s>
int main() {
	return 0;
}
""" % (obj.headers_code, obj.header_name)
			elif obj.fun == 'check_function':
				p=obj.function_name
				if not '(' in p:
					p = p+'();'
				elif not ';' in obj.function_name:
					p = p+';'
				obj.code = """
%s
int main() {
	%s
        return 0;
}
""" % (obj.headers_code, p)
			else:
				fatal('no code to process in check')
				
		# do not run the test if it is in cache
		#hash = "".join([obj.fun, obj.code])
		hash = obj.hash()

		# return early if "--nocache" on the command-line was given - do not re-run the compilation
		if not Params.g_options.nocache:
			if hash in self.m_cache_table:
				#print "cache for tryBuild found !!!  skipping ", hash
				ret = self.m_cache_table[hash]
				if obj.fun == 'try_build_and_exec':
					return ret
				if obj.fun == 'find_library':
					return ret
				checkS(ret, " (cached)")

				#if obj.fun == 'check_function':
				#	self.checkMessage('function', obj.function_name+' (cached)', not str(ret))
				#elif obj.fun == 'check_header':
				#	self.checkMessage('header', obj.header_name+' (cached)', not str(ret))

				return ret

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

		if obj.env:
			env = obj.env
		else:
			env = self.env.copy()

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
		if obj.fun == 'try_build_and_exec':
			lastprog = o.m_linktask.m_outputs[0].abspath(o.env)

		#if runopts is not None:
		#	ret = os.popen(obj.m_linktask.m_outputs[0].abspath(obj.env)).read().strip()

		os.chdir(back)
		Utils.reset()

		checkS(ret, "")
		if not obj.fun in ['check_function', 'check_header', 'check_flags']:
			# store the results of the build
			if not ret: self.m_cache_table[hash] = ret
		else:
			self.m_cache_table[hash] = ret

		# if we need to run the program, try to get its result
		if obj.fun == 'try_build_and_exec':
			if ret: return None
			try:
				ret = os.popen(lastprog).read().strip()
				self.m_cache_table[hash] = ret
			except:
				pass

		return ret





	# TODO for the moment it will do the same as try_build
	def try_compile(self, code, env='', uselib=''):
		"check if a c/c++ piece of code compiles"
		obj        = check()
		obj.fun    = 'try_compile'
		obj.code   = code
		obj.env    = env
		obj.uselib = uselib
		self.check(obj)

	def try_build(self, code, env='', uselib=''):
		"check if a c/c++ piece of code compiles and links into a program"
		obj        = check()
		obj.fun    = 'try_build'
		obj.code   = code
		obj.env    = env
		obj.uselib = uselib
		return self.check(obj)

	def try_build_and_exec(self, code, env='', uselib='', options=''):
		"check if a c/c++ piece of code compiles and then return its output (None if it does not compile)"
		obj         = check()
		obj.fun     = 'try_build_and_exec'
		obj.code    = code
		obj.env     = env
		obj.uselib  = uselib
		obj.options = options
		return self.check(obj)





	def check_header(self, header_name, define_name='', headers_code='', includes=[]):
		"check if a header is available in the include path given and set a define"
		obj               = check()
		obj.fun           = 'check_header'
		obj.define_name   = define_name
		obj.header_name   = header_name
		obj.headers_code  = headers_code
		obj.includes      = includes
		obj.env           = self.env
		return self.check(obj)

	def check_function(self, function_name, define_name='', headers_code=''):
		"check if a function exists in the include path "
		obj               = check()
		obj.fun           = 'check_function'
		obj.function_name = function_name
		obj.define_name   = define_name
		obj.headers_code  = headers_code
		obj.env           = self.env
		return self.check(obj)

	def check_flags(self, flags):
		obj               = check()
		obj.fun           = 'check_flags'
		obj.flags         = flags
		obj.code          = 'int main() { return 0; }\n'
		obj.env           = self.env
		return not self.check(obj)




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



### autoconfig_xxx functions end




