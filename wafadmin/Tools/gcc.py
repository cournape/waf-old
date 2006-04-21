#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import Utils, Action, Params

# tool specific setup
# is called when a build process is started 
def setup(env):
	# by default - when loading a compiler tool, it sets CC_SOURCE_TARGET to a string
	# like '%s -o %s' which becomes 'file.c -o file.o' when called
	cc_vardeps    = ['CC', 'CCFLAGS', 'CCFLAGS_' + Params.g_options.debug_level, '_CPPDEFFLAGS', '_CINCFLAGS', 'CC_ST']
	Action.GenAction('cc', cc_vardeps)

	# on windows libraries must be defined after the object files 
	link_vardeps   = ['LINK', 'LINK_ST', 'LINKFLAGS', 'LINKFLAGS_' + Params.g_options.debug_level, '_LIBDIRFLAGS', '_LIBFLAGS']
	action = Action.GenAction('cc_link', link_vardeps)

def detect(conf):
	cc = conf.checkProgram('cc')
	if not cc:
		return 0;

	comp = conf.checkProgram('gcc')
	if not comp:
		return 0;

	# gcc requires ar for static libs
	if not conf.checkTool('ar'):
		Utils.error('gcc needs ar - not found')
		return 0

	# preprocessor (what is that ? ita)
	#conf.env['CPP']             = cpp

	# cc compiler
	conf.env['CC']             = comp
	conf.env['_CPPDEFFLAGS']   = ''
	conf.env['_CINCFLAGS']     = ''
	conf.env['CC_ST']          = '%s -c -o %s'
	conf.env['CPPPATH_ST']     = '-I%s' # template for adding include pathes

	# compiler debug levels
	conf.env['CCFLAGS'] = []
	conf.env['CCFLAGS_OPTIMIZED']  = ['-O2']
	conf.env['CCFLAGS_RELEASE']    = ['-O2']
	conf.env['CCFLAGS_DEBUG']      = ['-g', '-DDEBUG']
	conf.env['CCFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']
		
	# linker	
	conf.env['LINK']            = comp
	conf.env['LIB']             = []
	conf.env['LINK_ST']         = '%s -o %s'
	conf.env['LIB_ST']          = '-l%s'	# template for adding libs
	conf.env['LIBPATH_ST']      = '-L%s' # template for adding libpathes
	conf.env['_LIBDIRFLAGS']    = ''
	conf.env['_LIBFLAGS']       = ''

	# linker debug levels
	conf.env['LINKFLAGS'] = []
	conf.env['LINKFLAGS_OPTIMIZED'] = ['-s']
	conf.env['LINKFLAGS_RELEASE'] = ['-s']
	conf.env['LINKFLAGS_DEBUG'] = ['-g']
	conf.env['LINKFLAGS_ULTRADEBUG'] = ['-g3']

	if sys.platform == "win32": 
		if not conf.env['PREFIX']: conf.env['PREFIX']='c:\\'
	
		# shared library 
		conf.env['shlib_CCFLAGS']  = ['']
		conf.env['shlib_LINKFLAGS'] = ['-shared']
		conf.env['shlib_obj_ext']   = ['.o']
		conf.env['shlib_PREFIX']    = 'lib'
		conf.env['shlib_SUFFIX']    = '.dll'
		conf.env['shlib_IMPLIB_SUFFIX'] = ['.dll.a']
	
		# static library
		conf.env['staticlib_LINKFLAGS'] = ['']
		conf.env['staticlib_obj_ext'] = ['.o']
		conf.env['staticlib_PREFIX']= 'lib'
		conf.env['staticlib_SUFFIX']= '.a'

		# program 
		conf.env['program_obj_ext'] = ['.o']
		conf.env['program_SUFFIX']  = '.exe'

	else:
		if not conf.env['PREFIX']: conf.env['PREFIX'] = '/usr'
	
		# shared library 
		conf.env['shlib_CCFLAGS']  = ['-fPIC', '-DPIC']
		conf.env['shlib_LINKFLAGS'] = ['-shared']
		conf.env['shlib_obj_ext']   = ['.os']
		conf.env['shlib_PREFIX']    = 'lib'
		conf.env['shlib_SUFFIX']    = '.so'
	
		# static lib
		conf.env['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
		conf.env['staticlib_obj_ext'] = ['.o']
		conf.env['staticlib_PREFIX']= 'lib'
		conf.env['staticlib_SUFFIX']= '.a'

		# program 
		conf.env['program_obj_ext'] = ['.o']
		conf.env['program_SUFFIX']  = ''

	return 1
