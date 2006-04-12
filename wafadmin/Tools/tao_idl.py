#! /usr/bin/env python
# encoding: utf-8
# Peter Soetens, 2006

import os, sys, imp
import Utils,Action,Params,Configure

def tao_idl_file(cppobj, node):
	# create the task for the idl file
	idltask = cppobj.create_task('idl', cppobj.env)

	idltask.m_scanner = Scan.c_scanner
	idltask.m_scanner_params = dir_lst

	# idl compiler generates from one input file 4 output files.
	idltask.m_inputs  = self.file_in(filename)
	idltask.m_outputs = self.file_in(base+ch_ext) + self.file_in(base+ccpp_ext) + self.file_in(base+sh_ext) + self.file_in(base+scpp_ext)
	#idltask.m_use_outputdir = 1 # No, task classes are already too big
	idltasks.append(idltask)


# tool specific setup
# is called when a build process is started 
def setup(env):
	# by default - when loading a compiler tool, it sets CC_SOURCE_TARGET to a string
	# like '%s -o %s' which becomes 'file.cpp -o file.o' when called
	idl_vardeps    = ['IDL', '_IDLDEFFLAGS', '_IDLINCFLAGS','IDL_ST']
	Action.GenAction('idl', idl_vardeps)

	if not sys.platform == "win32":
		Params.g_colors['idl']='\033[92m'

	# As last, load 'idl' language
	try:
		file,name,desc = imp.find_module('idl', Params.g_langdir)
	except: 
		print "no language 'idl' for tool 'tao_idl' found in ", Params.g_langdir
		raise
	module = imp.load_module('idl', file, name, desc)

	if not Params.g_handlers['cppobj']: Params.g_handlers['cppobj']={}
	if not Params.g_handlers['cppobj']['.idl'] = idlfunc

# tool detection and initial setup 
# is called when a configure process is started, 
# the values are cached for further build processes
def detect(conf):

	idl = conf.checkProgram('tao_idl')
	if not idl:
		return 0;

	# idl compiler
	conf.env['IDL']             = idl
	conf.env['_IDLDEFFLAGS']    = ''
	conf.env['_IDLINCFLAGS']    = ''
	conf.env['IDL_ST']          = '%s -o %s'
	conf.env['IDLPATH_ST']      = '-I%s' # template for adding include pathes

	if not conf.env['DESTDIR']: conf.env['DESTDIR']=''
	
	# tao_idl generated suffixes
	conf.env['idl_SH'] = ['S.h']
	conf.env['idl_SCPP'] = ['S.cpp']
	conf.env['idl_CH'] = ['C.h']
	conf.env['idl_CCPP'] = ['C.cpp']

	# hmmm this is usually set elsewhere
	if sys.platform == "win32": 
		if not conf.env['PREFIX']: conf.env['PREFIX']='c:\\'
	elif sys.platform == 'cygwin':
		if not conf.env['PREFIX']: conf.env['PREFIX']='/cygdrive/c/'
	else:
		if not conf.env['PREFIX']: conf.env['PREFIX'] = '/usr'

	return 1



