#! /usr/bin/env python
# encoding: utf-8

import os, types, sys, string, imp
import Params, Environment, Runner, Build, Utils
from Params import debug, error, trace, fatal

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
	def __init__(self, env=None):
		#for key in self.env.m_table:
		#	if key == 'modules':
		#		self.modules = self.env[key].split()

		self.env       = None
		self.m_envname = ''

		self.m_allenvs = {}
		self.defines = {}
		self.configheader = 'config.h'
		self.cwd  = os.getcwd()

		self.setenv('default')


	def __del__(self):
		if not self.env['tools']:
			self.error('you should add at least a checkTool() call in your wscript, otherwise you cannot build anything')

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

	def TryBuild(self, code, options='', pathlst=[]):
		"""Check if a program could be build, returns 0 if no errors 
		This method is currently platform specific and has to be made platform 
		independent, probably by refactoring the c++ or cc build engine
		"""

		dir = os.path.join(Utils.g_module.blddir, '.wscript-trybuild')
		bdir = os.path.join( dir, '_build_')
		try: os.mkdir(dir)
		except: pass
		try: os.mkdir(bdir)
		except: pass

		dest=open(os.path.join(dir, 'test.c'), 'w')
		dest.write(code)
		dest.close()

		env = self.env.copy()
		Utils.reset()

		bld = Build.Build()
		bld.load( bdir )
		bld.set_srcdir(dir)
		bld.load_dirs(dir, bdir )
		bld.m_allenvs['default'] = env

		bld.m_curdirnode = Params.g_build.m_tree.m_srcnode

		back=os.path.abspath('.')
		os.chdir(dir)

		env.setup(env['tools'])

		# TODO for the moment it is c++, in the future it will be c
		# and then we may need other languages here too
		import cpp
		obj=cpp.cppobj('program')
		obj.source = 'test.c'
		obj.target = 'test'

		envcopy = bld.m_allenvs['default'].copy()
		for p in pathlst:
			envcopy['CPPFLAGS'].append(' -I%s ' % p)

		try:
			ret = bld.compile()
		except:
			ret = 1
			raise

		os.chdir(back)
		Utils.reset()
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

	def checkHeader(self, header, define='', pathlst=[] ):
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
int main()
{
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
int main()
{
	%s();
}
""" % function

		is_found = int(not self.TryBuild(headers + code))
		self.checkMessage('function',function,is_found)
		self.addDefine(define,is_found)
		return is_found

	def checkProgram(self, file, path_list=None):
		"""find an application"""
		#print path_list
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
int main()
{
	%s();
}
""" % funcname
		elif not headers and not funcname: 
			headers = ""
			code = """
int main() {}
"""
		else:
			code = """
int main()
{
	%s();
}
""" % funcname
			
		# TODO setup libpath 
		libpath = "."
		is_found = int(not self.TryBuild(headers + code, 
				pathlst = self.env['LIBPATH_ST'] % libpath,
				uselib=uselib ))
		self.checkMessage('library',libname,is_found)
		self.addDefine(define,is_found)
		return is_found

	def checkTool(self,tool):
		"""check if a waf tool is available"""
		if type(tool) is types.ListType:
			for i in tool: self.checkTool(i)
			return

		define = 'HAVE_'+tool.upper().replace('.','_').replace('+','P')

		if self.isDefined(define):
			return self.getDefine(define)

		try:
			file,name,desc = imp.find_module(tool, Params.g_tooldir)
		except: 
			print "no tool named '" + tool + "' found"
			return 
		module = int(imp.load_module(tool,file,name,desc))
		ret = module.detect(self)
		self.addDefine(define, ret)
		self.env.appendValue('tools',tool)
		return ret
			
	def checkModule(self,tool):
		"""check if a a user provided module is given"""
		pass

	def error(self,module,str=''):
		"""prints an error message"""
		print "configuration error: " + module + " " + str

	def store(self, file=''):
		"""save config results into a cache file"""
		try: os.makedirs(Params.g_cachedir)
		except OSError: pass

		if not self.m_allenvs:
			fatal("nothing to store in Configure !")
		for key in self.m_allenvs:
			tmpenv = self.m_allenvs[key]
			self.env.store(os.path.join(Params.g_cachedir, key+'.cache.py'))

	def checkMessage(self,type,msg,state,option=''):
		"""print an checking message. This function is used by other checking functions"""
		sr = 'Checking for ' + type + ' ' + msg
		sp = '                                                 '
		l = len(sr)
		print sr,
		if l<35: print sp[:33-l],':',

		p=Params.pprint
		if state: p('GREEN', 'ok ' + option)
		else: p('YELLOW', 'not found')
		

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

# syntactic sugar
def create_config():
	return Configure()

