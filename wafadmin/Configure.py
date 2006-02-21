#! /usr/bin/env python
# encoding: utf-8

import os, types, sys, string
import Params
import Environment

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

	def execute(self):
		env = Environment.Environment()
		sys.path.append('bksys')
		for module in self.modules:
			module = __import__(module)
			if module.exists(env):
				env = module.generate(env)
		filename = env.getValue('OS') + '.env'
		env.store(filename)

	
	def setConfigHeader(self, header):
		"""set a config header file"""
		pass

	def checkHeaders(self, header, headers):
		"""find a header"""
		pass

	def checkFunction(self, function, header = None, language = None):
		"""find a function"""
		if not header:
			header = """
#ifdef __cplusplus
extern "C"
#endif
char %s();""" % function

	def checkProgram(self, file, path_list=None):
		"""find an application"""
		ret = find_program(self.config, file, path_list=None)
		self.checkMessage('program',file,ret,ret)
		return ret

	def checkLibrary(self, header, headers):
		"""find a library"""
		pass

	def checkTool(self,tool):
		"""check if a waf tool is available"""
		return self.config.detect(tool)
			
	def checkModule(self,tool):
		"""check if a tool is given"""
		pass

	def error(self,lenv,module,str):
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
	


