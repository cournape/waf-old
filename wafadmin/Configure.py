#! /usr/bin/env python
# encoding: utf-8

import os, types, sys, string, imp, cPickle
import Params, Environment, Runner, Build, Utils
from Params import debug, error, trace, fatal

maxlen = 35

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
			return os.path.join(dir, file)
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

def find_program(lenv, file, path_list=None):
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

		try:
			file = open(os.sep.join([os.environ['HOME'], '.wafcache', 'runs.txt']), 'rb')
			self.m_cache_table = cPickle.load(file)
			file.close()
		except:
			pass

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

		env.setup(env['tools'])

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

		#if runopts is not None:
		#	ret = os.popen(obj.m_linktask.m_outputs[0].abspath(obj.env)).read().strip()

		os.chdir(back)
		Utils.reset()

		self.m_cache_table[hash] = ret
		return ret

	def TryRun(self, code, options='', pathlst=[], uselib=''):
		""" Uses the cache """

		hash = "".join(['TryRun', code, str(options), str(pathlst), str(uselib)])
		if not Params.g_options.nocache:
			if hash in self.m_cache_table:
				#print "cache for tryBuild found !!!  skipping ", hash
				return self.m_cache_table[hash]

		dir = os.path.join(self.m_blddir, '.wscript-trybuild')
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

		env.setup(env['tools'])

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

	def addDefine(self, define, value):
		"""store a single define and its state into an internal list 
		   for later writing to a config header file"""	
		self.defines[define] = value
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

	def writeConfigHeader(self, configfile='config.h'):
		"""save the defines into a file"""
		if configfile=='': configfile = self.configheader

		try:
			# just in case the path is 'something/blah.h' (under the builddir)
			lst=configfile.split('/')
			lst = lst[:len(lst)-1]
			os.mkdir( os.sep.join(lst) )
		except:
			pass

		if not self.env['_BUILDDIR_']: self.env['_BUILDDIR_']='_build_'

		dest=open(os.path.join(self.env['_BUILDDIR_'], configfile), 'w')
		dest.write('/* configuration created by waf */\n')
		for key in self.defines: 
			if self.defines[key]:
				dest.write('#define %s %s\n' % (key, self.defines[key]))
				#if addcontent:
				#	dest.write(addcontent);
			else:
				dest.write('/* #undef '+key+' */\n')
		dest.close()

	def setConfigHeader(self, header):
		"""set a config header file"""
		self.configheader = header
		pass

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

	def checkProgram(self, file, path_list=None, var=None):
		"""find an application"""
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
		ret = find_program(self.env, file, path_list)
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

	def checkTool(self, input):
		"""check if a waf tool is available"""
		if type(input) is types.ListType:
			lst = input
		else:
			lst = input.split()

		ret = True
		for i in lst:
			ret = ret and self._checkToolImpl(i)
		return ret

	def _checkToolImpl(self, tool):
		define = 'HAVE_'+tool.upper().replace('.','_').replace('+','P')

		if self.isDefined(define):
			return self.getDefine(define)

		try:
			file,name,desc = imp.find_module(tool, Params.g_tooldir)
		except: 
			print "no tool named '" + tool + "' found"
			return 
		module = imp.load_module(tool,file,name,desc)
		ret = int(module.detect(self))
		self.addDefine(define, ret)
		self.env.appendValue('tools',tool)
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

		global maxlen
		dist = len(sr)
		if dist > maxlen:
			maxlen = dist+1

		if dist < maxlen:
			diff = maxlen - dist
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

		global maxlen
		dist = len(sr)
		if dist > maxlen:
			maxlen = dist+1

		if dist < maxlen:
			diff = maxlen - dist
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


	def checkPkg(self, modname, destvar='', vnum='', pkgpath='', pkgbin=''):
		if not destvar: destvar = modname.upper()

		if not pkgbin: pkgbin='pkg-config'
		if pkgpath: pkgpath='PKG_CONFIG_PATH='+pkgpath
		pkgcom = '%s %s' % (pkgpath, pkgbin)
		try:
			if vnum:
				ret = os.popen("%s --atleast-version=%s %s" % (pkgcom, vnum, modname)).close()
				self.checkMessage('%s >= %s' % (modname, vnum), '', not ret)
				if ret: raise "error"
			else:
				ret = os.popen("%s %s" % (pkgcom, modname)).close()
				self.checkMessage('%s ' % (modname), '', not ret)
				if ret: raise "error"
			self.env['CCFLAGS_'+destvar]   = os.popen('%s --cflags %s' % (pkgcom, modname)).read().strip()
			self.env['CXXFLAGS_'+destvar]  = os.popen('%s --cflags %s' % (pkgcom, modname)).read().strip()
			#self.env['LINKFLAGS_'+destvar] = os.popen('%s --libs %s' % (pkgcom, modname)).read().strip()
			self.addDefine('HAVE_'+destvar, 1)

			# Store the library names:
			modlibs = os.popen('%s --libs-only-l %s' % (pkgcom, modname)).read().strip().split()
			self.env['LIB_'+destvar] = []
			for item in modlibs:
				self.env['LIB_'+destvar].append( item[2:] ) #Strip '-l'

			# Store the library paths:
			modpaths = os.popen('%s --libs-only-L %s' % (pkgcom, modname)).read().strip().split()
			self.env['LIBPATH_'+destvar] = []
			for item in modpaths:
				self.env['LIBPATH_'+destvar].append( item[2:] ) #Strip '-l'
		except:
			self.addDefine('HAVE_'+destvar, 0)
			return 0
		return 1

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

