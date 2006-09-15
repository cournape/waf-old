#! /usr/bin/env python
# encoding: utf-8
# Peter Soetens, 2006

import os
import Action, Object
from Params import set_globals

set_globals('TAO_IDL_EXT', ['.idl'])

# This function is called when the class cppobj encounters a '.idl' file
def tao_idl_file(obj, node):

	# this function is used several times
	fi = obj.file_in

	# we create the task for the idl file
	# idl compiler generates from one input file 4 output files.
	idltask = obj.create_task('idl', nice=4)

	#idltask.m_scanner = Scan.g_c_scanner
	#idltask.m_scanner_params = dir_lst

	# Setup the inputs/outputs
	base, ext = os.path.splitext(node.m_name)
	idltask.m_inputs  = fi(node.m_name)
	idltask.m_outputs = fi(base+obj.env['idl_SH']) + fi(base+obj.env['idl_SCPP']) + fi(base+obj.env['idl_CH']) + fi(base+obj.env['idl_CCPP'])

	# now we also add the task that creates the object file ('.o' file)
	cpptask = obj.create_task('cpp')
	cpptask.m_inputs  = [idltask.m_outputs[1]]
	cpptask.m_outputs = fi(base+'S.o')
	cpptask.m_run_after = [idltask]

	cpptask = obj.create_task('cpp')
	cpptask.m_inputs  = [idltask.m_outputs[3]]
	cpptask.m_outputs = fi(base+'C.o')
	cpptask.m_run_after = [idltask]

# first, we define an action to build something
"""
tao_idl_vardeps    = ['IDL', 'IDL_DEFFLAGS', 'IDL_INCFLAGS','IDL_ST','ACE_ROOT','TAO_ROOT']
def tao_idl_build(task):
	tgt = task.m_inputs[0].cd_to()
	src = task.m_inputs[0].bldpath()
	cmd = '%s %s %s -o %s' % (task.m_env['IDL'], task.m_env['IDLPATH_ST'] % task.m_env['IDL_INCPATH'], src, tgt)
	return Runner.exec_command(cmd)
"""

# This function is called when a build process is started 
def setup(env):
	# TODO define the vars
	Action.simple_action('idl', '${IDL} ${IDL_INCLUDES} ${SRC} -o ${SRC[0].m_parent.bldpath(env)}', color='BLUE')

	# register the hook for use with cppobj
	Object.hook('cpp', 'TAO_IDL_EXT', tao_idl_file)

# tool detection and initial setup 
# is called when a configure process is started, 
# the values are cached for further build processes
def detect(conf):

	#The first part detects if the TAO environment is setup correctly
	acedir = os.getenv('ACE_ROOT')
	taodir = os.getenv('TAO_ROOT')

	# if ACE_ROOT was given, search tao_idl in ACE_ROOT, else
	# fall back to system paths.
	if acedir:
		acebindir = [os.path.join(acedir,'bin')]
		idl = conf.find_program('tao_idl', acebindir)
		if not conf.check_header('ace/ACE.h', pathlst=[ os.path.join(acedir,'include') ]):
			return 0
	else:
		if not conf.check_header('ace/ACE.h'):
			return 0
		
	if not idl:
		idl = conf.find_program('tao_idl')
		if not idl:
			return 0
	if taodir:
		if not conf.check_header('tao/corba.h', pathlst=[ os.path.join(acedir,'include'), os.path.join(taodir,'include') ]):
			return 0
	else:
		if not conf.check_header('tao/corba.h'):
			return 0
	
	# Check if the headers are present:
# 	if conf.checkPkg('TAO'):
# 		# OK, everything present.
# 		print 'TAO'
# 	else:

# 	if conf.checkPkg('ACE'):
# 		# OK, ACE found
# 		print 'ACE'
# 	else:
		
	conf.env['IDL']             = idl
	conf.env['IDL_DEFFLAGS']    = ''
	conf.env['IDL_INCPATH']     = os.path.join(taodir,'orbsvcs')
	conf.env['IDL_INCLUDES']     = '-I%s' % conf.env['IDL_INCPATH']
	# Seems to be unused by waf:
	#conf.env.appendValue('CPPPATH', conf.env['IDL_INCPATH'])

	# tao_idl generated suffixes
	conf.env['idl_SH'] = 'S.h'
	conf.env['idl_SCPP'] = 'S.cpp'
	conf.env['idl_CH'] = 'C.h'
	conf.env['idl_CCPP'] = 'C.cpp'

	# include / library paths
	if acedir:
		libdir = os.path.join(acedir, 'lib')
		conf.env['ACE_ROOT'] = acedir
		conf.env['LIBPATH_ACE']  = [ libdir ]
		conf.env['CPPPATH_ACE']  = [ conf.env['ACE_ROOT'] ]
	
        conf.env['LIB_ACE']          = ['ACE']

	# only add include paths if TAO_ROOT was set.
	if taodir:
		conf.env['TAO_ROOT'] = taodir
		conf.env['CPPPATH_TAO']      = [ conf.env['TAO_ROOT'] ]
		conf.env['CPPPATH_ORBSVCS']  = [ conf.env['TAO_ROOT']+'/orbsvcs' ]
		conf.env['CPPPATH_TAO_NAMING']  = [ conf.env['CPPPATH_ORBSVCS' ][0] ]
	
        conf.env['LIB_TAO']          = ['TAO']
        conf.env['LIB_TAOPOA']       = ['TAO_PortableServer']
        conf.env['LIB_COSNAMING']    = ['TAO_CosNaming']

	return 1

