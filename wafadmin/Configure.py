#! /usr/bin/env python
# encoding: utf-8

import os, types, sys, string
import Params, Environment

def find_path(file, path_list):
	for dir in path_list:
		if os.path.exists( os.path.join(dir, file) ):
			return dir
	return ''

def find_file(file, path_list):
	for dir in path_list:
		if os.path.exists( os.path.join(dir, file) ):
			return os.path.join(dir, file)
	return ''

def find_file_ext(file, path_list):
	import os, fnmatch;
	for p in path_list:
		for path, subdirs, files in os.walk( p ):
			for name in files:
				if fnmatch.fnmatch( name, file ):
					return path
	return ''

def find_program(lenv, file, path_list=None):
	if lenv['WINDOWS']:
		file += '.exe'
	if path_list is None: 
		try:
			path_list = os.environ['PATH']
		except KeyError:
			return None
		if type(path_list) is types.StringType: 
			path_list = string.split(path_list, os.pathsep)

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
	
	def __init__(self, config=None):
		if not config:
			self.config = Environment.Environment()
		else:
			self.config = config
		for key in self.config.m_table:
			if key == 'modules':
				self.modules = self.config[key].split()
		self.defines = {}
		self.configheader = 'config.h'

	def __del__(self):
		if not self.config.getValue('tools'):
			self.error('you should add at least a checkTool() call in your sconfigure, otherwise you cannot build anything')

	def execute(self):
		env = Environment.Environment()
		sys.path.append('bksys')
		for module in self.modules:
			module = __import__(module)
			if module.exists(env):
				env = module.generate(env)
		filename = env.getValue('OS') + '.env'
		env.store(filename)

	def addDefine(self, define, value):
		"""store a single define and its state into an internal list 
		   for later writing to a config header file"""	
		self.defines[define] = value
	
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

	def writeConfigHeader(self, configfile=''):
		"""save the defines into a file"""
		self.config['_BUILDDIR_'] = ''
		if configfile=='':
			configfile = self.configheader
		dest=open(os.path.join(self.config['_BUILDDIR_'], configfile), 'w')
		dest.write('/* configuration created by waf */\n')
		for key in self.defines: 
			if self.defines[key]:
				dest.write('#define '+key+' 1\n')
				#if addcontent:
				#	dest.write(addcontent);
			else:
				dest.write('/* #undef '+key+' */\n')
		dest.close()

	def setConfigHeader(self, header):
		"""set a config header file"""
		self.configheader = header
		pass

	def checkHeader(self, header, define=''):
		"""find a header"""
		if define == '':
			define = 'HAVE_'+header.upper().replace('.','_')

		if self.isDefined(define):
			return self.getDefine(define)
	
		is_found = 0 #=check_if_header_isavailable
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
char %s();""" % function

		is_found = 0 #=check_if_function_isavailable
		self.checkMessage('function',function,is_found)
		self.addDefine(define,is_found)
		return is_found

	def checkProgram(self, file, path_list=None):
		"""find an application"""
		ret = find_program(self.config, file, path_list=None)
		self.checkMessage('program',file,ret,ret)
		return ret

	def checkLibrary(self, libname, headers=None,define=''):
		"""find a library"""
		if define == '':
			define = 'HAVE_'+libname.upper().replace('.','_')

		if self.isDefined(define):
			return self.getDefine(define)

		is_found = 0 #=check_if_library_isavailable
		self.checkMessage('library',libname,is_found)
		self.addDefine(define,is_found)
		return is_found


	def checkTool(self,tool):
		"""check if a waf tool is available"""
		return self.config.detect(tool)
			
	def checkModule(self,tool):
		"""check if a a user provided module is given"""
		pass

	def error(self,module,str):
		"""prints an error message"""
		print "configuration error: " + module + " " + str

	def store(self, file):
		"""save config results into a cache file"""
		return self.config.store(file)

	def checkMessage(self,type,msg,state,option=''):
		"""print an checking message. This function is used by other checking functions"""
		str = 'checking for ' + type + ' ' + msg
		if state:
			str += ': found ' + option
		else:
			str += ': not found'
		print str
		

	def detect(self,tool):
		"""deprecated, replaced by checkTool"""
		return self.config.detect(tool)
	


