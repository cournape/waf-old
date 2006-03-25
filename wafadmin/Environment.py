#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os,sys,string, types, imp
import Params, Tools
from Params import debug, error, trace, fatal

# a safe-to-use dictionary
class Environment:
	def __init__(self):
		self.m_table={}

		# may be there is a better place for this
		if sys.platform == "win32":
			self.setValue('WINDOWS',1)

	def copy(self):
		newenv = Environment()
		newenv.m_table = self.m_table.copy()
		return newenv

	# setup tools for build process
	def setup(self, tool):
		if type(tool) is types.ListType:
			for i in tool: self.setup(i)
			return
	
		file,name,desc = imp.find_module(tool, Params.g_tooldir)
		module = imp.load_module(tool,file,name,desc)
		try:
			module.setup(self)
		except:
			print "setup function missing in tool: " + tool
		if file: file.close()

	def __str__(self):
		return "environment table\n"+str(self.m_table)+"\noverriden\n"+str(self.m_overriden)

	def __getitem__(self, key):
		try: return self.m_table[key]
		except: return []
	def __setitem__(self, key, value):
		self.m_table[key] = value

	# to be deprecated
	def setValue(self, key, value):
		self.m_table[key] = value

	# to be deprecated
	def getValue(self, key):
		try: return self.m_table[key]
		except: return []

	def appendValue(self, var, value):
		if type(value) is types.ListType: val = value
		else: val = [value]

		self.m_table[var] = self.m_table[var] + value

	def prependValue(self, var, value):
		if type(value) is types.ListType: val = value
		else: val = [value]

		self.m_table[var] = value + self.m_table[var]

	def store(self, filename):
		file=open(filename, 'w')
		keys=self.m_table.keys()+self.m_overriden.keys()
		keys.sort()
		curr_key = ''

		for key in keys:
			if key==curr_key:
				next
			if key in self.m_table:
				file.write('%s = %r\n'%(key,self.m_table[key]))
			else:
				file.write('%s = %r\n'%(key,self.m_overriden[key]))
			curr_key=key
		file.close()

	def load(self, filename):
		if not os.path.isfile(filename):
			return 0
		file=open(filename, 'r')
		for line in file:
			ln = line.strip()
			if not ln or ln[0]=='#': continue
			(key,value) = string.split(ln, '=', 1)
			line = 'self.m_table["%s"] = %s'%(key.strip(), value.strip())
			exec line
		file.close()
		debug(self.m_table)
		return 1

	# set a name to this environment
	def set_alias(self, name):
		Params.g_mapping_env[name]=env

# it is possible to give names to environments in order to re-use some of them quickly
def get_alias(name):
	return Params.g_mapping_env[name]

# syntactic sugar
def create_env():
	return Environment()

