#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os,sys,string, types, imp
import Params, Tools

def trace(msg):
	Params.trace(msg, 'Environment')
def debug(msg):
	Params.debug(msg, 'Environment')
def error(msg):
	Params.error(msg, 'Environment')

# a safe-to-use dictionary
class Environment:
	def __init__(self):
		self.m_table={}
		self.m_overriden={}
		self.tooldir = [os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),'wafadmin','Tools')]
		# may be there is a better place for this
		if sys.platform == "win32":
			self.setValue('WINDOWS',1)

	def copy2(self):
		newenv = Environment()
		newenv.m_overriden = self.m_table # share the same data

	def copy(self):
		newenv = Environment()
		tb = newenv.m_overriden
		for key in self.m_table.keys()+self.m_overriden.keys():
			try :
				tb[key] = self.m_table[key]
			except:
				tb[key] = self.m_overriden[key]
		return newenv

	# detect tools in configure process 
	# this method is really cool (ita)
	# env.detect('GCC') is equivalent to import Tools.GCC\nTools.GCC.detect(env)
	def detect(self, tool):
		if type(tool) is types.ListType:
			for i in tool: self.detect(i)
			return

		self.appendValue('tools',tool)
		try:
			file,name,desc = imp.find_module(tool,self.tooldir)
		except: 
			print "no tool named '" + tool + "' found"
			return 
		module = imp.load_module(tool,file,name,desc)
		module.detect(self)

	# setup tools for build process
	def setup(self, tool):
		if type(tool) is types.ListType:
			for i in tool: self.setup(i)
			return
	
		file,name,desc = imp.find_module(tool,self.tooldir)
		module = imp.load_module(tool,file,name,desc)
		try:
			module.setup(self)
		except:
			print "setup function missing in tool: " + tool

	def __str__(self):
		return "environment table\n"+str(self.m_table)+"\noverriden\n"+str(self.m_overriden)

	def __getitem__(self, key):
		return self.getValue(key)
	def __setitem__(self, key, val):
		self.setValue(key, val)

	# get down by only one level, there is no need to fetch values very far
	# but copy is handled properly

	def setValue(self, var, value):
		self.m_table[var]=value
	def getValue(self, var):
		try:
			return self.m_table[var]
		except:
			if var in self.m_overriden: return self.m_overriden[var]
			return []
	def appendValue(self, var, value):
		if not var in self.m_table:
			try:
				self.m_table[var]    = []+self.m_overriden[var]
			except:
				self.m_table[var] = []
		if type(value) is types.ListType: self.m_table[var] += value
		else: self.m_table[var].append(value)
	def prependValue(self, var, value):
		if not var in self.m_table:
			try: self.m_table[var]    = []+self.m_overriden[var]
			except: self.m_table[var] = []
		self.m_table[var] = [value]+self.m_table[var]
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

