#! /usr/bin/env python
# encoding: utf-8
# Matthias Jahn <jahn.matthias@freenet.de>, 2007 (pmarat)

import os, sys, imp, types
import optparse
import Utils, Action, Params, checks, Configure

def __detect_platform():
	"""Stolen from scons"""
	osname = os.name
	if osname == 'java':
		osname = os._osType
	if osname == 'posix':
		if sys.platform == 'cygwin':
			return 'cygwin'
		if str.find(sys.platform, 'linux') != -1:
			return 'linux'
		if str.find(sys.platform, 'irix') != -1:
			return 'irix'
		if str.find(sys.platform, 'sunos') != -1:
			return 'sunos'
		if str.find(sys.platform, 'hp-ux') != -1:
			return 'hpux'
		if str.find(sys.platform, 'aix') != -1:
			return 'aix'
		if str.find(sys.platform, 'darwin') != -1:
			return 'darwin'
		return 'posix'
	elif os.name == 'os2':
		return 'os2'
	else:
		return sys.platform

def __list_possible_compiler():
	plattform = __detect_platform()
	c_compiler = {
		"win32": ['msvc', 'g++'],
		"cygwin": ['g++'],
		"darwin": ['g++'],
		"aix5": ['g++'],
		"linux": ['g++', 'sunc++'],
		"sunos": ['sunc++', 'g++'],
		"irix": ['g++'],
		"hpux":['g++'],
		"default": ['g++']
	}
	try:
		return(c_compiler[plattform])
	except:
		return(c_compiler["default"])
		
	
def setup(env):
	pass

def detect(conf):
	test_for_compiler = Params.g_options.check_cxx_compiler
	for cxx_compiler in test_for_compiler.split():
		if conf.check_tool(cxx_compiler):
			conf.check_message("%s" %cxx_compiler, '', True)
			return (1)
		conf.check_message("%s" %cxx_compiler, '', False)
	return (0)

def set_options(opt):
	test_for_compiler = str(" ").join(__list_possible_compiler())
	cxx_compiler_opts = opt.parser.add_option_group("C++ Compiler Options")
	try:
		cc_compiler_opts.add_option('--check-cxx-compiler', default="%s" % test_for_compiler,
			help='On this Plattform (%s) following C++ Compiler will be checked default: "%s"' % 
								(__detect_platform(), test_for_compiler),
			dest="check_cxx_compiler")
	except optparse.OptionConflictError:
		# the g++ tool might have added that option already
		pass

	def l_tool_options(opts, tool, tooldir=None):
		if type(tool) is types.ListType:
			for i in tool: self.tool_options(i, tooldir)
			return

		if not tooldir: tooldir = Params.g_tooldir
		tooldir = Utils.to_list(tooldir)
		try:
			file,name,desc = imp.find_module(tool, tooldir)
		except:
			error("no tool named '%s' found" % tool)
			return
		module = imp.load_module(tool,file,name,desc)
		try:
			module.set_options(opts)
		except:
			warning("tool %s has no function set_options or set_options failed" % tool)
			pass

	for cxx_compiler in test_for_compiler.split():
		l_tool_options(cxx_compiler_opts, '%s' % cxx_compiler)

