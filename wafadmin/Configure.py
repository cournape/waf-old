#! /usr/bin/env python
# encoding: utf-8

import os
import sys
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

def find_program(lenv, file, path_list):
	if lenv['WINDOWS']:
		file += '.exe'
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

	def __init__(self, config):
		for key in config.keys():
			if key == 'modules':
				self.modules = config[key].split()

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
		pass

	def checkFunction(self, function, header = None, language = None):
		if not header:
			header = """
#ifdef __cplusplus
extern "C"
#endif
char %s();""" % function

		
	def checkHeaders(self, header, headers):
		pass





